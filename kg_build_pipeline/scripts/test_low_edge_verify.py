"""Unit tests for Step 1: post-extract Neo4j edge verification."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from kg_build_pipeline.src.stages.build_kg import (
    _verify_edges_enabled,
    verify_schema_edge_written,
)


def test_verify_edges_enabled() -> None:
    cfg_on = {"verify_edges_after_extract": True}
    cfg_off = {"verify_edges_after_extract": False}
    assert _verify_edges_enabled("low_ll", cfg_on)
    assert not _verify_edges_enabled("low_ll", cfg_off)
    assert not _verify_edges_enabled("build", cfg_on)


def test_verify_schema_edge_written_delta() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session

    def _run_side_effect(cypher, **params):
        result = MagicMock()
        if "whu_declaredUsed" in cypher:
            result.single.return_value = {"c": 1}
        else:
            result.single.return_value = {"c": 0}
        return result

    session.run.side_effect = _run_side_effect

    ok, after, reason = verify_schema_edge_written(
        driver,
        "neo4j",
        ["whu_ResearchStep", "whu_declaredUsed", "mp_Method"],
        parent_element_id="pid-1",
        count_before=0,
    )
    assert ok is True
    assert after == 1
    assert reason == ""

    ok2, after2, reason2 = verify_schema_edge_written(
        driver,
        "neo4j",
        ["whu_ResearchStep", "whu_declaredInput", "whu_DataSet"],
        parent_element_id="pid-1",
        count_before=0,
    )
    assert ok2 is False
    assert after2 == 0
    assert "no matching edge" in reason2


def test_verify_invalid_triple() -> None:
    driver = MagicMock()
    ok, after, reason = verify_schema_edge_written(driver, "neo4j", [])
    assert ok is False
    assert after == 0
    assert reason == "invalid triple"


def main() -> None:
    test_verify_edges_enabled()
    test_verify_schema_edge_written_delta()
    test_verify_invalid_triple()
    print("test_low_edge_verify: OK")


if __name__ == "__main__":
    main()
