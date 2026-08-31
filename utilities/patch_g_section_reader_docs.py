"""Patch G-section markdown in 3_0_2 Retevie.ipynb for 6-node recall/rerank architecture."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"


def _md(s: str) -> list:
    if not s.endswith("\n"):
        s += "\n"
    return s.splitlines(keepends=True)


G_GLOSSARY = r"""## 术语表（读代码 / 评估前先看）

### 图数据库里两类核心对象

| 名称 | 代码字段 | 说明 |
|------|----------|------|
| **证据路径** | Neo4j 节点 `MetaPath` | 从论文 KG 预抽取的一条「小路径」+ 摘要 `metaPathText` |
| **路径编号** | `mp_id` | 每条证据路径的**唯一 ID** |

### 三个主题模块（≠ 候选路径池）

| 名称 | 代码字段 | 说明 |
|------|----------|------|
| **主题模块 r** | `target_subgraphs` | **MPU** / **EEM** / **EBM** |

### 路径粗细

| 名称 | 代码字段 | 说明 |
|------|----------|------|
| **路径层级 l** | `path_level` | **mid** 概览；**low** 细节。**首轮由 Route/LLM 选择**，不写死 mid |

### 多轮操作

| 名称 | 代码字段 | 说明 |
|------|----------|------|
| **操作类型 κ** | `kappa` | first_turn / drill_down / roll_up / sibling_nav / drill_across |

### 每轮检索名单

| 名称 | 代码字段 | 说明 |
|------|----------|------|
| **OLAP 先验池** | `gsub_mp_ids` | Node 3：Turn2+ 图算子展开的路径 ID；**空池不中断** |
| **广召回池 C_rec** | `recall_candidates` | Node 4：**50** 条 hybrid 结果 |
| **最佳短名单 P\*** | `retrieval_mp_ids` / `candidate_mp_ids` | Node 5 重排后 **10** 条 |
| **写答案** | Node 6 取 P* 拼 Context | 评估 Top-10 对应 P* |

### 重排公式（无结构分）

`s_final = α·s_search + η·s_pr + γ·s_olap`

- **s_olap**：mp_id ∈ G_sub → 1.0，否则 0.3；**首轮 γ=0**
- **s_pr**：`maxPageRank`（缺失则报错，不用 COALESCE 掩盖）
"""

G_CELL2 = """##### G Cell 2: 对话状态（多轮记忆）

| 字段 | 含义 |
|------|------|
| `target_subgraphs` | 主题模块 r |
| `path_level` | l = mid / low（首轮由 Route 选） |
| `kappa` | 多轮操作 κ |
| `candidate_mp_ids` | 上一轮 P*（10 条） |
| `gsub_mp_ids` | OLAP 软先验池 |
| `recall_candidates` | Node 4 广召回 50 条 |
| `retrieval_mp_ids` | Node 5 输出 P* |

`PIPELINE_VARIANT`: `full` | `no_hierarchy`（Turn≥2 强制首轮式 mid 重搜，消融用）
"""


def patch_glossary_only() -> None:
    """Insert/update glossary cell if present."""
    nb = json.loads(NB.read_text(encoding="utf-8"))
    for i, c in enumerate(nb["cells"]):
        s = "".join(c.get("source", []))
        if "术语表" in s and "OLAP 先验池" in s:
            c["source"] = _md(G_GLOSSARY)
            break
        if c.get("id") == "glossary_reader":
            c["source"] = _md(G_GLOSSARY)
            break
    else:
        for i, c in enumerate(nb["cells"]):
            if c.get("id") == "3df025bb":
                nb["cells"].insert(
                    i + 1,
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "id": "glossary_reader",
                        "source": _md(G_GLOSSARY),
                    },
                )
                break
    for c in nb["cells"]:
        if "G Cell 2: 对话状态" in "".join(c.get("source", [])):
            c["source"] = _md(G_CELL2)
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Glossary/cell2 patched in {NB}")


if __name__ == "__main__":
    patch_glossary_only()
