"""Unit tests for low_parent_context + low_schema_router (no Neo4j/LLM)."""
from __future__ import annotations

from kg_build_pipeline.src.low_parent_context import (
    build_pass1_context,
    build_pass2_context,
    text_supported_by_corpus,
)
from kg_build_pipeline.src.low_schema_router import (
    expand_reachable_labels,
    partition_schema_batches,
    route_schema_for_parent,
    schema_for_rule_ids,
)


def test_pass1_excludes_neighbors() -> None:
    ctx = build_pass1_context(
        parent_element_id="p1",
        parent_name="ExpA",
        parent_labels=["whu_BioChemical_Experiment"],
        parent_original_text="step one wash cells",
        filename="doc.md",
        home_chunks=[{"id": "c1", "index": 5, "text": "wash cells with PBS"}],
    )
    text = ctx.extraction_text()
    assert "PARENT_ORIGINAL_TEXT" in text
    assert "HOME_CHUNK" in text
    assert "PREVIOUS" not in text
    assert "NEXT" not in text
    assert "neighbor" not in text.lower()


def test_pass2_role_separated() -> None:
    p1 = build_pass1_context(
        parent_element_id="p1",
        parent_name="ExpA",
        parent_labels=["whu_BioChemical_Experiment"],
        parent_original_text="core",
        filename="doc.md",
        home_chunks=[{"id": "c1", "index": 5, "text": "current text"}],
    )
    p2 = build_pass2_context(
        p1,
        previous_chunks=[{"id": "c0", "index": 4, "text": "prev text"}],
        next_chunks=[{"id": "c2", "index": 6, "text": "next text"}],
    )
    text = p2.extraction_text()
    assert "[PREVIOUS_CHUNK" in text
    assert "[CURRENT_CHUNK" in text
    assert "[NEXT_CHUNK" in text
    assert "prev text" in text and "next text" in text


def test_text_supported_by_corpus() -> None:
    corpus = "Parent says wash cells with PBS then centrifuge."
    assert text_supported_by_corpus("wash cells with PBS", corpus)
    assert not text_supported_by_corpus("completely unrelated span", corpus)


def test_router_includes_research_step_for_experiment() -> None:
    ps = [
        [
            "whu_ResearchStep",
            "p_plan_isStepOfPlan",
            "whu_BioChemical_Experiment",
            ["Methods_Materials"],
            "mid2low",
        ],
        [
            "whu_ResearchStep",
            "whu_declaredUsed",
            "mp_Method",
            ["Methods_Materials"],
            "low",
        ],
        [
            "whu_ResearchStep",
            "p_plan_isPrecededBy",
            "whu_ResearchStep",
            ["Methods_Materials"],
            "low",
        ],
        [
            "whu_Device",
            "whu_declaredUsed",
            "mp_Method",
            ["Methods_Materials"],
            "low",
        ],
    ]
    routed = route_schema_for_parent("whu_BioChemical_Experiment", ps)
    rels = {(r[0], r[1], r[2]) for r in routed}
    assert ("whu_ResearchStep", "p_plan_isStepOfPlan", "whu_BioChemical_Experiment") in rels
    assert ("whu_ResearchStep", "whu_declaredUsed", "mp_Method") in rels
    assert ("whu_ResearchStep", "p_plan_isPrecededBy", "whu_ResearchStep") in rels
    # Unrelated Device-Method without path from parent should be excluded
    assert ("whu_Device", "whu_declaredUsed", "mp_Method") not in rels

    labels = expand_reachable_labels("whu_BioChemical_Experiment", ps)
    assert "whu_ResearchStep" in labels
    assert "mp_Method" in labels


def test_partition_and_w01_targeted() -> None:
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
            "p_plan_isPrecededBy",
            "whu_ResearchStep",
            ["All"],
            "low",
        ],
        ["whu_DataSet", "prov_hadMember", "mp_Method", ["All"], "low"],
    ]
    routed = route_schema_for_parent("whu_BioChemical_Experiment", ps)
    batches = partition_schema_batches(routed)
    names = [b[0] for b in batches]
    assert "entities_attach" in names
    assert "low_low_links" in names
    w01 = schema_for_rule_ids(routed, ["W01"])
    assert any(r[1] == "p_plan_isStepOfPlan" for r in w01)


def main() -> None:
    test_pass1_excludes_neighbors()
    test_pass2_role_separated()
    test_text_supported_by_corpus()
    test_router_includes_research_step_for_experiment()
    test_partition_and_w01_targeted()
    print("test_low_context_router: OK")


if __name__ == "__main__":
    main()
