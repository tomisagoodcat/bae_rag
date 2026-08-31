"""T1/T3: Local Low Schema Activation (no Neo4j / LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.low_schema_router import (
    activate_local_low_schema,
    mid2low_entry_labels,
    route_mid2low_incident,
)
from kg_build_pipeline.src.schema_loader import load_schema


def main() -> None:
    _, _, potential_schema = load_schema(ROOT / "schema")
    parent = "whu_BioChemical_Experiment"
    local = activate_local_low_schema(parent, potential_schema, hops=2)

    mid2low = route_mid2low_incident(parent, potential_schema)
    entries = mid2low_entry_labels(parent, mid2low)
    assert local.entry_labels == entries
    assert "whu_ResearchStep" in local.entry_labels
    assert "whu_Goal" in local.entry_labels

    # T1: activation expands beyond mid2low direct endpoints
    required = {
        "whu_ResearchStep",
        "whu_Goal",
        "mp_Method",
        "whu_Device",
        "whu_Reagent",
        "whu_DataSet",
        "whu_TargetVariable",
        "whu_ChemicalEntity",
    }
    missing = required - local.entity_labels
    assert not missing, f"T1 missing expanded labels: {missing}"

    # Direct mid2low entries alone must NOT already include Method/ChemicalEntity
    assert "mp_Method" not in entries
    assert "whu_ChemicalEntity" not in entries

    # T3: TargetVariable / ChemicalEntity via low expansion, not mid2low entry
    assert "whu_TargetVariable" in local.entity_labels
    assert "whu_ChemicalEntity" in local.entity_labels
    assert "whu_TargetVariable" not in entries
    assert "whu_ChemicalEntity" not in entries

    # Must not equal full low dump
    from kg_build_pipeline.src.schema_tier import filter_potential_schema

    all_low = filter_potential_schema(potential_schema, tiers={"low"})
    assert len(local.low_rows) < len(all_low)
    assert len(local.mid2low_rows) == len(mid2low)

    # hops=0 → entries only, no low expansion
    shallow = activate_local_low_schema(parent, potential_schema, hops=0)
    assert shallow.entity_labels == entries
    assert shallow.low_rows == []

    print("test_low_schema_activation: OK")


if __name__ == "__main__":
    main()
