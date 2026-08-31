"""Path constants for kg_build_pipeline (isolated from repo output/)."""
from __future__ import annotations

from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_ROOT.parent
SCHEMA_DIR = PIPELINE_ROOT / "schema"
DEFAULT_CONFIG = PIPELINE_ROOT / "config.yaml"
DEFAULT_MARKDOWN_DIR = REPO_ROOT / "data" / "markdown" / "forTest"
DOCS_DIR = PIPELINE_ROOT / "docs"


def resolve_repo_path(rel: str | Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else REPO_ROOT / p


def ensure_repo_on_syspath() -> None:
    import sys

    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
