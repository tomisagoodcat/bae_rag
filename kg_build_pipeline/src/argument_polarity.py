"""Explicit-challenge lexicon for mp_challenges extraction gating."""
from __future__ import annotations

from typing import Any, Iterable, List

# Do not use bare "challenge" / "挑战": they occur in risk/future-work prose.
_CHALLENGE_MARKERS = (
    "contradict",
    "refute",
    "inconsistent with",
    "undermines",
    "fails to confirm",
    "disprove",
    "not supported by",
    "contrary to",
    "反驳",
    "否定了",
    "未能证实",
    "并不支持",
    "不能支持",
    "不支持该",
    "相矛盾",
    "相悖",
    "推翻了",
    "与此不符",
    "与之不符",
    "结果不符",
)


def text_has_challenge_language(text: str | None) -> bool:
    """True when the span contains explicit refute/contradict language."""
    raw = text or ""
    if not raw.strip():
        return False
    lower = raw.lower()
    for marker in _CHALLENGE_MARKERS:
        if marker.isascii():
            if marker in lower:
                return True
        elif marker in raw:
            return True
    return False


def node_text(node: Any) -> str:
    if node is None:
        return ""
    getter = getattr(node, "get_text", None)
    if callable(getter):
        return getter() or ""
    return str(getattr(node, "text", "") or "")


def filter_nodes_with_challenge_language(nodes: Iterable[Any]) -> List[Any]:
    """Keep only chunks whose own text has explicit refute language."""
    return [n for n in nodes if text_has_challenge_language(node_text(n))]


def should_skip_challenges_extract(relation_label: str, text: str | None) -> bool:
    """Skip LLM when the schema row is mp_challenges but the text has no refute cue."""
    if str(relation_label or "").strip() != "mp_challenges":
        return False
    return not text_has_challenge_language(text)
