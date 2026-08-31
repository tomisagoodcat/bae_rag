"""Remove E/F sections from 3_0_2 Retevie.ipynb; add link to 1_2_1_2pagerankMetapath.ipynb."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "3_0_2 Retevie.ipynb"
PAGERANK_NB = ROOT / "1_2_1_2pagerankMetapath.ipynb"


def _find_g_section_index(cells: list) -> int:
    for i, c in enumerate(cells):
        if c.get("cell_type") != "markdown":
            continue
        src = "".join(c.get("source", [])).strip()
        if src.startswith("# G 子图agentic graph rag"):
            return i
    raise ValueError("G section not found")


def main() -> None:
    if not PAGERANK_NB.is_file():
        raise FileNotFoundError(f"Missing target notebook: {PAGERANK_NB}")

    nb = json.loads(RETRIEVAL.read_text(encoding="utf-8"))
    g_idx = _find_g_section_index(nb["cells"])

    link_cell = {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": [
            "# 3_0_2 对话检索（G 段及以后）\n",
            "\n",
            "**E / F 段已迁移**至专用 Notebook："
            "[`1_2_1_2pagerankMetapath.ipynb`](./1_2_1_2pagerankMetapath.ipynb)\n",
            "\n",
            "| 原章节 | 内容 | 新位置 |\n",
            "|--------|------|--------|\n",
            "| E | 分子图 GDS 投影与中心性写回 | `1_2_1_2pagerankMetapath` § E |\n",
            "| F1 | MetaPath 构建（subgraph 属性） | § F1 |\n",
            "| F2 | meta path query（LLM） | § F2 |\n",
            "| F3 | embedding / fulltext index | § F3 |\n",
            "| F4 | mid/low MetaPath 层级 | § F4（stub） |\n",
            "\n",
            "**本 Notebook 从 G 段开始**。运行 G 段前请确认：\n",
            "\n",
            "1. KG 已构建（[`1_2_0_2build_kg__neo4j.ipynb`](./1_2_0_2build_kg__neo4j.ipynb) + 模块4 子图标注）\n",
            "2. 已在 [`1_2_1_2pagerankMetapath.ipynb`](./1_2_1_2pagerankMetapath.ipynb) 完成 E → F3\n",
            "\n",
            "---\n",
        ],
    }

    remaining = nb["cells"][g_idx:]
    nb["cells"] = [link_cell] + remaining

    RETRIEVAL.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {RETRIEVAL}")
    print(f"  removed cells: 0..{g_idx - 1} ({g_idx} cells)")
    print(f"  remaining cells: {len(nb['cells'])} (1 link + {len(remaining)} from G)")


if __name__ == "__main__":
    main()
