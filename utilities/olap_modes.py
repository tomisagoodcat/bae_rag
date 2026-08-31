"""OLAP 实验模式（κ）开关：多选 / 预设，联动 pipeline 路由与 dialogue 测试集筛选。

CLI::

    python utilities/run_retrieval_eval.py --olap-modes core --test-set legacy10
    python utilities/run_retrieval_eval.py --olap-modes drill_down,roll_up,first_turn

环境变量 ``OLAP_MODES`` 与 ``configure_olap_modes()`` 等价。

预设:
  - core: first_turn + drill_down + roll_up（classic_3 / legacy10）
  - extended: core + sibling_nav
  - all: 五种 κ 全开
"""
from __future__ import annotations

import os
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

from utilities.dialogue_routing import VALID_KAPPA

MODE_FIRST = "first_turn"
MODE_DRILL_DOWN = "drill_down"
MODE_ROLL_UP = "roll_up"
MODE_SIBLING = "sibling_nav"
MODE_DRILL_ACROSS = "drill_across"

ALL_OLAP_MODES: FrozenSet[str] = frozenset(VALID_KAPPA)

PRESET_CORE: FrozenSet[str] = frozenset({MODE_FIRST, MODE_DRILL_DOWN, MODE_ROLL_UP})
PRESET_EXTENDED: FrozenSet[str] = PRESET_CORE | {MODE_SIBLING}
PRESET_ALL: FrozenSet[str] = ALL_OLAP_MODES

OLAP_MODE_PRESETS: Dict[str, FrozenSet[str]] = {
    "core": PRESET_CORE,
    "extended": PRESET_EXTENDED,
    "all": PRESET_ALL,
}

_KAPPA_PROMPT_LINES = {
    MODE_FIRST: "- first_turn: only if user clearly resets topic",
    MODE_DRILL_DOWN: "- drill_down: same r, l=low, expand detail paths",
    MODE_ROLL_UP: "- roll_up: same r, l=mid, summarize / aggregate",
    MODE_SIBLING: "- sibling_nav: switch top-level module, keep l",
    MODE_DRILL_ACROSS: "- drill_across: l=low, cross-module detail pivot",
}


def parse_olap_modes_spec(spec: Optional[str] = None) -> Optional[FrozenSet[str]]:
    """解析预设名或逗号分隔 κ 列表；空 → None（不限制）。"""
    raw = (spec or os.environ.get("OLAP_MODES") or "").strip()
    if not raw:
        return None
    key = raw.lower()
    if key in OLAP_MODE_PRESETS:
        return OLAP_MODE_PRESETS[key]
    modes = frozenset(m.strip().lower() for m in raw.split(",") if m.strip())
    unknown = modes - ALL_OLAP_MODES
    if unknown:
        raise ValueError(
            f"未知 olap mode: {sorted(unknown)}；"
            f"合法 κ: {sorted(ALL_OLAP_MODES)}；预设: {sorted(OLAP_MODE_PRESETS)}"
        )
    return modes


def configure_olap_modes(spec: Optional[str] = None) -> Optional[FrozenSet[str]]:
    """写入 PipelineConfig.allowed_olap_modes。"""
    from utilities.pipeline_config import set_olap_modes

    allowed = parse_olap_modes_spec(spec)
    set_olap_modes(allowed)
    return allowed


def get_active_olap_modes() -> Optional[FrozenSet[str]]:
    from utilities.pipeline_config import get_pipeline_config

    return get_pipeline_config().allowed_olap_modes


def effective_modes_for_scenario_filter(allowed: FrozenSet[str]) -> FrozenSet[str]:
    """多轮场景通常含首轮；筛选 JSON 时自动允许 first_turn。"""
    if MODE_FIRST in allowed:
        return allowed
    return allowed | {MODE_FIRST}


def scenario_expected_kappas(scenario: Dict[str, Any]) -> FrozenSet[str]:
    found: set = set()
    for turn in scenario.get("turns") or []:
        k = (turn.get("expected_kappa") or "").strip()
        if k:
            found.add(k)
    return frozenset(found)


def scenario_matches_olap_modes(
    scenario: Dict[str, Any], allowed: Optional[FrozenSet[str]]
) -> bool:
    """保留 expected_kappa 全部落在允许集合内的 scenario。"""
    if not allowed:
        return True
    expected = scenario_expected_kappas(scenario)
    if not expected:
        return True
    eff = effective_modes_for_scenario_filter(allowed)
    return expected.issubset(eff)


def filter_scenarios_by_olap_modes(
    scenarios: Sequence[Dict[str, Any]],
    allowed: Optional[FrozenSet[str]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not allowed:
        return list(scenarios), {
            "olap_modes": None,
            "olap_modes_filter": "disabled",
            "scenarios_after_olap_filter": len(scenarios),
        }
    selected = [s for s in scenarios if scenario_matches_olap_modes(s, allowed)]
    return selected, {
        "olap_modes": ",".join(sorted(allowed)),
        "olap_modes_filter": "expected_kappa ⊆ allowed",
        "scenarios_after_olap_filter": len(selected),
        "scenarios_dropped_by_olap": len(scenarios) - len(selected),
    }


def clamp_routed_olap(
    kappa: str,
    path_level: str,
    allowed: FrozenSet[str],
) -> Tuple[str, str]:
    """LLM 返回未启用的 κ 时，映射到仍开启的算子（优先 roll_up，避免 G_sub 空）。"""
    if kappa in allowed:
        return kappa, path_level
    if MODE_ROLL_UP in allowed:
        return MODE_ROLL_UP, "mid"
    if MODE_DRILL_DOWN in allowed:
        return MODE_DRILL_DOWN, "low"
    if MODE_SIBLING in allowed:
        return MODE_SIBLING, path_level if path_level in ("mid", "low") else "mid"
    return MODE_FIRST, path_level if path_level in ("mid", "low") else "mid"


def olap_mode_prompt_lines(allowed: Optional[FrozenSet[str]]) -> str:
    modes = sorted(allowed or ALL_OLAP_MODES)
    return "\n".join(_KAPPA_PROMPT_LINES[m] for m in modes if m in _KAPPA_PROMPT_LINES)


def format_olap_modes_banner(allowed: Optional[FrozenSet[str]]) -> str:
    if not allowed:
        return "olap_modes=(all, unrestricted)"
    return f"olap_modes={','.join(sorted(allowed))}"
