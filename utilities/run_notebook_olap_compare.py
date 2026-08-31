"""Run notebook-equivalent OLAP compare (Stateful vs Stateless).

Executes G pipeline cells from `3_0_2 Retevie.ipynb` then the OLAP compare block
(same as ##### OLAP 对比评估 cell).

Usage:
  python utilities/run_notebook_olap_compare.py
  python utilities/run_notebook_olap_compare.py --test-set legacy10
  python utilities/run_notebook_olap_compare.py --test-set all
  python utilities/run_notebook_olap_compare.py --test-set first --max-scenarios 2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utilities.run_retrieval_eval import DEFAULT_LOG, run_olap_compare  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Notebook OLAP compare runner")
    parser.add_argument(
        "--test-set",
        choices=["legacy10", "all", "first"],
        default=None,
        help="legacy10=q01–q10 (default); all=66; first needs --max-scenarios",
    )
    parser.add_argument("--max-scenarios", type=int, default=0)
    parser.add_argument("--log-md", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--version", default="v5-recall-wide-legacy10")
    args = parser.parse_args()
    return run_olap_compare(
        version=args.version,
        log_path=args.log_md,
        skip_smoke=args.skip_smoke,
        max_scenarios=args.max_scenarios,
        test_set=args.test_set,
    )


if __name__ == "__main__":
    raise SystemExit(main())
