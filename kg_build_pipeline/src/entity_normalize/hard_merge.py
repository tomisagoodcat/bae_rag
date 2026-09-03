"""Same source_doc + WHU_HASORIGINALTEXT hard merge for whitelisted labels."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import Driver, Session

from kg_build_pipeline.src.entity_normalize.audit import NormalizeAudit
from kg_build_pipeline.src.entity_normalize.constants import HARD_MERGE_LABELS
from kg_build_pipeline.src.entity_normalize.text_keys import hard_merge_key, normalize_original_text


def unique_merge_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop duplicate elementIds (multi-chunk OPTIONAL MATCH can fan out one node)."""
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for node in nodes:
        nid = str(node.get("id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)
        unique.append(node)
    return unique


def merge_keeper_and_sources(
    nodes: List[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (keeper, other distinct nodes). Empty sources if only one real node."""
    uniq = sorted(unique_merge_nodes(nodes), key=lambda x: str(x.get("id") or ""))
    if len(uniq) <= 1:
        return None, []
    return uniq[0], uniq[1:]


class EntityHardMerger:
    """Physical merge of duplicate entities within one source_doc (ChunkMerger pattern)."""

    def __init__(self, driver: Driver, database: str, audit: NormalizeAudit):
        self.driver = driver
        self.database = database
        self.audit = audit

    def run(self, labels: Optional[List[str]] = None) -> Dict[str, int]:
        target_labels = sorted(labels or HARD_MERGE_LABELS)
        stats = {"groups_merged": 0, "nodes_removed": 0, "by_label": {}}
        with self.driver.session(database=self.database) as session:
            for label in target_labels:
                label_stats = self._merge_label(session, label)
                stats["by_label"][label] = label_stats
                stats["groups_merged"] += label_stats["groups_merged"]
                stats["nodes_removed"] += label_stats["nodes_removed"]
        self.audit.hard_merge_groups = stats["groups_merged"]
        self.audit.hard_merge_nodes_removed = stats["nodes_removed"]
        return stats

    def _merge_label(self, session: Session, label: str) -> Dict[str, int]:
        groups = self._find_duplicate_groups(session, label)
        removed = 0
        for group in groups:
            removed += self._merge_group(session, label, group)
        return {"groups_merged": len(groups), "nodes_removed": removed}

    def _find_duplicate_groups(self, session: Session, label: str) -> List[List[Dict[str, Any]]]:
        rows = session.run(
            f"""
            MATCH (n:`{label}`)
            WHERE coalesce(n.whu_rejected, false) = false
              AND n.WHU_HASORIGINALTEXT IS NOT NULL
              AND trim(n.WHU_HASORIGINALTEXT) <> ''
            WITH n,
                 trim(n.WHU_HASORIGINALTEXT) AS ot,
                 coalesce(
                   nullif(trim(n.source_doc), ''),
                   head([(c:Chunk)-[:FROM_CHUNK]-(n) |
                     CASE
                       WHEN c.filename IS NOT NULL AND c.filename ENDS WITH '.md'
                         THEN replace(c.filename, '.md', '')
                       ELSE c.filename
                     END
                   ])
                 ) AS source_doc
            WHERE source_doc IS NOT NULL AND trim(source_doc) <> ''
            WITH source_doc, ot, collect(DISTINCT {{
                id: elementId(n),
                name: n.WHU_HASNAME,
                source_doc: source_doc,
                original_text: ot
            }}) AS nodes
            WHERE size(nodes) > 1
            RETURN source_doc, ot, nodes
            ORDER BY size(nodes) DESC
            """,
        ).data()
        groups: List[List[Dict[str, Any]]] = []
        for rec in rows:
            nodes = unique_merge_nodes(rec.get("nodes") or [])
            if len(nodes) <= 1:
                continue
            sd = rec.get("source_doc")
            ot = rec.get("ot")
            key = hard_merge_key(label, str(sd or ""), str(ot or ""))
            if key is None:
                continue
            groups.append(nodes)
        return groups

    def _merge_group(
        self,
        session: Session,
        label: str,
        nodes: List[Dict[str, Any]],
    ) -> int:
        keeper, sources = merge_keeper_and_sources(nodes)
        if keeper is None:
            return 0
        removed = 0
        for src in sources:
            if src["id"] == keeper["id"]:
                continue
            self._transfer_relationships(session, src["id"], keeper["id"])
            session.run(
                "MATCH (s) WHERE elementId(s)=$sid DETACH DELETE s",
                sid=src["id"],
            )
            self.audit.log(
                "hard_merge",
                label=label,
                keeper_id=keeper["id"],
                removed_id=src["id"],
                source_doc=keeper.get("source_doc"),
                original_text=keeper.get("original_text"),
            )
            removed += 1
        return removed

    def _transfer_relationships(self, session: Session, source_id: str, target_id: str) -> None:
        self._transfer_incoming(session, source_id, target_id)
        self._transfer_outgoing(session, source_id, target_id)

    def _transfer_incoming(self, session: Session, source_id: str, target_id: str) -> None:
        incoming = session.run(
            """
            MATCH (source) WHERE elementId(source)=$sid
            MATCH (target) WHERE elementId(target)=$tid
            MATCH (other)-[r]->(source)
            WHERE elementId(other) <> $tid
            RETURN elementId(other) AS other_id, type(r) AS rel_type, properties(r) AS rel_props
            """,
            sid=source_id,
            tid=target_id,
        ).data()
        for rel in incoming:
            rel_type = rel["rel_type"]
            session.run(
                f"""
                MATCH (o) WHERE elementId(o)=$oid
                MATCH (t) WHERE elementId(t)=$tid
                MERGE (o)-[nr:`{rel_type}`]->(t)
                SET nr += $props
                """,
                oid=rel["other_id"],
                tid=target_id,
                props=rel["rel_props"] or {},
            )
        session.run(
            "MATCH (s) WHERE elementId(s)=$sid MATCH (o)-[r]->(s) DELETE r",
            sid=source_id,
        )

    def _transfer_outgoing(self, session: Session, source_id: str, target_id: str) -> None:
        outgoing = session.run(
            """
            MATCH (source) WHERE elementId(source)=$sid
            MATCH (target) WHERE elementId(target)=$tid
            MATCH (source)-[r]->(other)
            WHERE elementId(other) <> $tid
            RETURN elementId(other) AS other_id, type(r) AS rel_type, properties(r) AS rel_props
            """,
            sid=source_id,
            tid=target_id,
        ).data()
        for rel in outgoing:
            rel_type = rel["rel_type"]
            session.run(
                f"""
                MATCH (t) WHERE elementId(t)=$tid
                MATCH (o) WHERE elementId(o)=$oid
                MERGE (t)-[nr:`{rel_type}`]->(o)
                SET nr += $props
                """,
                tid=target_id,
                oid=rel["other_id"],
                props=rel["rel_props"] or {},
            )
        session.run(
            "MATCH (s) WHERE elementId(s)=$sid MATCH (s)-[r]->(o) DELETE r",
            sid=source_id,
        )
