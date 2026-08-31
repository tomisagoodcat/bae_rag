"""Shared test/evaluation utilities for 3_0_2 retrieval pipeline."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from utilities.pipeline_config import PipelineConfig, get_pipeline_config
from utilities.rag_llm_judge import (
    LLMJudgeError,
    judge_answer_relevance,
    judge_context_precision,
    judge_faithfulness,
    judge_metapath_relevance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS_CSV = PROJECT_ROOT / "data" / "questions.csv"
DEFAULT_DIALOGUE_JSON = PROJECT_ROOT / "data" / "dialogue_test_cases.json"
DEFAULT_EVAL_LOG = PROJECT_ROOT / "output" / "eval_log.md"
DEFAULT_RETRIEVAL_K = 10
CANDIDATE_POOL_CAP = 50

CORE_METRIC_KEYS = (
    "recall_at_10",
    "precision_at_10",
    "anchor_overlap",
    "faithfulness",
    "answer_relevance",
    "context_precision",
)


class TurnMetricError(RuntimeError):
    """Turn-level metric computation failed; do not substitute default scores."""


class MetricInputError(ValueError):
    """Invalid evaluation inputs."""


def resolve_questions_csv(path: Optional[str | Path] = None) -> Path:
    if path is not None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"questions CSV 不存在: {p}")
        return p
    if not DEFAULT_QUESTIONS_CSV.is_file():
        raise FileNotFoundError(f"默认 questions CSV 不存在: {DEFAULT_QUESTIONS_CSV}")
    return DEFAULT_QUESTIONS_CSV


def load_test_cases(csv_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Load first-turn QA cases: query + expected top-level modules."""
    path = resolve_questions_csv(csv_path)
    df = pd.read_csv(path)
    if "questions" not in df.columns:
        raise ValueError(f"CSV 缺少 questions 列: {list(df.columns)}")
    if "expected" not in df.columns:
        raise ValueError(f"CSV 缺少 expected 列，请先完成人工标注")

    cases = []
    for _, row in df.iterrows():
        cases.append(
            {
                "query": str(row["questions"]).strip(),
                "expected": [sg.strip() for sg in str(row["expected"]).split("|") if sg.strip()],
            }
        )
    if not cases:
        raise ValueError(f"CSV 无测试用例: {path}")
    return cases


def load_dialogue_test_cases(
    json_path: Optional[str | Path] = None,
    *,
    test_set: Optional[str] = None,
    max_scenarios: int = 0,
    olap_modes: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """加载多轮测试 scenario，并可按 ``utilities.dialogue_test_set`` 预设筛选。

    Parameters
    ----------
    test_set:
        ``legacy10`` | ``all`` | ``first``；默认见 ``DIALOGUE_TEST_SET`` 环境变量
        （未设置时为 ``legacy10``，避免误跑 66 条全量）。
    max_scenarios:
        仅对 ``all`` / ``first`` 生效；``legacy10`` 固定 10 条。
    olap_modes:
        预设 ``core`` / ``extended`` / ``all`` 或逗号分隔 κ；筛 JSON 中 expected_kappa。
    """
    from utilities.dialogue_test_set import filter_dialogue_scenarios, resolve_dialogue_test_set

    path = Path(json_path) if json_path else DEFAULT_DIALOGUE_JSON
    if not path.is_file():
        raise FileNotFoundError(f"多轮测试 JSON 不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if not data:
            raise ValueError(f"多轮测试 JSON 格式无效: {path}")
        raw = data
    elif isinstance(data, dict) and "scenarios" in data:
        scenarios = data["scenarios"]
        if not isinstance(scenarios, list) or not scenarios:
            raise ValueError(f"多轮测试 JSON scenarios 为空: {path}")
        raw = scenarios
    else:
        raise ValueError(f"多轮测试 JSON 格式无效: {path}")

    ts = resolve_dialogue_test_set(test_set)
    filtered, _meta = filter_dialogue_scenarios(
        raw, ts, max_scenarios=max_scenarios, olap_modes=olap_modes
    )
    return filtered


def load_dialogue_test_cases_with_meta(
    json_path: Optional[str | Path] = None,
    *,
    test_set: Optional[str] = None,
    max_scenarios: int = 0,
    olap_modes: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """同 ``load_dialogue_test_cases``，并返回筛选元数据（写入 eval log）。"""
    from utilities.dialogue_test_set import filter_dialogue_scenarios, resolve_dialogue_test_set

    path = Path(json_path) if json_path else DEFAULT_DIALOGUE_JSON
    if not path.is_file():
        raise FileNotFoundError(f"多轮测试 JSON 不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict) and "scenarios" in data:
        raw = data["scenarios"]
    else:
        raise ValueError(f"多轮测试 JSON 格式无效: {path}")
    ts = resolve_dialogue_test_set(test_set)
    return filter_dialogue_scenarios(
        raw, ts, max_scenarios=max_scenarios, olap_modes=olap_modes
    )


def compute_route_hit(expected: Sequence[str], actual: Sequence[str]) -> Dict[str, Any]:
    exp = set(expected or [])
    act = set(actual or [])
    if not exp:
        raise ValueError("expected 为空，无法计算路由命中")
    hit_any = bool(exp & act)
    hit_all = exp.issubset(act)
    return {
        "hit_any": hit_any,
        "hit_all": hit_all,
        "expected": sorted(exp),
        "actual": sorted(act),
        "missing": sorted(exp - act),
        "extra": sorted(act - exp),
    }


def _analyze_citations(answer: str, retrieval_count: int) -> Dict[str, Any]:
    citations = re.findall(r"\[[\d,\s]+\]", answer or "")
    cited_ids: set = set()
    for citation in citations:
        cited_ids.update(re.findall(r"\d+", citation))
    coverage = len(cited_ids) / retrieval_count if retrieval_count > 0 else 0.0
    return {
        "has_citation": len(citations) > 0,
        "citation_count": len(citations),
        "cited_ids": sorted(list(cited_ids), key=int),
        "coverage": coverage,
    }


def _calculate_context_precision(answer: str, retrieval_count: int) -> Dict[str, Any]:
    if retrieval_count == 0:
        return {"used_count": 0, "precision": 0.0, "cited_ids": []}
    citations = re.findall(r"\[[\d,\s]+\]", answer or "")
    cited_ids: set = set()
    for citation in citations:
        cited_ids.update(re.findall(r"\d+", citation))
    used_count = len(cited_ids)
    return {
        "used_count": used_count,
        "precision": used_count / retrieval_count,
        "cited_ids": sorted(list(cited_ids), key=int),
    }


def _calculate_relevancy(query: str, answer: str, embedder) -> float:
    if not answer or len(answer.strip()) < 5:
        return 0.0
    query_emb = embedder.embed_query(query)
    answer_emb = embedder.embed_query(answer)
    query_vec = np.array(query_emb).reshape(1, -1)
    answer_vec = np.array(answer_emb).reshape(1, -1)
    similarity = float(cosine_similarity(query_vec, answer_vec)[0][0])
    return max(0.0, min(1.0, similarity))


def _classify_relevancy(score: float) -> str:
    if score >= 0.8:
        return "高相关"
    if score >= 0.6:
        return "中相关"
    return "低相关"


def _require_llm_and_driver(llm: Any, neo4j_driver: Any, *, context: str) -> None:
    if llm is None:
        raise MetricInputError(f"{context}: 需要 llm 实例（OLAP 核心指标不可省略）")
    if neo4j_driver is None:
        raise MetricInputError(f"{context}: 需要 neo4j_driver（Faithfulness context 构建不可省略）")


def get_qrels_for_turn(turn: Dict[str, Any]) -> Optional[List[str]]:
    """Return qrels if turn defines non-empty relevant_mp_ids; else None (LLM fallback)."""
    if "relevant_mp_ids" not in turn:
        return None
    raw = turn["relevant_mp_ids"]
    if not isinstance(raw, list):
        raise MetricInputError("relevant_mp_ids 必须为 list")
    ids = [str(x).strip() for x in raw if str(x).strip()]
    return ids if ids else None


def parse_retrieval_items(state: Dict[str, Any], k: int = DEFAULT_RETRIEVAL_K) -> List[Dict[str, Any]]:
    retrieval_json = state.get("retrieval_results") or "{}"
    try:
        data = json.loads(retrieval_json)
    except json.JSONDecodeError as exc:
        raise TurnMetricError(f"retrieval_results JSON 无效: {exc}") from exc
    results = data.get("results")
    if not isinstance(results, list) or not results:
        raise TurnMetricError("retrieval_results.results 为空，无法计算检索指标")
    items: List[Dict[str, Any]] = []
    for row in results[:k]:
        if not isinstance(row, dict):
            raise TurnMetricError(f"retrieval result 行应为 dict: {row!r}")
        mp_id = row.get("mp_id")
        if not mp_id:
            raise TurnMetricError(f"检索项缺少 mp_id: {row!r}")
        preview = row.get("preview")
        if not preview:
            content = row.get("content")
            if isinstance(content, dict):
                preview = (content.get("metapath_text") or "").strip()
        if not preview:
            raise TurnMetricError(f"检索项缺少 preview/metapath_text: mp_id={mp_id}")
        rank = row.get("rank")
        if rank is None:
            rank = len(items) + 1
        items.append({"rank": int(rank), "mp_id": str(mp_id), "preview": str(preview)})
    return items


def parse_all_retrieval_mp_ids(state: Dict[str, Any]) -> List[str]:
    retrieval_json = state.get("retrieval_results") or "{}"
    data = json.loads(retrieval_json)
    results = data.get("results") or []
    ids: List[str] = []
    seen: set = set()
    for row in results:
        mp_id = row.get("mp_id") if isinstance(row, dict) else None
        if mp_id and mp_id not in seen:
            seen.add(mp_id)
            ids.append(str(mp_id))
    return ids


def _recall_precision_from_qrels(
    qrels: Sequence[str],
    retrieved_mp_ids: Sequence[str],
    k: int = DEFAULT_RETRIEVAL_K,
) -> Dict[str, Any]:
    qrels_set = set(qrels)
    if not qrels_set:
        raise TurnMetricError("qrels 为空集合")
    top_k = list(retrieved_mp_ids)[:k]
    hits = qrels_set & set(top_k)
    return {
        "recall_at_10": len(hits) / len(qrels_set),
        "precision_at_10": len(hits) / k,
        "retrieval_metric_source": "qrels",
        "qrels_size": len(qrels_set),
        "retrieved_hits": len(hits),
    }


def _build_pool_items(
    driver: Any,
    pool_mp_ids: Sequence[str],
    retrieval_items_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    from utilities.dialogue_routing import fetch_metapath_rows

    items: List[Dict[str, Any]] = []
    missing_preview: List[str] = []
    for i, mp_id in enumerate(pool_mp_ids, 1):
        if mp_id in retrieval_items_by_id:
            row = dict(retrieval_items_by_id[mp_id])
            row["rank"] = i
            items.append(row)
        else:
            missing_preview.append(mp_id)
    if missing_preview:
        rows = fetch_metapath_rows(driver, missing_preview)
        by_id = {str(r["mp_id"]): r for r in rows}
        for mp_id in missing_preview:
            row = by_id.get(mp_id)
            if not row:
                raise TurnMetricError(f"候选池 mp_id 在 Neo4j 不存在: {mp_id}")
            text = (row.get("metapath_text") or "").strip()
            if not text:
                raise TurnMetricError(f"候选池 mp_id 缺少 metapath_text: {mp_id}")
            items.append({"rank": len(items) + 1, "mp_id": mp_id, "preview": text})
    return items


def _recall_precision_from_llm(
    llm: Any,
    driver: Any,
    query: str,
    retrieval_items: Sequence[Dict[str, Any]],
    retrieved_mp_ids: Sequence[str],
    *,
    turn1_p_star: Optional[Sequence[str]] = None,
    gsub_mp_ids: Optional[Sequence[str]] = None,
    k: int = DEFAULT_RETRIEVAL_K,
) -> Dict[str, Any]:
    by_id = {it["mp_id"]: it for it in retrieval_items}
    pool: List[str] = []
    seen: set = set()
    for mid in list(retrieved_mp_ids) + list(turn1_p_star or []) + list(gsub_mp_ids or []):
        if mid and mid not in seen:
            seen.add(mid)
            pool.append(mid)
        if len(pool) >= CANDIDATE_POOL_CAP:
            break
    pool_items = _build_pool_items(driver, pool, by_id)
    pool_relevant = judge_metapath_relevance(llm, query, pool_items)
    relevant_ids = {pool_items[i]["mp_id"] for i, rel in enumerate(pool_relevant) if rel}
    top_k_ids = set(list(retrieved_mp_ids)[:k])
    hits = relevant_ids & top_k_ids
    recall = len(hits) / len(relevant_ids) if relevant_ids else 0.0
    precision = len(hits) / k
    return {
        "recall_at_10": recall,
        "precision_at_10": precision,
        "retrieval_metric_source": "llm_judge",
        "llm_relevant_pool_size": len(relevant_ids),
        "retrieved_hits": len(hits),
        "recall_is_proxy": True,
    }


def compute_anchor_overlap(
    turn1_p_star: Optional[Sequence[str]],
    retrieved_mp_ids: Sequence[str],
    k: int = DEFAULT_RETRIEVAL_K,
) -> Optional[float]:
    if not turn1_p_star:
        return None
    anchor = set(turn1_p_star)
    if not anchor:
        return None
    top_k = set(list(retrieved_mp_ids)[:k])
    return len(anchor & top_k) / len(anchor)


def score_turn_core_metrics(
    *,
    state: Dict[str, Any],
    turn: Dict[str, Any],
    query: str,
    llm: Any,
    neo4j_driver: Any,
    turn_index: int,
    turn1_p_star: Optional[Sequence[str]] = None,
    k: int = DEFAULT_RETRIEVAL_K,
) -> Dict[str, Any]:
    _require_llm_and_driver(llm, neo4j_driver, context=f"Turn {turn_index} core metrics")

    answer = (state.get("final_answer") or "").strip()
    if not answer:
        raise TurnMetricError(f"Turn {turn_index}: final_answer 为空")

    retrieval_items = parse_retrieval_items(state, k=k)
    retrieved_mp_ids = [it["mp_id"] for it in retrieval_items]
    all_retrieved = parse_all_retrieval_mp_ids(state) or retrieved_mp_ids

    qrels = get_qrels_for_turn(turn)
    if qrels is not None:
        retrieval_scores = _recall_precision_from_qrels(qrels, all_retrieved, k=k)
    else:
        retrieval_scores = _recall_precision_from_llm(
            llm,
            neo4j_driver,
            query,
            retrieval_items,
            all_retrieved,
            turn1_p_star=turn1_p_star if turn_index >= 2 else None,
            gsub_mp_ids=state.get("gsub_mp_ids") or [],
            k=k,
        )

    anchor_overlap = (
        compute_anchor_overlap(turn1_p_star, all_retrieved, k=k)
        if turn_index >= 2
        else None
    )

    from utilities.dialogue_routing import build_context_for_paths

    context_mp_ids = all_retrieved[:k]
    context = build_context_for_paths(neo4j_driver, context_mp_ids, max_paths=k)

    try:
        faithfulness = judge_faithfulness(llm, query, context, answer)
        answer_relevance = judge_answer_relevance(llm, query, answer)
        context_precision = judge_context_precision(llm, query, retrieval_items)
    except LLMJudgeError as exc:
        raise TurnMetricError(f"Turn {turn_index} LLM judge 失败: {exc}") from exc

    return {
        **retrieval_scores,
        "anchor_overlap": anchor_overlap,
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
        "context_precision": context_precision,
        "retrieved_mp_ids": all_retrieved[:k],
        "generation_metric_source": "llm_judge",
    }


def _mean_optional(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    return float(np.mean(nums)) if nums else None


def _aggregate_core_metrics(turns: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [t for t in turns if "error" not in t]
    turn1 = [t for t in valid if t.get("turn") == 1]
    turn2 = [t for t in valid if t.get("turn") == 2]
    turn2_plus = [t for t in valid if t.get("turn", 0) >= 2]

    def col(rows: Sequence[Dict[str, Any]], key: str) -> List[Optional[float]]:
        return [r.get(key) for r in rows]

    qrels_turns = sum(1 for t in valid if t.get("retrieval_metric_source") == "qrels")
    llm_turns = sum(1 for t in valid if t.get("retrieval_metric_source") == "llm_judge")

    return {
        "turn1_avg_recall_at_10": _mean_optional(col(turn1, "recall_at_10")),
        "turn1_avg_precision_at_10": _mean_optional(col(turn1, "precision_at_10")),
        "turn1_avg_faithfulness": _mean_optional(col(turn1, "faithfulness")),
        "turn1_avg_answer_relevance": _mean_optional(col(turn1, "answer_relevance")),
        "turn1_avg_context_precision": _mean_optional(col(turn1, "context_precision")),
        "turn2_avg_recall_at_10": _mean_optional(col(turn2, "recall_at_10")),
        "turn2_avg_precision_at_10": _mean_optional(col(turn2, "precision_at_10")),
        "turn2_avg_anchor_overlap": _mean_optional(col(turn2, "anchor_overlap")),
        "turn2_avg_faithfulness": _mean_optional(col(turn2, "faithfulness")),
        "turn2_avg_answer_relevance": _mean_optional(col(turn2, "answer_relevance")),
        "turn2_avg_context_precision": _mean_optional(col(turn2, "context_precision")),
        "turn2_plus_avg_recall_at_10": _mean_optional(col(turn2_plus, "recall_at_10")),
        "turn2_plus_avg_precision_at_10": _mean_optional(col(turn2_plus, "precision_at_10")),
        "turn2_plus_avg_anchor_overlap": _mean_optional(col(turn2_plus, "anchor_overlap")),
        "turn2_plus_avg_faithfulness": _mean_optional(col(turn2_plus, "faithfulness")),
        "turn2_plus_avg_answer_relevance": _mean_optional(col(turn2_plus, "answer_relevance")),
        "turn2_plus_avg_context_precision": _mean_optional(col(turn2_plus, "context_precision")),
        "qrels_scored_turns": qrels_turns,
        "llm_judge_scored_turns": llm_turns,
    }


def run_single_case(
    graph_app,
    make_initial_state: Callable[[str], Dict],
    query: str,
    embedder=None,
    expected: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Invoke pipeline once; return routing + retrieval + answer metrics."""
    state = make_initial_state(query)
    try:
        final = graph_app.invoke(state)
    except Exception as exc:
        return {
            "query": query,
            "expected": list(expected or []),
            "error": str(exc),
        }

    answer = final.get("final_answer", "")
    retrieval_json = final.get("retrieval_results", "{}")
    retrieval_data = json.loads(retrieval_json) if retrieval_json else {}
    retrieval_count = int(retrieval_data.get("count", 0) or 0)

    citation = _analyze_citations(answer, retrieval_count)
    precision = _calculate_context_precision(answer, retrieval_count)
    relevancy_score = (
        _calculate_relevancy(query, answer, embedder) if embedder is not None else None
    )

    actual_modules = list(final.get("target_subgraphs") or [])
    route = compute_route_hit(expected, actual_modules) if expected else None

    return {
        "query": query,
        "expected": list(expected or []),
        "actual_modules": actual_modules,
        "kappa": final.get("kappa"),
        "path_level": final.get("path_level"),
        "retrieval_count": retrieval_count,
        "answer_length": len(answer),
        "has_citation": citation["has_citation"],
        "citation_count": citation["citation_count"],
        "cited_ids": citation["cited_ids"],
        "coverage": citation["coverage"],
        "precision": precision["precision"],
        "used_count": precision["used_count"],
        "relevancy_score": relevancy_score,
        "relevancy_level": _classify_relevancy(relevancy_score) if relevancy_score is not None else None,
        "route_hit_any": route["hit_any"] if route else None,
        "route_hit_all": route["hit_all"] if route else None,
        "route_missing": route["missing"] if route else None,
        "candidate_mp_ids": final.get("candidate_mp_ids") or [],
        "entity_ids": final.get("entity_ids") or [],
    }


def evaluate_test_cases(
    graph_app,
    make_initial_state: Callable[[str], Dict],
    test_cases: Sequence[Dict[str, Any]],
    embedder=None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Single-pass evaluation: faithfulness + relevancy + precision + routing."""
    details: List[Dict[str, Any]] = []
    for i, case in enumerate(test_cases, 1):
        query = case.get("query") or case.get("questions", "")
        expected = case.get("expected") or []
        if verbose:
            print(f"\n[{i}/{len(test_cases)}] {query[:80]}")
        row = run_single_case(
            graph_app, make_initial_state, query, embedder=embedder, expected=expected
        )
        details.append(row)
        if verbose:
            if "error" in row:
                print(f"  ❌ {row['error'][:120]}")
            else:
                print(
                    f"  r={row['actual_modules']} κ={row['kappa']} l={row['path_level']} "
                    f"|P*|={row['retrieval_count']}"
                )
                if expected:
                    print(
                        f"  route hit_any={row['route_hit_any']} hit_all={row['route_hit_all']} "
                        f"(expected={expected})"
                    )
                print(
                    f"  citation={row['has_citation']} coverage={row['coverage']*100:.1f}% "
                    f"relevancy={row['relevancy_score']}"
                )

    valid = [d for d in details if "error" not in d]
    with_expected = [d for d in valid if d.get("expected")]
    summary = {
        "total": len(details),
        "success": len(valid),
        "failed": len(details) - len(valid),
        "avg_coverage": float(np.mean([d["coverage"] for d in valid])) if valid else 0.0,
        "citation_rate": sum(1 for d in valid if d["has_citation"]) / len(valid) if valid else 0.0,
        "avg_relevancy": float(np.mean([d["relevancy_score"] for d in valid if d["relevancy_score"] is not None]))
        if valid
        else 0.0,
        "avg_precision": float(np.mean([d["precision"] for d in valid])) if valid else 0.0,
        "route_hit_any_rate": float(np.mean([1.0 if d["route_hit_any"] else 0.0 for d in with_expected]))
        if with_expected
        else 0.0,
        "route_hit_all_rate": float(np.mean([1.0 if d["route_hit_all"] else 0.0 for d in with_expected]))
        if with_expected
        else 0.0,
    }
    return {"summary": summary, "details": details}


def run_dialogue_scenario(
    graph_app,
    make_initial_state: Callable[[str], Dict],
    scenario: Dict[str, Any],
    verbose: bool = True,
    embedder=None,
    pipeline_config: Optional[PipelineConfig] = None,
    llm=None,
    neo4j_driver=None,
    score_core_metrics: bool = True,
    session_mode: str = "stateful",
) -> Dict[str, Any]:
    """Run multi-turn scenario; state carries over between turns (stateful)."""
    if session_mode != "stateful":
        raise MetricInputError("run_dialogue_scenario 仅用于 stateful；stateless 请用 run_stateless_scenario")
    if score_core_metrics:
        _require_llm_and_driver(llm, neo4j_driver, context=f"scenario {scenario.get('name')}")

    cfg = pipeline_config or get_pipeline_config()
    name = scenario.get("name", "unnamed")
    turns = scenario.get("turns") or []
    if not turns:
        raise ValueError(f"scenario {name} 无 turns")

    state = make_initial_state(turns[0]["query"], session_mode="stateful")
    turn_results: List[Dict[str, Any]] = []
    turn1_p_star: Optional[List[str]] = None

    for i, turn in enumerate(turns, 1):
        q = turn["query"]
        if i > 1:
            state["previous_query"] = turns[i - 2]["query"]
            state["original_query"] = q
            state["rewritten_query"] = ""
        if verbose:
            print(f"\n  Turn {i}: {q[:70]}")
        try:
            state = graph_app.invoke(state)
        except Exception as exc:
            err = str(exc)
            turn_results.append({"turn": i, "query": q, "error": err, "session_mode": session_mode})
            if verbose:
                print(f"  ❌ Turn {i} pipeline 失败: {err[:200]}")
            break

        answer = state.get("final_answer") or ""
        relevancy = (
            _calculate_relevancy(q, answer, embedder) if embedder is not None else None
        )
        exp_kappa = cfg.expected_kappa_for_turn(i, turn.get("expected_kappa"))
        exp_l = cfg.expected_l_for_turn(i, turn.get("expected_l"))
        act_kappa = state.get("kappa")
        act_l = state.get("path_level")
        kappa_ok = (exp_kappa is None) or (act_kappa == exp_kappa)
        l_ok = (exp_l is None) or (act_l == exp_l)

        row: Dict[str, Any] = {
            "turn": i,
            "query": q,
            "kappa": act_kappa,
            "path_level": act_l,
            "modules": state.get("target_subgraphs"),
            "|P*|": len(state.get("candidate_mp_ids") or []),
            "|G_sub|": len(state.get("gsub_mp_ids") or []),
            "answer_length": len(answer),
            "relevancy_score": relevancy,
            "expected_kappa": exp_kappa,
            "expected_l": exp_l,
            "expected_modules": turn.get("expected_modules")
            or (scenario.get("expected_modules_turn1") if i == 1 else None),
            "kappa_ok": kappa_ok,
            "l_ok": l_ok,
            "session_mode": session_mode,
        }

        if i == 1:
            turn1_p_star = list(state.get("candidate_mp_ids") or [])

        if score_core_metrics:
            try:
                metrics = score_turn_core_metrics(
                    state=state,
                    turn=turn,
                    query=q,
                    llm=llm,
                    neo4j_driver=neo4j_driver,
                    turn_index=i,
                    turn1_p_star=turn1_p_star if i >= 2 else None,
                )
                row.update(metrics)
            except (TurnMetricError, LLMJudgeError, MetricInputError) as exc:
                row["error"] = str(exc)
                turn_results.append(row)
                break

        turn_results.append(row)

    return {
        "name": name,
        "source_no": scenario.get("source_no"),
        "turns": turn_results,
        "pipeline_variant": cfg.variant,
        "session_mode": session_mode,
    }


def run_stateless_scenario(
    graph_app,
    make_initial_state: Callable[[str], Dict],
    scenario: Dict[str, Any],
    verbose: bool = True,
    embedder=None,
    pipeline_config: Optional[PipelineConfig] = None,
    llm=None,
    neo4j_driver=None,
    score_core_metrics: bool = True,
) -> Dict[str, Any]:
    """Each turn is an independent invoke; Turn1 P* saved for Turn2 anchor overlap."""
    if score_core_metrics:
        _require_llm_and_driver(llm, neo4j_driver, context=f"stateless scenario {scenario.get('name')}")

    cfg = pipeline_config or get_pipeline_config()
    name = scenario.get("name", "unnamed")
    turns = scenario.get("turns") or []
    if not turns:
        raise ValueError(f"scenario {name} 无 turns")

    turn_results: List[Dict[str, Any]] = []
    turn1_p_star: Optional[List[str]] = None

    for i, turn in enumerate(turns, 1):
        q = turn["query"]
        if verbose:
            print(f"\n  Turn {i} (stateless): {q[:70]}")
        state = make_initial_state(q, session_mode="stateless")
        try:
            state = graph_app.invoke(state)
        except Exception as exc:
            err = str(exc)
            turn_results.append({"turn": i, "query": q, "error": err, "session_mode": "stateless"})
            if verbose:
                print(f"  ❌ Turn {i} pipeline 失败: {err[:200]}")
            break

        answer = state.get("final_answer") or ""
        relevancy = (
            _calculate_relevancy(q, answer, embedder) if embedder is not None else None
        )
        exp_kappa = "first_turn"
        exp_l = None
        act_kappa = state.get("kappa")
        act_l = state.get("path_level")

        row: Dict[str, Any] = {
            "turn": i,
            "query": q,
            "kappa": act_kappa,
            "path_level": act_l,
            "modules": state.get("target_subgraphs"),
            "|P*|": len(state.get("candidate_mp_ids") or []),
            "|G_sub|": len(state.get("gsub_mp_ids") or []),
            "answer_length": len(answer),
            "relevancy_score": relevancy,
            "expected_kappa": exp_kappa,
            "expected_l": exp_l,
            "kappa_ok": act_kappa == exp_kappa,
            "l_ok": True,
            "session_mode": "stateless",
        }

        if i == 1:
            turn1_p_star = list(state.get("candidate_mp_ids") or [])

        if score_core_metrics:
            try:
                metrics = score_turn_core_metrics(
                    state=state,
                    turn=turn,
                    query=q,
                    llm=llm,
                    neo4j_driver=neo4j_driver,
                    turn_index=i,
                    turn1_p_star=turn1_p_star if i >= 2 else None,
                )
                row.update(metrics)
            except (TurnMetricError, LLMJudgeError, MetricInputError) as exc:
                row["error"] = str(exc)
                turn_results.append(row)
                break

        turn_results.append(row)

    return {
        "name": name,
        "source_no": scenario.get("source_no"),
        "turns": turn_results,
        "pipeline_variant": cfg.variant,
        "session_mode": "stateless",
    }


def evaluate_dialogue_scenarios(
    graph_app,
    make_initial_state: Callable[[str], Dict],
    scenarios: Sequence[Dict[str, Any]],
    embedder=None,
    pipeline_config: Optional[PipelineConfig] = None,
    verbose: bool = True,
    llm=None,
    neo4j_driver=None,
    session_mode: str = "stateful",
    score_core_metrics: bool = True,
    dialogue_test_set: Optional[str] = None,
    olap_modes: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate dialogue scenarios with optional OLAP core metrics."""
    cfg = pipeline_config or get_pipeline_config()
    if session_mode not in ("stateful", "stateless"):
        raise MetricInputError(f"无效 session_mode: {session_mode}")

    runner = run_stateless_scenario if session_mode == "stateless" else run_dialogue_scenario
    scenario_results: List[Dict[str, Any]] = []
    for scenario in scenarios:
        if verbose:
            print(f"\nScenario: {scenario.get('name')} [{session_mode}]")
        scenario_results.append(
            runner(
                graph_app,
                make_initial_state,
                scenario,
                verbose=verbose,
                embedder=embedder,
                pipeline_config=cfg,
                llm=llm,
                neo4j_driver=neo4j_driver,
                score_core_metrics=score_core_metrics,
            )
        )

    all_turns = [t for s in scenario_results for t in s["turns"] if "error" not in t]
    failed_turns = [t for s in scenario_results for t in s["turns"] if "error" in t]
    with_kappa_exp = [t for t in all_turns if t.get("expected_kappa")]
    with_l_exp = [t for t in all_turns if t.get("expected_l")]
    turn2_plus = [t for t in all_turns if t["turn"] >= 2]
    relevancy_vals = [t["relevancy_score"] for t in all_turns if t.get("relevancy_score") is not None]

    summary: Dict[str, Any] = {
        "scenarios_total": len(scenarios),
        "scenarios_completed": sum(
            1 for s in scenario_results if not any("error" in t for t in s["turns"])
        ),
        "turns_total": sum(len(s["turns"]) for s in scenario_results),
        "turns_ok": len(all_turns),
        "turns_failed": len(failed_turns),
        "kappa_hit_rate": float(np.mean([1.0 if t["kappa_ok"] else 0.0 for t in with_kappa_exp]))
        if with_kappa_exp
        else 0.0,
        "l_hit_rate": float(np.mean([1.0 if t["l_ok"] else 0.0 for t in with_l_exp]))
        if with_l_exp
        else 0.0,
        "avg_relevancy": float(np.mean(relevancy_vals)) if relevancy_vals else 0.0,
        "turn2_plus_avg_relevancy": float(
            np.mean([t["relevancy_score"] for t in turn2_plus if t.get("relevancy_score") is not None])
        )
        if turn2_plus
        else 0.0,
        "pipeline_variant": cfg.variant,
        "session_mode": session_mode,
        "score_core_metrics": score_core_metrics,
        "dialogue_test_set": dialogue_test_set,
        "olap_modes": olap_modes,
    }
    if score_core_metrics:
        summary.update(_aggregate_core_metrics(all_turns))

    return {"summary": summary, "scenarios": scenario_results}


def _paired_turn_metrics(
    stateful_report: Dict[str, Any],
    stateless_report: Dict[str, Any],
    turn_number: int,
) -> List[Dict[str, Any]]:
    stateful_by_name = {s["name"]: s for s in stateful_report["scenarios"]}
    stateless_by_name = {s["name"]: s for s in stateless_report["scenarios"]}
    if set(stateful_by_name) != set(stateless_by_name):
        raise MetricInputError("Stateful/Stateless scenario 名称集合不一致，无法配对")

    rows: List[Dict[str, Any]] = []
    for name in sorted(stateful_by_name):
        st_turns = {t["turn"]: t for t in stateful_by_name[name]["turns"]}
        sl_turns = {t["turn"]: t for t in stateless_by_name[name]["turns"]}
        if turn_number not in st_turns or turn_number not in sl_turns:
            continue
        st = st_turns[turn_number]
        sl = sl_turns[turn_number]
        if "error" in st or "error" in sl:
            rows.append({"scenario": name, "turn": turn_number, "error": "turn failed in one arm"})
            continue
        row: Dict[str, Any] = {"scenario": name, "turn": turn_number}
        for key in CORE_METRIC_KEYS:
            if key not in st or key not in sl:
                if key == "anchor_overlap" and turn_number == 1:
                    continue
                row[f"{key}_stateful"] = st.get(key)
                row[f"{key}_stateless"] = sl.get(key)
                row[f"{key}_delta"] = None
                continue
            sv, lv = st.get(key), sl.get(key)
            if sv is None or lv is None:
                row[f"{key}_delta"] = None
            else:
                row[f"{key}_delta"] = float(sv) - float(lv)
            row[f"{key}_stateful"] = sv
            row[f"{key}_stateless"] = lv
        rows.append(row)
    return rows


def evaluate_olap_comparison(
    stateful_report: Dict[str, Any],
    stateless_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Paired comparison: Turn1 sanity + Turn2 core Δ (Stateful − Stateless)."""
    turn1_pairs = _paired_turn_metrics(stateful_report, stateless_report, turn_number=1)
    turn2_pairs = _paired_turn_metrics(stateful_report, stateless_report, turn_number=2)

    def _avg_delta(pairs: Sequence[Dict[str, Any]], key: str) -> Optional[float]:
        deltas = [p[f"{key}_delta"] for p in pairs if p.get(f"{key}_delta") is not None]
        return float(np.mean(deltas)) if deltas else None

    turn1_summary = {
        key: {
            "stateful": _mean_optional([p.get(f"{key}_stateful") for p in turn1_pairs]),
            "stateless": _mean_optional([p.get(f"{key}_stateless") for p in turn1_pairs]),
            "delta": _avg_delta(turn1_pairs, key),
        }
        for key in CORE_METRIC_KEYS
        if key != "anchor_overlap"
    }

    turn2_summary = {
        key: {
            "stateful": _mean_optional([p.get(f"{key}_stateful") for p in turn2_pairs]),
            "stateless": _mean_optional([p.get(f"{key}_stateless") for p in turn2_pairs]),
            "delta": _avg_delta(turn2_pairs, key),
        }
        for key in CORE_METRIC_KEYS
    }

    return {
        "turn1_sanity": turn1_summary,
        "turn2_delta": turn2_summary,
        "turn1_pairs": turn1_pairs,
        "turn2_pairs": turn2_pairs,
        "paired_scenarios_turn2": len(turn2_pairs),
    }


def _flag(enabled: bool) -> str:
    return "✅" if enabled else "❌"


def _fmt_metric(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _core_metric_summary_lines(summary: Dict[str, Any], prefix: str) -> List[str]:
    lines = []
    mapping = [
        ("recall_at_10", f"{prefix}_avg_recall_at_10"),
        ("precision_at_10", f"{prefix}_avg_precision_at_10"),
        ("anchor_overlap", f"{prefix}_avg_anchor_overlap"),
        ("faithfulness", f"{prefix}_avg_faithfulness"),
        ("answer_relevance", f"{prefix}_avg_answer_relevance"),
        ("context_precision", f"{prefix}_avg_context_precision"),
    ]
    for label, key in mapping:
        if key in summary and summary[key] is not None:
            lines.append(f"- {label}: {_fmt_metric(summary[key])}")
    return lines


def format_eval_log_md(
    *,
    meta: Dict[str, Any],
    single_report: Optional[Dict[str, Any]] = None,
    dialogue_report: Optional[Dict[str, Any]] = None,
    ablation_compare: Optional[Dict[str, Any]] = None,
    olap_compare: Optional[Dict[str, Any]] = None,
) -> str:
    """Build markdown section for one eval run."""
    ts = meta.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    variant = meta.get("pipeline_variant", "full")
    flags = meta.get("feature_flags") or {}

    lines = [
        f"## Run {ts}",
        "",
        "| 项 | 值 |",
        "|----|-----|",
        f"| version | {meta.get('version', '(未指定)')} |",
        f"| dialogue_test_set | {meta.get('dialogue_test_set', '—')} |",
        f"| olap_modes | {meta.get('olap_modes', '—')} |",
        f"| PIPELINE_VARIANT | `{variant}` |",
        f"| session_mode | {meta.get('session_mode', dialogue_report['summary'].get('session_mode') if dialogue_report else '—')} |",
        f"| retrieval_scoring | {meta.get('retrieval_scoring', 'qrels优先 / 无则 LLM judge')} |",
        f"| multi_dim_retrieval | {_flag(flags.get('multi_dim_retrieval', variant == 'full'))} |",
        f"| kappa_routing | {_flag(flags.get('kappa_routing_drill_roll_sibling', variant == 'full'))} |",
        f"| gsub_rank_bias | {_flag(flags.get('gsub_rank_bias', flags.get('gsub_constraint', variant == 'full')))} |",
        f"| recall_module_flat | {_flag(flags.get('recall_module_flat', True))} |",
        f"| path_level_navigation | {_flag(flags.get('path_level_mid_low_navigation', variant == 'full'))} |",
        f"| python | {meta.get('python', sys.executable)} |",
        f"| duration_sec | {meta.get('duration_sec', '—')} |",
        f"| exit | {meta.get('exit', '—')} |",
        "",
    ]

    if single_report:
        s = single_report["summary"]
        lines.extend(
            [
                "### 单轮综合 (questions.csv)",
                f"- success: {s['success']}/{s['total']}",
                f"- route hit_any: {s['route_hit_any_rate']*100:.1f}%",
                f"- route hit_all: {s['route_hit_all_rate']*100:.1f}%",
                f"- citation rate: {s['citation_rate']*100:.1f}%",
                f"- avg relevancy (legacy): {s['avg_relevancy']:.3f}",
                f"- avg precision (legacy citation): {s['avg_precision']*100:.1f}%",
                "",
            ]
        )

    if dialogue_report:
        s = dialogue_report["summary"]
        lines.extend(
            [
                "### 多轮对话 (dialogue_test_cases.json)",
                f"- test_set: {s.get('dialogue_test_set', meta.get('dialogue_test_set', '—'))}",
                f"- scenarios completed: {s['scenarios_completed']}/{s['scenarios_total']}",
                f"- turns OK: {s['turns_ok']}/{s['turns_total']} (failed: {s['turns_failed']})",
                f"- κ hit rate (mechanism): {s['kappa_hit_rate']*100:.1f}%",
                f"- l hit rate (mechanism): {s['l_hit_rate']*100:.1f}%",
                f"- avg relevancy (legacy): {s['avg_relevancy']:.3f}",
            ]
        )
        if s.get("score_core_metrics"):
            lines.append(f"- qrels scored turns: {s.get('qrels_scored_turns', 0)}")
            lines.append(f"- LLM-judge scored turns: {s.get('llm_judge_scored_turns', 0)}")
            lines.extend(["", "#### Turn1 核心指标"])
            lines.extend(_core_metric_summary_lines(s, "turn1") or ["- (无)"])
            lines.extend(["", "#### Turn2 核心指标"])
            lines.extend(_core_metric_summary_lines(s, "turn2") or ["- (无)"])
        lines.append("")

    if olap_compare:
        lines.extend(
            [
                "### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)",
                "| metric | Stateful | Stateless | Δ |",
                "|--------|----------|-----------|---|",
            ]
        )
        for key, vals in olap_compare.get("turn1_sanity", {}).items():
            lines.append(
                f"| {key} | {_fmt_metric(vals.get('stateful'))} | "
                f"{_fmt_metric(vals.get('stateless'))} | {_fmt_metric(vals.get('delta'))} |"
            )
        lines.extend(
            [
                "",
                "### Turn2 Core Δ (Stateful − Stateless, 主结论)",
                "| metric | Stateful | Stateless | Δ |",
                "|--------|----------|-----------|---|",
            ]
        )
        for key, vals in olap_compare.get("turn2_delta", {}).items():
            lines.append(
                f"| {key} | {_fmt_metric(vals.get('stateful'))} | "
                f"{_fmt_metric(vals.get('stateless'))} | {_fmt_metric(vals.get('delta'))} |"
            )
        lines.append("")

    if ablation_compare:
        lines.extend(
            [
                "### Multidim Ablation (full vs no_hierarchy, Stateful Turn2+)",
                "| metric | full | no_hierarchy | Δ |",
                "|--------|------|--------------|---|",
            ]
        )
        for row in ablation_compare.get("rows", []):
            lines.append(
                f"| {row['metric']} | {row['full']} | {row['no_hierarchy']} | {row['delta']} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def append_eval_log(content: str, log_path: Optional[str | Path] = None) -> Path:
    path = Path(log_path) if log_path else DEFAULT_EVAL_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = "<!-- APPEND_BELOW -->"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            raise ValueError(f"eval log 缺少追加标记 {marker}: {path}")
        updated = text.replace(marker, f"{marker}\n\n{content}")
    else:
        updated = f"# Retrieval Pipeline Evaluation Log\n\n{marker}\n\n{content}"
    path.write_text(updated, encoding="utf-8")
    return path


def compare_ablation_reports(
    full_dialogue: Dict[str, Any],
    flat_dialogue: Dict[str, Any],
) -> Dict[str, Any]:
    """Build comparison table rows from two Stateful dialogue evaluation reports."""
    fs = full_dialogue["summary"]
    ns = flat_dialogue["summary"]

    def _delta(a: Optional[float], b: Optional[float], as_pct: bool = False) -> str:
        if a is None or b is None:
            return "—"
        d = a - b
        if as_pct:
            return f"{d * 100:+.1f}%"
        return f"{d:+.3f}"

    def _row(metric: str, key: str, as_pct: bool = False) -> Dict[str, str]:
        a = fs.get(key)
        b = ns.get(key)
        return {
            "metric": metric,
            "full": _fmt_metric(a),
            "no_hierarchy": _fmt_metric(b),
            "delta": _delta(a, b, as_pct=as_pct),
        }

    rows = [
        _row("Turn2 recall@10", "turn2_avg_recall_at_10"),
        _row("Turn2 precision@10", "turn2_avg_precision_at_10"),
        _row("Turn2 anchor_overlap", "turn2_avg_anchor_overlap"),
        _row("Turn2 faithfulness", "turn2_avg_faithfulness"),
        _row("Turn2 answer_relevance", "turn2_avg_answer_relevance"),
        _row("Turn2 context_precision", "turn2_avg_context_precision"),
        _row("Turn2+ recall@10", "turn2_plus_avg_recall_at_10"),
        _row("Turn2+ precision@10", "turn2_plus_avg_precision_at_10"),
        _row("κ hit rate (mechanism)", "kappa_hit_rate", as_pct=True),
        _row("l hit rate (mechanism)", "l_hit_rate", as_pct=True),
        _row("avg relevancy (legacy)", "avg_relevancy"),
        {
            "metric": "turns failed",
            "full": str(fs.get("turns_failed", "—")),
            "no_hierarchy": str(ns.get("turns_failed", "—")),
            "delta": str(int(fs.get("turns_failed", 0)) - int(ns.get("turns_failed", 0))),
        },
    ]
    return {"rows": rows}


def print_evaluation_summary(report: Dict[str, Any]) -> None:
    s = report["summary"]
    print("\n" + "=" * 72)
    print("综合评估摘要（单次 invoke / 用例）")
    print("=" * 72)
    print(f"  成功/总数     : {s['success']}/{s['total']}")
    print(f"  路由 hit_any  : {s['route_hit_any_rate']*100:.1f}%")
    print(f"  路由 hit_all  : {s['route_hit_all_rate']*100:.1f}%")
    print(f"  Citation Rate : {s['citation_rate']*100:.1f}%")
    print(f"  平均覆盖率    : {s['avg_coverage']*100:.1f}%")
    print(f"  平均相关性    : {s['avg_relevancy']:.3f}")
    print(f"  平均精确度    : {s['avg_precision']*100:.1f}%")
