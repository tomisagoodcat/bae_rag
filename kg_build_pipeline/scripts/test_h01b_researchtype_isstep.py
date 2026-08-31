"""T1–T4 (+ same-chunk) H01-B ResearchType ↔ isStepOfPlan guards (no Neo4j / LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.low_schema_router import schema_for_rule_ids
from kg_build_pipeline.src.stages.low_extract import (
    RESEARCHTYPE_ISSTEP_CROSSLINK_BAN,
    parent_scoped_isstep_hint,
)
from kg_build_pipeline.src.stages.low_validate import check_h01b_research_type
from kg_build_pipeline.src.stages.mid_low_linker import would_reject_cross_experiment_step


def _issues(steps):
    return check_h01b_research_type(steps)


def test_t1_biochemical_pass() -> None:
    issues = _issues(
        [
            {
                "id": "s1",
                "name": "digest",
                "labels": ["whu_ResearchStep"],
                "research_type": "BioChemical",
                "parent_labels": ["whu_BioChemical_Experiment"],
                "parent_ids": ["A"],
            }
        ]
    )
    assert issues == [], issues


def test_t2_computational_pass() -> None:
    issues = _issues(
        [
            {
                "id": "s2",
                "name": "pca",
                "labels": ["whu_ResearchStep"],
                "research_type": "Computational",
                "parent_labels": ["whu_Computational_Experiment"],
                "parent_ids": ["B"],
            }
        ]
    )
    assert issues == [], issues


def test_t3_bio_to_comp_fail() -> None:
    assert would_reject_cross_experiment_step(
        "BioChemical", "whu_Computational_Experiment"
    )
    issues = _issues(
        [
            {
                "id": "s3",
                "name": "digest",
                "labels": ["whu_ResearchStep"],
                "research_type": "BioChemical",
                "parent_labels": ["whu_Computational_Experiment"],
                "parent_ids": ["B"],
            }
        ]
    )
    assert any(i.get("rule_id") == "H01-B" for i in issues), issues


def test_t4_comp_to_bio_fail() -> None:
    assert would_reject_cross_experiment_step(
        "Computational", "whu_BioChemical_Experiment"
    )
    issues = _issues(
        [
            {
                "id": "s4",
                "name": "pca",
                "labels": ["whu_ResearchStep"],
                "research_type": "Computational",
                "parent_labels": ["whu_BioChemical_Experiment"],
                "parent_ids": ["A"],
            }
        ]
    )
    assert any(i.get("rule_id") == "H01-B" for i in issues), issues


def test_t5_same_chunk_no_cross() -> None:
    """Same chunk: S1→A and S2→B OK; S1→B / S2→A HARD."""
    ok = _issues(
        [
            {
                "id": "S1",
                "name": "digest",
                "research_type": "BioChemical",
                "parent_labels": ["whu_BioChemical_Experiment"],
                "parent_ids": ["A"],
            },
            {
                "id": "S2",
                "name": "pca",
                "research_type": "Computational",
                "parent_labels": ["whu_Computational_Experiment"],
                "parent_ids": ["B"],
            },
        ]
    )
    assert ok == [], ok

    bad = _issues(
        [
            {
                "id": "S1",
                "name": "digest",
                "research_type": "BioChemical",
                "parent_labels": ["whu_Computational_Experiment"],
                "parent_ids": ["B"],
            },
            {
                "id": "S2",
                "name": "pca",
                "research_type": "Computational",
                "parent_labels": ["whu_BioChemical_Experiment"],
                "parent_ids": ["A"],
            },
        ]
    )
    assert sum(1 for i in bad if i.get("rule_id") == "H01-B") >= 2, bad


def test_prompt_ban_present() -> None:
    assert "Never link a BioChemical ResearchStep" in RESEARCHTYPE_ISSTEP_CROSSLINK_BAN
    assert "ComputationalExperiment" in parent_scoped_isstep_hint(
        ["whu_BioChemical_Experiment"]
    )
    assert "BioChemicalExperiment" in parent_scoped_isstep_hint(
        ["whu_Computational_Experiment"]
    )
    assert parent_scoped_isstep_hint(["whu_ScienceEvidence"]) == ""


def test_schema_for_rule_ids_h01b() -> None:
    routed = [
        ["whu_ResearchStep", "p_plan_isStepOfPlan", "whu_BioChemical_Experiment", [], "mid2low"],
        ["whu_ResearchStep", "whu_declaredUsed", "mp_Method", [], "low"],
        ["whu_Goal", "whu_hasTarget", "whu_TargetVariable", [], "low"],
    ]
    clipped = schema_for_rule_ids(routed, ["H01-B"])
    rels = {r[1] for r in clipped}
    assert "p_plan_isStepOfPlan" in rels
    assert "whu_hasTarget" not in rels


def main() -> None:
    test_t1_biochemical_pass()
    test_t2_computational_pass()
    test_t3_bio_to_comp_fail()
    test_t4_comp_to_bio_fail()
    test_t5_same_chunk_no_cross()
    test_prompt_ban_present()
    test_schema_for_rule_ids_h01b()
    print("test_h01b_researchtype_isstep: OK")


if __name__ == "__main__":
    main()
