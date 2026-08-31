"""OLAP session mode: stateful (full) vs stateless (flat retrieval baseline)."""
from __future__ import annotations

from typing import Any, Mapping

SESSION_STATEFUL = "stateful"
SESSION_STATELESS = "stateless"
VALID_SESSION_MODES = frozenset({SESSION_STATEFUL, SESSION_STATELESS})

# path_level sentinel when Recall does not filter mid/low
PATH_LEVEL_FLAT = "flat"


def normalize_session_mode(mode: str | None) -> str:
    m = (mode or SESSION_STATEFUL).strip().lower()
    if m not in VALID_SESSION_MODES:
        raise ValueError(
            f"无效 session_mode={mode!r}；合法值: {sorted(VALID_SESSION_MODES)}"
        )
    return m


def is_stateless(state: Mapping[str, Any]) -> bool:
    return normalize_session_mode(state.get("session_mode")) == SESSION_STATELESS
