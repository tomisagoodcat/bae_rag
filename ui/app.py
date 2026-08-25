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
from kg_build_pipeline.src.runner import PipelineRunner, STAGE_ORDER
from kg_build_pipeline.src.stages.document_loader import (
    count_markdown_documents,
    effective_document_count,
)

ensure_repo_on_syspath()

UI_ROOT = Path(__file__).resolve().parent
STATIC_DIR = UI_ROOT / "static"
MANIFEST_PATH = UI_ROOT / "stage_manifest.json"
LOGS_DIR = UI_ROOT.parent / "logs"

app = FastAPI(title="KG Build Pipeline UI")


class BuildRequest(BaseModel):
    stages: Dict[str, bool] = Field(default_factory=dict)


class FileLogWriter:
    def __init__(self, path: Path) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file: TextIO = path.open("a", encoding="utf-8")

    def write_header(self, stages: Dict[str, bool], config_path: Path) -> None:
        self._file.write(f"=== KG Build Log {datetime.now().isoformat()} ===\n")
        self._file.write(f"Config: {config_path}\n")
        self._file.write(f"Stages: {json.dumps(stages, ensure_ascii=False)}\n")
        self._file.write("---\n")
        self._file.flush()

    def write_event(self, event: Dict[str, Any]) -> None:
        if event.get("type") == "log":
            self._file.write(event.get("message", "") + "\n")
        else:
            self._file.write(json.dumps(event, ensure_ascii=False) + "\n")
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

    def start_build(self, stages: Dict[str, bool]) -> None:
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
            self._file_logger.write_header(stages, DEFAULT_CONFIG)

        thread = threading.Thread(target=self._run_build, args=(stages,), daemon=True)
        thread.start()

    def cancel_build(self) -> bool:
        with self._lock:
            if not self.running:
                return False
            self.cancel_event.set()
            return True

    def _run_build(self, stages: Dict[str, bool]) -> None:
        summary: Optional[Dict[str, Any]] = None
        try:
            cfg = PipelineConfig.load(DEFAULT_CONFIG)
            merged = deepcopy(cfg.stages)
            for key, enabled in stages.items():
                if key in STAGE_ORDER:
                    merged[key] = bool(enabled)
            cfg.stages = merged

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


def _default_stages() -> Dict[str, bool]:
    cfg = PipelineConfig.load(DEFAULT_CONFIG)
    return {item["id"]: cfg.stage_enabled(item["id"]) for item in _load_manifest()}


def _document_count_payload() -> Dict[str, Any]:
    cfg = PipelineConfig.load(DEFAULT_CONFIG)
    markdown_dir = cfg.markdown_dir
    max_docs = cfg.build_kg.get("max_docs", "all")
    total_files = count_markdown_documents(str(markdown_dir))
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
    }


@app.on_event("startup")
async def _startup() -> None:
    build_manager.set_loop(asyncio.get_running_loop())


@app.get("/api/stages")
def api_stages() -> Dict[str, Any]:
    return {"stages": _load_manifest(), "defaults": _default_stages()}


@app.get("/api/documents/count")
def api_documents_count() -> Dict[str, Any]:
    return _document_count_payload()


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
    build_manager.start_build(req.stages)
    return {"status": "started"}


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
