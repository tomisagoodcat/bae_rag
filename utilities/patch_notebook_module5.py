"""Rename chunk dedup to module 5; normalize module 4 level-1 headings."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "1_2_0_2build_kg__neo4j.ipynb"


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

    nb["cells"][14]["source"] = [
        "# 模块4 子图属性标注\n",
        "\n",
        "为 Neo4j 实体节点写入 `subgraph` / `subgraphs` 属性，依据 "
        "[`output/subgraph_mapping.json`](../output/subgraph_mapping.json)。\n",
        "\n",
        "| 属性 | 规则 |\n",
        "|------|------|\n",
        "| `subgraphs` | `List[str]`，取值 `MPU` / `EBM` / `EEM`，**始终写入** |\n",
        "| `subgraph` | 仅当节点类型只属于 **一个** 子图时写入标量；跨子图节点 **不写入** |\n",
        "\n",
        "**本 Cell 可独立运行**（不依赖模块3 的 torch/LLM 导入）。"
        "KG 已存在时直接 `run_subgraph_assignment()`。\n",
        "\n",
        "若通过模块3 `build_knowledge_graph` 自动执行步骤 6.5，"
        "须在同 Kernel **先运行本 Cell** 以注册函数。\n",
        "\n",
        "**严格校验**（失败即 `SubgraphMappingError`）：mapping 与 entity.json 完全一致；"
        "所有 ontology 实体节点必须有 `subgraphs`。\n",
    ]

    src15 = "".join(nb["cells"][15]["source"])
    src15 = src15.replace(
        "# ==================== 模块4: 子图属性标注（可独立运行） ====================\n",
        "# 模块4 子图属性标注（可独立运行）\n",
    )
    nb["cells"][15]["source"] = [src15]

    src17 = "".join(nb["cells"][17]["source"])
    src17 = src17.replace("# 模块4：chunk去重", "# 模块5 chunk去重")
    nb["cells"][17]["source"] = [src17]

    src18 = "".join(nb["cells"][18]["source"])
    if not src18.lstrip().startswith("# 模块5"):
        src18 = "# 模块5 chunk去重（可独立运行）\n" + src18.lstrip()
    nb["cells"][18]["source"] = [src18]

    NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB_PATH}")
    for idx in (14, 15, 17, 18):
        first = "".join(nb["cells"][idx]["source"]).split("\n")[0]
        print(f"  Cell {idx}: {first}")


if __name__ == "__main__":
    main()
