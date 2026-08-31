"""Create or refresh 1_2_1_2pagerankMetapath.ipynb (E + F sections).

After E/F migration, cells are taken from the existing pagerank notebook;
legacy fallback reads cells[0:G] from 3_0_2 Retevie.ipynb if still present.
"""
from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "3_0_2 Retevie.ipynb"
DST = ROOT / "1_2_1_2pagerankMetapath.ipynb"


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _clear_cell_for_fresh_run(cell: dict) -> dict:
    c = deepcopy(cell)
    if c.get("cell_type") == "code":
        c["execution_count"] = None
        c["outputs"] = []
    c["id"] = _new_id()
    return c


def _find_g_section_index(cells: list) -> int:
    for i, c in enumerate(cells):
        if c.get("cell_type") != "markdown":
            continue
        src = "".join(c.get("source", [])).strip()
        if src.startswith("# G 子图agentic graph rag"):
            return i
    raise ValueError("G section not found in source notebook")


def _load_ef_cells() -> tuple[list, str]:
    if RETRIEVAL.is_file():
        nb = json.loads(RETRIEVAL.read_text(encoding="utf-8"))
        try:
            g_idx = _find_g_section_index(nb["cells"])
            if g_idx > 0:
                return nb["cells"][:g_idx], f"{RETRIEVAL.name} cells[0:{g_idx}]"
        except ValueError:
            pass

    if not DST.is_file():
        raise FileNotFoundError(
            "E/F not in retrieval notebook and pagerank notebook missing; "
            "run migration first or restore 3_0_2 Retevie.ipynb"
        )
    nb = json.loads(DST.read_text(encoding="utf-8"))
    cells = nb["cells"]
    start = 1 if cells and cells[0].get("cell_type") == "markdown" else 0
    return cells[start:], f"{DST.name} cells[{start}:] (refresh)"


def main() -> None:
    ef_cells, source_desc = _load_ef_cells()
    metadata_src = json.loads(
        (RETRIEVAL if RETRIEVAL.is_file() else DST).read_text(encoding="utf-8")
    )
    metadata = metadata_src.get("metadata", {})

    intro = {
        "cell_type": "markdown",
        "id": _new_id(),
        "metadata": {},
        "source": [
            "# 1_2_1 PageRank 与 MetaPath 构建\n",
            "\n",
            "本 Notebook 由 [`3_0_2 Retevie.ipynb`](./3_0_2%20Retevie.ipynb) 拆分迁移：\n",
            "\n",
            "- **E** 分子图图分析并赋值（GDS 投影 + 中心性写回）\n",
            "- **F** MetaPath 构建（F1–F4）\n",
            "\n",
            "**执行顺序**：E → F1 → F2 → F3 → F4（F4 为 stub，待实现）\n",
            "\n",
            "**前置**：Neo4j KG 已由 [`1_2_0_2build_kg__neo4j.ipynb`](./1_2_0_2build_kg__neo4j.ipynb) 构建，"
            "且建议已运行模块4 `subgraph/subgraphs` 标注。\n",
            "\n",
            "**下游**：完成后在 `3_0_2 Retevie.ipynb` G 段进行对话检索。\n",
        ],
    }

    migrated = [intro] + [_clear_cell_for_fresh_run(c) for c in ef_cells]

    new_nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": metadata.get(
                "kernelspec",
                {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
            ),
            "language_info": metadata.get(
                "language_info",
                {"name": "python", "version": "3.11.0"},
            ),
        },
        "cells": migrated,
    }

    DST.write_text(json.dumps(new_nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {DST}")
    print(f"  cells: {len(migrated)} (1 intro + {len(ef_cells)} from source)")
    print(f"  source: {source_desc}")


if __name__ == "__main__":
    main()
