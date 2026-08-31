"""Fidelity guards: low_ll merge filters, SE activation, entity evidence filter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.low_schema_router import (
    activate_local_low_schema,
    schema_for_rule_ids,
)
from kg_build_pipeline.src.schema_loader import load_schema
from kg_build_pipeline.src.stages.low_extract import (
    _parse_relations_json,
    filter_entities_for_write,
)


def test_se_activation_no_goal_step() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")
    local = activate_local_low_schema(
        "whu_ScienceEvidence", potential_schema, hops=2
    )
    assert local.hops == 0
    assert "whu_Goal" not in local.entity_labels
    assert "whu_ResearchStep" not in local.entity_labels
    assert local.entry_labels <= {"whu_DataSet", "mp_Method", "whu_Method"}
    assert not local.low_rows


def test_schema_for_rule_ids_no_hasgoal_for_se() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")
    rows = schema_for_rule_ids(
        potential_schema,
        ["H09"],
        parent_labels=["whu_ScienceEvidence"],
    )
    for row in rows:
        if isinstance(row, (list, tuple)) and len(row) >= 3:
            assert row[1] != "whu_hasGoal", row
            assert row[0] != "whu_Goal" and row[2] != "whu_Goal"


def test_schema_for_rule_ids_hasgoal_for_experiment() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")
    rows = schema_for_rule_ids(
        potential_schema,
        ["H09"],
        parent_labels=["whu_Computational_Experiment"],
    )
    assert any(
        isinstance(row, (list, tuple)) and len(row) >= 3 and row[1] == "whu_hasGoal"
        for row in rows
    )


def test_filter_entities_evidence_and_ban() -> None:
    corpus = "We measured cadmium in rice using ICP-MS."
    ents = [
        {
            "label": "whu_Goal",
            "name": "fake goal",
            "original_text": "We measured cadmium",
        },
        {
            "label": "mp_Method",
            "name": "ICP-MS",
            "original_text": "ICP-MS",
        },
        {
            "label": "mp_Method",
            "name": "hallucinated",
            "original_text": "not in corpus at all xyz",
        },
        {
            "label": "mp_Method",
            "name": "ICP-MS",
            "original_text": "ICP-MS",
        },
    ]
    out = filter_entities_for_write(
        ents,
        allowed_labels={"whu_Goal", "mp_Method"},
        parent_labels=["whu_ScienceEvidence"],
        evidence_corpus=corpus,
        max_entities_per_parent=40,
    )
    kept = out["entities"]
    assert len(kept) == 1
    assert kept[0]["name"] == "ICP-MS"
    assert out["dropped_banned"] >= 1
    assert out["dropped_evidence"] >= 1
    assert out["dropped_dup"] >= 1


def test_parse_relations_json() -> None:
    raw = """
    {"relations":[
      {"src_name":"step1","src_label":"whu_ResearchStep",
       "rel":"whu_declaredUsed","tgt_name":"ICP-MS","tgt_label":"mp_Method"}
    ]}
    """
    rels = _parse_relations_json(raw)
    assert len(rels) == 1
    assert rels[0]["rel"] == "whu_declaredUsed"


def main() -> None:
    test_se_activation_no_goal_step()
    test_schema_for_rule_ids_no_hasgoal_for_se()
    test_schema_for_rule_ids_hasgoal_for_experiment()
    test_filter_entities_evidence_and_ban()
    test_parse_relations_json()
    print("OK: fidelity guards")


if __name__ == "__main__":
    main()
