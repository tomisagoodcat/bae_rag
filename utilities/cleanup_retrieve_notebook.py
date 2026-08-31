"""Cleanup and fix 3_0_2 Retevie.ipynb after §5.1 patch."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parent.parent / "3_0_2 Retevie.ipynb"


def _src(cell) -> str:
    return "".join(cell.get("source", []))


def cleanup() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    drop_if = (
        "Cell 13: 测试 Node 5",
        "node1-node2-node4-node5 pipeline",
        "_CYPHER_CACHE.get",
    )
    cleaned = [c for c in cells if not any(x in _src(c) for x in drop_if)]

    for c in cleaned:
        s = _src(c)
        if "def route_node" in s and "from typing import Dict" not in s:
            c["source"] = s.replace(
                "import sys\nfrom pathlib import Path",
                "import sys\nfrom pathlib import Path\nfrom typing import Dict",
            ).splitlines(keepends=True)

        if "def _convert_single_item" in s and "RetrieverResultItem" not in s:
            old = '''def _convert_single_item(item: Any) -> Dict:
    if hasattr(item, "data"):
        return dict(item.data())
    if isinstance(item, dict):
        return item
    if hasattr(item, "content") and isinstance(item.content, dict):
        return item.content
    raise TypeError(f"无法转换检索结果项: {type(item)}")'''
            new = '''def _convert_single_item(item: Any) -> Dict:
    if isinstance(item, dict):
        return item
    if hasattr(item, "metadata") and isinstance(item.metadata, dict) and item.metadata:
        return dict(item.metadata)
    if hasattr(item, "content"):
        if isinstance(item.content, dict):
            return item.content
        if isinstance(item.content, str):
            raise TypeError(f"检索项 content 为 str 而非字段 dict: {item.content[:80]}")
    if hasattr(item, "data"):
        return dict(item.data())
    raise TypeError(f"无法转换检索结果项: {type(item)}")'''
            c["source"] = s.replace(old, new).splitlines(keepends=True)

        if "graph_app = build_graph_rag_pipeline()" in s and "draw_mermaid_png" not in s:
            c["source"] = (
                s
                + """

try:
    from IPython.display import Image, display
    display(Image(graph_app.get_graph().draw_mermaid_png()))
except Exception as exc:
    print(f"流程图渲染失败: {exc}")
"""
            ).splitlines(keepends=True)

        if "以下为简化后的流程" in s or s.startswith("# 流程（论文"):
            c["source"] = (
                """# 流程（论文 §5.1 / §5.4）

```
Start → Node1 QueryRewriter
     → Node2 Route(r,l,κ)
     → Node3 G_sub Builder
     → Node4 Retriever → P*
     → Node5 Context(p)+Answer → 写回 M_t
```

- **r**：顶层语义模块 {EBM,EEM,MPU}（非 path_level）
- **l**：MetaPath.path_level {mid,low}
- **κ**：first_turn / drill_down / roll_up / sibling_nav / drill_across
"""
            ).splitlines(keepends=True)

    # Fix G Cell 5 placeholder
    for c in cleaned:
        if _src(c).startswith("##### G Cell 5: Node 4"):
            c["source"] = [
                "##### G Cell 5: 检索子系统概览\n\n",
                "Node 4 在 **G_sub** 约束下检索并排序候选路径 P*：\n",
                "- `first_turn`：顶层模块 r 内 hybrid 检索（path_level=l）\n",
                "- 其他 κ：仅在 Node3 输出的 `gsub_mp_ids` 内 embedding rerank\n",
            ]

    nb["cells"] = cleaned
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Cleanup done ({len(cleaned)} cells)")


if __name__ == "__main__":
    cleanup()
