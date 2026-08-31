"""Remove duplicate Prep Cypher markdown before N4."""
from __future__ import annotations

import json
import re
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"
RUN_EVAL = Path(__file__).resolve().parents[1] / "utilities" / "run_retrieval_eval.py"


def _src(c: dict) -> str:
    return "".join(c.get("source", []))


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]
    out = []
    seen_n4 = False
    seen_prep_md = False
    for c in cells:
        s = _src(c)
        if c["cell_type"] == "markdown" and "### N4 广召回" in s:
            seen_n4 = True
            out.append(c)
            continue
        if (
            c["cell_type"] == "markdown"
            and "### Prep Recall 用 Cypher" in s
            and not seen_n4
        ):
            continue  # drop prep md that appears before N4
        if c["cell_type"] == "markdown" and "### Prep Recall 用 Cypher" in s:
            if seen_prep_md:
                continue
            seen_prep_md = True
        out.append(c)

    nb["cells"] = out
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    # refresh indices
    from fix_nb_restore_v3 import find_pipeline_indices, find_eval_indices, patch_run_retrieval_eval

    patch_run_retrieval_eval(
        find_pipeline_indices(out), *find_eval_indices(out)
    )
    print(f"✅ dedupe → {len(out)} cells")


if __name__ == "__main__":
    main()
