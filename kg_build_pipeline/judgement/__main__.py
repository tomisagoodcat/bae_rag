"""CLI: python -m kg_build_pipeline.judgement"""
from __future__ import annotations

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.neo4j_util import build_neo4j_driver
from kg_build_pipeline.judgement.run import run_judgement


def main() -> int:
    cfg = PipelineConfig.load()
    driver = build_neo4j_driver(cfg)
    try:
        result = run_judgement(cfg, driver, stages_run=[])
    finally:
        driver.close()
    path = result.get("log_path")
    print(f"judgement log: {path}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
