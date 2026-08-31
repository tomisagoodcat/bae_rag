"""Patch 3_0_2 Retevie.ipynb: Stateful dual Route + Recall flat (Search Wide, Rank Narrow)."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"

PIPELINE_TABLE_OLD = "| `gsub_builder` | §5.1 | 构造 OLAP 软先验池 `gsub_mp_ids` |"
PIPELINE_TABLE_NEW = """| `route_r` | §5.1 | Recall 前：LLM 选顶层模块 **r** |
| `route_olap` | §5.1 | Recall 后：$(q_{n-1}, q_n)$ → **κ, l**（不改动 r） |
| `gsub_builder` | §5.1 | 由 κ 展开 **G_sub**（仅 Rerank；空池 Turn≥2 **raise**） |"""

PART2_MD = r"""## Part 2 · 检索与重排（Recall + Rerank）

### 设计原则（Stateful · Search Wide, Rank Narrow）

| 阶段 | 范围 |
|------|------|
| **Recall** | 模块图全集（mid+low flat），**不**按 κ / G_sub / l 过滤 |
| **Route_olap + G_sub** | 结构导航，仅影响 **Rerank** |
| **Rerank** | $s_{\mathrm{final}} = \alpha s_{\mathrm{search}} + \eta s_{\mathrm{pr}} + \gamma s_{\mathrm{olap}}$ |

### 重排公式（Node 5 · Stateful）

$$s_{\mathrm{final}} = \alpha s_{\mathrm{search}} + \eta s_{\mathrm{pr}} + \gamma s_{\mathrm{olap}}$$

| 符号 | 代码 | Stateful 默认 | 含义 |
|------|------|---------------|------|
| $s_{\mathrm{search}}$ | hybrid `score` | 归一化 | 语义相关性 |
| $s_{\mathrm{pr}}$ | `maxPageRank` | 归一化 | 图分析分；缺失 **raise** |
| $s_{\mathrm{olap}}$ | G_sub 内/外 | **1.0 / 0.0** | 结构对齐（二元，无 0.3 软兜底） |
| α, η, γ | `RerankWeights` | 0.5, 0.35, 0.15 | Turn1: γ=0；Turn2+ κ≠first_turn: γ=0.15 且 **G_sub 非空** |

实现：`utilities/retrieval_rerank.py` → `rerank_metapath_candidates()`。

### Stateful vs Stateless（E5 OLAP 对照）

| 维度 | Stateful (`session_mode=stateful`) | Stateless (`session_mode=stateless`) |
|------|-----------------------------------|--------------------------------------|
| 轮间状态 | 保留 C、r、l、κ、`dialogue_turn`、`previous_query` | 每轮 `make_initial_state`，**无记忆** |
| Route | **Route_r**（r）→ Recall → **Route_olap**（κ,l）→ G_sub | **仅 r**；κ=`first_turn` |
| G_sub | Turn2+ κ 展开；**空池 raise** | **恒空** |
| Recall | **模块级 flat**（与 Stateless 同宽） | **flat** |
| Rerank | α·检索 + η·PR + γ·OLAP | **仅 η·PR**（α=0，γ=0） |
| 改写 / 答案 | 保留 | 保留 |

**E5 读数**：Turn1 两臂 Recall 机制趋同；Turn2+ 看 OLAP 是否通过 **Rerank** 提升 Precision 且不牺牲 Recall。
"""

STATE_FIELDS = r"""    dialogue_turn: int
    session_mode: str  # stateful | stateless（E5 对照）
    previous_query: str  # q_{n-1}，Route_olap 必填（Turn≥2）

    # G_sub（Route_olap 之后；仅 Rerank 偏置，不限制 Recall）
    gsub_mp_ids: list[str]
    gsub_size: int
"""

MAKE_STATE = r'''def make_initial_state(
    query: str, *, session_mode: str = "stateful"
) -> SimplifiedGraphRAGState:
    """初始化单轮 state。Stateless 评估每轮调用且 session_mode='stateless'。"""
    from utilities.session_config import normalize_session_mode

    mode = normalize_session_mode(session_mode)
    return {
        "original_query": query,
        "rewritten_query": "",
        "previous_query": "",
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

ROUTE_R_NODE = r'''# ══════════════════════════════════════════════════════════════
# Node 2a: Route_r — Recall 前仅选顶层模块 r
# ══════════════════════════════════════════════════════════════

from utilities.dialogue_routing import route_modules_recall, route_modules_only
from utilities.session_config import is_stateless, PATH_LEVEL_FLAT


def route_r_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 2a: Route_r (modules only)")
    print("=" * 60)

    query = state.get("rewritten_query") or state["original_query"]
    if not query or not query.strip():
        raise ValueError("Route_r 需要非空查询")

    print(f"查询: {query[:80]}...")
    print(f"  turn={state.get('dialogue_turn', 0)} session={state.get('session_mode')}")

    if is_stateless(state):
        modules = route_modules_only(llm, query)
        print(f"  → [stateless] r={modules} (κ/l 在 Route 节点占位)")
        return {
            "target_subgraphs": modules,
            "kappa": "first_turn",
            "path_level": PATH_LEVEL_FLAT,
        }

    modules = route_modules_recall(llm, query)
    print(f"  → r={modules} (Recall 将 module-flat 检索，不按 l 过滤)")
    return {"target_subgraphs": modules}


print("✅ Node 2a route_r_node 定义完成")
'''

ROUTE_OLAP_NODE = r'''# ══════════════════════════════════════════════════════════════
# Node 2b: Route_olap — Recall 后 (q_{n-1}, q_n) → κ, l
# ══════════════════════════════════════════════════════════════

from utilities.dialogue_routing import route_olap_dialogue
from utilities.pipeline_config import get_pipeline_config
from utilities.session_config import is_stateless, PATH_LEVEL_FLAT


def route_olap_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 2b: Route_olap (κ, l)")
    print("=" * 60)

    if is_stateless(state):
        print("  [stateless] 跳过 Route_olap")
        return {}

    query = state.get("rewritten_query") or state["original_query"]
    if not query.strip():
        raise ValueError("Route_olap 需要非空查询")

    prev_q = state.get("previous_query") or ""
    turn = int(state.get("dialogue_turn") or 0)
    print(f"  q_n: {query[:60]}...")
    if turn > 0:
        print(f"  q_{{n-1}}: {prev_q[:60]}...")

    routed = route_olap_dialogue(llm, query, prev_q, state)
    cfg = get_pipeline_config()
    routed = cfg.apply_olap_route_override(
        routed,
        dialogue_turn=turn,
        llm=llm,
        query=query,
    )
    print(f"  → κ={routed['kappa']}, l={routed['path_level']} (r 保持 {state.get('target_subgraphs')})")
    return {
        "kappa": routed["kappa"],
        "path_level": routed["path_level"],
    }


print("✅ Node 2b route_olap_node 定义完成")
'''

GSUB_NODE = r'''# ══════════════════════════════════════════════════════════════
# Node 3: G_sub Builder（Route_olap 之后；空池 Turn≥2 raise）
# ══════════════════════════════════════════════════════════════

from utilities.pipeline_config import get_pipeline_config
from utilities.session_config import is_stateless


def gsub_builder_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 3: G_sub Builder")
    print("=" * 60)

    kappa = state["kappa"]
    path_level = state["path_level"]
    modules = state["target_subgraphs"]
    candidates = state.get("candidate_mp_ids") or []

    print(f"  κ={kappa}, l={path_level}, r={modules}")
    print(f"  |C_{{t-1}}|={len(candidates)}")

    cfg = get_pipeline_config()
    if is_stateless(state):
        print("  G_sub = ∅ (stateless)")
        return {"gsub_mp_ids": [], "gsub_size": 0}

    if not cfg.gsub_enabled:
        if kappa != "first_turn":
            raise RuntimeError(
                f"variant={cfg.variant} 禁用 G_sub，但 κ={kappa}"
            )
        print("  G_sub = ∅ (variant 禁用 / first_turn)")
        return {"gsub_mp_ids": [], "gsub_size": 0}

    if kappa == "first_turn":
        print("  G_sub = ∅ (首轮；Rerank γ=0)")
        return {"gsub_mp_ids": [], "gsub_size": 0}

    gsub_ids = build_gsub_mp_ids(
        driver=neo4j_driver,
        kappa=kappa,
        candidate_mp_ids=candidates,
        active_modules=modules,
        path_level=path_level,
    )

    if not gsub_ids:
        raise RuntimeError(
            f"G_sub 为空: κ={kappa}, l={path_level}, |C|={len(candidates)} — "
            "禁止静默降级；请检查图算子或 Route_olap 标注"
        )

    print(f"  G_sub = {len(gsub_ids)} 条 MetaPath（Rerank OLAP 偏置）")
    return {"gsub_mp_ids": gsub_ids, "gsub_size": len(gsub_ids)}


print("✅ Node 3 gsub_builder_node 定义完成")
'''

RECALL_PATCH_OLD = """    path_level = state[\"path_level\"]
    kappa = state[\"kappa\"]
    cfg = get_pipeline_config()
    if not cfg.multi_dim_enabled and kappa != \"first_turn\":
        raise RuntimeError(f\"variant={cfg.variant} 仅支持 first_turn 式 Recall\")

    print(f\"查询: {query_text[:80]}...\")
    print(f\"r={modules} | κ={kappa} | l={path_level}\")

    all_results: List[Dict] = []
    for sg in modules:
        print(f\"\\n  ── hybrid {sg} (l={path_level}) ──\")
        batch = _search_single_subgraph(query_text, sg, path_level)
        print(f\"  返回: {len(batch)}\")
        all_results.extend(batch)

    if not all_results:
        raise RuntimeError(
            f\"Recall 无结果: r={modules}, l={path_level}, κ={kappa}\"
        )
"""

RECALL_PATCH_NEW = """    cfg = get_pipeline_config()
    if not cfg.multi_dim_enabled:
        pass  # Recall 已统一 flat；κ/l 仅用于 Route_olap / G_sub / Rerank

    print(f\"查询: {query_text[:80]}...\")
    print(f\"r={modules} | Stateful Recall=flat (module-wide, no l filter)\")

    all_results: List[Dict] = []
    for sg in modules:
        print(f\"\\n  ── hybrid {sg} (flat) ──\")
        batch = _search_single_subgraph_flat(query_text, sg)
        print(f\"  返回: {len(batch)}\")
        all_results.extend(batch)

    if not all_results:
        raise RuntimeError(f\"Stateful Recall 无结果: r={modules}\")
"""

GRAPH_BUILD = r'''def build_graph_rag_pipeline():
    workflow = StateGraph(SimplifiedGraphRAGState)

    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("route_r", route_r_node)
    workflow.add_node("recall", recall_node)
    workflow.add_node("route_olap", route_olap_node)
    workflow.add_node("gsub_builder", gsub_builder_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("answer_generator", answer_generator_node)

    workflow.set_entry_point("query_rewriter")
    workflow.add_edge("query_rewriter", "route_r")
    workflow.add_edge("route_r", "recall")
    workflow.add_edge("recall", "route_olap")
    workflow.add_edge("route_olap", "gsub_builder")
    workflow.add_edge("gsub_builder", "rerank")
    workflow.add_edge("rerank", "answer_generator")
    workflow.add_edge("answer_generator", END)
    return workflow.compile()


def invoke_dialogue_turn(state: SimplifiedGraphRAGState) -> SimplifiedGraphRAGState:
    """单轮 invoke；多轮时传入上轮 state 并更新 original_query / previous_query。"""
    return graph_app.invoke(state)


def test_multiturn_dialogue():
    print("\n" + "=" * 80)
    print("多轮对话测试 (Route_r → Recall → Route_olap → G_sub → Rerank)")
    print("=" * 80)

    turns = [
        ("大米中汞污染的整体情况", "first_turn"),
        ("展开具体检测步骤细节", "drill_down / low"),
        ("回到概览层面", "roll_up / mid"),
    ]

    state = make_initial_state(turns[0][0])
    prev_query = turns[0][0]
    for i, (query, label) in enumerate(turns, 1):
        print(f"\n── Turn {i}: {label} ──")
        print(f"Q: {query}")
        if i > 1:
            state["previous_query"] = prev_query
            state["original_query"] = query
            state["rewritten_query"] = ""
        state = invoke_dialogue_turn(state)
        prev_query = query
        print(
            f"  κ={state.get('kappa')} l={state.get('path_level')} "
            f"r={state.get('target_subgraphs')} |G_sub|={len(state.get('gsub_mp_ids') or [])} "
            f"|P*|={len(state.get('candidate_mp_ids') or [])}"
        )

    print("\n✅ 多轮测试完成")


graph_app = build_graph_rag_pipeline()

print("✅ Pipeline: Rewriter → Route_r → Recall(flat) → Route_olap → G_sub → Rerank → Answer")

try:
    from IPython.display import Image, display
    display(Image(graph_app.get_graph().draw_mermaid_png()))
except Exception as exc:
    print(f"流程图渲染失败: {exc}")
'''


def _src(cell) -> str:
    return "".join(cell.get("source", []))


def _set_src(cell, text: str) -> None:
    cell["source"] = [line + "\n" for line in text.splitlines()]
    if text.endswith("\n"):
        pass
    elif cell["source"]:
        cell["source"][-1] = cell["source"][-1].rstrip("\n") + "\n"


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    n = 0
    for cell in nb["cells"]:
        src = _src(cell)
        if cell["cell_type"] == "markdown" and "改写(N1) → 路由(N2)" in src:
            _set_src(
                cell,
                "\n"
                "```\n"
                "改写 → Route_r → Recall(flat) → Route_olap → G_sub → Rerank → 答案\n"
                "```\n\n"
                "| LangGraph 节点 | 论文章节 | 中文职责 |\n"
                "|----------------|----------|----------|\n"
                "| `query_rewriter` | — | 问题改写成英文检索短语 |\n"
                + PIPELINE_TABLE_NEW
                + "\n"
                "| `recall` | §5.2 | 模块级 Hybrid flat Top-50（不按 l/G_sub 过滤） |\n"
                "| `rerank` | §5.2 | α·检索 + η·PR + γ·OLAP → Top-10 |\n"
                "| `answer_generator` | §5.4 | 路径级 Context + 答案 + 写回状态 |\n\n"
                "### 准备层 / 评估层（非 LangGraph 节点）\n\n"
                "| 编号 | 内容 |\n"
                "|------|------|\n"
                "| **P0–P3** | 依赖、状态、Neo4j/LLM 连接 |\n"
                "| **Prep** | 图算子 import、Recall 用 Cypher 模板 |\n"
                "| **E1–E5** | 指标说明、评估脚本、OLAP 对比 |\n",
            )
            n += 1
        if cell["cell_type"] == "markdown" and "| `route` |" in src and "Route" in src:
            src = src.replace(
                "| `route` | §5.1 | 路由：κ + 顶层模块 r + 路径层级 l |",
                PIPELINE_TABLE_NEW,
            )
            _set_src(cell, src)
            n += 1
        if cell["cell_type"] == "markdown" and "## Part 2 · 检索与重排" in src:
            _set_src(cell, PART2_MD)
            n += 1
        if "class SimplifiedGraphRAGState" in src and "dialogue_turn: int" in src:
            start = src.index("    dialogue_turn: int")
            end = src.index("    # 检索 / 答案")
            src = src[:start] + STATE_FIELDS + src[end:]
            _set_src(cell, src)
            n += 1
        if "def make_initial_state(" in src and "session_mode" in src:
            start = src.index("def make_initial_state(")
            end = src.index('print("✅ SimplifiedGraphRAGState')
            _set_src(cell, src[:start] + MAKE_STATE + "\n\n" + src[end:])
            n += 1
        if "def route_node(state:" in src and "route_dialogue" in src:
            _set_src(cell, ROUTE_R_NODE)
            n += 1
        if "def gsub_builder_node(state:" in src:
            _set_src(cell, GSUB_NODE)
            n += 1
        if RECALL_PATCH_OLD.strip() in src:
            src = src.replace(RECALL_PATCH_OLD, RECALL_PATCH_NEW)
            _set_src(cell, src)
            n += 1
        if "def build_graph_rag_pipeline():" in src:
            start = src.index("def build_graph_rag_pipeline():")
            _set_src(cell, src[:start] + GRAPH_BUILD)
            n += 1

    # Insert route_olap cell after recall if missing
    has_olap = any("def route_olap_node" in _src(c) for c in nb["cells"])
    if not has_olap:
        recall_idx = next(
            i for i, c in enumerate(nb["cells"]) if "def recall_node" in _src(c)
        )
        md_cell = {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### N2b Route_olap（Recall 之后）\n",
                "\n",
                "**输入**：`previous_query` + 当前 query + `candidate_mp_ids`。\n",
                "**输出**：`kappa`, `path_level`（**不**改 `target_subgraphs`）。\n",
            ],
        }
        code_cell = {
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in ROUTE_OLAP_NODE.splitlines()],
        }
        nb["cells"].insert(recall_idx + 1, md_cell)
        nb["cells"].insert(recall_idx + 2, code_cell)
        n += 2

    # Update gsub md if present
    for cell in nb["cells"]:
        src = _src(cell)
        if cell["cell_type"] == "markdown" and "md_n3_gsub" in cell.get("id", ""):
            _set_src(
                cell,
                "### N3 G_sub（Route_olap 之后）\n\n"
                "**在整体中的位置**：Recall **之后**；由 κ 展开 `gsub_mp_ids`，**仅**供 Rerank。\n\n"
                "**严格模式**：Turn≥2 且 κ≠first_turn 时 G_sub 为空 → **RuntimeError**（不 warn 继续）。\n",
            )
            n += 1
        if cell["cell_type"] == "markdown" and "md_n2_route" in str(cell.get("id", "")):
            _set_src(
                cell,
                "### N2a Route_r（Recall 之前）\n\n"
                "仅 LLM 选择 **r**（MPU/EEM/EBM）。Recall 在模块内 **flat** 检索。\n",
            )
            n += 1

    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB} ({n} updates)")


if __name__ == "__main__":
    patch()
