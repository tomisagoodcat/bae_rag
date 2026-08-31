"""多轮对话评估测试集筛选（可切换）。

用法（任选其一）：
  1. CLI: ``python utilities/run_retrieval_eval.py --olap-compare --test-set legacy10``
  2. 环境变量: ``set DIALOGUE_TEST_SET=legacy10``（Windows）/ ``export DIALOGUE_TEST_SET=legacy10``
  3. Notebook: ``load_dialogue_test_cases(test_set="legacy10")``

测试集预设
----------
- ``all``：``dialogue_test_cases.json`` 中的全部 scenario（当前 66 条）。
- ``legacy10``：**严格** legacy 集——仅保留 ``name`` 匹配 ``q01``–``q10`` 的 10 条
  （``^q(0[1-9]|10)_``），与 JSON 中顺序无关；用于与 v3 等同集对比。
- ``first``：取 JSON 列表前 N 条（N 由 ``max_scenarios`` 指定）；**不等同于 legacy10**
  （扩展集后前 10 条可能含 ``gen_*``）。

默认：环境变量未设置时为 ``legacy10``，避免误跑全量 66 条（耗时数小时）。
若需全量，请显式 ``--test-set all`` 或 ``DIALOGUE_TEST_SET=all``。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 与 data/dialogue_test_cases.json 中 hand-crafted 场景一致：q01_ … q10_
LEGACY_SCENARIO_NAME_RE = re.compile(r"^q(0[1-9]|10)_")

TEST_SET_ALL = "all"
TEST_SET_LEGACY10 = "legacy10"
TEST_SET_FIRST = "first"

VALID_TEST_SETS = (TEST_SET_ALL, TEST_SET_LEGACY10, TEST_SET_FIRST)
DEFAULT_TEST_SET = TEST_SET_LEGACY10


def resolve_dialogue_test_set(explicit: Optional[str] = None) -> str:
    """解析测试集名称：CLI/参数 > 环境变量 DIALOGUE_TEST_SET > 默认 legacy10。"""
    raw = (explicit or os.environ.get("DIALOGUE_TEST_SET") or DEFAULT_TEST_SET).strip().lower()
    if raw not in VALID_TEST_SETS:
        raise ValueError(
            f"未知 test_set={raw!r}，可选: {', '.join(VALID_TEST_SETS)}"
        )
    return raw


def is_legacy_scenario(scenario: Dict[str, Any]) -> bool:
    name = str(scenario.get("name") or "")
    return bool(LEGACY_SCENARIO_NAME_RE.match(name))


def filter_dialogue_scenarios(
    scenarios: Sequence[Dict[str, Any]],
    test_set: str,
    *,
    max_scenarios: int = 0,
    olap_modes: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """按 test_set 与 olap_modes 筛选 scenario，返回 (filtered, meta)。"""
    from utilities.olap_modes import (
        filter_scenarios_by_olap_modes,
        format_olap_modes_banner,
        parse_olap_modes_spec,
    )

    test_set = resolve_dialogue_test_set(test_set)
    total_in_file = len(scenarios)
    names_all = [str(s.get("name") or "") for s in scenarios]
    allowed_kappa = parse_olap_modes_spec(olap_modes)

    if test_set == TEST_SET_ALL:
        selected = list(scenarios)
        if max_scenarios > 0:
            selected = selected[:max_scenarios]
        filter_desc = "all scenarios in JSON"
        if max_scenarios > 0:
            filter_desc += f", capped to first {max_scenarios}"

    elif test_set == TEST_SET_LEGACY10:
        selected = [s for s in scenarios if is_legacy_scenario(s)]
        missing = _expected_legacy_names() - {str(s.get("name")) for s in selected}
        if missing:
            raise ValueError(
                f"legacy10 缺少场景: {sorted(missing)}；"
                f"请检查 {', '.join(names_all[:3])}… 等 name 字段"
            )
        if len(selected) != 10:
            raise ValueError(f"legacy10 应恰好 10 条，实际 {len(selected)}")
        # legacy10 忽略 max_scenarios（避免与「严格 10 条」混淆）
        if max_scenarios > 0 and max_scenarios != 10:
            filter_desc = (
                "legacy q01–q10 by name (max_scenarios ignored; use --test-set first)"
            )
        else:
            filter_desc = "legacy q01–q10 by name pattern ^q(0[1-9]|10)_"

    else:  # TEST_SET_FIRST
        n = max_scenarios if max_scenarios > 0 else total_in_file
        if max_scenarios <= 0:
            raise ValueError(
                "test_set=first 需要 --max-scenarios N > 0（取 JSON 前 N 条，非 legacy10）"
            )
        selected = list(scenarios)[:n]
        filter_desc = f"first {n} scenarios in JSON file order"

    before_olap = len(selected)
    selected, olap_meta = filter_scenarios_by_olap_modes(selected, allowed_kappa)
    if allowed_kappa and not selected:
        raise ValueError(
            f"olap_modes={olap_meta.get('olap_modes')!r} 在 test_set={test_set!r} 下"
            f" 无匹配 scenario（筛选前 {before_olap} 条）"
        )
    if allowed_kappa and olap_meta.get("scenarios_dropped_by_olap"):
        filter_desc += (
            f"; olap κ-filter dropped {olap_meta['scenarios_dropped_by_olap']}"
        )

    meta = {
        "test_set": test_set,
        "filter_desc": filter_desc,
        "scenarios_in_file": total_in_file,
        "scenarios_selected": len(selected),
        "scenario_names": [str(s.get("name") or "") for s in selected],
        **olap_meta,
    }
    return selected, meta


def _expected_legacy_names() -> set:
    # 与 JSON 中实际 name 前缀一致；仅用于完整性检查
    return {
        "q01_mercury_methylation_factors",
        "q02_measurement_qc",
        "q03_hazard_exposure",
        "q04_experimental_design_eem",
        "q05_detection_methods_eem_ebm",
        "q06_agricultural_management",
        "q07_control_measures_ebm",
        "q08_sample_concentrations",
        "q09_study_area_background",
        "q10_experimental_design_eem_ebm",
    }


def format_test_set_banner(meta: Dict[str, Any]) -> str:
    from utilities.olap_modes import format_olap_modes_banner

    names = ", ".join(meta.get("scenario_names") or [])
    olap_line = format_olap_modes_banner(
        frozenset(meta["olap_modes"].split(",")) if meta.get("olap_modes") else None
    )
    return (
        f"dialogue test_set={meta['test_set']}: {meta['scenarios_selected']}/"
        f"{meta['scenarios_in_file']} ({meta['filter_desc']})\n"
        f"  {olap_line}\n"
        f"  scenarios: {names}"
    )
