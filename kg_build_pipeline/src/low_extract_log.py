"""File logger for Low hierarchical expand sessions."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kg_build_pipeline.src.paths import REPO_ROOT


class LowExtractLogger:
    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = log_dir or (REPO_ROOT / "kg_build_pipeline" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path: Optional[Path] = None
        self._fh = None

    def start_session(self, filenames: List[str]) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = self.log_dir / f"low_expand_{ts}.jsonl"
        self._fh = self.path.open("w", encoding="utf-8")
        self._write(
            {
                "type": "session_start",
                "filenames": filenames,
                "ts": ts,
            }
        )
        return self.path

    def _write(self, obj: Dict[str, Any]) -> None:
        if not self._fh:
            return
        self._fh.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()

    def log_parent(self, filename: str, entry: Dict[str, Any]) -> None:
        self._write({"type": "parent", "filename": filename, **entry})

    def close(self) -> None:
        if self._fh:
            self._write({"type": "session_end"})
            self._fh.close()
            self._fh = None
