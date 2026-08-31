"""Update 1_2_1_2pagerankMetapath.ipynb for path_level + F4."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "1_2_1_2pagerankMetapath.ipynb"


def _join(src) -> str:
    if isinstance(src, list):
        return "".join(src)
    return src


def _set(nb, idx: int, text: str, cell_type: str = "code") -> None:
    nb["cells"][idx]["source"] = text
    nb["cells"][idx]["cell_type"] = cell_type
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None


def _find(nb, needle: str) -> int:
    for i, c in enumerate(nb["cells"]):
        if needle in _join(c.get("source", [])):
            return i
    raise KeyError(needle)


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))

    # Cell 0: intro
    intro = _join(nb["cells"][0]["source"])
    intro = intro.replace(
        "**执行顺序**：E → F1 手写关系清单 → F1 验收 → F1 构建 MetaPath → F2 → F3 → F4",
        "**执行顺序**：E → F1 清单/验收 → **F1 low 构建** → **F4 mid + 层级边** → **验收** → F2 → F3",
    )
    _set(nb, 0, intro, "markdown")

    f12 = _find(nb, "## F1.2 定义构建metaPath函数")
    f12_code = '''import sys
from pathlib import Path

_ROOT = Path.cwd()
if not (_ROOT / "utilities").is_dir():
    raise FileNotFoundError(f"utilities 目录不存在: {_ROOT / 'utilities'}")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utilities.metapath_path_level import build_metapath_for_relation

print("✅ F1.2: build_metapath_for_relation（path_level=low）已加载")
'''
    _set(nb, f12 + 1, f12_code)

    f13 = _find(nb, "## F1.3 构建metapath主程序")
    f13_code = '''from utilities.metapath_path_level import build_all_metapaths

def run_f1_build(driver):
    """F1: 全量 low MetaPath；任一条模板异常则中止。"""
    return build_all_metapaths(driver, SUBGRAPH_RELATIONS, PAGERANK_PROP)


print("✅ F1.3: run_f1_build 已定义")
print("   执行: summary = run_f1_build(neo4j_driver)")
'''
    _set(nb, f13 + 1, f13_code)

    # Execution cell after F1.3 - find build_all_metapaths call or same cell
    # User had summary in same cell - split: f13+1 is def, need exec cell
    # Check if next cell is verify
    exec_code = '''# F1 全量构建 low MetaPath（需先跑 Neo4j 连接 + SUBGRAPH_RELATIONS + F1.2/F1.3）
summary = run_f1_build(neo4j_driver)
summary
'''
    verify_idx = _find(nb, "def verify_metapath_creation")
    # Insert exec before verify if verify exists at verify_idx
    if _join(nb["cells"][verify_idx]["source"]).strip().startswith("def verify"):
        nb["cells"].insert(verify_idx, {
            "cell_type": "code",
            "execution_count": None,
            "id": "f1exec001",
            "metadata": {},
            "outputs": [],
            "source": exec_code,
        })
        verify_idx += 1

    verify_code = '''from utilities.metapath_path_level import verify_metapath_path_level

def verify_metapath_creation(driver, *, require_mid: bool = False):
    """包装严格验收；F1 后 require_mid=False，F4 后 require_mid=True。"""
    return verify_metapath_path_level(driver, require_mid=require_mid)


print("✅ verify_metapath_creation / verify_metapath_path_level 已加载")
print("   F1 后: verify_metapath_creation(neo4j_driver, require_mid=False)")
print("   F4 后: verify_metapath_creation(neo4j_driver, require_mid=True)")
'''
    _set(nb, verify_idx, verify_code)

    f4_md = _find(nb, "### F1.1  构建 middle level")
    f4_md_text = """## F4 构建 mid MetaPath 与层级边

**判定规则（构建时确定，非检索推断）**

| path_level | 构建入口 | 含义 |
|------------|----------|------|
| `low` | F1 `build_metapath_for_relation` + `SUBGRAPH_RELATIONS` | 原子 2-hop `(entity)-[rel]->(entity)` |
| `mid` | F4 Plan / 容器聚合 | 每个 Plan 或 SupportGraph/ScienceEvidence 实例 1 条 |

**层级边（论文 κ：drill_down / roll_up）**

- `(:MetaPath {path_level:'mid'})-[:hasDetailPath]->(:MetaPath {path_level:'low'})`
- `(:MetaPath {path_level:'low'})-[:detailOf]->(:MetaPath {path_level:'mid'})`

**链接规则（`hasDetailPath` / `detailOf`）**

- 同子图 `subgraph` 内，mid 锚点实体与 low 路径实体 **共享 `FROM_CHUNK` 的 Chunk** 时连边
- 原因：当前 KG 中 F1 low 上的 Step/part **节点 ID** 与 `isStepOfPlan`/`whu_hasPart` 结构中的节点 **无交集**（诊断 overlap=0），故采用 Chunk 共现而非纯拓扑

**执行**：先完成 F1 low 构建，再运行下方 code cell。验收失败将 `raise`，不静默跳过。
"""
    _set(nb, f4_md, f4_md_text, "markdown")

    f4_code = '''from utilities.metapath_path_level import (
    build_mid_metapaths_for_plans,
    build_mid_metapaths_for_containers,
    link_mid_to_low,
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
link_stats
'''
    # Insert or replace cell after F4 md
    next_idx = f4_md + 1
    if next_idx < len(nb["cells"]) and nb["cells"][next_idx]["cell_type"] == "code":
        if "build_mid_metapaths" in _join(nb["cells"][next_idx]["source"]):
            _set(nb, next_idx, f4_code)
        else:
            nb["cells"].insert(next_idx, {
                "cell_type": "code",
                "execution_count": None,
                "id": "f4run001",
                "metadata": {},
                "outputs": [],
                "source": f4_code,
            })
    else:
        nb["cells"].insert(next_idx, {
            "cell_type": "code",
            "execution_count": None,
            "id": "f4run001",
            "metadata": {},
            "outputs": [],
            "source": f4_code,
        })

    # F2: strict LLM - no fallback
    for i, c in enumerate(nb["cells"]):
        src = _join(c.get("source", []))
        if "def generate_metapath_query" in src and "使用 metaPathText 作为 fallback" in src:
            src = src.replace(
                '    print(f"    ⚠️  全部重试失败，使用 metaPathText 作为 fallback")\n'
                "    return metapath_text\n",
                '    raise RuntimeError(f"LLM metaPathQuery 生成失败，已重试 {retry + 1} 次")\n',
            )
            _set(nb, i, src)
        if "def batch_generate_metapath_query" in src:
            src = src.replace(
                '            is_fallback = (metapath_query == metapath_text)\n'
                "            \n"
                "            if is_fallback:\n"
                '                stats["fallback"] += 1\n'
                "            else:\n"
                '                stats["success"] += 1\n',
                '            stats["success"] += 1\n',
            )
            src = src.replace(
                '                if is_fallback:\n'
                '                    print(f"    (使用 fallback)")\n',
                "",
            )
            src = src.replace('    stats = {"total": total, "success": 0, "fallback": 0}\n',
                              '    stats = {"total": total, "success": 0, "failed": 0}\n')
            src = src.replace('        return {"total": 0, "success": 0, "fallback": 0}\n',
                              '        return {"total": 0, "success": 0, "failed": 0}\n')
            src = src.replace('    print(f"  Fallback: {stats[\'fallback\']}")\n',
                              '    print(f"  失败: {stats[\'failed\']}")\n')
            if "raise RuntimeError" not in src and "return stats" in src:
                src = src.replace(
                    "    print(f\"  平均: {elapsed/stats['total']:.2f}s/条\")\n"
                    "    \n"
                    "    return stats\n",
                    "    print(f\"  平均: {elapsed/stats['total']:.2f}s/条\")\n"
                    "    if stats['failed']:\n"
                    "        raise RuntimeError(f\"metaPathQuery 生成失败 {stats['failed']} 条\")\n"
                    "    return stats\n",
                )
            _set(nb, i, src)

    # F2 markdown
    f2_md = _find(nb, "## F2 基于meta path")
    _set(
        nb,
        f2_md,
        """## F2 基于 metaPathText 生成 metaPathQuery（LLM）

- 处理 **全部** `:MetaPath`（含 `path_level` 为 `low` 与 `mid`）
- LLM 失败 **直接 raise**，不使用 metaPathText 兜底
- **前置**：F4 完成且验收通过
""",
        "markdown",
    )

    f3_md = _find(nb, "## F3 基于meta path query")
    _set(
        nb,
        f3_md,
        """## F3 embedding + 向量/全文索引

- 对已有 `metaPathQuery` 的 MetaPath 写 `embedding`（BCE 768 维）
- 重建 `metapath_embedding_index`（向量）与 `metapath_fulltext_index`（metaPathText）
- **前置**：F2 完成
""",
        "markdown",
    )

    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Updated {NB}")


if __name__ == "__main__":
    main()
