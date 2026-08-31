"""E2E verify mid quality gate targeted re-extract (doc_04)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.neo4j_util import build_neo4j_driver
from kg_build_pipeline.src.runner import PipelineRunner

DOC = "doc_04_松江区消费环节大米重金属污染状况及安全评价_石春红.md"
OUTPUT = REPO_ROOT / "kg_build_pipeline" / "output" / "mid_quality_gate_targeted_verify.json"


def _graph_audit(driver, database: str) -> dict:
    with driver.session(database=database) as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        se_claim = session.run(
            """
            MATCH (se)-[r]->(cl)
            WHERE 'whu_ScienceEvidence' IN labels(se)
              AND 'mp_Claim' IN labels(cl)
              AND type(r) IN ['mp_supports', 'mp_challenges']
            RETURN count(r) AS c
            """
        ).single()["c"]
        se_sg = session.run(
            """
            MATCH (se)-[r]->(sg)
            WHERE 'whu_ScienceEvidence' IN labels(se)
              AND 'whu_SupportGraph' IN labels(sg)
              AND type(r) IN ['mp_supports', 'mp_challenges']
            RETURN count(r) AS c
            """
        ).single()["c"]
    return {"nodes": nodes, "se_to_claim": se_claim, "se_to_support_graph": se_sg}


def main() -> int:
    cfg = PipelineConfig.load()
    cfg.build_kg["selected_files"] = [DOC]
    for stage in list(cfg.stages.keys()):
        cfg.stages[stage] = stage in {
            "clear_neo4j",
            "build_kg",
            "mid_quality_gate",
        }

    runner = PipelineRunner(cfg, only=["clear_neo4j", "build_kg", "mid_quality_gate"])
    results = runner.run()

    driver = build_neo4j_driver(cfg)
    try:
        audit = _graph_audit(driver, cfg.neo4j_database)
    finally:
        driver.close()

    gate = results.get("mid_quality_gate") or results.get("stages", {}).get(
        "mid_quality_gate", {}
    )
    out = {
        "document": DOC,
        "graph_audit": audit,
        "mid_quality_gate": gate,
        "summary": results.get("summary", {}),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
