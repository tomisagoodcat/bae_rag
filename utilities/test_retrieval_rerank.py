"""Unit tests for retrieval_rerank (no Neo4j)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from utilities.retrieval_rerank import (
    OLAP_IN_POOL,
    OLAP_NOT_IN_POOL,
    olap_prior_score,
    rerank_metapath_candidates,
    rerank_page_rank_only,
)


class _FakeEmbedder:
    def embed_query(self, text: str):
        if "query" in text.lower():
            return [1.0, 0.0]
        return [1.0, 0.0]


class TestRetrievalRerank(unittest.TestCase):
    def test_olap_prior(self):
        pool = {"A", "B"}
        self.assertEqual(olap_prior_score("A", pool), OLAP_IN_POOL)
        self.assertEqual(olap_prior_score("Z", pool), OLAP_NOT_IN_POOL)

    def test_olap_prior_empty_pool_raises(self):
        with self.assertRaises(ValueError):
            olap_prior_score("A", set())

    def test_rerank_gamma_positive_requires_gsub(self):
        rows = [
            {"mp_id": "A", "score": 0.9, "graph_score": 10.0, "metaPathQuery": "a"},
        ]
        with self.assertRaises(ValueError):
            rerank_metapath_candidates(
                _FakeEmbedder(), "query", rows, gsub_mp_ids=[], gamma=0.15
            )

    def test_rerank_gamma_zero(self):
        rows = [
            {"mp_id": "A", "score": 0.9, "graph_score": 10.0, "metaPathQuery": "a"},
            {"mp_id": "B", "score": 0.1, "graph_score": 1.0, "metaPathQuery": "b"},
        ]
        out = rerank_metapath_candidates(
            _FakeEmbedder(), "query", rows, gsub_mp_ids=["A"], gamma=0.0
        )
        self.assertEqual(out[0]["mp_id"], "A")

    def test_missing_graph_score_raises(self):
        rows = [{"mp_id": "X", "score": 0.5, "metaPathQuery": "x"}]
        with self.assertRaises(ValueError):
            rerank_metapath_candidates(
                _FakeEmbedder(), "q", rows, gsub_mp_ids=[], gamma=0.0
            )

    def test_page_rank_only_orders_by_pr(self):
        rows = [
            {"mp_id": "low", "score": 0.99, "graph_score": 1.0},
            {"mp_id": "high", "score": 0.01, "graph_score": 100.0},
        ]
        out = rerank_page_rank_only(rows)
        self.assertEqual(out[0]["mp_id"], "high")
        self.assertEqual(out[0]["s_search"], 0.0)


if __name__ == "__main__":
    unittest.main()
