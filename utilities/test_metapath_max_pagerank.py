"""Unit tests for unified maxPageRank computation (no Neo4j)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from utilities.metapath_path_level import (
    PAGERANK_PROP_BY_SUBGRAPH,
    compute_max_pagerank_for_linked_entities,
    pagerank_prop_for_subgraph,
)


class _FakeSession:
    def __init__(self, pr_by_eid: dict[str, float | None]) -> None:
        self._pr_by_eid = pr_by_eid

    def run(self, _cypher: str, eid: str) -> MagicMock:
        result = MagicMock()
        result.single.return_value = {"pr": self._pr_by_eid.get(eid)}
        return result


class TestMaxPageRankUnified(unittest.TestCase):
    def test_pagerank_prop_for_subgraph(self) -> None:
        self.assertEqual(pagerank_prop_for_subgraph("MPU"), "mpu_pagerank")
        self.assertEqual(pagerank_prop_for_subgraph("EEM"), "eem_pagerank")
        self.assertEqual(pagerank_prop_for_subgraph("EBM"), "ebm_pagerank")
        with self.assertRaises(ValueError):
            pagerank_prop_for_subgraph("UNKNOWN")

    def test_compute_max_two_linked_entities(self) -> None:
        session = _FakeSession({"e1": 0.1, "e2": 0.35})
        result = compute_max_pagerank_for_linked_entities(
            session,
            ["e1", "e2"],
            "MPU",
            mp_id="MPU_000001",
        )
        self.assertEqual(result, 0.35)

    def test_compute_max_single_linked_entity_mid(self) -> None:
        session = _FakeSession({"plan": 0.15})
        result = compute_max_pagerank_for_linked_entities(
            session,
            ["plan"],
            "EBM",
            mp_id="EBM_MID_00001",
        )
        self.assertEqual(result, 0.15)

    def test_compute_max_zero_is_valid(self) -> None:
        session = _FakeSession({"e1": 0.0, "e2": 0.0})
        result = compute_max_pagerank_for_linked_entities(
            session,
            ["e1", "e2"],
            "EEM",
            mp_id="EEM_000002",
        )
        self.assertEqual(result, 0.0)

    def test_compute_max_empty_linked_raises(self) -> None:
        session = _FakeSession({})
        with self.assertRaises(ValueError) as ctx:
            compute_max_pagerank_for_linked_entities(
                session, [], "MPU", mp_id="MPU_000003"
            )
        self.assertIn("无 metaPathRelation", str(ctx.exception))

    def test_compute_max_missing_pagerank_raises(self) -> None:
        session = _FakeSession({"e1": 0.2, "e2": None})
        with self.assertRaises(ValueError) as ctx:
            compute_max_pagerank_for_linked_entities(
                session,
                ["e1", "e2"],
                "MPU",
                mp_id="MPU_000004",
            )
        self.assertIn("缺少 mpu_pagerank", str(ctx.exception))

    def test_pagerank_prop_map_complete(self) -> None:
        self.assertEqual(set(PAGERANK_PROP_BY_SUBGRAPH), {"MPU", "EEM", "EBM"})


if __name__ == "__main__":
    unittest.main()
