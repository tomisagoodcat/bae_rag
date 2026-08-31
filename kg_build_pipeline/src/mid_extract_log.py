"""Append-only mid extraction log (build_kg mid + quality gate)."""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kg_build_pipeline.src.paths import REPO_ROOT
from kg_build_pipeline.src.pipeline_event_format import format_pipeline_event

DEFAULT_LOG_PATH = REPO_ROOT / "kg_build_pipeline" / "logs" / "mid_extract_log.txt"


def _triple_str(triple: Any) -> str:
    if isinstance(triple, (list, tuple)) and len(triple) >= 3:
        return f"{triple[0]} -[{triple[1]}]-> {triple[2]}"
    return str(triple)


class MidExtractLogger:
    """Thread-safe writer for logs/mid_extract_log.txt."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_LOG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._current_doc: Optional[str] = None
        self._doc_first_iter: Dict[str, Dict[str, Any]] = {}
        self._doc_last_iter: Dict[str, Dict[str, Any]] = {}

    def start_session(
        self,
        extract_mode: str,
        selected_files: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 72}\n")
                f.write(f"=== Mid Extract Session {datetime.now().isoformat()} ===\n")
                f.write(f"extract_mode: {extract_mode}\n")
                if selected_files:
                    f.write(f"papers ({len(selected_files)}): {selected_files}\n")
                f.write(f"{'=' * 72}\n")

    def handle_event(self, event: Dict[str, Any]) -> None:
        etype = event.get("type")
        if etype == "document_progress":
            fn = event.get("filename")
            if fn:
                self._begin_doc(str(fn))
        elif etype == "schema_extract":
            self._write_schema_extract(event)
        elif etype == "document_extract_summary":
            line = format_pipeline_event(event)
            if line:
                self._write_line(f"  Phase A | {line.replace('[build_kg] ', '')}")
        elif etype == "phase_a_coverage":
            self._write_phase_a_coverage(event)
        elif etype in {
            "mid_gate_phase",
            "mid_gate_validate",
            "mid_gate_review",
            "mid_gate_reextract",
            "mid_gate_reject",
            "mid_gate_early_stop",
        }:
            self._write_mid_gate(event)
        elif etype == "log" and event.get("message", "").startswith("[mid_quality_gate]"):
            fn = event.get("message", "").replace("[mid_quality_gate]", "").strip()
            self._begin_doc(fn)

    def finish_document(self, filename: str, status: str, final_score: Any = None) -> None:
        with self._lock:
            first = self._doc_first_iter.get(filename, {})
            last = self._doc_last_iter.get(filename, {})
            lines = [f"\n--- Improvement ({filename}) ---"]
            if first or last:
                lines.append(
                    f"  hard: {first.get('hard_count', '—')} -> {last.get('hard_count', '—')}"
                )
                lines.append(
                    f"  warn: {first.get('warning_count', '—')} -> {last.get('warning_count', '—')}"
                )
                lines.append(
                    f"  score: {first.get('overall_score', '—')} -> {last.get('overall_score', '—')}"
                )
            lines.append(f"  final: {status}" + (f" score={final_score}" if final_score else ""))
        self._write_lines(lines)

    def _begin_doc(self, filename: str) -> None:
        if self._current_doc != filename:
            self._current_doc = filename
            self._write_line(f"\n## Paper: {filename}")

    def _write_schema_extract(self, event: Dict[str, Any]) -> None:
        fn = event.get("filename")
        if fn:
            self._begin_doc(str(fn))
        phase = str(event.get("phase") or "build").lower()
        status = str(event.get("status", "?")).upper()
        triple = _triple_str(event.get("triple"))
        reason = event.get("reason") or ""
        if phase == "reextract":
            line = f"  Phase B | reextract schema | {status} | {triple}"
        else:
            line = f"  Phase A | {status} | {triple}"
        if reason and status != "OK":
            line += f" ({reason})"
        self._write_line(line)

    def _write_phase_a_coverage(self, event: Dict[str, Any]) -> None:
        fn = event.get("filename")
        if fn:
            self._begin_doc(str(fn))
        hist = event.get("section_role_histogram") or {}
        hist_s = (
            ", ".join(f"{k}={v}" for k, v in sorted(hist.items(), key=lambda kv: (-int(kv[1]), kv[0])))
            if hist
            else "—"
        )
        lines = [
            f"  Phase A | section roles: {hist_s}",
            (
                f"  Phase A summary: ok={event.get('ok', 0)} "
                f"skip={event.get('skip', 0)} fail={event.get('fail', 0)} "
                f"/ {event.get('expected_total', 0)} expected"
            ),
        ]
        missing = event.get("missing_triples") or []
        if missing:
            lines.append(f"  Phase A missing ({len(missing)}):")
            for item in missing:
                if not isinstance(item, dict):
                    continue
                t = _triple_str(item.get("triple"))
                st = item.get("status", "?")
                reason = item.get("reason") or ""
                allowed = item.get("allowed_sections") or []
                allow_s = ",".join(str(a) for a in allowed) if allowed else "—"
                lines.append(
                    f"    - {t} | {st} | {reason} | allowed=[{allow_s}] "
                    f"| chunks={item.get('matching_chunk_count', 0)}"
                )
        self._write_lines(lines)

    def _write_mid_gate(self, event: Dict[str, Any]) -> None:
        fn = event.get("filename")
        if fn:
            self._begin_doc(str(fn))
        etype = event.get("type")
        if etype == "mid_gate_validate":
            it = int(event.get("iteration", 0))
            key = str(fn or "")
            snap = {
                "hard_count": event.get("hard_count", 0),
                "warning_count": event.get("warning_count", 0),
            }
            if key and it == 1:
                self._doc_first_iter[key] = dict(snap)
            if key:
                self._doc_last_iter[key] = dict(snap)
        if etype == "mid_gate_review":
            key = str(fn or "")
            it = int(event.get("iteration", 0))
            scores = event.get("scores") or {}
            snap = {
                "overall_score": scores.get("overall_score", event.get("overall_score")),
            }
            if key:
                prev = self._doc_last_iter.get(key, {})
                prev.update(snap)
                self._doc_last_iter[key] = prev
                if it == 1:
                    first = self._doc_first_iter.get(key, {})
                    first.update(snap)
                    self._doc_first_iter[key] = first
        line = format_pipeline_event(event)
        if line:
            prefix = "  Phase B | "
            if "\n" in line:
                self._write_line("  Phase B |")
                for sub in line.split("\n"):
                    self._write_line(f"    {sub}")
            else:
                self._write_line(prefix + line.replace("[mid_gate] ", ""))

    def _write_line(self, text: str) -> None:
        if not text:
            return
        self._write_lines([text])

    def _write_lines(self, lines: List[str]) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
