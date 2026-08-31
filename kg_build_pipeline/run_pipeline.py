#!/usr/bin/env python3
"""KG Build Pipeline CLI — one-click entry (also used by run_pipeline.bat and 99_run_all.ipynb)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.runner import PipelineRunner


def main() -> int:
    p = argparse.ArgumentParser(description="BAE KG Build Pipeline")
    p.add_argument(
        "--config",
        type=Path,
        default=PIPELINE_ROOT / "config.yaml",
        help="Path to config.yaml",
    )
    p.add_argument("--all", action="store_true", help="Run all enabled stages in config")
    p.add_argument(
        "--stage",
        type=str,
        default="",
        help="Comma-separated stages (overrides --all)",
    )
    p.add_argument("--skip", type=str, default="", help="Comma-separated stages to skip")
    args = p.parse_args()

    cfg = PipelineConfig.load(args.config)
    skip = [s.strip() for s in args.skip.split(",") if s.strip()]
    only = None
    if args.stage:
        only = [s.strip() for s in args.stage.split(",") if s.strip()]
    elif not args.all:
        p.error("Specify --all or --stage")

    runner = PipelineRunner(cfg, skip=skip, only=only)
    results = runner.run()
    print("\n=== PIPELINE COMPLETE ===")
    print(json.dumps(results.get("summary", results), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
