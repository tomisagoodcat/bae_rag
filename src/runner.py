"""Pipeline orchestrator: stage order, skip flags, summary stats."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.schema_loader import validate_schema_dir

STAGE_ORDER = [
    "clear_neo4j",
    "build_kg",
    "subgraph_annotate",
    "chunk_merge",
    "entity_merge",
    "pagerank",
    "metapath",
]


def _build_driver(cfg: PipelineConfig) -> Driver:
    from kg_build_pipeline.src.neo4j_util import build_neo4j_driver

    return build_neo4j_driver(cfg)


class PipelineRunner:
    def __init__(self, cfg: PipelineConfig, skip: Optional[List[str]] = None, only: Optional[List[str]] = None):
        self.cfg = cfg
        self.skip = set(skip or [])
        self.only = set(only) if only else None
        self.results: Dict[str, Any] = {}

    def _should_run(self, stage: str) -> bool:
        if self.only is not None and stage not in self.only:
            return False
        if stage in self.skip:
            return False
        return self.cfg.stage_enabled(stage)

    def run(self) -> Dict[str, Any]:
        print("Validating schema...")
        validate_schema_dir(self.cfg.schema_dir)

        driver: Driver | None = None
        try:
            if any(self._should_run(s) for s in STAGE_ORDER if s != "clear_neo4j"):
                driver = _build_driver(self.cfg)
                driver.verify_connectivity()

            if self._should_run("clear_neo4j"):
                print("\n=== clear_neo4j ===")
                from kg_build_pipeline.src.neo4j_util import clear_neo4j

                d = driver or _build_driver(self.cfg)
                clear_neo4j(d, self.cfg.neo4j_database)
                if driver is None:
                    d.close()
                self.results["clear_neo4j"] = {"ok": True}

            if self._should_run("build_kg"):
                print("\n=== build_kg ===")
                from kg_build_pipeline.src.stages.build_kg import run_build_kg

                if not self.cfg.deepseek_api_key:
                    raise RuntimeError("DEEPSEEK_API_KEY required for build_kg")
                self.results["build_kg"] = run_build_kg(self.cfg, driver=driver)

            if self._should_run("subgraph_annotate"):
                print("\n=== subgraph_annotate ===")
                from kg_build_pipeline.src.stages.subgraph_annotate import run_subgraph_annotate

                assert driver is not None
                self.results["subgraph_annotate"] = run_subgraph_annotate(self.cfg, driver)

            if self._should_run("chunk_merge"):
                print("\n=== chunk_merge ===")
                from kg_build_pipeline.src.stages.chunk_merge import run_chunk_merge

                assert driver is not None
                self.results["chunk_merge"] = run_chunk_merge(driver)

            if self._should_run("entity_merge"):
                print("\n=== entity_merge ===")
                from kg_build_pipeline.src.stages.entity_merge import run_entity_merge

                assert driver is not None
                self.results["entity_merge"] = run_entity_merge(self.cfg, driver)

            if self._should_run("pagerank"):
                print("\n=== pagerank ===")
                from kg_build_pipeline.src.stages.pagerank import run_pagerank

                assert driver is not None
                self.results["pagerank"] = run_pagerank(self.cfg, driver)

            if self._should_run("metapath"):
                print("\n=== metapath ===")
                from kg_build_pipeline.src.stages.metapath import run_metapath

                assert driver is not None
                self.results["metapath"] = run_metapath(self.cfg, driver)

            if driver:
                self.results["summary"] = self._summary(driver)
            return self.results
        finally:
            if driver:
                driver.close()

    def _summary(self, driver: Driver) -> Dict[str, Any]:
        with driver.session(database=self.cfg.neo4j_database) as session:
            return {
                "nodes": session.run("MATCH (n) RETURN count(n) AS c").single()["c"],
                "relationships": session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"],
                "chunks": session.run("MATCH (c:Chunk) RETURN count(c) AS c").single()["c"],
                "metapaths": session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"],
            }
