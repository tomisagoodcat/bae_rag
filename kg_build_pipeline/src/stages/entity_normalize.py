"""Pipeline stage: entity_normalize (after chunk_merge, before pagerank)."""
from __future__ import annotations

from typing import Any, Dict

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.entity_normalize.runner import run_entity_normalize


def run_entity_normalize_stage(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    return run_entity_normalize(cfg, driver)
