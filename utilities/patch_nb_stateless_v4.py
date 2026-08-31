"""Patch 3_0_2 Retevie.ipynb: Stateless baseline + docs (Stateful unchanged)."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"

PART2_MD = """## Part 2 · 检索与重排（Recall + Rerank）

### 重排公式（Node 5 · Stateful）

$$s_{\\mathrm{final}} = \\alpha s_{\\mathrm{search}} + \\eta s_{\\mathrm{pr}} + \\gamma s_{\\mathrm{olap}}$$

| 符号 | 代码 | Stateful 默认 | 含义 |
|------|------|---------------|------|
| $s_{\\mathrm{search}}$ | hybrid `score` | 归一化 | 语义相关性 |
| $s_{\\mathrm{pr}}$ | `maxPageRank` | 归一化 | 图分析分；缺失 **raise** |
| $s_{\\mathrm{olap}}$ | G_sub 内/外 | 1.0 / 0.3 | OLAP 软先验 |
| α, η, γ | `RerankWeights` | 0.5, 0.35, 0.15 | Turn2+ 且 κ≠first_turn 时 γ=0.15 |

实现：`utilities/retrieval_rerank.py` → `rerank_metapath_candidates()`。

### Stateful vs Stateless（E5 OLAP 对照）

| 维度 | Stateful (`session_mode=stateful`) | Stateless (`session_mode=stateless`) |
|------|-----------------------------------|--------------------------------------|
| 轮间状态 | 保留 C、r、l、κ、`dialogue_turn` | 每轮 `make_initial_state`，**无记忆** |
| Route | 多轮 κ + LLM 选 **r 与 l** | **仅 LLM 选 r**；κ 恒 `first_turn`；`l=flat`（不用于过滤） |
| G_sub | Turn2+ 可展开 OLAP 池 | **恒空**（无 κ 导航） |
| Recall | hybrid，Cypher **按 l 过滤** mid/low | hybrid，**不按 l 过滤**（同模块 mid+low 一并检索） |
| Rerank | α·检索 + η·PR + γ·OLAP | **仅 η·PR**（α=0，γ=0） |
| 改写 / 答案 | 保留 | 保留（答案指标可比） |

**E5 读数**：Turn1 两臂 Δ≈0（sanity）；Turn2 看 core Δ，解释 Stateful 多轮 OLAP 导航收益。
"""

P2_MD_SNIPPET = """**`no_hierarchy`**（Stateful 消融）：Turn≥2 仅强制 `κ=first_turn`；**l 仍由 Route LLM 选择**（见 `pipeline_config.py`）。

**`session_mode`**：`stateful`（默认）| `stateless`（E5 扁平检索基线，见 Part 2 对照表）。
"""

E5_MD = """### E5 OLAP 对比（Stateful vs Stateless）

**成对运行**同一批 `dialogue_test_cases.json` scenario：

| 臂 | 机制 |
|----|------|
| **Stateful** | 6 节点 + 多轮记忆 + Turn2+ κ / G_sub / γ |
| **Stateless** | 每轮独立 state；Route **只选 r**；Recall **不区分 mid/low**；Rerank **仅 PageRank** |

**报告结构**

1. **Turn1 sanity**：Stateful − Stateless，Δ 应接近 0  
2. **Turn2 core Δ**：Precision@10、Recall@10、anchor_overlap、faithfulness 等  

CLI：`python utilities/run_retrieval_eval.py --olap-compare --skip-comprehensive`

结果追加写入 `output/eval_log.md`。
"""

STATE_CELL = r'''    dialogue_turn: int
    session_mode: str  # stateful | stateless（E5 对照）

    # G_sub 构造结果（Node 3）
'''

MAKE_STATE = r'''def make_initial_state(
    query: str, *, session_mode: str = "stateful"
) -> SimplifiedGraphRAGState:
    """初始化单轮 state。Stateless 评估每轮调用且 session_mode='stateless'。"""
    from utilities.session_config import normalize_session_mode

    mode = normalize_session_mode(session_mode)
    return {
        "original_query": query,
        "rewritten_query": "",
        "final_answer": "",
        "schema_info": "",
        "keywords_zh": [],
        "keywords_en": [],
        "keywords_both": [],
        "target_subgraphs": [],
        "path_level": "mid",
        "kappa": "first_turn",
        "candidate_mp_ids": [],
        "anchor_mp_ids": [],
        "entity_ids": [],
        "dialogue_turn": 0,
        "session_mode": mode,
        "gsub_mp_ids": [],
        "gsub_size": 0,
        "recall_candidates": [],
        "recall_count": 0,
        "retrieval_mp_ids": [],
        "retrieval_results": "",
        "generated_cypher": "",
        "cypher_valid": False,
        "retry_count": 0,
        "error_log": [],
    }
'''

PREP_IMPORT = r'''from utilities.retrieval_rerank import (
    RECALL_TOP_K,
    OUTPUT_TOP_K,
    rerank_metapath_candidates,
    rerank_page_rank_only,
)
from utilities.session_config import is_stateless, PATH_LEVEL_FLAT
from utilities.recall_flat import (
    build_cypher_for_subgraph_flat,
    HYBRID_SCAN_FLAT_PER_MODULE,
)
'''

ROUTE_NODE = r'''# ══════════════════════════════════════════════════════════════
# Node 2: Route(q, M_{t-1}) → (r, l, κ)
# ══════════════════════════════════════════════════════════════

import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))
from utilities.dialogue_routing import (
    route_dialogue,
    route_first_turn,
    route_modules_first_turn,
    route_modules_only,
)
from utilities.pipeline_config import get_pipeline_config
from utilities.session_config import is_stateless, PATH_LEVEL_FLAT, SESSION_STATELESS


def route_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 2: Route (r, l, κ)")
    print("=" * 60)

    query = state.get("rewritten_query") or state["original_query"]
    if not query or not query.strip():
        raise ValueError("Route 需要非空查询")

    print(f"查询: {query[:80]}")
    print(
        f"  M_{{t-1}}: r={state.get('target_subgraphs')} "
        f"l={state.get('path_level')} C={len(state.get('candidate_mp_ids') or [])} "
        f"turn={state.get('dialogue_turn', 0)} session={state.get('session_mode')}"
    )

    if is_stateless(state):
        modules = route_modules_only(llm, query)
        routed = {
            "kappa": "first_turn",
            "path_level": PATH_LEVEL_FLAT,
            "target_subgraphs": modules,
        }
        print(f"  → [stateless] κ=first_turn, l={PATH_LEVEL_FLAT}, r={modules}")
        return routed

    routed = route_dialogue(llm, query, state)
    cfg = get_pipeline_config()
    routed = cfg.apply_route_override(
        routed,
        dialogue_turn=int(state.get("dialogue_turn") or 0),
        llm=llm,
        query=query,
        route_modules_first_turn=route_modules_first_turn,
    )
    kappa = routed["kappa"]
    path_level = routed["path_level"]
    modules = routed["target_subgraphs"]

    print(f"  → κ={kappa}, l={path_level}, r={modules} [variant={cfg.variant}]")

    return {
        "target_subgraphs": modules,
        "path_level": path_level,
        "kappa": kappa,
    }


print("✅ Node 2 route_node 定义完成")
'''

GSUB_NODE = r'''    cfg = get_pipeline_config()
    if is_stateless(state):
        print("  G_sub = ∅ (stateless 基线，无 OLAP 池)")
        return {"gsub_mp_ids": [], "gsub_size": 0}

    if not cfg.gsub_enabled:
'''

RECALL_APPEND = r'''

def _search_single_subgraph_flat(query_text: str, subgraph: str) -> List[Dict]:
    retrieval_query = build_cypher_for_subgraph_flat(subgraph)
    retriever = HybridCypherRetriever(
        driver=neo4j_driver,
        vector_index_name=METAPATH_VECTOR_INDEX,
        fulltext_index_name=METAPATH_FULLTEXT_INDEX,
        embedder=neo4j_embed_model,
        retrieval_query=retrieval_query,
        result_formatter=metapath_result_formatter,
    )
    retriever_result = retriever.search(
        query_text=query_text, top_k=HYBRID_SCAN_FLAT_PER_MODULE
    )
    results = _safe_convert_results(retriever_result)
    for r in results:
        r["_subgraph"] = subgraph
    return results
'''

RECALL_LOOP_PATCH = r'''    if is_stateless(state):
        print(f"查询: {query_text[:80]}...")
        print(f"r={modules} | κ=first_turn | Recall=flat (无 l 过滤)")
        all_results: List[Dict] = []
        for sg in modules:
            print(f"\n  ── hybrid {sg} (flat) ──")
            batch = _search_single_subgraph_flat(query_text, sg)
            print(f"  返回: {len(batch)}")
            all_results.extend(batch)
        if not all_results:
            raise RuntimeError(f"Stateless Recall 无结果: r={modules}")
        all_results.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
        merged = _deduplicate_by_mp_id(all_results)[:RECALL_TOP_K]
        print(f"  C_rec: {len(merged)} 条 (cap={RECALL_TOP_K})")
        return {"recall_candidates": merged, "recall_count": len(merged)}

    path_level = state["path_level"]
'''

RERANK_PATCH = r'''    if is_stateless(state):
        print(f"  |C_rec|={len(pool)} | stateless rerank: η·PageRank only")
        ranked = rerank_page_rank_only(pool)
        top = ranked[:OUTPUT_TOP_K]
    else:
        kappa = state["kappa"]
        path_level = state["path_level"]
        gsub_ids = state.get("gsub_mp_ids") or []
        gamma = 0.0 if kappa == "first_turn" else None

        print(
            f"  |C_rec|={len(pool)} |G_sub|={len(gsub_ids)} | κ={kappa} | "
            f"γ={gamma if gamma is not None else 'default'}"
        )

        ranked = rerank_metapath_candidates(
            neo4j_embed_model,
            query_text,
            pool,
            gsub_mp_ids=gsub_ids,
            gamma=gamma if gamma is not None else 0.15,
        )
        top = ranked[:OUTPUT_TOP_K]

    p_star = [r["mp_id"] for r in top if r.get("mp_id")]
'''


def _src(cell: dict) -> str:
    return "".join(cell.get("source", []))


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] != "code" and cell["cell_type"] != "markdown":
            continue
        s = _src(cell)
        if cell["cell_type"] == "markdown" and "Part 2 · 检索与重排" in s:
            cell["source"] = (PART2_MD + "\n").splitlines(keepends=True)
        if cell["cell_type"] == "markdown" and "### E5 OLAP 对比" in s:
            cell["source"] = (E5_MD + "\n").splitlines(keepends=True)
        if cell["cell_type"] == "markdown" and "**`no_hierarchy`**" in s or (
            "### P2 对话状态" in s and "no_hierarchy" in s
        ):
            if "### P2 对话状态" in s:
                if "session_mode" not in s:
                    cell["source"] = (s.rstrip() + "\n\n" + P2_MD_SNIPPET + "\n").splitlines(
                        keepends=True
                    )
        if cell["cell_type"] == "code" and "class SimplifiedGraphRAGState" in s:
            text = s
            if "session_mode" not in text:
                text = text.replace(
                    "    dialogue_turn: int\n",
                    STATE_CELL,
                )
            if "def make_initial_state(query: str)" in text:
                text = text.replace(
                    'def make_initial_state(query: str) -> SimplifiedGraphRAGState:\n    """首轮初始化；后续轮次应复用上轮 state 并更新 original_query。"""\n    return {',
                    MAKE_STATE.split("return {", 1)[0] + "return {",
                )
                # full replace make_initial_state block
                import re

                text = re.sub(
                    r"def make_initial_state\([^)]*\)[^:]*:.*?(?=\n\nprint\(\"✅ Simplified)",
                    MAKE_STATE + "\n\n",
                    text,
                    flags=re.DOTALL,
                )
            cell["source"] = text.splitlines(keepends=True)
        if cell["cell_type"] == "code" and "G_sub 算子 + Rerank 导入" in s:
            if "rerank_page_rank_only" not in s:
                cell["source"] = s.replace(
                    "    rerank_metapath_candidates,\n)",
                    PREP_IMPORT.split("from utilities.retrieval_rerank")[1],
                )
                # simpler: append imports after rerank import block
                extra = (
                    "from utilities.retrieval_rerank import (\n"
                    "    RECALL_TOP_K,\n"
                    "    OUTPUT_TOP_K,\n"
                    "    rerank_metapath_candidates,\n"
                    "    rerank_page_rank_only,\n"
                    ")\n"
                    "from utilities.session_config import is_stateless, PATH_LEVEL_FLAT\n"
                    "from utilities.recall_flat import (\n"
                    "    build_cypher_for_subgraph_flat,\n"
                    "    HYBRID_SCAN_FLAT_PER_MODULE,\n"
                    ")\n"
                )
                cell["source"] = extra.splitlines(keepends=True) + [
                    l
                    for l in s.splitlines(keepends=True)
                    if "from utilities.retrieval_rerank" not in l
                    and "RECALL_TOP_K" not in l
                    and "rerank_metapath" not in l
                    and "OUTPUT_TOP_K" not in l
                ]
        if cell["cell_type"] == "code" and "def route_node" in s:
            cell["source"] = ROUTE_NODE.splitlines(keepends=True)
        if cell["cell_type"] == "code" and "def gsub_builder_node" in s:
            if "is_stateless" not in s:
                cell["source"] = s.replace(
                    "    cfg = get_pipeline_config()\n    if not cfg.gsub_enabled:",
                    '    from utilities.session_config import is_stateless\n\n'
                    + GSUB_NODE
                    + "    if not cfg.gsub_enabled:",
                ).splitlines(keepends=True)
        if cell["cell_type"] == "code" and "def recall_node" in s:
            text = s
            if "_search_single_subgraph_flat" not in text:
                text = text.replace(
                    'print("✅ Node 4 recall_node 定义完成")',
                    RECALL_APPEND.strip()
                    + '\n\nprint("✅ Node 4 recall_node 定义完成")',
                )
            if "is_stateless(state)" not in text:
                text = text.replace(
                    "from utilities.pipeline_config import get_pipeline_config",
                    "from utilities.pipeline_config import get_pipeline_config\n"
                    "from utilities.session_config import is_stateless",
                )
                text = text.replace(
                    "    path_level = state[\"path_level\"]\n    kappa = state[\"kappa\"]\n"
                    "    cfg = get_pipeline_config()\n"
                    "    if not cfg.multi_dim_enabled and kappa != \"first_turn\":\n"
                    "        raise RuntimeError(f\"variant={cfg.variant} 仅支持 first_turn 式 Recall\")\n\n"
                    "    print(f\"查询: {query_text[:80]}...\")\n"
                    "    print(f\"r={modules} | κ={kappa} | l={path_level}\")\n\n"
                    "    all_results: List[Dict] = []\n"
                    "    for sg in modules:\n"
                    "        print(f\"\\n  ── hybrid {sg} (l={path_level}) ──\")\n"
                    "        batch = _search_single_subgraph(query_text, sg, path_level)\n",
                    RECALL_LOOP_PATCH,
                )
            cell["source"] = text.splitlines(keepends=True)
        if cell["cell_type"] == "code" and "def rerank_node" in s:
            text = s
            if "rerank_page_rank_only" not in text:
                text = text.replace(
                    "from typing import Dict, List, Any",
                    "from typing import Dict, List, Any\n"
                    "from utilities.session_config import is_stateless",
                )
                old = """    kappa = state["kappa"]
    path_level = state["path_level"]
    gsub_ids = state.get("gsub_mp_ids") or []
    gamma = 0.0 if kappa == "first_turn" else None

    print(f"  |C_rec|={len(pool)} |G_sub|={len(gsub_ids)} | κ={kappa} | γ={gamma if gamma is not None else 'default'}")

    ranked = rerank_metapath_candidates(
        neo4j_embed_model,
        query_text,
        pool,
        gsub_mp_ids=gsub_ids,
        gamma=gamma if gamma is not None else 0.15,
    )
    top = ranked[:OUTPUT_TOP_K]

    p_star = [r["mp_id"] for r in top if r.get("mp_id")]"""
                text = text.replace(old, RERANK_PATCH)
                # fix return to use path_level from state for stateless too
                text = text.replace(
                    '        "path_level": path_level,\n        "kappa": kappa,',
                    '        "path_level": state["path_level"],\n        "kappa": state["kappa"],',
                )
            cell["source"] = text.splitlines(keepends=True)

    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB}")


if __name__ == "__main__":
    patch()
