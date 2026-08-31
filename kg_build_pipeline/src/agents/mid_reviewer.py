"""Qwen Mid Reviewer — diagnosis only; does not mutate the KG."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.paths import REPO_ROOT
from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS

ALLOWED_ACTIONS = {"KEEP", "DELETE", "RETYPE", "EXPAND_SPAN", "REEXTRACT"}


def _load_prompt() -> str:
    path = REPO_ROOT / "kg_build_pipeline" / "prompts" / "mid_reviewer.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        "Review the mid-level KG. Return JSON only with type_score, relation_score, "
        "coverage_score, overall_score, decision, issues."
    )


def _overall(type_s: float, rel_s: float, cov_s: float) -> float:
    return round(0.3 * type_s + 0.35 * rel_s + 0.35 * cov_s, 4)


def fetch_mid_graph_summary(
    driver: Driver,
    database: str,
    filename: str,
    limit: int = 80,
) -> Dict[str, Any]:
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    mid_labels = sorted(MID_CORE_ENTITY_LABELS)
    with driver.session(database=database) as session:
        nodes = session.run(
            """
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $mid_labels)
              AND coalesce(n.whu_rejected, false) = false
              AND (
                n.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
                  WHERE c.filename = $filename
                }
              )
            RETURN labels(n) AS labels, n.WHU_HASNAME AS name,
                   left(coalesce(n.WHU_HASORIGINALTEXT, ''), 240) AS original_text
            LIMIT $limit
            """,
            filename=filename,
            source_doc=source_doc,
            mid_labels=mid_labels,
            limit=limit,
        ).data()
        rels = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE any(l IN labels(a) WHERE l IN $mid_labels)
              AND any(l IN labels(b) WHERE l IN $mid_labels)
              AND coalesce(a.whu_rejected, false) = false
              AND coalesce(b.whu_rejected, false) = false
              AND (
                a.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(a)
                  WHERE c.filename = $filename
                }
              )
            RETURN labels(a) AS a_labels, a.WHU_HASNAME AS a_name,
                   type(r) AS rel,
                   labels(b) AS b_labels, b.WHU_HASNAME AS b_name
            LIMIT $limit
            """,
            filename=filename,
            source_doc=source_doc,
            mid_labels=mid_labels,
            limit=limit,
        ).data()
        chunks = session.run(
            """
            MATCH (c:Chunk)
            WHERE c.filename = $filename
            RETURN c.id AS chunk_id, c.section_role AS section_role,
                   left(coalesce(c.text, ''), 500) AS text
            LIMIT 40
            """,
            filename=filename,
        ).data()
    return {"nodes": nodes, "relations": rels, "chunks": chunks}


def _parse_json_payload(text: str) -> Dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def review_mid_document(
    cfg: PipelineConfig,
    driver: Driver,
    filename: str,
    validation_report: Dict[str, Any],
    mid_schema_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call Qwen reviewer. Raises if QWEN_API_KEY missing (no silent PASS)."""
    api_key = os.environ.get("QWEN_API_KEY") or (
        (cfg.raw.get("reviewer") or {}).get("qwen_api_key") or ""
    )
    if isinstance(api_key, str) and api_key.startswith("${"):
        api_key = os.environ.get("QWEN_API_KEY", "")
    if not api_key:
        raise EnvironmentError("QWEN_API_KEY required for mid_quality_gate / Mid Reviewer")

    reviewer_cfg = cfg.raw.get("reviewer") or {}
    model = reviewer_cfg.get("qwen_model", "qwen-plus")
    base_url = reviewer_cfg.get(
        "qwen_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    from neo4j_graphrag.llm import OpenAILLM

    llm = OpenAILLM(
        model_name=model,
        base_url=base_url,
        api_key=api_key,
        model_params={"temperature": 0.1, "max_tokens": 4000},
    )

    graph = fetch_mid_graph_summary(driver, cfg.neo4j_database, filename)
    prompt_tpl = _load_prompt()
    payload = {
        "filename": filename,
        "validation_report": validation_report,
        "mid_graph": graph,
        "mid_schema": mid_schema_summary or {},
    }
    user_msg = (
        prompt_tpl
        + "\n\n# Input\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)[:120000]
        + "\n```\n"
    )
    resp = llm.invoke(user_msg)
    content = resp.content if hasattr(resp, "content") else str(resp)
    data = _parse_json_payload(content)

    type_s = float(data.get("type_score", 0.0))
    rel_s = float(data.get("relation_score", 0.0))
    cov_s = float(data.get("coverage_score", 0.0))
    overall = data.get("overall_score")
    if overall is None:
        overall = _overall(type_s, rel_s, cov_s)
    else:
        overall = float(overall)

    issues = []
    for raw in data.get("issues") or []:
        if not isinstance(raw, dict):
            continue
        action = str(raw.get("suggested_action", "KEEP")).upper()
        if action not in ALLOWED_ACTIONS:
            action = "REEXTRACT"
        issues.append(
            {
                "type": raw.get("type", "UNKNOWN"),
                "rule_id": raw.get("rule_id"),
                "entity": raw.get("entity"),
                "source_chunk": raw.get("source_chunk"),
                "reason": raw.get("reason", ""),
                "suggested_action": action,
                "confidence": float(raw.get("confidence", 0.5)),
            }
        )

    decision = str(data.get("decision", "REEXTRACT")).upper()
    if decision not in {"PASS", "REEXTRACT"}:
        decision = "REEXTRACT"

    return {
        "filename": filename,
        "type_score": type_s,
        "relation_score": rel_s,
        "coverage_score": cov_s,
        "overall_score": overall,
        "decision": decision,
        "issues": issues,
        "raw_preview": content[:500],
    }
