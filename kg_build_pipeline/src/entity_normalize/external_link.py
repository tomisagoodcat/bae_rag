"""Write whu_ExternalConcept + whu_normalizedTo (exact, then constrained LLM)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set

from neo4j import Driver

from kg_build_pipeline.src.entity_normalize.audit import NormalizeAudit
from kg_build_pipeline.src.entity_normalize.constants import (
    EXCLUDED_LABELS,
    EXTERNAL_CONCEPT_LABELS,
    LABEL_EXTERNAL_CONCEPT,
    LABEL_ONTOLOGY_MAP,
    LLM_ALIGN_LABELS,
    REL_NORMALIZED_TO,
    SPECIMEN_NO_DIRECT_ONTOLOGY,
)
from kg_build_pipeline.src.entity_normalize.llm_align import AlignmentResult, LlmAligner, resolve_external_hit
from kg_build_pipeline.src.entity_normalize.ontology_lookup import OntologyIndexRegistry
from kg_build_pipeline.src.entity_normalize.text_keys import ontology_lookup_query


class ExternalConceptLinker:
    """Exact SQLite link, then optional LLM pick from index candidates (CheBI labels only)."""

    def __init__(
        self,
        driver: Driver,
        database: str,
        registry: OntologyIndexRegistry,
        audit: NormalizeAudit,
        *,
        min_query_length: int = 2,
        aligner: Optional[LlmAligner] = None,
        llm_labels: Optional[Sequence[str]] = None,
        max_candidates: int = 8,
        confidence_llm: float = 0.6,
    ):
        self.driver = driver
        self.database = database
        self.registry = registry
        self.audit = audit
        self.min_query_length = max(1, min_query_length)
        self.aligner = aligner
        self.llm_labels: Set[str] = set(llm_labels) if llm_labels else set(LLM_ALIGN_LABELS)
        self.max_candidates = max(1, int(max_candidates))
        self.confidence_llm = float(confidence_llm)

    def run(self, labels: Optional[List[str]] = None) -> Dict[str, int]:
        target_labels = sorted(labels or EXTERNAL_CONCEPT_LABELS)
        stats = {
            "linked": 0,
            "linked_exact": 0,
            "linked_llm": 0,
            "skipped_no_index": 0,
            "skipped_no_match": 0,
            "skipped_specimen_policy": 0,
            "skipped_excluded": 0,
            "by_label": {},
        }
        with self.driver.session(database=self.database) as session:
            for label in target_labels:
                if label in EXCLUDED_LABELS:
                    stats["skipped_excluded"] += 1
                    continue
                label_stats = self._link_label(session, label)
                stats["by_label"][label] = label_stats
                for k in (
                    "linked",
                    "linked_exact",
                    "linked_llm",
                    "skipped_no_index",
                    "skipped_no_match",
                    "skipped_specimen_policy",
                ):
                    stats[k] += label_stats.get(k, 0)
        self.audit.external_links_created = stats["linked"]
        self.audit.external_links_llm = stats["linked_llm"]
        self.audit.external_skipped_no_index = stats["skipped_no_index"]
        self.audit.external_skipped_no_match = stats["skipped_no_match"]
        self.audit.external_skipped_specimen_policy = stats["skipped_specimen_policy"]
        self.audit.external_skipped_excluded = stats["skipped_excluded"]
        return stats

    def _link_label(self, session, label: str) -> Dict[str, int]:
        stats = {
            "linked": 0,
            "linked_exact": 0,
            "linked_llm": 0,
            "skipped_no_index": 0,
            "skipped_no_match": 0,
            "skipped_specimen_policy": 0,
        }
        if label in SPECIMEN_NO_DIRECT_ONTOLOGY:
            rows = session.run(
                f"""
                MATCH (n:`{label}`)
                WHERE coalesce(n.whu_rejected, false) = false
                RETURN count(n) AS c
                """,
            ).single()
            count = int(rows["c"] if rows else 0)
            stats["skipped_specimen_policy"] = count
            self.audit.log("skip_specimen_direct", label=label, count=count)
            return stats

        ontology_name = LABEL_ONTOLOGY_MAP.get(label)
        if not ontology_name:
            return stats

        index = self.registry.for_ontology(ontology_name)
        if not index.available:
            stats["skipped_no_index"] += self._count_candidates(session, label)
            self.audit.log("skip_no_index", label=label, ontology=ontology_name)
            return stats

        rows = session.run(
            f"""
            MATCH (n:`{label}`)
            WHERE coalesce(n.whu_rejected, false) = false
              AND n.WHU_HASORIGINALTEXT IS NOT NULL
              AND trim(n.WHU_HASORIGINALTEXT) <> ''
            RETURN elementId(n) AS id,
                   n.WHU_HASNAME AS name,
                   trim(n.WHU_HASORIGINALTEXT) AS original_text
            """,
        ).data()

        for row in rows:
            query = ontology_lookup_query(label, row.get("original_text"))
            if not query or len(query) < self.min_query_length:
                continue
            result = resolve_external_hit(
                index,
                label=label,
                original_text=str(row.get("original_text") or ""),
                query=query,
                aligner=self.aligner,
                llm_labels=self.llm_labels,
                max_candidates=self.max_candidates,
                confidence_llm=self.confidence_llm,
            )
            if result is None:
                stats["skipped_no_match"] += 1
                continue
            created = self._write_link(session, row, result)
            if created:
                stats["linked"] += 1
                if result.match_type == "llm":
                    stats["linked_llm"] += 1
                else:
                    stats["linked_exact"] += 1
                self.audit.log(
                    "external_link",
                    entity_id=row["id"],
                    label=label,
                    query=result.query_text,
                    external_id=result.hit.external_id,
                    matched_label=result.hit.matched_label,
                    match_type=result.match_type,
                    method=result.method,
                )
        return stats

    def _count_candidates(self, session, label: str) -> int:
        row = session.run(
            f"""
            MATCH (n:`{label}`)
            WHERE coalesce(n.whu_rejected, false) = false
            RETURN count(n) AS c
            """,
        ).single()
        return int(row["c"] if row else 0)

    def _write_link(self, session, entity_row: Dict[str, Any], result: AlignmentResult) -> bool:
        hit = result.hit
        row = session.run(
            f"""
            MATCH (e) WHERE elementId(e)=$eid
            MERGE (x:{LABEL_EXTERNAL_CONCEPT} {{whu_externalID: $external_id}})
            ON CREATE SET
              x.whu_externalURI = $external_uri,
              x.skos_prefLabel = $pref_label,
              x.whu_sourceOntology = $source_ontology,
              x.WHU_HASNAME = $pref_label
            MERGE (e)-[r:{REL_NORMALIZED_TO}]->(x)
            ON CREATE SET
              r.matchType = $match_type,
              r.confidence = $confidence,
              r.method = $method,
              r.matchedLabel = $matched_label,
              r.queryText = $query_text
            RETURN elementId(x) AS xid, r.matchType AS mt
            """,
            eid=entity_row["id"],
            external_id=hit.external_id,
            external_uri=hit.external_uri,
            pref_label=hit.pref_label,
            source_ontology=hit.source_ontology,
            match_type=result.match_type,
            confidence=result.confidence,
            method=result.method,
            matched_label=hit.matched_label,
            query_text=result.query_text,
        ).single()
        return row is not None
