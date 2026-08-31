"""FastAPI web UI for the KG build pipeline."""
from __future__ import annotations

import asyncio
import json
import sys
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TextIO

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.neo4j_util import build_neo4j_driver, get_db_stats
from kg_build_pipeline.src.paths import DEFAULT_CONFIG, REPO_ROOT, ensure_repo_on_syspath
from kg_build_pipeline.src.mid_extract_log import DEFAULT_LOG_PATH, MidExtractLogger
from kg_build_pipeline.src.pipeline_event_format import format_pipeline_event
from kg_build_pipeline.src.runner import PipelineRunner, STAGE_ORDER
from kg_build_pipeline.src.stages.document_loader import (
    effective_document_count,
    list_markdown_documents,
)

ensure_repo_on_syspath()

UI_ROOT = Path(__file__).resolve().parent
STATIC_DIR = UI_ROOT / "static"
MANIFEST_PATH = UI_ROOT / "stage_manifest.json"
LOGS_DIR = UI_ROOT.parent / "logs"

app = FastAPI(title="KG Build Pipeline UI")


class BuildRequest(BaseModel):
    stages: Dict[str, bool] = Field(default_factory=dict)
    selected_files: List[str] = Field(default_factory=list)
    extract_mode: str = Field(default="mid")  # mid | expand_mid | low_and_all | mid_then_low


class FileLogWriter:
    def __init__(self, path: Path) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file: TextIO = path.open("a", encoding="utf-8")

    def write_header(
        self,
        stages: Dict[str, bool],
        config_path: Path,
        selected_files: Optional[List[str]] = None,
        extract_mode: Optional[str] = None,
    ) -> None:
        self._file.write(f"=== KG Build Log {datetime.now().isoformat()} ===\n")
        self._file.write(f"Config: {config_path}\n")
        if extract_mode:
            self._file.write(f"Extract mode: {extract_mode}\n")
        self._file.write(f"Stages: {json.dumps(stages, ensure_ascii=False)}\n")
        if selected_files is not None:
            self._file.write(
                f"Selected files ({len(selected_files)}): "
                f"{json.dumps(selected_files, ensure_ascii=False)}\n"
            )
        self._file.write("---\n")
        self._file.flush()

    def write_event(self, event: Dict[str, Any]) -> None:
        formatted = format_pipeline_event(event)
        if formatted is not None:
            self._file.write(formatted + "\n")
        elif event.get("type") != "log":
            self._file.write(json.dumps(event, ensure_ascii=False) + "\n")
        else:
            self._file.write(event.get("message", "") + "\n")
        self._file.flush()

    def close(self, summary: Optional[Dict[str, Any]] = None) -> None:
        self._file.write("=== END ===\n")
        if summary is not None:
            self._file.write(json.dumps(summary, ensure_ascii=False, indent=2))
            self._file.write("\n")
        self._file.flush()
        self._file.close()


class BuildManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.running = False
        self.cancel_event = threading.Event()
        self.current_stage: Optional[str] = None
        self.progress_index = 0
        self.progress_total = 0
        self.last_summary: Optional[Dict[str, Any]] = None
        self.last_error: Optional[str] = None
        self.current_log_path: Optional[Path] = None
        self._file_logger: Optional[FileLogWriter] = None
        self._mid_logger: Optional[MidExtractLogger] = None
        self._extract_mode: str = "mid"
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subscribers: Set[asyncio.Queue] = set()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def _broadcast(self, event: Dict[str, Any]) -> None:
        if not self._loop:
            return
        for q in list(self._subscribers):
            asyncio.run_coroutine_threadsafe(q.put(event), self._loop)

    def on_pipeline_event(self, event: Dict[str, Any]) -> None:
        if self._file_logger:
            self._file_logger.write_event(event)
        if self._mid_logger:
            self._mid_logger.handle_event(event)
            if event.get("type") == "mid_gate_phase" and event.get("phase") == "done":
                self._mid_logger.finish_document(
                    str(event.get("filename", "")),
                    str(event.get("status", "")),
                    event.get("final_score"),
                )

        etype = event.get("type")
        if etype == "stage_start":
            self.current_stage = event.get("stage")
            self.progress_index = int(event.get("index", 0))
            self.progress_total = int(event.get("total", 0))
        elif etype == "stage_done":
            self.progress_index = int(event.get("index", self.progress_index))
            self.progress_total = int(event.get("total", self.progress_total))
        elif etype == "complete":
            self.last_summary = event.get("summary")
            self.current_stage = None
        elif etype == "error":
            self.last_error = event.get("message")
            self.current_stage = None
        elif etype == "cancelled":
            self.current_stage = None
        self._broadcast(event)

    def start_build(
        self,
        stages: Dict[str, bool],
        selected_files: Optional[List[str]] = None,
        extract_mode: str = "mid",
    ) -> None:
        selected_files = list(selected_files or [])
        extract_mode = (extract_mode or "mid").strip().lower()
        if extract_mode not in {"mid", "low_and_all", "expand_mid", "mid_then_low"}:
            extract_mode = "mid"
        with self._lock:
            if self.running:
                raise HTTPException(status_code=409, detail="A build is already running")
            self.running = True
            self.cancel_event = threading.Event()
            self.current_stage = None
            self.progress_index = 0
            self.progress_total = 0
            self.last_error = None
            self.last_summary = None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_log_path = LOGS_DIR / f"build_{timestamp}.log"
            self._file_logger = FileLogWriter(self.current_log_path)
            self._extract_mode = extract_mode
            self._mid_logger = None
            if extract_mode == "mid":
                self._mid_logger = MidExtractLogger()
                self._mid_logger.start_session(extract_mode, selected_files)
            stages_applied, adjustments = apply_extract_mode_stages(stages, extract_mode)
            self._file_logger.write_header(
                stages_applied, DEFAULT_CONFIG, selected_files, extract_mode=extract_mode
            )
            for note in adjustments:
                self._file_logger.write_event({"type": "log", "message": note})

        thread = threading.Thread(
            target=self._run_build,
            args=(stages_applied, selected_files, extract_mode),
            daemon=True,
        )
        thread.start()

    def cancel_build(self) -> bool:
        with self._lock:
            if not self.running:
                return False
            self.cancel_event.set()
            return True

    def _run_build(
        self,
        stages: Dict[str, bool],
        selected_files: Optional[List[str]] = None,
        extract_mode: str = "mid",
    ) -> None:
        summary: Optional[Dict[str, Any]] = None
        try:
            cfg = PipelineConfig.load(DEFAULT_CONFIG)
            merged = deepcopy(cfg.stages)
            for key, enabled in stages.items():
                if key in STAGE_ORDER:
                    merged[key] = bool(enabled)

            build_kg_cfg = dict(cfg.build_kg)
            merged, adjustments = apply_extract_mode_stages(stages, extract_mode)
            if extract_mode == "mid":
                build_kg_cfg["schema_tiers"] = ["mid"]
            elif extract_mode in {"expand_mid", "mid_then_low"}:
                build_kg_cfg["schema_tiers"] = ["mid"]
            else:
                build_kg_cfg.pop("schema_tiers", None)

            cfg.stages = merged
            cfg.raw.setdefault("pipeline", {})["extract_mode"] = extract_mode
            low_ext = dict(cfg.raw.get("low_extraction") or {})
            if extract_mode in {"expand_mid", "mid_then_low"}:
                low_ext["enabled"] = True
            elif extract_mode == "low_and_all":
                low_ext["enabled"] = False
            cfg.raw["low_extraction"] = low_ext
            if selected_files:
                build_kg_cfg["selected_files"] = list(selected_files)
            cfg.build_kg = build_kg_cfg

            for note in adjustments:
                self.on_pipeline_event({"type": "log", "message": note})

            runner = PipelineRunner(
                cfg,
                on_event=self.on_pipeline_event,
                cancel_event=self.cancel_event,
            )
            summary = runner.run()
        except Exception:
            pass
        finally:
            if self._file_logger:
                self._file_logger.close(summary)
                self._file_logger = None
            with self._lock:
                self.running = False


build_manager = BuildManager()


def _load_manifest() -> List[Dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def apply_extract_mode_stages(
    stages: Dict[str, bool],
    extract_mode: str,
) -> tuple[Dict[str, bool], List[str]]:
    """Merge UI stage toggles with extract-mode constraints; return notes."""
    merged = deepcopy(stages)
    notes: List[str] = []
    manifest = {item["id"]: item for item in _load_manifest()}

    if extract_mode == "mid":
        merged["mid_quality_gate"] = True
        merged["low_expand"] = False
        merged["metapath"] = False
        merged["pagerank"] = False
        if stages.get("metapath"):
            notes.append("[auto] MetaPath disabled (incompatible with Extract Mid).")
        if stages.get("pagerank"):
            notes.append("[auto] PageRank disabled (incompatible with Extract Mid).")
        if stages.get("low_expand"):
            notes.append("[auto] Low Expand disabled in Extract Mid (enable Mid+Low or Extract Low).")
    elif extract_mode == "mid_then_low":
        merged["mid_quality_gate"] = True
        merged["low_expand"] = True
        notes.append("[auto] Mid+Low: mid_quality_gate and low_expand enabled.")
    elif extract_mode == "expand_mid":
        merged["clear_neo4j"] = False
        merged["build_kg"] = False
        merged["mid_quality_gate"] = False
        merged["low_expand"] = True
        notes.append(
            "[auto] Extract Low: expand mid_gate_status=PASS parents only "
            "(no clear / build_kg / mid gate)."
        )
    else:
        # Deprecated low_and_all — isolate from new low_expand
        merged["mid_quality_gate"] = False
        merged["low_expand"] = False
        if stages.get("mid_quality_gate"):
            notes.append("[auto] Mid Quality Gate disabled (Extract Low and All — deprecated).")
        if stages.get("low_expand"):
            notes.append(
                "[auto] Low Hierarchical Expand disabled (incompatible with deprecated low_and_all)."
            )

    for stage_id, item in manifest.items():
        incompatible = item.get("incompatible_extract_modes") or []
        if extract_mode in incompatible and merged.get(stage_id):
            merged[stage_id] = False
            reason = item.get("incompatible_reason", "incompatible with extract mode")
            notes.append(f"[auto] {item.get('title', stage_id)} disabled: {reason}")

    return merged, notes


def _default_stages() -> Dict[str, bool]:
    cfg = PipelineConfig.load(DEFAULT_CONFIG)
    return {item["id"]: cfg.stage_enabled(item["id"]) for item in _load_manifest()}


def _document_payload() -> Dict[str, Any]:
    cfg = PipelineConfig.load(DEFAULT_CONFIG)
    markdown_dir = cfg.markdown_dir
    max_docs = cfg.build_kg.get("max_docs", "all")
    files = list_markdown_documents(str(markdown_dir))
    total_files = len(files)
    effective = effective_document_count(str(markdown_dir), max_docs)
    try:
        rel_dir = markdown_dir.relative_to(REPO_ROOT)
        markdown_display = str(rel_dir).replace("\\", "/")
    except ValueError:
        markdown_display = str(markdown_dir)
    return {
        "markdown_dir": markdown_display,
        "total_files": total_files,
        "max_docs": max_docs,
        "effective_count": effective,
        "files": files,
    }


@app.on_event("startup")
async def _startup() -> None:
    build_manager.set_loop(asyncio.get_running_loop())


@app.get("/api/stages")
def api_stages() -> Dict[str, Any]:
    return {"stages": _load_manifest(), "defaults": _default_stages()}


@app.get("/api/documents")
def api_documents() -> Dict[str, Any]:
    return _document_payload()


@app.get("/api/documents/count")
def api_documents_count() -> Dict[str, Any]:
    return _document_payload()


@app.get("/api/neo4j/stats")
def api_neo4j_stats() -> Dict[str, Any]:
    cfg = PipelineConfig.load(DEFAULT_CONFIG)
    driver = build_neo4j_driver(cfg)
    try:
        driver.verify_connectivity()
        return get_db_stats(driver, cfg.neo4j_database)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {exc}") from exc
    finally:
        driver.close()


@app.post("/api/build")
def api_build(req: BuildRequest) -> Dict[str, str]:
    build_kg_enabled = bool(req.stages.get("build_kg", False))
    if build_kg_enabled and not req.selected_files:
        raise HTTPException(
            status_code=400,
            detail="Select at least one paper when Build Knowledge Graph is enabled",
        )
    mode = (req.extract_mode or "mid").strip().lower()
    if mode not in {"mid", "low_and_all", "expand_mid", "mid_then_low"}:
        raise HTTPException(
            status_code=400,
            detail="extract_mode must be mid | expand_mid | mid_then_low | low_and_all",
        )
    build_manager.start_build(req.stages, req.selected_files, extract_mode=mode)
    return {"status": "started", "extract_mode": mode}


@app.post("/api/build/cancel")
def api_build_cancel() -> Dict[str, Any]:
    cancelled = build_manager.cancel_build()
    return {"cancelled": cancelled}


@app.get("/api/build/status")
def api_build_status() -> Dict[str, Any]:
    return {
        "running": build_manager.running,
        "current_stage": build_manager.current_stage,
        "progress": {
            "index": build_manager.progress_index,
            "total": build_manager.progress_total,
        },
        "last_summary": build_manager.last_summary,
        "last_error": build_manager.last_error,
    }


@app.get("/api/build/mid-extract-log")
def api_mid_extract_log() -> Dict[str, Any]:
    path = DEFAULT_LOG_PATH
    if not path.is_file():
        return {"path": None, "filename": None}
    return {"path": str(path), "filename": path.name}


@app.get("/api/build/last-log")
def api_build_last_log() -> Dict[str, Any]:
    path = build_manager.current_log_path
    if path is None:
        logs = sorted(LOGS_DIR.glob("build_*.log"), reverse=True)
        path = logs[0] if logs else None
    if path is None or not path.is_file():
        return {"path": None, "filename": None}
    return {"path": str(path), "filename": path.name}


@app.websocket("/ws")
async def websocket_logs(ws: WebSocket) -> None:
    await ws.accept()
    queue = build_manager.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        build_manager.unsubscribe(queue)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main() -> None:
    import uvicorn

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    uvicorn.run(
        "kg_build_pipeline.ui.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
