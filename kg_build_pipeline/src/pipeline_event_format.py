"""Human-readable formatting for structured pipeline WebSocket / log events."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _triple_str(triple: Any) -> str:
    if isinstance(triple, (list, tuple)) and len(triple) >= 3:
        return f"{triple[0]} -[{triple[1]}]-> {triple[2]}"
    return str(triple)


def _issue_lines(items: List[Dict[str, Any]], severity: str) -> List[str]:
    lines: List[str] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        rule_id = item.get("rule_id", "?")
        entity = item.get("entity_name") or item.get("entity") or ""
        msg = item.get("message") or item.get("reason") or ""
        prefix = f"  {rule_id} {severity}"
        if entity:
            prefix += f" [{entity}]"
        lines.append(f"{prefix}: {msg}")
    return lines


def _hist_str(hist: Dict[str, Any]) -> str:
    if not hist:
        return "—"
    parts = [f"{k}={v}" for k, v in sorted(hist.items(), key=lambda kv: (-int(kv[1]), kv[0]))]
    return ", ".join(parts)


def format_pipeline_event(event: Dict[str, Any]) -> Optional[str]:
    """Return a log line (or multi-line string) for structured events, or None."""
    etype = event.get("type")
    if etype == "log":
        return str(event.get("message", ""))

    if etype == "schema_extract":
        status = str(event.get("status", "?")).upper()
        fn = event.get("filename", "")
        triple = _triple_str(event.get("triple"))
        reason = event.get("reason") or ""
        phase = str(event.get("phase") or "build").lower()
        parent = event.get("parent") or ""
        if phase == "reextract":
            line = f"[mid_gate] reextract schema | {fn} | {status} | {triple}"
        elif phase.startswith("low_"):
            tag = {
                "low_pass1": "low_pass1",
                "low_pass2": "low_pass2",
                "low_repair": "low_repair",
                "low_child_pass1": "low_child",
            }.get(phase, phase)
            parent_s = f" parent={parent}" if parent else ""
            line = f"[{tag}] {fn}{parent_s} | {status} | {triple}"
        else:
            line = f"[build_kg] {fn} | {status} | {triple}"
        if reason and status not in ("OK",):
            line += f" ({reason})"
        return line

    if etype == "document_extract_summary":
        fn = event.get("filename", "")
        return (
            f"[build_kg] {fn} summary: ok={event.get('schemas_ok', 0)} "
            f"skip={event.get('schemas_skipped', 0)} fail={event.get('schemas_failed', 0)}"
        )

    if etype == "phase_a_coverage":
        fn = event.get("filename", "")
        hist = event.get("section_role_histogram") or {}
        lines = [
            f"[build_kg] {fn} Phase A coverage: "
            f"ok={event.get('ok', 0)} skip={event.get('skip', 0)} "
            f"fail={event.get('fail', 0)} / {event.get('expected_total', 0)} expected",
            f"[build_kg] {fn} section roles: {_hist_str(hist)}",
        ]
        missing = event.get("missing_triples") or []
        if missing:
            lines.append(f"[build_kg] {fn} Phase A missing ({len(missing)}):")
            for item in missing:
                if not isinstance(item, dict):
                    continue
                t = _triple_str(item.get("triple"))
                st = item.get("status", "?")
                reason = item.get("reason") or ""
                allowed = item.get("allowed_sections") or []
                allow_s = ",".join(str(a) for a in allowed) if allowed else "—"
                lines.append(
                    f"  - {t} | {st} | {reason} | allowed=[{allow_s}] "
                    f"| chunks={item.get('matching_chunk_count', 0)}"
                )
        return "\n".join(lines)

    if etype == "mid_gate_phase":
        phase = event.get("phase", "")
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        labels = {
            "validate": "SHACL/Cypher validation",
            "review": "Qwen reviewer running",
            "reextract": "Agent targeted re-extract",
            "done": "Quality gate done",
        }
        label = labels.get(phase, phase)
        return f"[mid_gate] {fn} iter {it} | {label}"

    if etype == "mid_gate_validate":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        hard_n = event.get("hard_count", 0)
        warn_n = event.get("warning_count", 0)
        lines = [f"[mid_gate] {fn} iter {it} | validate: hard={hard_n} warn={warn_n}"]
        lines.extend(_issue_lines(event.get("hard_violations") or [], "HARD"))
        lines.extend(_issue_lines(event.get("warnings") or [], "WARN"))
        return "\n".join(lines)

    if etype == "mid_gate_review":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        scores = event.get("scores") or {}
        decision = event.get("decision", "")
        n_issues = event.get("issue_count", 0)
        overall = scores.get("overall_score", event.get("overall_score", ""))
        return (
            f"[mid_gate] {fn} iter {it} | reviewer: score={overall} "
            f"decision={decision} ({n_issues} issues)"
        )

    if etype == "mid_gate_reextract":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        n = event.get("reextract_schemas", 0)
        merged = event.get("merged_issue_count")
        chunk = event.get("chunk_resolution") or {}
        chunk_s = ", ".join(f"{k}={v}" for k, v in chunk.items()) if chunk else "—"
        line = f"[mid_gate] {fn} iter {it} | agent re-extract: {n} schema calls | chunk: {chunk_s}"
        if merged is not None:
            line += f" | merged_issues={merged}"
        return line

    if etype == "mid_gate_scrub":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        clone_n = event.get("deleted_identical_ot", 0)
        ch_n = event.get("deleted_challenges_no_lexicon", 0)
        return (
            f"[mid_gate] {fn} iter {it} | scrub: identical-OT edges={clone_n}, "
            f"challenges-no-lexicon={ch_n}"
        )

    if etype == "mid_gate_reject":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        mode = event.get("mode", "")
        count = event.get("count", 0)
        names = event.get("names") or []
        preview = ", ".join(str(n) for n in names[:5])
        if len(names) > 5:
            preview += f", +{len(names) - 5} more"
        return (
            f"[mid_gate] {fn} iter {it} | pre-reject ({mode}): {count} nodes"
            + (f" [{preview}]" if preview else "")
        )

    if etype == "mid_gate_early_stop":
        fn = event.get("filename", "")
        it = event.get("iteration", "")
        hard = event.get("hard_count", "")
        reason = event.get("reason", "")
        return f"[mid_gate] {fn} iter {it} | early-stop: {reason} (hard={hard})"

    if etype == "low_expand_start":
        return (
            f"[low] start | strategy={event.get('strategy', '')} "
            f"| PASS docs={event.get('count', 0)}"
        )

    if etype == "low_expand_doc":
        return f"[low] {event.get('filename', '')} | {event.get('phase', '')}"

    if etype == "low_activate":
        return (
            f"[low_activate] {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| entries={len(event.get('entry_labels') or [])} "
            f"| labels={len(event.get('entity_labels') or [])} "
            f"| low_rows={event.get('low_rows', 0)}"
        )

    if etype == "low_entity":
        return (
            f"[low_entity] {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| allowed={event.get('allowed_labels', 0)} "
            f"| budget={event.get('budget_used', '')}"
        )

    if etype == "low_ll":
        return (
            f"[low_ll] {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| runnable={event.get('runnable_rows', 0)} "
            f"| missing={event.get('missing_triples', 0)}"
        )

    if etype == "low_ml":
        return (
            f"[low_ml] {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| rules={event.get('rule_created', 0)} "
            f"| remain={event.get('remaining_slots', 0)} "
            f"| llm={event.get('use_llm', False)}"
        )

    if etype == "low_pass1":
        return (
            f"[low_pass1] {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| mode={event.get('routing_mode', '')} | schema_rows={event.get('schema_rows', 0)}"
        )

    if etype == "low_child_pass1":
        return (
            f"[low_child] {event.get('filename', '')} | child={event.get('parent', '')} "
            f"| mid={event.get('mid_parent', '')} | schema_rows={event.get('schema_rows', 0)}"
            f"| fallback={event.get('text_fallback', False)}"
        )

    if etype == "low_child_repair":
        return (
            f"[low_child] repair | {event.get('filename', '')} | {event.get('parent', '')} "
            f"| rules={event.get('rule_ids', [])} | rows={event.get('schema_rows', 0)}"
        )

    if etype == "low_abort":
        return (
            f"[low] ABORT | {event.get('reason', '')} | {event.get('filename', '')} "
            f"| {event.get('parent', '')} | {event.get('message', '')}"
        )

    if etype == "low_extract_batch":
        return (
            f"[low] extract | {event.get('filename', '')} | parent={event.get('parent', '')} "
            f"| {event.get('batch', '')} | ok={event.get('ok', 0)}/{event.get('schema_rows', 0)} "
            f"| phase={event.get('phase', '')}"
        )

    if etype == "low_validate":
        return (
            f"[low] validate | {event.get('filename', '')} | {event.get('parent', '')} "
            f"| hard={event.get('hard_count', 0)} warn={event.get('warning_count', 0)}"
        )

    if etype == "low_repair":
        return (
            f"[low] repair | {event.get('filename', '')} | round={event.get('round', '')} "
            f"| rules={event.get('rule_ids', [])}"
        )

    if etype == "low_review":
        return (
            f"[low] review | {event.get('filename', '')} | {event.get('decision', '')} "
            f"| neighbor={event.get('needs_neighbor_pass')}"
        )

    if etype == "low_pass2":
        return (
            f"[low] pass2 | {event.get('filename', '')} | schema_rows={event.get('schema_rows', 0)} "
            f"| ±chunks={event.get('prev_chunks', 0)}/{event.get('next_chunks', 0)}"
        )

    if etype == "low_cross_parent":
        return (
            f"[low] cross-parent | {event.get('filename', '')} "
            f"| specimen={event.get('specimen_links', 0)} "
            f"data={event.get('data_links', 0)} arg={event.get('argument_links', 0)}"
        )

    if etype == "low_final_validate":
        return (
            f"[low] final | {event.get('filename', '')} "
            f"| hard={event.get('hard_count', 0)} warn={event.get('warning_count', 0)}"
        )

    if etype == "low_final_repair":
        return (
            f"[low] final-repair | {event.get('filename', '')} "
            f"| round={event.get('round', '')} hard={event.get('hard_count', 0)}"
        )

    return None
