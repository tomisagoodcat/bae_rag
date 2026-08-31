"""Recall pool reranking: s_final = α·s_search + η·s_pr + γ·s_olap (no structural score)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set

RECALL_TOP_K = 50
OUTPUT_TOP_K = 10

OLAP_IN_POOL = 1.0
OLAP_NOT_IN_POOL = 0.0


@dataclass(frozen=True)
class RerankWeights:
    alpha: float = 0.5
    eta: float = 0.35
    gamma: float = 0.15


# Stateless OLAP baseline: s_final = η·s_pr only (α=0, γ=0)
RERANK_STATELESS = RerankWeights(alpha=0.0, eta=1.0, gamma=0.0)


def olap_prior_score(mp_id: str, gsub_mp_ids: Set[str]) -> float:
    """Binary structural alignment: 1.0 in G_sub, 0.0 otherwise."""
    if not gsub_mp_ids:
        raise ValueError("olap_prior_score: gsub_mp_ids 为空，无法计算 s_olap")
    return OLAP_IN_POOL if mp_id in gsub_mp_ids else OLAP_NOT_IN_POOL


def _minmax_normalize(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    span = vmax - vmin
    if span == 0.0:
        return [1.0 for _ in values]
    return [(v - vmin) / span for v in values]


def _cosine_similarity(embedder: Any, query: str, document: str) -> float:
    text = document.strip()
    if not text:
        raise ValueError("rerank 需要非空路径文本 (metaPathQuery/metaPathText)")
    q_vec = embedder.embed_query(query)
    d_vec = embedder.embed_query(text)
    q_norm = sum(x * x for x in q_vec) ** 0.5 or 1.0
    d_norm = sum(x * x for x in d_vec) ** 0.5 or 1.0
    return sum(a * b for a, b in zip(q_vec, d_vec)) / (q_norm * d_norm)


def _search_score(row: Dict[str, Any], embedder: Any, query: str) -> float:
    raw = row.get("score")
    if raw is not None:
        return float(raw)
    text = (row.get("meta_path_query") or row.get("metapath_text") or "").strip()
    return _cosine_similarity(embedder, query, text)


def _graph_score(row: Dict[str, Any]) -> float:
    raw = row.get("graph_score")
    if raw is None:
        mp_id = row.get("mp_id")
        raise ValueError(f"MetaPath {mp_id} 缺少 maxPageRank (graph_score 为 NULL)")
    return float(raw)


def rerank_metapath_candidates(
    embedder: Any,
    query: str,
    rows: Sequence[Dict[str, Any]],
    *,
    gsub_mp_ids: Sequence[str],
    gamma: float,
    weights: Optional[RerankWeights] = None,
) -> List[Dict[str, Any]]:
    """
    Rerank recall pool rows.
    s_final = α·s_search + η·s_pr + γ·s_olap
    First turn: caller passes gamma=0.
    """
    if not rows:
        raise ValueError("rerank_metapath_candidates: 空 rows")
    if gamma > 0.0 and not gsub_mp_ids:
        raise ValueError(
            "rerank_metapath_candidates: γ>0 要求非空 gsub_mp_ids（禁止空 G_sub 静默降级）"
        )

    w = weights or RerankWeights()
    pool: Set[str] = set(gsub_mp_ids)

    search_raw = [_search_score(row, embedder, query) for row in rows]
    pr_raw = [_graph_score(row) for row in rows]
    if gamma == 0.0:
        olap_raw = [0.0 for _ in rows]
    else:
        olap_raw = [
            olap_prior_score(str(row.get("mp_id") or ""), pool) for row in rows
        ]

    s_search = _minmax_normalize(search_raw)
    s_pr = _minmax_normalize(pr_raw)
    s_olap = _minmax_normalize(olap_raw)

    scored: List[Dict[str, Any]] = []
    for row, ss, sp, so, sr, pr, ol in zip(
        rows, s_search, s_pr, s_olap, search_raw, pr_raw, olap_raw
    ):
        s_final = w.alpha * ss + w.eta * sp + gamma * so
        item = dict(row)
        item["s_search"] = ss
        item["s_pr"] = sp
        item["s_olap"] = so
        item["s_search_raw"] = sr
        item["s_pr_raw"] = pr
        item["s_olap_raw"] = ol
        item["combined_score"] = s_final
        item["score"] = s_final
        scored.append(item)

    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    return scored


def rerank_page_rank_only(
    rows: Sequence[Dict[str, Any]],
    *,
    weights: Optional[RerankWeights] = None,
) -> List[Dict[str, Any]]:
    """Stateless baseline: rank recall pool by normalized PageRank only."""
    if not rows:
        raise ValueError("rerank_page_rank_only: 空 rows")
    w = weights or RERANK_STATELESS
    if w.alpha != 0.0 or w.gamma != 0.0:
        raise ValueError(f"Stateless rerank 要求 α=0, γ=0；got α={w.alpha}, γ={w.gamma}")
    pr_raw = [_graph_score(row) for row in rows]
    s_pr = _minmax_normalize(pr_raw)
    scored: List[Dict[str, Any]] = []
    for row, sp, pr in zip(rows, s_pr, pr_raw):
        item = dict(row)
        item["s_search"] = 0.0
        item["s_pr"] = sp
        item["s_olap"] = 0.0
        item["s_search_raw"] = float(row.get("score") or 0.0)
        item["s_pr_raw"] = pr
        item["s_olap_raw"] = 0.0
        item["combined_score"] = w.eta * sp
        item["score"] = item["combined_score"]
        scored.append(item)
    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    return scored
