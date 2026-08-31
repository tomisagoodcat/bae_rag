"""Low reviewer — diagnosis for local SHACL warnings / hard issues."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.paths import REPO_ROOT

ALLOWED_DECISIONS = {"ACCEPT", "REPAIR", "EXPAND_NEIGHBOR", "FLAG"}


def _load_prompt() -> str:
    path = REPO_ROOT / "kg_build_pipeline" / "prompts" / "low_reviewer.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        "Review low-level KG SHACL report. Return JSON with decision, "
        "needs_neighbor_pass, suggested_rule_ids, issues."
    )


def _parse_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def review_low_parent(
    *,
    cfg: PipelineConfig,
    filename: str,
    parent_name: Optional[str],
    parent_labels: List[str],
    shacl_report: Dict[str, Any],
    context_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Call Qwen (or fallback heuristic) for Low local review."""
    hard = shacl_report.get("hard_count") or len(shacl_report.get("hard_violations") or [])
    warn = shacl_report.get("warning_count") or len(shacl_report.get("warnings") or [])

    # Heuristic fallback when no API key: expand on warnings, repair on hard
    api_key = os.environ.get("QWEN_API_KEY") or ""
    if not api_key:
        rule_ids = [
            str(i.get("rule_id"))
            for i in (shacl_report.get("hard_violations") or [])
            + (shacl_report.get("warnings") or [])
            if i.get("rule_id")
        ]
        has_h01b = any(str(r).upper().replace("_", "-") == "H01-B" for r in rule_ids)
        if has_h01b and hard:
            decision = "REPAIR"
        elif hard:
            decision = "FLAG"
        elif warn:
            decision = "EXPAND_NEIGHBOR"
        else:
            decision = "ACCEPT"
        return {
            "decision": decision,
            "needs_neighbor_pass": bool(warn and not hard),
            "suggested_rule_ids": rule_ids,
            "issues": shacl_report.get("hard_violations") or [],
            "source": "heuristic",
        }

    prompt = _load_prompt()
    user = {
        "filename": filename,
        "parent_name": parent_name,
        "parent_labels": parent_labels,
        "context": context_summary,
        "hard_count": hard,
        "warning_count": warn,
        "hard_violations": (shacl_report.get("hard_violations") or [])[:20],
        "warnings": (shacl_report.get("warnings") or [])[:20],
    }
    try:
        from openai import OpenAI

        base = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        model = os.environ.get("QWEN_MODEL", "qwen-plus")
        client = OpenAI(api_key=api_key, base_url=base)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        data = _parse_json(content)
    except Exception as exc:
        return {
            "decision": "REPAIR" if hard else ("EXPAND_NEIGHBOR" if warn else "ACCEPT"),
            "needs_neighbor_pass": bool(warn),
            "suggested_rule_ids": [
                str(i.get("rule_id"))
                for i in (shacl_report.get("warnings") or [])
                if i.get("rule_id")
            ],
            "issues": [],
            "source": "error_fallback",
            "error": str(exc),
        }

    decision = str(data.get("decision") or "ACCEPT").upper()
    if decision not in ALLOWED_DECISIONS:
        decision = "REPAIR" if hard else "ACCEPT"
    needs = data.get("needs_neighbor_pass")
    if needs is None:
        needs = decision == "EXPAND_NEIGHBOR" or (
            warn > 0 and decision in {"EXPAND_NEIGHBOR", "REPAIR"}
        )
    return {
        "decision": decision,
        "needs_neighbor_pass": bool(needs),
        "suggested_rule_ids": list(data.get("suggested_rule_ids") or []),
        "issues": list(data.get("issues") or []),
        "source": "qwen",
        "raw": data,
    }
