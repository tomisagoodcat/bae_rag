"""Patch 3_0_2 Retevie.ipynb for OLAP evaluation cells."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "3_0_2 Retevie.ipynb"

EVAL_IMPORTS = r"""# ══════════════════════════════════════════════════════════════
# 评估共享模块（OLAP 核心指标 + 路由命中率）
# ══════════════════════════════════════════════════════════════

from utilities.test_evaluation import (
    resolve_questions_csv,
    load_test_cases,
    load_dialogue_test_cases,
    evaluate_test_cases,
    evaluate_dialogue_scenarios,
    evaluate_olap_comparison,
    compare_ablation_reports,
    run_dialogue_scenario,
    run_stateless_scenario,
    print_evaluation_summary,
    run_single_case,
    append_eval_log,
    format_eval_log_md,
    CORE_METRIC_KEYS,
)

QUESTIONS_CSV = str(resolve_questions_csv())
print(f"✅ 测试 CSV: {QUESTIONS_CSV}")
print(f"✅ OLAP 核心指标: {list(CORE_METRIC_KEYS)}")
"""

DIALOGUE_CORE = r"""# ══════════════════════════════════════════════════════════════
# 多轮对话测试 + OLAP 核心指标（Stateful, qrels优先/LLM fallback）
# ══════════════════════════════════════════════════════════════

from utilities.pipeline_config import get_pipeline_config

_scenarios = load_dialogue_test_cases()
print(f"Pipeline variant: {get_pipeline_config().variant}")
print(f"Scenarios: {len(_scenarios)}")

dialogue_report = evaluate_dialogue_scenarios(
    graph_app,
    make_initial_state,
    _scenarios,
    embedder=neo4j_embed_model,
    llm=llm,
    neo4j_driver=neo4j_driver,
    session_mode="stateful",
    score_core_metrics=True,
    verbose=True,
)
print("\nTurn2 核心指标摘要:")
_summary = dialogue_report["summary"]
for k in CORE_METRIC_KEYS:
    key = f"turn2_avg_{k}"
    if key in _summary:
        print(f"  {k}: {_summary.get(key)}")
"""

OLAP_COMPARE = r"""# ══════════════════════════════════════════════════════════════
# OLAP 对比评估：Stateful vs Stateless + 写 eval_log.md
# ══════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from utilities.pipeline_config import PipelineConfig

_scenarios = load_dialogue_test_cases()
_started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

report_stateful = evaluate_dialogue_scenarios(
    graph_app, make_initial_state, _scenarios,
    embedder=neo4j_embed_model, llm=llm, neo4j_driver=neo4j_driver,
    session_mode="stateful", score_core_metrics=True, verbose=True,
)
report_stateless = evaluate_dialogue_scenarios(
    graph_app, make_initial_state, _scenarios,
    embedder=neo4j_embed_model, llm=llm, neo4j_driver=neo4j_driver,
    session_mode="stateless", score_core_metrics=True, verbose=True,
)
olap = evaluate_olap_comparison(report_stateful, report_stateless)

print("\n" + "=" * 72)
print("Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)")
print("=" * 72)
for key, vals in olap["turn1_sanity"].items():
    print(f"  {key}: Δ={vals.get('delta')}")

print("\nTurn2 Core Δ (Stateful − Stateless)")
for key, vals in olap["turn2_delta"].items():
    print(f"  {key}: stateful={vals.get('stateful')} stateless={vals.get('stateless')} Δ={vals.get('delta')}")

_flags = PipelineConfig(variant=PIPELINE_VARIANT).feature_flags()
_md = format_eval_log_md(
    meta={
        "timestamp": _started + " [notebook olap]",
        "version": "notebook-olap-compare",
        "pipeline_variant": PIPELINE_VARIANT,
        "session_mode": "paired",
        "retrieval_scoring": "qrels优先 / 无则 LLM judge",
        "feature_flags": _flags,
        "exit": "success",
    },
    dialogue_report=report_stateful,
    olap_compare=olap,
)
_log = append_eval_log(_md)
print(f"\n📝 eval log: {_log}")
"""

COMP_MD = """##### 综合测试模块

- 单轮：`data/questions.csv`（路由 + legacy citation/relevancy）
- 多轮 OLAP 核心指标：`dialogue_test_cases.json`
  - Recall@10 / Precision@10（turn 含 `relevant_mp_ids` 时用 qrels，否则 LLM judge）
  - Anchor Overlap, Faithfulness, Answer Relevance, Context Precision
- CLI：`python utilities/run_retrieval_eval.py --full-eval --version v2.0-olap-metrics`
"""

DIALOGUE_MD = """##### G Cell 8: 多轮对话测试（OLAP 核心指标）

Stateful 多轮 + LLM judge / qrels 优先。Stateless 对比见下方 OLAP 对比 cell。
"""


def _lines(s: str) -> list:
    return s.splitlines(keepends=True)


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    for i, c in enumerate(cells):
        s = "".join(c.get("source", []))
        if "评估共享模块" in s and "evaluate_olap_comparison" not in s:
            cells[i]["source"] = _lines(EVAL_IMPORTS)
        elif s.startswith("# 多轮对话测试（dialogue_test_cases.json）"):
            cells[i]["source"] = _lines(DIALOGUE_CORE)
        elif "G Cell 8: 多轮对话测试" in s and c["cell_type"] == "markdown":
            cells[i]["source"] = _lines(DIALOGUE_MD)
        elif s.strip().startswith("##### 综合测试模块"):
            cells[i]["source"] = _lines(COMP_MD)

    if not any("OLAP 对比评估" in "".join(c.get("source", [])) for c in cells):
        cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _lines("##### OLAP 对比评估 (Stateful vs Stateless)\n"),
            }
        )
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": _lines(OLAP_COMPARE),
            }
        )

    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB}")


if __name__ == "__main__":
    patch()
