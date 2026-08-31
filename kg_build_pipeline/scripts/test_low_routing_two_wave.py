"""Unit tests for incident two-wave Low routing (no Neo4j / LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.low_schema_router import (
    _row_triple,
    intersect_schema_rows,
    route_low_incident,
    route_mid2low_incident,
    route_schema_for_parent,
    schema_for_rule_ids_intersect,
)
from kg_build_pipeline.src.schema_loader import load_schema
from kg_build_pipeline.src.stages.build_kg import (
    InsufficientBalanceError,
    _is_insufficient_balance,
)


def _keys(rows):
    out = set()
    for r in rows:
        t = _row_triple(r)
        if t:
            out.add(t)
    return out


def main() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")

    se = route_mid2low_incident("whu_ScienceEvidence", potential_schema)
    se_keys = _keys(se)
    assert se_keys == {
        ("whu_ScienceEvidence", "prov_hadMember", "whu_DataSet"),
        ("whu_ScienceEvidence", "prov_hadMember", "mp_Method"),
    }, se_keys
    assert not any(k[1] == "whu_declaredUsed" for k in se_keys)

    bio = route_mid2low_incident("whu_BioChemical_Experiment", potential_schema)
    bio_keys = _keys(bio)
    assert ("whu_BioChemical_Experiment", "whu_hasGoal", "whu_Goal") in bio_keys
    assert (
        "whu_ResearchStep",
        "p_plan_isStepOfPlan",
        "whu_BioChemical_Experiment",
    ) in bio_keys
    assert (
        "whu_ProcessedSpecimen",
        "p_plan_isInputVarOf",
        "whu_BioChemical_Experiment",
    ) in bio_keys
    assert not any(k[1] == "whu_declaredUsed" for k in bio_keys), bio_keys

    rs_low = route_low_incident("whu_ResearchStep", potential_schema)
    rs_keys = _keys(rs_low)
    assert ("whu_ResearchStep", "whu_declaredUsed", "mp_Method") in rs_keys
    assert ("whu_ResearchStep", "p_plan_isPrecededBy", "whu_ResearchStep") in rs_keys

    # legacy closure still returns a (typically larger) set
    legacy = route_schema_for_parent("whu_ScienceEvidence", potential_schema)
    assert len(legacy) >= len(se)
    # incident mid2low is a subset of legacy for SE (legacy includes low closure too)
    assert se_keys <= _keys(legacy)

    # intersect: targeted H04 on mid allow-set should not invent declaredUsed
    clipped = schema_for_rule_ids_intersect(legacy, ["H04"], allow=se)
    assert not any(_row_triple(r) and _row_triple(r)[1] == "whu_declaredUsed" for r in clipped)

    assert intersect_schema_rows(legacy, se) == se or _keys(intersect_schema_rows(legacy, se)) == se_keys

    assert _is_insufficient_balance(
        Exception("Error code: 402 - Insufficient Balance")
    )
    assert isinstance(InsufficientBalanceError("x"), RuntimeError)

    print("test_low_routing_two_wave: OK")


if __name__ == "__main__":
    main()
