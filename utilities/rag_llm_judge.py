"""LLM-as-judge metrics for RAG / OLAP dialogue evaluation.

Strict mode: parse failures and missing LLM raise explicit errors (no silent defaults).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence

RELEVANCE_BATCH_PROMPT = """You are an evaluation assistant for scientific GraphRAG retrieval.

Given a user query and numbered MetaPath evidence snippets, judge whether each snippet is RELEVANT to answering the query.

Query:
{query}

Evidence snippets:
{items_block}

Return ONLY valid JSON (no markdown fences):
{{"judgments": [{{"index": 1, "relevant": true}}, ...]}}

Rules:
- relevant=true only if the snippet directly helps answer the query.
- One judgment per snippet index listed above.
- Do not invent indices.
"""

FAITHFULNESS_PROMPT = """You are evaluating answer faithfulness for RAG.

Given context, query, and answer, score whether ALL factual claims in the answer are supported by the context.

Query:
{query}

Context:
{context}

Answer:
{answer}

Return ONLY valid JSON:
{{"faithfulness": 0.0}}

Score faithfulness from 0.0 (unsupported / hallucinated) to 1.0 (fully supported).
"""

ANSWER_RELEVANCE_PROMPT = """You are evaluating answer relevance.

Given query and answer, score how directly the answer addresses the query.

Query:
{query}

Answer:
{answer}

Return ONLY valid JSON:
{{"answer_relevance": 0.0}}

Score from 0.0 (irrelevant) to 1.0 (fully addresses the query).
"""

CONTEXT_PRECISION_PROMPT = """You are evaluating context precision (RAGAS-style).

Given a query and ordered context snippets, score precision: the fraction of snippets that are relevant to the query, considering rank order importance (earlier irrelevant snippets hurt more).

Query:
{query}

Ordered context snippets:
{items_block}

Return ONLY valid JSON:
{{"context_precision": 0.0}}

Score from 0.0 to 1.0.
"""


class LLMJudgeError(RuntimeError):
    """Raised when LLM judge invocation or response parsing fails."""


def _llm_text(llm: Any, prompt: str) -> str:
    if llm is None:
        raise LLMJudgeError("LLM judge 需要 llm 实例，但未提供")
    response = llm.invoke(prompt)
    content = getattr(response, "content", response)
    if not isinstance(content, str) or not content.strip():
        raise LLMJudgeError(f"LLM 返回空内容: {response!r}")
    return content.strip()


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise LLMJudgeError(f"LLM 响应无法解析为 JSON: {text[:300]}") from exc
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError as exc2:
            raise LLMJudgeError(f"LLM 响应 JSON 无效: {text[:300]}") from exc2
    if not isinstance(obj, dict):
        raise LLMJudgeError(f"LLM 响应应为 JSON object，实际: {type(obj)}")
    return obj


def _invoke_json(llm: Any, prompt: str) -> Dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            return _extract_json_object(_llm_text(llm, prompt))
        except LLMJudgeError as exc:
            last_err = exc
            prompt = prompt + "\n\nIMPORTANT: Return ONLY raw JSON, no prose."
    raise LLMJudgeError(f"LLM judge 两次解析均失败: {last_err}") from last_err


def _format_items_block(items: Sequence[Dict[str, Any]]) -> str:
    if not items:
        raise LLMJudgeError("judge 输入 items 为空")
    lines = []
    for item in items:
        idx = item.get("rank") or item.get("index")
        mp_id = item.get("mp_id", "?")
        preview = (item.get("preview") or item.get("text") or "").strip()
        if not preview:
            raise LLMJudgeError(f"MetaPath item 缺少 preview: mp_id={mp_id}")
        lines.append(f"[{idx}] mp_id={mp_id}\n{preview[:1200]}")
    return "\n\n".join(lines)


def judge_metapath_relevance(
    llm: Any,
    query: str,
    items: Sequence[Dict[str, Any]],
) -> List[bool]:
    """Return relevance bool per item (same order as items)."""
    if not query.strip():
        raise LLMJudgeError("judge_metapath_relevance: query 为空")
    obj = _invoke_json(
        llm,
        RELEVANCE_BATCH_PROMPT.format(
            query=query.strip(),
            items_block=_format_items_block(items),
        ),
    )
    judgments = obj.get("judgments")
    if not isinstance(judgments, list):
        raise LLMJudgeError(f"judgments 字段缺失或类型错误: {obj}")

    by_index: Dict[int, bool] = {}
    for row in judgments:
        if not isinstance(row, dict):
            raise LLMJudgeError(f"judgment 行应为 dict: {row}")
        idx = row.get("index")
        rel = row.get("relevant")
        if not isinstance(idx, int):
            raise LLMJudgeError(f"judgment index 无效: {row}")
        if not isinstance(rel, bool):
            raise LLMJudgeError(f"judgment relevant 应为 bool: {row}")
        by_index[idx] = rel

    expected = [int(it.get("rank") or it.get("index")) for it in items]
    missing = [i for i in expected if i not in by_index]
    if missing:
        raise LLMJudgeError(f"LLM 未返回全部 index 判定: missing={missing}")

    return [by_index[i] for i in expected]


def judge_faithfulness(llm: Any, query: str, context: str, answer: str) -> float:
    if not context.strip():
        raise LLMJudgeError("judge_faithfulness: context 为空")
    if not answer.strip():
        raise LLMJudgeError("judge_faithfulness: answer 为空")
    obj = _invoke_json(
        llm,
        FAITHFULNESS_PROMPT.format(
            query=query.strip(),
            context=context.strip()[:12000],
            answer=answer.strip()[:8000],
        ),
    )
    score = obj.get("faithfulness")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
        raise LLMJudgeError(f"faithfulness 分数无效: {obj}")
    return float(score)


def judge_answer_relevance(llm: Any, query: str, answer: str) -> float:
    if not answer.strip():
        raise LLMJudgeError("judge_answer_relevance: answer 为空")
    obj = _invoke_json(
        llm,
        ANSWER_RELEVANCE_PROMPT.format(
            query=query.strip(),
            answer=answer.strip()[:8000],
        ),
    )
    score = obj.get("answer_relevance")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
        raise LLMJudgeError(f"answer_relevance 分数无效: {obj}")
    return float(score)


def judge_context_precision(
    llm: Any,
    query: str,
    items: Sequence[Dict[str, Any]],
) -> float:
    obj = _invoke_json(
        llm,
        CONTEXT_PRECISION_PROMPT.format(
            query=query.strip(),
            items_block=_format_items_block(items),
        ),
    )
    score = obj.get("context_precision")
    if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
        raise LLMJudgeError(f"context_precision 分数无效: {obj}")
    return float(score)
