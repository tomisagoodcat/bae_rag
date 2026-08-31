"""Pipeline orchestrator: stage order, skip flags, summary stats."""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.schema_loader import validate_schema_dir

STAGE_ORDER = [
    "clear_neo4j",
    "build_kg",
    "mid_quality_gate",
    "low_expand",
    "subgraph_annotate",
    "chunk_merge",
    "entity_merge",
    "pagerank",
    "metapath",
]

EventCallback = Callable[[Dict[str, Any]], None]


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _build_driver(cfg: PipelineConfig) -> Driver:
    from kg_build_pipeline.src.neo4j_util import build_neo4j_driver

    return build_neo4j_driver(cfg)


def _require_torch(stage: str) -> None:
    """Fail fast with a actionable message when pip-installed torch cannot load on Windows."""
    try:
        import torch  # noqa: F401
    except OSError as exc:
        raise RuntimeError(
            f"PyTorch failed to load (required for {stage}). "
            "Use conda env tomluck2 or recreate pipelineD_env from it: "
            r"C:\Users\tom\.conda\envs\tomluck2\python.exe -m venv --system-site-packages pipelineD_env. "
            "Do not use Windows Store Python + pip torch on this machine. "
            f"Original error: {exc}"
        ) from exc


class PipelineRunner:
    def __init__(
        self,
        cfg: PipelineConfig,
        skip: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        on_event: Optional[EventCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self.cfg = cfg
        self.skip = set(skip or [])
        self.only = set(only) if only else None
        self.results: Dict[str, Any] = {}
        self.on_event = on_event
        self.cancel_event = cancel_event

    def _emit(self, event: Dict[str, Any]) -> None:
        if self.on_event:
            self.on_event(event)

    def _log(self, message: str) -> None:
        print(message)
        self._emit({"type": "log", "message": message})

    def _should_run(self, stage: str) -> bool:
        if self.only is not None and stage not in self.only:
            return False
        if stage in self.skip:
            return False
        return self.cfg.stage_enabled(stage)

    def _planned_stages(self) -> List[str]:
        return [s for s in STAGE_ORDER if self._should_run(s)]

    def _check_cancelled(self) -> bool:
        if self.cancel_event and self.cancel_event.is_set():
            self._log("Pipeline cancelled by user.")
            self._emit({"type": "cancelled"})
            return True
        return False

    def run(self) -> Dict[str, Any]:
        start_time = time.time()
        planned = self._planned_stages()
        total = len(planned)
        completed = 0

        self._log("Validating schema...")
        validate_schema_dir(self.cfg.schema_dir)

        torch_stages = {"build_kg", "mid_quality_gate", "low_expand", "metapath"}
        if any(self._should_run(s) for s in torch_stages):
            _require_torch("build_kg / embedding stages")

        driver: Driver | None = None
        cancelled = False
        error: Optional[str] = None

        try:
            if any(self._should_run(s) for s in STAGE_ORDER if s != "clear_neo4j"):
                driver = _build_driver(self.cfg)
                driver.verify_connectivity()

            stage_runners = [
                ("clear_neo4j", self._run_clear_neo4j),
                ("build_kg", self._run_build_kg),
                ("mid_quality_gate", self._run_mid_quality_gate),
                ("low_expand", self._run_low_expand),
                ("subgraph_annotate", self._run_subgraph_annotate),
                ("chunk_merge", self._run_chunk_merge),
                ("entity_merge", self._run_entity_merge),
                ("pagerank", self._run_pagerank),
                ("metapath", self._run_metapath),
            ]

            for stage, runner_fn in stage_runners:
                if not self._should_run(stage):
                    continue
                if self._check_cancelled():
                    cancelled = True
                    break

                index = planned.index(stage) + 1
                self._emit(
                    {
                        "type": "stage_start",
                        "stage": stage,
                        "index": index,
                        "total": total,
                    }
                )
                self._log(f"\n=== {stage} ===")

                try:
                    result = runner_fn(driver)
                    self.results[stage] = result
                    self._emit(
                        {
                            "type": "stage_done",
                            "stage": stage,
                            "index": index,
                            "total": total,
                            "result": _json_safe(result),
                        }
                    )
                except Exception as exc:
                    error = str(exc)
                    self._emit({"type": "error", "message": error, "stage": stage})
                    raise

                completed += 1

            if driver and not cancelled:
                self.results["summary"] = self._summary(driver, start_time, planned, completed)
        finally:
            if driver:
                driver.close()

        duration_sec = round(time.time() - start_time, 2)
        if cancelled:
            self.results["cancelled"] = True
            self.results["duration_sec"] = duration_sec
            return self.results

        if error is None:
            summary = self.results.get("summary", {})
            if isinstance(summary, dict):
                summary["duration_sec"] = duration_sec
            self._emit({"type": "complete", "summary": _json_safe(self.results)})
        return self.results

    def _run_clear_neo4j(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.neo4j_util import clear_neo4j

        d = driver or _build_driver(self.cfg)
        clear_neo4j(d, self.cfg.neo4j_database)
        if driver is None:
            d.close()
        return {"ok": True}

    def _run_build_kg(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.build_kg import run_build_kg

        if not self.cfg.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY required for build_kg")
        return run_build_kg(self.cfg, driver=driver, on_event=self._emit)

    def _run_mid_quality_gate(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.mid_quality_gate import run_mid_quality_gate

        if not self.cfg.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY required for mid_quality_gate re-extract")
        assert driver is not None
        return run_mid_quality_gate(self.cfg, driver=driver, on_event=self._emit)

    def _run_low_expand(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.low_expand import run_low_expand

        assert driver is not None
        return run_low_expand(self.cfg, driver=driver, on_event=self._emit)

    def _run_subgraph_annotate(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.subgraph_annotate import run_subgraph_annotate

        assert driver is not None
        return run_subgraph_annotate(self.cfg, driver)

    def _run_chunk_merge(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.chunk_merge import run_chunk_merge

        assert driver is not None
        return run_chunk_merge(driver)

    def _run_entity_merge(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.entity_merge import run_entity_merge

        assert driver is not None
        return run_entity_merge(self.cfg, driver)

    def _run_pagerank(self, driver: Driver | None) -> Dict[str, Any]:
        from kg_build_pipeline.src.stages.pagerank import run_pagerank

        assert driver is not None
        return run_pagerank(self.cfg, driver)

    def _run_metapath(self, driver: Driver | None) -> Dict[str, Any]:
        import importlib

        import kg_build_pipeline.src.stages.metapath as metapath_mod

        importlib.reload(metapath_mod)
        assert driver is not None
        return metapath_mod.run_metapath(self.cfg, driver)

    def _summary(
        self,
        driver: Driver,
        start_time: float,
        planned: List[str],
        completed: int,
    ) -> Dict[str, Any]:
        from kg_build_pipeline.src.neo4j_util import get_db_stats

        stats = get_db_stats(driver, self.cfg.neo4j_database)
        stages_run = [s for s in planned if s in self.results]
        stages_failed = [s for s in planned if s not in self.results]
        build_kg = self.results.get("build_kg", {})
        if not isinstance(build_kg, dict):
            build_kg = {}

        return {
            **stats,
            "duration_sec": round(time.time() - start_time, 2),
            "stages_run": stages_run,
            "stages_failed": stages_failed,
            "stages_completed": completed,
            "stages_total": len(planned),
            "entities": build_kg.get("entities"),
            "relations": build_kg.get("relations"),
            "documents": build_kg.get("document_count"),
            "succeeded_docs": build_kg.get("succeeded_docs"),
            "failed_docs": build_kg.get("failed_docs"),
        }
