"""从 output/eval_log.md 解析 OLAP 对比块，生成跨版本对比报告。

用法:
  python utilities/compare_eval_logs.py
  python utilities/compare_eval_logs.py --versions v3-stateless-baseline v5-recall-wide-legacy10
  python utilities/compare_eval_logs.py -o output/legacy10_version_compare.md
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = PROJECT_ROOT / "output" / "eval_log.md"
DEFAULT_OUT = PROJECT_ROOT / "output" / "legacy10_version_compare.md"

CORE_METRICS = (
    "recall_at_10",
    "precision_at_10",
    "anchor_overlap",
    "faithfulness",
    "answer_relevance",
    "context_precision",
)


def _parse_table_block(text: str, header: str) -> Dict[str, Dict[str, float]]:
    """Parse markdown table after a ### header; metric -> {stateful, stateless, delta}."""
    idx = text.find(header)
    if idx < 0:
        return {}
    rest = text[idx + len(header) :]
    next_h = rest.find("\n### ")
    chunk = rest if next_h < 0 else rest[:next_h]
    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip().startswith("|")]
    out: Dict[str, Dict[str, float]] = {}
    for ln in lines[2:]:  # skip header + separator
        parts = [p.strip() for p in ln.strip("|").split("|")]
        if len(parts) < 4:
            continue
        metric, st, sl, delta = parts[0], parts[1], parts[2], parts[3]
        if metric.lower() == "metric":
            continue
        try:
            out[metric] = {
                "stateful": float(st),
                "stateless": float(sl),
                "delta": float(delta),
            }
        except ValueError:
            continue
    return out


def _parse_run_meta(block: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for key in ("version", "session_mode", "exit", "duration_sec"):
        m = re.search(rf"\| {key} \| ([^|]+) \|", block)
        if m:
            meta[key] = m.group(1).strip()
    return meta


def _parse_arm_metrics(block: str, prefix: str) -> Dict[str, float]:
    """Turn1 / Turn2 bullet metrics under #### TurnN 核心指标."""
    metrics: Dict[str, float] = {}
    section = re.search(rf"#### {prefix} 核心指标\n((?:- .+\n)+)", block)
    if not section:
        return metrics
    for ln in section.group(1).splitlines():
        m = re.match(r"- (\w+): ([\d.]+)", ln.strip())
        if m:
            metrics[m.group(1)] = float(m.group(2))
    return metrics


def extract_olap_runs(log_text: str) -> List[Dict[str, Any]]:
    """Each ## Run ... [olap compare] block with paired tables."""
    pattern = re.compile(
        r"(## Run [^\n]+\[olap compare\][\s\S]*?)(?=\n## Run |\Z)",
        re.MULTILINE,
    )
    runs: List[Dict[str, Any]] = []
    for m in pattern.finditer(log_text):
        block = m.group(1)
        meta = _parse_run_meta(block)
        version = meta.get("version", "").strip()
        if not version:
            continue
        runs.append(
            {
                "version": version,
                "timestamp": block.split("\n")[0].replace("## Run ", "").strip(),
                "meta": meta,
                "turn1_sanity": _parse_table_block(block, "### Turn1 Sanity"),
                "turn2_delta": _parse_table_block(block, "### Turn2 Core Δ"),
            }
        )
    return runs


def extract_arm_runs(log_text: str, session_mode: str) -> Dict[str, Dict[str, Any]]:
    """Latest run per version for stateful/stateless arms (dialogue metrics)."""
    pattern = re.compile(
        r"(## Run [^\n]+)\n\n([\s\S]*?)(?=\n## Run |\Z)",
        re.MULTILINE,
    )
    by_version: Dict[str, Dict[str, Any]] = {}
    for m in pattern.finditer(log_text):
        title, body = m.group(1), m.group(2)
        if f"[{session_mode}]" not in title and f"session_mode | {session_mode}" not in body:
            continue
        if "[olap compare]" in title:
            continue
        meta = _parse_run_meta(body)
        version = meta.get("version", "").strip()
        if not version:
            continue
        if version in by_version:
            continue  # 保留文件中第一条（最新 run）
        by_version[version] = {
            "timestamp": title.replace("## Run ", "").strip(),
            "turn1": _parse_arm_metrics(body, "Turn1"),
            "turn2": _parse_arm_metrics(body, "Turn2"),
            "summary_lines": _extract_summary_lines(body),
        }
    return by_version


def _extract_summary_lines(body: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for pat, key in [
        (r"scenarios completed: (\S+)", "scenarios"),
        (r"turns OK: (\S+)", "turns"),
    ]:
        m = re.search(pat, body)
        if m:
            out[key] = m.group(1)
    return out


def build_compare_report(
    log_path: Path,
    versions: Optional[List[str]] = None,
    *,
    title: str = "Legacy10 同集 OLAP 跨版本对比",
) -> str:
    text = log_path.read_text(encoding="utf-8")
    olap_runs = extract_olap_runs(text)
    if versions:
        olap_runs = [r for r in olap_runs if r["version"] in versions]
    if not olap_runs:
        return f"# {title}\n\n（未在 {log_path} 中找到匹配的 [olap compare] 记录）\n"

    # 每个 version 只保留最新一条 compare（eval_log 新条目插在 APPEND_BELOW 之后，先出现者更新）
    latest: Dict[str, Dict[str, Any]] = {}
    for r in olap_runs:
        if r["version"] not in latest:
            latest[r["version"]] = r
    ordered = [latest[v] for v in (versions or list(latest.keys())) if v in latest]

    stateful_arms = extract_arm_runs(text, "stateful")
    stateless_arms = extract_arm_runs(text, "stateless")

    lines = [
        f"# {title}",
        "",
        f"数据源: `{log_path}`",
        "",
        "说明: **legacy10** 对比应使用 ``--test-set legacy10``（按 name 筛选 q01–q10）。",
        "旧版 ``--max-scenarios 10`` 仅取 JSON 前 10 条，在 66 条文件中与 legacy10 等价；",
        "扩展后应用 ``legacy10`` 而非 ``first``。",
        "",
        "## Turn2 Core Δ（Stateful − Stateless）",
        "",
        "| version | recall Δ | precision Δ | anchor Δ | faithfulness Δ | answer_rel Δ | ctx_prec Δ |",
        "|---------|----------|-------------|----------|----------------|--------------|------------|",
    ]
    for r in ordered:
        t2 = r.get("turn2_delta") or {}
        def d(k: str) -> str:
            v = t2.get(k, {}).get("delta")
            return f"{v:+.3f}" if v is not None else "—"

        lines.append(
            f"| {r['version']} | {d('recall_at_10')} | {d('precision_at_10')} | "
            f"{d('anchor_overlap')} | {d('faithfulness')} | {d('answer_relevance')} | "
            f"{d('context_precision')} |"
        )

    lines.extend(["", "## Turn2 绝对值（Stateful / Stateless）", ""])
    for r in ordered:
        t2 = r.get("turn2_delta") or {}
        lines.append(f"### {r['version']}")
        lines.append("| metric | Stateful | Stateless | Δ |")
        lines.append("|--------|----------|-----------|---|")
        for metric in CORE_METRICS:
            row = t2.get(metric, {})
            if not row:
                continue
            lines.append(
                f"| {metric} | {row.get('stateful', '—')} | {row.get('stateless', '—')} | "
                f"{row.get('delta', '—')} |"
            )
        sv = stateful_arms.get(r["version"], {})
        sl = stateless_arms.get(r["version"], {})
        if sv.get("summary_lines") or sl.get("summary_lines"):
            lines.append("")
            lines.append(
                f"- Stateful: scenarios {sv.get('summary_lines', {}).get('scenarios', '—')}, "
                f"turns {sv.get('summary_lines', {}).get('turns', '—')}"
            )
            lines.append(
                f"- Stateless: scenarios {sl.get('summary_lines', {}).get('scenarios', '—')}, "
                f"turns {sl.get('summary_lines', {}).get('turns', '—')}"
            )
        lines.append("")

    lines.extend(["## Turn1 Sanity Δ", ""])
    lines.append("| version | recall Δ | precision Δ | answer_rel Δ |")
    lines.append("|---------|----------|-------------|--------------|")
    for r in ordered:
        t1 = r.get("turn1_sanity") or {}

        def d1(k: str) -> str:
            v = t1.get(k, {}).get("delta")
            return f"{v:+.3f}" if v is not None else "—"

        lines.append(
            f"| {r['version']} | {d1('recall_at_10')} | {d1('precision_at_10')} | "
            f"{d1('answer_relevance')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare OLAP eval versions from eval_log.md")
    parser.add_argument("--log-md", type=Path, default=DEFAULT_LOG)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--versions",
        nargs="*",
        default=None,
        help="Version labels to include (default: all olap compare runs in log)",
    )
    args = parser.parse_args()
    report = build_compare_report(args.log_md, args.versions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n✅ 报告已写入 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
