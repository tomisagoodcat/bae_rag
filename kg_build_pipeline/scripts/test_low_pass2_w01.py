"""Test7: W01 triggers Pass2 with ResearchStep-only targeted schema + neighbor roles."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from kg_build_pipeline.src.low_parent_context import build_pass1_context, build_pass2_context
from kg_build_pipeline.src.low_schema_router import route_schema_for_parent, schema_for_rule_ids


def test7_w01_pass2_targeted_and_neighbor() -> None:
    ps = [
        [
            "whu_ResearchStep",
            "p_plan_isStepOfPlan",
            "whu_BioChemical_Experiment",
            ["All"],
            "mid2low",
        ],
        [
            "whu_ResearchStep",
            "whu_declaredUsed",
            "mp_Method",
            ["All"],
            "low",
        ],
        [
            "whu_DataSet",
            "prov_hadMember",
            "mp_Method",
            ["All"],
            "mid2low",
        ],
    ]
    routed = route_schema_for_parent("whu_BioChemical_Experiment", ps)
    targeted = schema_for_rule_ids(routed, ["W01"])
    assert targeted, "W01 must activate ResearchStep schema"
    assert all(
        "ResearchStep" in str(r[0]) or "ResearchStep" in str(r[2]) or r[1] == "p_plan_isStepOfPlan"
        for r in targeted
    )
    # Must not dump unrelated SE membership when W01-only
    assert not any(r[0] == "whu_DataSet" for r in targeted)

    p1 = build_pass1_context(
        parent_element_id="p",
        parent_name="E",
        parent_labels=["whu_BioChemical_Experiment"],
        parent_original_text="parent",
        filename="doc.md",
        home_chunks=[{"id": "c1", "index": 3, "text": "home"}],
    )
    p2 = build_pass2_context(
        p1,
        previous_chunks=[{"id": "c0", "index": 2, "text": "neighbor-prev"}],
        next_chunks=[{"id": "c2", "index": 4, "text": "neighbor-next"}],
    )
    text = p2.extraction_text()
    assert "neighbor-prev" in text and "neighbor-next" in text
    assert "[PREVIOUS_CHUNK" in text

    # Mock reviewer decision
    review = {
        "decision": "EXPAND_NEIGHBOR",
        "needs_neighbor_pass": True,
        "suggested_rule_ids": ["W01"],
    }
    assert review["needs_neighbor_pass"] is True
    assert schema_for_rule_ids(routed, review["suggested_rule_ids"]) == targeted


def main() -> None:
    test7_w01_pass2_targeted_and_neighbor()
    print("test_low_pass2_w01: OK")


if __name__ == "__main__":
    main()
