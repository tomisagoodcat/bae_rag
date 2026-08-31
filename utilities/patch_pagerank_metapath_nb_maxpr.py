"""Patch 1_2_1_2pagerankMetapath.ipynb: unified maxPageRank documentation."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "1_2_1_2pagerankMetapath.ipynb"

MAXPR_UNIFIED = """**maxPageRank（统一规则，low / mid 相同）**

```
maxPageRank(mp) = max( e.{sg}_pagerank
                     for (mp)-[:metaPathRelation]->(e) )
```

- `{sg}` 由 `mp.subgraph` 决定：`MPU`→`mpu_pagerank`，`EEM`→`eem_pagerank`，`EBM`→`ebm_pagerank`
- 只统计 **metaPathRelation 直接相连** 的基础节点（不沿 Plan/Part 等间接扩展）
- 每个相连节点必须有 E 段写回的 pagerank（NULL → raise，不用 0 掩盖）
- **low** 通常 |E|=2（source/target）；**mid** 通常 |E|=1（Plan/容器锚点）
"""

F4_MD = f"""## F4 构建 mid MetaPath 与层级边

**判定规则（构建时确定）**

| path_level | 构建入口 | 含义 |
|------------|----------|------|
| low | F1 SUBGRAPH_RELATIONS | 原子 2-hop 路径 |
| mid | F4 Plan/容器聚合 | 每 Plan 或 SupportGraph/ScienceEvidence 实例 1 条 |

{MAXPR_UNIFIED}

**前置**：必须先完成 **E 段** GDS 写回。

**层级边**：hasDetailPath（mid→low）、detailOf（low→mid）

**链接**：同子图内 mid 锚点与 low 实体 **共享 FROM_CHUNK**（当前 KG 中 Step/part 节点 ID 与 F1 low 无交集）

**执行**：F1 完成后运行下方 cell；验收失败将 raise。
"""

F4_1_MD = f"""## F4.1 刷新 maxPageRank（E 段之后 / 已有 MetaPath 时）

当 **E 段在 F 之后补跑**，或需要校验全库 `maxPageRank` 时，单独执行本 cell。

{MAXPR_UNIFIED}

- 输出：更新条数、按 `path_level` / `subgraph` 的均值与 `zero` 计数
"""

SCHEMA_LINE = (
    "  maxPageRank:   Float,     // max(e.{sg}_pagerank) for (mp)-[:metaPathRelation]->(e)\n"
)

F4_CODE = """from utilities.metapath_path_level import (
    build_mid_metapaths_for_plans,
    build_mid_metapaths_for_containers,
    link_mid_to_low,
    refresh_and_verify_metapath_max_pagerank,
    verify_metapath_path_level,
)

print("=" * 60)
print("F4: mid MetaPath + hasDetailPath / detailOf")
print("=" * 60)

mid_counters = {"MPU": 1, "EBM": 1, "EEM": 1}
mid_counters = build_mid_metapaths_for_plans(neo4j_driver, mid_counters)
mid_counters = build_mid_metapaths_for_containers(neo4j_driver, mid_counters)
link_stats = link_mid_to_low(neo4j_driver)
verify_metapath_path_level(neo4j_driver, require_mid=True)

print("\\n" + "=" * 60)
print("F4.1: maxPageRank 全量刷新与统计（统一规则）")
print("=" * 60)
pr_report = refresh_and_verify_metapath_max_pagerank(neo4j_driver, pagerank_prop=PAGERANK_PROP)
pr_report
"""

F4_1_CODE = """from utilities.metapath_path_level import refresh_and_verify_metapath_max_pagerank

pr_report = refresh_and_verify_metapath_max_pagerank(neo4j_driver, pagerank_prop=PAGERANK_PROP)
pr_report
"""


def _md(s: str) -> list:
    if not s.endswith("\n"):
        s += "\n"
    return s.splitlines(keepends=True)


def _replace_maxpr_docs(src: str) -> str:
    """Normalize legacy maxPageRank markdown fragments."""
    replacements = [
        (
            "  maxPageRank:   Float,     // low 取路径两端实体较大 pagerank；mid 默认 0\n",
            SCHEMA_LINE,
        ),
        (
            "  maxPageRank:   Float,     // low: max(端点 {sg}_pagerank); mid: 锚点 {sg}_pagerank（E 段写回）\n",
            SCHEMA_LINE,
        ),
        ("mid 默认 0", "统一 metaPathRelation 邻居 max"),
        ("mid: 锚点 {sg}_pagerank", "metaPathRelation 邻居 {sg}_pagerank 的 max"),
    ]
    for old, new in replacements:
        src = src.replace(old, new)
    return src


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    for i, c in enumerate(cells):
        cid = c.get("id")
        src = "".join(c.get("source", []))

        if cid == "ce68ee6f":
            cells[i]["source"] = _md(F4_MD)
        elif cid == "f4run001":
            cells[i]["source"] = _md(F4_CODE)
        elif cid == "f41_maxpr_md":
            cells[i]["source"] = _md(F4_1_MD)
        elif cid == "f41_maxpr_code":
            cells[i]["source"] = _md(F4_1_CODE)
        elif "maxPageRank" in src and c.get("cell_type") == "markdown":
            cells[i]["source"] = _md(_replace_maxpr_docs(src))

    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB} ({len(cells)} cells)")


if __name__ == "__main__":
    patch()
