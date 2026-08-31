"""Execute G-section pipeline cells from notebook and run evaluation."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NB_PATH = PROJECT_ROOT / "3_0_2 Retevie.ipynb"
DEFAULT_LOG = PROJECT_ROOT / "output" / "eval_log.md"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# G 段 pipeline cells（与 3_0_2 Retevie.ipynb：route_r→recall→route_olap→gsub→rerank 对齐）
PIPELINE_CELL_INDICES = [5, 7, 9, 11, 13, 16, 18, 21, 22, 24, 26, 28, 30]
EVAL_IMPORT_CELL = 33
OLAP_COMPARE_CELL = 39


def bootstrap_eval_context(g: dict) -> None:
    """Load evaluation helpers (same as notebook OLAP cells)."""
    exec_notebook_cells(g, [EVAL_IMPORT_CELL])


def _load_dotenv() -> None:
    from dotenv import load_dotenv

    candidates = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env",
        Path(os.environ.get("USERPROFILE", ""))
        / "OneDrive"
        / "LUCK"
        / "luck grpahrag"
        / "code"
        / "PaperExtract2"
        / "PaperExtract2"
        / ".env",
    ]
    for p in candidates:
        if p.is_file():
            load_dotenv(p)
            print(f"✅ load_dotenv: {p}")
            return
    load_dotenv()
    print("⚠️  使用默认 load_dotenv()")


def exec_notebook_cells(globals_dict: dict, indices: list[int]) -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    cells = nb["cells"]
    for idx in indices:
        src = "".join(cells[idx].get("source", []))
        print(f"\n── exec cell {idx} ──")
        exec(compile(src, f"{NB_PATH.name}:cell_{idx}", "exec"), globals_dict)


from utilities.eval_preflight import EvalPreflightError, check_neo4j_ready


def bootstrap_pipeline(variant: str = "full", *, skip_preflight: bool = False) -> dict:
    from utilities.pipeline_config import set_pipeline_variant

    os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    _load_dotenv()
    set_pipeline_variant(variant)

    if not skip_preflight:
        from neo4j import GraphDatabase

        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "")
        _pf_driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            preflight = check_neo4j_ready(_pf_driver)
            print(
                f"✅ Neo4j preflight: MetaPath={preflight['metapath_count']} "
                f"emb={preflight['metapath_with_embedding']} indexes={len(preflight['indexes'])}"
            )
        finally:
            _pf_driver.close()

    from typing import Annotated, Dict, List, TypedDict
    import operator

    g: dict = {
        "__name__": "__main__",
        "__file__": str(NB_PATH),
        "List": List,
        "Dict": Dict,
        "Annotated": Annotated,
        "TypedDict": TypedDict,
        "operator": operator,
        "PIPELINE_VARIANT": variant,
    }
    exec_notebook_cells(g, PIPELINE_CELL_INDICES[:-1])
    import __main__

    __main__.__dict__.update(
        {k: v for k, v in g.items() if isinstance(k, str) and not k.startswith("__")}
    )
    exec_notebook_cells(g, PIPELINE_CELL_INDICES[-1:])
    set_pipeline_variant(variant)
    g["PIPELINE_VARIANT"] = variant
    if "graph_app" not in g:
        raise RuntimeError("graph_app 未构建")
    if "make_initial_state" not in g:
        raise RuntimeError("make_initial_state 未定义")
    if "llm" not in g:
        raise RuntimeError("llm 未定义，OLAP 核心指标评估需要 LLM judge")
    if "neo4j_driver" not in g:
        raise RuntimeError("neo4j_driver 未定义，OLAP 核心指标评估需要 Neo4j context")
    return g


def smoke_test(g: dict) -> None:
    print("\n" + "=" * 72)
    print("Pipeline 冒烟测试（单条 first_turn）")
    print("=" * 72)
    state = g["make_initial_state"](
        "What are the key influencing factors of mercury methylation"
    )
    final = g["graph_app"].invoke(state)
    print(
        f"  r={final.get('target_subgraphs')} κ={final.get('kappa')} "
        f"l={final.get('path_level')}"
    )
    print(
        f"  |P*|={len(final.get('candidate_mp_ids') or [])} "
        f"answer_len={len(final.get('final_answer') or '')}"
    )


def dialogue_test(
    g: dict,
    verbose: bool = True,
    session_mode: str = "stateful",
    score_core_metrics: bool = True,
    max_scenarios: int = 0,
    test_set: str | None = None,
    olap_modes: str | None = None,
) -> dict:
    from utilities.dialogue_test_set import format_test_set_banner
    from utilities.olap_modes import format_olap_modes_banner, get_active_olap_modes
    from utilities.pipeline_config import get_pipeline_config
    from utilities.test_evaluation import evaluate_dialogue_scenarios, load_dialogue_test_cases_with_meta

    print("\n" + "=" * 72)
    print(
        f"多轮对话测试 (variant={get_pipeline_config().variant}, "
        f"session={session_mode}, core_metrics={score_core_metrics})"
    )
    print("=" * 72)
    scenarios, ts_meta = load_dialogue_test_cases_with_meta(
        test_set=test_set, max_scenarios=max_scenarios, olap_modes=olap_modes
    )
    print(format_test_set_banner(ts_meta))
    print(format_olap_modes_banner(get_active_olap_modes()))
    return evaluate_dialogue_scenarios(
        g["graph_app"],
        g["make_initial_state"],
        scenarios,
        embedder=g.get("neo4j_embed_model"),
        llm=g.get("llm"),
        neo4j_driver=g.get("neo4j_driver"),
        verbose=verbose,
        session_mode=session_mode,
        score_core_metrics=score_core_metrics,
        dialogue_test_set=ts_meta.get("test_set"),
        olap_modes=ts_meta.get("olap_modes"),
    )


def comprehensive_test(g: dict) -> dict:
    from utilities.test_evaluation import (
        evaluate_test_cases,
        load_test_cases,
        print_evaluation_summary,
        resolve_questions_csv,
    )

    print("\n" + "=" * 72)
    print("综合测试（questions.csv）")
    print("=" * 72)
    csv_path = resolve_questions_csv()
    print(f"CSV: {csv_path}")
    cases = load_test_cases(csv_path)
    report = evaluate_test_cases(
        g["graph_app"],
        g["make_initial_state"],
        cases,
        embedder=g.get("neo4j_embed_model"),
        verbose=True,
    )
    print_evaluation_summary(report)
    failed = [d for d in report["details"] if "error" in d]
    if failed:
        print(f"\n❌ 失败 {len(failed)} 条:")
        for d in failed:
            print(f"  - {d['query'][:50]}: {d['error'][:120]}")
    return report


def run_olap_compare(
    version: str,
    log_path: Path,
    skip_smoke: bool = True,
    max_scenarios: int = 0,
    test_set: str | None = None,
    olap_modes: str | None = None,
    skip_preflight: bool = False,
) -> int:
    from utilities.olap_modes import configure_olap_modes, format_olap_modes_banner, get_active_olap_modes
    from utilities.pipeline_config import PipelineConfig
    from utilities.test_evaluation import (
        append_eval_log,
        evaluate_olap_comparison,
        format_eval_log_md,
    )

    configure_olap_modes(olap_modes)
    if get_active_olap_modes():
        print(format_olap_modes_banner(get_active_olap_modes()))

    t0 = time.perf_counter()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exit_code = 0

    print("\n" + "#" * 72)
    print("# OLAP Compare: Stateful (full OLAP) vs Stateless (flat recall + PR-only rerank)")
    print("#" * 72)

    g = bootstrap_pipeline("full", skip_preflight=skip_preflight)
    if not skip_smoke:
        smoke_test(g)

    from utilities.dialogue_test_set import resolve_dialogue_test_set

    ts_label = resolve_dialogue_test_set(test_set)
    report_stateful = dialogue_test(
        g,
        verbose=True,
        session_mode="stateful",
        max_scenarios=max_scenarios,
        test_set=test_set,
        olap_modes=olap_modes,
    )
    report_stateless = dialogue_test(
        g,
        verbose=True,
        session_mode="stateless",
        max_scenarios=max_scenarios,
        test_set=test_set,
        olap_modes=olap_modes,
    )
    olap = evaluate_olap_comparison(report_stateful, report_stateless)

    print("\n" + "=" * 72)
    print("Turn2 Core Δ (Stateful − Stateless)")
    print("=" * 72)
    for key, vals in olap["turn2_delta"].items():
        print(
            f"  {key}: stateful={vals.get('stateful')}  "
            f"stateless={vals.get('stateless')}  Δ={vals.get('delta')}"
        )

    duration = round(time.perf_counter() - t0, 1)
    flags = PipelineConfig(variant="full").feature_flags()

    md_stateful = format_eval_log_md(
        meta={
            "timestamp": started + " [stateful]",
            "version": version,
            "dialogue_test_set": ts_label,
            "olap_modes": ",".join(sorted(get_active_olap_modes() or [])) or "all",
            "pipeline_variant": "full",
            "session_mode": "stateful",
            "feature_flags": flags,
            "python": sys.executable,
            "duration_sec": "—",
            "exit": "success",
        },
        dialogue_report=report_stateful,
    )
    md_stateless = format_eval_log_md(
        meta={
            "timestamp": started + " [stateless]",
            "version": version,
            "dialogue_test_set": ts_label,
            "pipeline_variant": "full",
            "session_mode": "stateless",
            "feature_flags": flags,
            "python": sys.executable,
            "duration_sec": "—",
            "exit": "success",
        },
        dialogue_report=report_stateless,
    )
    failed = (
        report_stateful["summary"]["turns_failed"]
        or report_stateless["summary"]["turns_failed"]
        or olap["paired_scenarios_turn2"] == 0
    )
    if failed:
        exit_code = 1
        print("\n❌ OLAP 评估未产生有效 Turn2 配对结果（见上方 pipeline 错误）")

    md_compare = format_eval_log_md(
        meta={
            "timestamp": started + " [olap compare]",
            "version": version,
            "dialogue_test_set": ts_label,
            "pipeline_variant": "full (Stateful vs Stateless)",
            "session_mode": "paired",
            "retrieval_scoring": (
                "Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); "
                "Stateless: Route_r + Recall(flat) + Rerank(η·PR only)"
            ),
            "stateless_baseline": "route_r_only, recall_flat, rerank_pr_only, no_memory",
            "feature_flags": flags,
            "python": sys.executable,
            "duration_sec": duration,
            "exit": "failed" if exit_code else "success",
        },
        olap_compare=olap,
    )
    append_eval_log(md_stateful + md_stateless + md_compare, log_path)
    print(f"\n✅ OLAP 对比结果已写入 {log_path}")
    return exit_code


def run_ablation_dialogue(
    version: str,
    log_path: Path,
    skip_smoke: bool = True,
    skip_comprehensive: bool = True,
    max_scenarios: int = 0,
    test_set: str | None = None,
    skip_preflight: bool = False,
) -> int:
    from utilities.pipeline_config import PipelineConfig, get_pipeline_config
    from utilities.test_evaluation import (
        append_eval_log,
        compare_ablation_reports,
        format_eval_log_md,
    )

    t0 = time.perf_counter()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exit_code = 0

    print("\n" + "#" * 72)
    print("# Ablation: full vs no_hierarchy (Stateful, core metrics)")
    print("#" * 72)

    g_full = bootstrap_pipeline("full", skip_preflight=skip_preflight)
    if not skip_smoke:
        smoke_test(g_full)
    report_full = dialogue_test(
        g_full,
        verbose=True,
        session_mode="stateful",
        max_scenarios=max_scenarios,
        test_set=test_set,
    )

    g_flat = bootstrap_pipeline("no_hierarchy", skip_preflight=skip_preflight)
    report_flat = dialogue_test(
        g_flat,
        verbose=True,
        session_mode="stateful",
        max_scenarios=max_scenarios,
        test_set=test_set,
    )

    compare = compare_ablation_reports(report_full, report_flat)
    print("\n" + "=" * 72)
    print("Ablation 对比摘要 (Turn2 core)")
    print("=" * 72)
    for row in compare["rows"]:
        print(f"  {row['metric']}: full={row['full']}  no_hierarchy={row['no_hierarchy']}  Δ={row['delta']}")

    duration = round(time.perf_counter() - t0, 1)

    md = format_eval_log_md(
        meta={
            "timestamp": started,
            "version": version,
            "pipeline_variant": "ablation (full vs no_hierarchy)",
            "session_mode": "stateful",
            "feature_flags": PipelineConfig(variant="full").feature_flags(),
            "python": sys.executable,
            "duration_sec": duration,
            "exit": "success",
        },
        dialogue_report=report_full,
        ablation_compare=compare,
    )
    md_full = format_eval_log_md(
        meta={
            "timestamp": started + " [full arm]",
            "version": version,
            "pipeline_variant": "full",
            "session_mode": "stateful",
            "feature_flags": PipelineConfig(variant="full").feature_flags(),
            "python": sys.executable,
            "duration_sec": "—",
            "exit": "success",
        },
        dialogue_report=report_full,
    )
    md_flat = format_eval_log_md(
        meta={
            "timestamp": started + " [no_hierarchy arm]",
            "version": version,
            "pipeline_variant": "no_hierarchy",
            "session_mode": "stateful",
            "feature_flags": get_pipeline_config().__class__(variant="no_hierarchy").feature_flags(),
            "python": sys.executable,
            "duration_sec": "—",
            "exit": "success",
        },
        dialogue_report=report_flat,
    )
    append_eval_log(md_full + md_flat + md, log_path)
    print(f"\n✅ Ablation 结果已写入 {log_path}")

    if report_full["summary"]["turns_failed"] or report_flat["summary"]["turns_failed"]:
        exit_code = 1
    return exit_code


def run_full_eval(
    version: str,
    log_path: Path,
    skip_smoke: bool = True,
    max_scenarios: int = 0,
    test_set: str | None = None,
    olap_modes: str | None = None,
    skip_preflight: bool = False,
) -> int:
    code = run_olap_compare(
        version=version + "-olap",
        log_path=log_path,
        skip_smoke=skip_smoke,
        max_scenarios=max_scenarios,
        test_set=test_set,
        olap_modes=olap_modes,
        skip_preflight=skip_preflight,
    )
    code_ab = run_ablation_dialogue(
        version=version + "-ablation",
        log_path=log_path,
        skip_smoke=True,
        max_scenarios=max_scenarios,
        test_set=test_set,
        skip_preflight=skip_preflight,
    )
    return max(code, code_ab)


def main() -> int:
    import argparse

    from utilities.pipeline_config import get_pipeline_config
    from utilities.test_evaluation import append_eval_log, format_eval_log_md

    parser = argparse.ArgumentParser(description="Run retrieval pipeline evaluation")
    parser.add_argument("--neo4j-only", action="store_true", help="Only Neo4j G_sub smoke")
    parser.add_argument("--skip-comprehensive", action="store_true", help="Skip 10-case CSV eval")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke test")
    parser.add_argument(
        "--variant",
        choices=["full", "no_hierarchy"],
        default="full",
        help="Pipeline variant (overrides notebook PIPELINE_VARIANT)",
    )
    parser.add_argument("--version", default="", help="Version label for eval log")
    parser.add_argument("--log-md", type=Path, default=DEFAULT_LOG, help="Append results here")
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Run full vs no_hierarchy Stateful ablation with core metrics",
    )
    parser.add_argument(
        "--olap-compare",
        action="store_true",
        help="Run Stateful vs Stateless OLAP comparison (full variant)",
    )
    parser.add_argument(
        "--full-eval",
        action="store_true",
        help="Run --olap-compare and --ablation sequentially",
    )
    parser.add_argument(
        "--legacy-metrics-only",
        action="store_true",
        help="Skip OLAP core metrics (legacy relevancy/κ/l only)",
    )
    parser.add_argument(
        "--test-set",
        choices=["legacy10", "all", "first"],
        default=None,
        help=(
            "Dialogue eval subset: legacy10=q01–q10 by name (default via env), "
            "all=full JSON, first=N needs --max-scenarios"
        ),
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=0,
        help="With --test-set first: take first N rows; with all: cap count (0=no cap)",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip Neo4j MetaPath/index preflight (not recommended)",
    )
    parser.add_argument(
        "--olap-modes",
        default=None,
        metavar="SPEC",
        help="OLAP κ subset: preset core|extended|all or comma list (env OLAP_MODES)",
    )
    parser.add_argument(
        "--e3-only",
        action="store_true",
        help="Run E3 Stateful dialogue eval only (skip E4 questions.csv)",
    )
    parser.add_argument(
        "--e4-only",
        action="store_true",
        help="Run E4 single-turn questions.csv only (skip E3 dialogue)",
    )
    args = parser.parse_args()

    if args.neo4j_only:
        import utilities.run_neo4j_gsub_smoke as m

        exec(open(m.__file__, encoding="utf-8").read(), {"__name__": "__main__"})
        return 0

    version = args.version or "eval-run"

    if args.e3_only and args.e4_only:
        print("❌ 不能同时指定 --e3-only 与 --e4-only")
        return 2

    from utilities.olap_modes import configure_olap_modes, format_olap_modes_banner, get_active_olap_modes

    configure_olap_modes(args.olap_modes)
    active_modes = get_active_olap_modes()
    if active_modes:
        print(format_olap_modes_banner(active_modes))

    try:
        if args.full_eval:
            return run_full_eval(
                version=version,
                log_path=args.log_md,
                skip_smoke=args.skip_smoke,
                max_scenarios=args.max_scenarios,
                test_set=args.test_set,
                olap_modes=args.olap_modes,
                skip_preflight=args.skip_preflight,
            )

        if args.olap_compare:
            return run_olap_compare(
                version=version,
                log_path=args.log_md,
                skip_smoke=args.skip_smoke,
                max_scenarios=args.max_scenarios,
                test_set=args.test_set,
                olap_modes=args.olap_modes,
                skip_preflight=args.skip_preflight,
            )

        if args.ablation:
            return run_ablation_dialogue(
                version=version,
                log_path=args.log_md,
                skip_smoke=args.skip_smoke,
                skip_comprehensive=args.skip_comprehensive,
                max_scenarios=args.max_scenarios,
                test_set=args.test_set,
                skip_preflight=args.skip_preflight,
            )
    except EvalPreflightError as exc:
        from utilities.test_evaluation import append_eval_log

        started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        append_eval_log(
            f"## Run {started} [preflight failed]\n\n"
            f"| 项 | 值 |\n|----|-----|\n"
            f"| version | {version} |\n"
            f"| exit | failed |\n\n"
            f"### 错误\n\n```\n{exc}\n```\n\n---\n",
            args.log_md,
        )
        print(f"\n❌ {exc}")
        return 2

    t0 = time.perf_counter()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exit_code = 0
    single_report = None
    dialogue_report = None

    try:
        from utilities.pipeline_config import set_pipeline_variant

        set_pipeline_variant(args.variant)
        g = bootstrap_pipeline(args.variant, skip_preflight=args.skip_preflight)
        if not args.skip_smoke:
            smoke_test(g)
        dialogue_report = None
        single_report = None
        if not args.e4_only:
            dialogue_report = dialogue_test(
                g,
                verbose=True,
                session_mode="stateful",
                score_core_metrics=not args.legacy_metrics_only,
                max_scenarios=args.max_scenarios,
                test_set=args.test_set,
                olap_modes=args.olap_modes,
            )
        if not args.e3_only and not args.skip_comprehensive:
            single_report = comprehensive_test(g)
        elif args.e4_only:
            single_report = comprehensive_test(g)
        print("\n✅ 测试流程执行完成")
    except OSError as exc:
        if "c10.dll" in str(exc).lower() or "dll" in str(exc).lower():
            print(
                "\n❌ PyTorch/sentence-transformers 加载失败（OneDrive 路径常见）。"
                "\n   请在 tomLuck2 环境中从 Notebook 顺序运行 G Cell 0–7，再运行综合测试 cell。"
            )
        traceback.print_exc()
        exit_code = 1
    except Exception:
        traceback.print_exc()
        exit_code = 1

    duration = round(time.perf_counter() - t0, 1)
    cfg = get_pipeline_config()
    md = format_eval_log_md(
        meta={
            "timestamp": started,
            "version": args.version or "(未指定)",
            "pipeline_variant": cfg.variant,
            "session_mode": "stateful",
            "olap_modes": ",".join(sorted(active_modes)) if active_modes else "all",
            "feature_flags": cfg.feature_flags(),
            "python": sys.executable,
            "duration_sec": duration,
            "exit": "success" if exit_code == 0 else "failed",
        },
        single_report=single_report,
        dialogue_report=dialogue_report,
    )
    append_eval_log(md, args.log_md)
    print(f"📝 评估日志已追加: {args.log_md}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
