"""Orchestrate hard merge + ExternalConcept linking."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.entity_normalize.audit import NormalizeAudit
from kg_build_pipeline.src.entity_normalize.external_link import ExternalConceptLinker
from kg_build_pipeline.src.entity_normalize.hard_merge import EntityHardMerger
from kg_build_pipeline.src.entity_normalize.llm_align import build_llm_aligner
from kg_build_pipeline.src.entity_normalize.ontology_lookup import OntologyIndexRegistry
from kg_build_pipeline.src.paths import PIPELINE_ROOT


def _index_dir(cfg: PipelineConfig) -> Path:
    raw = (cfg.entity_normalize or {}).get("ontology_index_dir")
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else PIPELINE_ROOT.parent / p
    return PIPELINE_ROOT / "resources" / "ontologies" / "_index"


def run_entity_normalize(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Stage entry: same-doc hard merge then exact ExternalConcept linking."""
    opts = cfg.entity_normalize or {}
    audit = NormalizeAudit()
    stats: Dict[str, Any] = {"audit": audit}

    hard_enabled = bool(opts.get("hard_merge", {}).get("enabled", True))
    external_enabled = bool(opts.get("external_concept", {}).get("enabled", True))
    min_query_length = int(opts.get("external_concept", {}).get("min_query_length", 2))

    registry = OntologyIndexRegistry(_index_dir(cfg))
    try:
        if hard_enabled:
            merger = EntityHardMerger(driver, cfg.neo4j_database, audit)
            stats["hard_merge"] = merger.run()
        else:
            stats["hard_merge"] = {"skipped": True}

        if external_enabled:
            ext_opts = opts.get("external_concept") or {}
            llm_labels = ext_opts.get("llm_labels") or ["whu_ChemicalEntity", "whu_Reagent"]
            linker = ExternalConceptLinker(
                driver,
                cfg.neo4j_database,
                registry,
                audit,
                min_query_length=min_query_length,
                aligner=build_llm_aligner(cfg),
                llm_labels=list(llm_labels),
                max_candidates=int(ext_opts.get("max_candidates", 8)),
                confidence_llm=float(ext_opts.get("confidence_llm", 0.6)),
            )
            stats["external_concept"] = linker.run()
        else:
            stats["external_concept"] = {"skipped": True}
    finally:
        registry.close()

    stats["audit"] = audit.to_dict()
    return stats
