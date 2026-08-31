"""Execute notebook module 4 and run subgraph assignment."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "1_2_0_2build_kg__neo4j.ipynb"


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    mod4_idx = next(
        i for i, c in enumerate(nb["cells"]) if c.get("id") == "mod4-subgraph-code"
    )
    cell4 = "".join(nb["cells"][mod4_idx]["source"])
    g: dict = {"__name__": "__main__", "__file__": str(NB)}
    exec(compile(cell4, "<module4>", "exec"), g)
    g["run_subgraph_assignment"](schema_base_path=str(ROOT / "output"))


if __name__ == "__main__":
    main()
