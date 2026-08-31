"""T2/T4–T7 entity-first guards (no Neo4j / LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.low_parent_context import build_pass1_context
from kg_build_pipeline.src.low_schema_router import (
    _row_triple,
    activate_local_low_schema,
    filter_low_rows_for_present_types,
    research_type_for_parent,
)
from kg_build_pipeline.src.schema_loader import load_schema
from kg_build_pipeline.src.stages.low_extract import LlmCallBudget
from kg_build_pipeline.src.stages.low_validate import check_h01b_research_type
from kg_build_pipeline.src.stages.mid_low_linker import (
    research_type_matches_parent,
    would_reject_cross_experiment_step,
)


def test_t2_low_low_missing_method() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")
    local = activate_local_low_schema(
        "whu_BioChemical_Experiment", potential_schema, hops=2
    )
    # ResearchStep present, Method absent → declaredUsed must be missing
    present = {"whu_ResearchStep", "whu_Goal"}
    runnable, missing = filter_low_rows_for_present_types(local.low_rows, present)
    runnable_keys = {t for r in runnable if (t := _row_triple(r))}
    assert not any(
        t[0] == "whu_ResearchStep" and t[1] == "whu_declaredUsed" and t[2] == "mp_Method"
        for t in runnable_keys
    )
    assert any(
        t[1] == "whu_declaredUsed" and t[2] == "mp_Method" for t in missing
    ), missing


def test_t4_t5_t6_research_type() -> None:
    assert research_type_for_parent("whu_BioChemical_Experiment") == "BioChemical"
    assert research_type_for_parent("whu_Computational_Experiment") == "Computational"

    # T4 PASS
    assert research_type_matches_parent(
        "BioChemical", ["whu_BioChemical_Experiment", "__Entity__"]
    )
    ok = check_h01b_research_type(
        [
            {
                "id": "s1",
                "name": "digest",
                "labels": ["whu_ResearchStep"],
                "research_type": "BioChemical",
                "parent_labels": ["whu_BioChemical_Experiment"],
                "parent_ids": ["p1"],
            }
        ]
    )
    assert ok == [], ok

    # T5 FAIL: BioChemical step vs Computational parent
    assert would_reject_cross_experiment_step(
        "BioChemical", "whu_Computational_Experiment"
    )
    bad = check_h01b_research_type(
        [
            {
                "id": "s2",
                "name": "digest",
                "labels": ["whu_ResearchStep"],
                "research_type": "BioChemical",
                "parent_labels": ["whu_Computational_Experiment"],
                "parent_ids": ["p2"],
            }
        ]
    )
    assert any(i.get("rule_id") == "H01-B" for i in bad), bad

    # T6 FAIL: same step two parents
    dual = check_h01b_research_type(
        [
            {
                "id": "s3",
                "name": "step",
                "labels": ["whu_ResearchStep"],
                "research_type": "BioChemical",
                "parent_labels": [
                    "whu_BioChemical_Experiment",
                    "whu_Computational_Experiment",
                ],
                "parent_ids": ["p1", "p2"],
            }
        ]
    )
    assert any(i.get("rule_id") in {"H01", "H01-B"} for i in dual), dual


def test_t7_pass1_no_neighbors() -> None:
    ctx = build_pass1_context(
        parent_element_id="pid",
        parent_name="exp",
        parent_labels=["whu_BioChemical_Experiment"],
        parent_original_text="digest with HNO3",
        filename="doc.md",
        home_chunks=[{"id": "c1", "index": 3, "text": "chunk text here"}],
        use_parent_original_text=True,
        use_current_chunk=True,
    )
    assert ctx.pass_kind == "pass1"
    assert ctx.previous_chunks == []
    assert ctx.next_chunks == []
    text = ctx.extraction_text()
    assert "PARENT_ORIGINAL_TEXT" in text
    assert "HOME_CHUNK" in text
    assert "PREVIOUS_CHUNK" not in text
    assert "NEXT_CHUNK" not in text


def test_llm_budget() -> None:
    b = LlmCallBudget(3)
    assert b.consume(1)
    assert b.consume(1)
    assert b.consume(1)
    assert not b.consume(1)
    assert b.used == 3
    assert b.remaining() == 0


def main() -> None:
    test_t2_low_low_missing_method()
    test_t4_t5_t6_research_type()
    test_t7_pass1_no_neighbors()
    test_llm_budget()
    print("test_low_entity_first_guards: OK")


if __name__ == "__main__":
    main()
