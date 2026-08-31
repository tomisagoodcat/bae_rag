"""Unit tests for OLAP metric functions (no Neo4j / LLM required for qrels path)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utilities.test_evaluation import (
    _recall_precision_from_qrels,
    compute_anchor_overlap,
    get_qrels_for_turn,
    parse_retrieval_items,
)


class TestOlapMetrics(unittest.TestCase):
    def test_qrels_priority(self):
        turn = {"relevant_mp_ids": ["mp_a", "mp_b", "mp_c"]}
        qrels = get_qrels_for_turn(turn)
        self.assertEqual(qrels, ["mp_a", "mp_b", "mp_c"])
        scores = _recall_precision_from_qrels(qrels, ["mp_x", "mp_a", "mp_b"], k=10)
        self.assertAlmostEqual(scores["recall_at_10"], 2 / 3)
        self.assertAlmostEqual(scores["precision_at_10"], 2 / 10)
        self.assertEqual(scores["retrieval_metric_source"], "qrels")

    def test_empty_qrels_falls_back_none(self):
        self.assertIsNone(get_qrels_for_turn({"relevant_mp_ids": []}))
        self.assertIsNone(get_qrels_for_turn({"query": "q"}))

    def test_anchor_overlap(self):
        p_star = [f"mp_{i}" for i in range(20)]
        retrieved = [f"mp_{i}" for i in range(10)]
        overlap = compute_anchor_overlap(p_star, retrieved, k=10)
        self.assertAlmostEqual(overlap, 0.5)

    def test_parse_retrieval_items(self):
        state = {
            "retrieval_results": json.dumps(
                {
                    "count": 2,
                    "results": [
                        {"rank": 1, "mp_id": "mp_1", "preview": "text one"},
                        {"rank": 2, "mp_id": "mp_2", "preview": "text two"},
                    ],
                }
            )
        }
        items = parse_retrieval_items(state, k=10)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["mp_id"], "mp_1")


if __name__ == "__main__":
    unittest.main()
