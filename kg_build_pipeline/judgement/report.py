"""Render a detailed Markdown judgement log (no LLM)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from kg_build_pipeline.judgement.constants import LIMITATIONS_FIXED, METRIC_GLOSSARY, SAMPLE_LIMIT
from kg_build_pipeline.src.paths import PIPELINE_ROOT

LOG_DIR = PIPELINE_ROOT / "judgement" / "log"


def _md_escape(text: Any) -> str:
    s = str(text if text is not None else "")
    return s.replace("|", "\\|").replace("\n", " ")


def _ratio_cell(metric: Dict[str, Any]) -> str:
    status = metric.get("status") or "OK"
    if status == "NOT_COMPUTABLE" or metric.get("value") is None:
        reason = metric.get("reason") or "NOT_COMPUTABLE"
        return f"NOT_COMPUTABLE ({_md_escape(reason)})"
    return f"{metric['value']:.4f} ({status})"


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# BAE KG 内在质量评价（Judgement）")
    lines.append("")
    lines.append(f"- 生成时间: `{payload.get('generated_at')}`")
    lines.append(f"- Neo4j: `{payload.get('neo4j_uri')}` / `{payload.get('neo4j_database')}`")
    lines.append(f"- 论文文件: {', '.join(f'`{f}`' for f in payload.get('filenames') or []) or '（无）'}")
    stages = payload.get("stages_run") or []
    lines.append(f"- 本次 pipeline stages: {', '.join(stages) if stages else '（手动运行，无 stage 列表）'}")
    if payload.get("error"):
        lines.append(f"- **评价过程错误（fail-soft）:** `{_md_escape(payload['error'])}`")
    lines.append("")
    lines.append("## 1. 固定说明与限制")
    lines.append("")
    lines.append(LIMITATIONS_FIXED.strip())
    lines.append("")
    lines.append("### 指标词典（每次相同）")
    lines.append("")
    lines.append("| 指标 | 定义 | 方向/说明 | 计算口径 |")
    lines.append("| --- | --- | --- | --- |")
    for row in METRIC_GLOSSARY:
        lines.append(
            f"| {_md_escape(row['id'])} | {_md_escape(row['definition'])} | "
            f"{_md_escape(row['direction'])} | {_md_escape(row['method'])} |"
        )
    lines.append("")
    lines.append("## 2. 本次总表")
    lines.append("")
    summary = payload.get("summary") or {}
    lines.append("| 指标 | 本次值 | 方向 | 状态 |")
    lines.append("| --- | --- | --- | --- |")
    order = [
        ("Class Richness (CR)", "cr", "描述 Schema 利用"),
        ("Average Population (AP)", "ap", "描述性"),
        ("SHACL Conformance Rate (SCR)", "scr", "↑ 核心"),
        ("Orphan Rate (OR)", "or", "↓"),
        ("Document Connectivity (DC)", "dc", "↑ 跨篇均值"),
        ("Mid-level Connectivity (MC)", "mc", "↑ 跨篇均值"),
        ("Multi-hop Path Coverage (MPC)", "mpc", "↑"),
        ("Duplicate Entity Rate (DER)", "der", "↓"),
        ("Relation Schema Conformance (RSC)", "rsc", "↑ 核心"),
        ("Relation Conflict Rate (RCR)", "rcr", "↓"),
        ("Provenance Coverage (PC)", "pc", "↑"),
    ]
    for title, key, direction in order:
        cell = summary.get(key) or {}
        lines.append(
            f"| {title} | {_ratio_cell(cell)} | {direction} | {_md_escape(cell.get('status', ''))} |"
        )
    lines.append("")
    pop = payload.get("class_population") or {}
    lines.append(f"- BAE 实例总数: **{sum(pop.values()) if pop else 0}**；可实例化类数: **{len(pop)}**")
    rcr = summary.get("rcr") or {}
    mutex = rcr.get("mutex") or {}
    if mutex:
        lines.append(
            f"- RCR 互斥冲突: {_ratio_cell(mutex)}"
        )
    lines.append("")
    lines.append("## 3. 分论文连通与路径")
    lines.append("")
    docs = payload.get("documents") or []
    if not docs:
        lines.append("无可评价论文（Chunk.filename / source_doc 均为空）。")
    else:
        lines.append("| 论文 | BAE 节点 | DC | MC | 合法≥3跳路径 |")
        lines.append("| --- | ---: | --- | --- | --- |")
        for d in docs:
            mpc = "是" if d.get("mpc_has_ge3") else "否"
            lines.append(
                f"| `{_md_escape(d.get('filename'))}` | {d.get('bae_nodes', 0)} | "
                f"{_ratio_cell(d.get('dc') or {})} | {_ratio_cell(d.get('mc') or {})} | {mpc} |"
            )
    lines.append("")
    lines.append("## 4. Class Population")
    lines.append("")
    lines.append("| BAE 类 | 实例数 |")
    lines.append("| --- | ---: |")
    for lab, n in (pop or {}).items():
        lines.append(f"| `{lab}` | {n} |")
    lines.append("")
    lines.append("## 5. SCR / OR 规则命中")
    lines.append("")
    scr = summary.get("scr") or {}
    orphan = summary.get("or") or {}
    lines.append(
        f"- SCR 受检节点 {scr.get('total', 0)}，其中 HARD 节点 {scr.get('hard_nodes', 0)}。"
    )
    lines.append(
        f"- OR 应具结构节点 {orphan.get('total', 0)}，缺必要结构节点 {orphan.get('orphan_nodes', 0)}。"
    )
    lines.append("")
    lines.append("| 规则 | 命中次数 | 用于 |")
    lines.append("| --- | ---: | --- |")
    for rule, cnt in sorted((scr.get("rule_counts") or {}).items()):
        lines.append(f"| `{_md_escape(rule)}` | {cnt} | SCR HARD |")
    for rule, cnt in sorted((orphan.get("rule_counts") or {}).items()):
        lines.append(f"| `{_md_escape(rule)}` | {cnt} | OR |")
    if not (scr.get("rule_counts") or orphan.get("rule_counts")):
        lines.append("| （无） | 0 | |")
    lines.append("")
    lines.append("## 6. RSC / RCR 样例")
    lines.append("")
    rsc = summary.get("rsc") or {}
    lines.append(
        f"- RSC 合法边 {rsc.get('legal', 0)} / 待评价边 {rsc.get('total', 0)}。"
    )
    lines.append(
        f"- RCR duplicate_extra={rcr.get('duplicate_extra', 0)}, "
        f"illegal_direction={rcr.get('illegal_direction', 0)}, self_loop={rcr.get('self_loop', 0)}。"
    )
    lines.append(f"- 同一对多种关系不记 RCR 错误。样例上限 {SAMPLE_LIMIT}。")
    lines.append("")
    lines.append("### 非法 schema 边")
    lines.append("")
    illegal = rsc.get("illegal_samples") or []
    if not illegal:
        lines.append("无。")
    else:
        lines.append("| src | rel | tgt | triple |")
        lines.append("| --- | --- | --- | --- |")
        for s in illegal:
            lines.append(
                f"| `{s.get('src')}` | `{s.get('rel')}` | `{s.get('tgt')}` | `{s.get('triple')}` |"
            )
    lines.append("")
    lines.append("### 冲突边")
    lines.append("")
    conflicts = rcr.get("samples") or []
    if not conflicts:
        lines.append("无。")
    else:
        lines.append("| src | rel | tgt | kinds |")
        lines.append("| --- | --- | --- | --- |")
        for s in conflicts:
            lines.append(
                f"| `{s.get('src')}` | `{s.get('rel')}` | `{s.get('tgt')}` | "
                f"{_md_escape(','.join(s.get('kinds') or []))} |"
            )
    lines.append("")
    lines.append("## 7. 风险检查")
    lines.append("")
    risks = payload.get("risks") or {}
    site = risks.get("site_matrix") or []
    lines.append("### EnvironmentFeature / EnvironmentMaterial / Organism / Specimen")
    lines.append("")
    if not site:
        lines.append("无命中（含：图中无相关节点/边，或边均符合 potential_schema 且无 H14 场所误标）。")
    else:
        lines.append("| 类型 | 说明 | src | rel | tgt |")
        lines.append("| --- | --- | --- | --- | --- |")
        for s in site[:SAMPLE_LIMIT]:
            lines.append(
                f"| {_md_escape(s.get('kind'))} | {_md_escape(s.get('message'))} | "
                f"`{_md_escape(s.get('src_name'))}` | `{_md_escape(s.get('rel'))}` | "
                f"`{_md_escape(s.get('tgt_name'))}` |"
            )
    lines.append("")
    lines.append("### BioChemical / Computational ResearchStep 与 Parent")
    lines.append("")
    steps = risks.get("research_step_parent") or []
    if not steps:
        lines.append("无 ResearchStep 或无 H01/H01-B 命中。")
    else:
        lines.append("| 规则 | 名称 | 说明 |")
        lines.append("| --- | --- | --- |")
        for s in steps[:SAMPLE_LIMIT]:
            lines.append(
                f"| `{_md_escape(s.get('rule_id'))}` | {_md_escape(s.get('entity_name'))} | "
                f"{_md_escape(s.get('message'))} |"
            )
    lines.append("")
    lines.append("## 8. 限制与不可算项")
    lines.append("")
    lines.append("- DER 比率不计算；下列共现组**不是**重复判定：")
    lines.append("")
    cands = payload.get("duplicate_candidates") or []
    if not cands:
        lines.append("  无同文+同类+同 FROM_CHUNK 多节点组。")
    else:
        lines.append("| 论文 | 类 | 组大小 | 名称样例 |")
        lines.append("| --- | --- | ---: | --- |")
        for c in cands:
            names = ", ".join(c.get("names") or [])
            lines.append(
                f"| `{_md_escape(c.get('filename'))}` | `{_md_escape(c.get('label'))}` | "
                f"{c.get('size')} | {_md_escape(names)} |"
            )
    lines.append("")
    uncomputable = [
        f"- {k}: {v.get('reason')}"
        for k, v in summary.items()
        if isinstance(v, dict) and v.get("status") == "NOT_COMPUTABLE"
    ]
    if uncomputable:
        lines.append("本次 NOT_COMPUTABLE：")
        lines.extend(uncomputable)
    else:
        lines.append("除 DER 与 RCR 互斥项外，其余比率均已计算。")
        lines.append("- DER: " + (summary.get("der") or {}).get("reason", ""))
        if mutex.get("reason"):
            lines.append("- RCR mutex: " + str(mutex.get("reason")))
    lines.append("")
    return "\n".join(lines) + "\n"


def write_log(payload: Dict[str, Any], log_dir: Path | None = None) -> Path:
    directory = log_dir or LOG_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stamp = payload.get("generated_at") or datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = str(stamp).replace(":", "").replace("-", "").replace("T", "_")[:15]
    if len(safe) < 8:
        safe = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"judgement_{safe}.md"
    path.write_text(render_markdown(payload), encoding="utf-8")
    return path
