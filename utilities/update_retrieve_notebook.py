"""Patch 3_0_2 Retevie.ipynb for paper §5.1 / §5.4 dialogue routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


NB_PATH = Path(__file__).resolve().parent.parent / "3_0_2 Retevie.ipynb"


def _md(lines: str) -> Dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": lines.splitlines(keepends=True)}


def _code(lines: str) -> Dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines.splitlines(keepends=True),
    }


STATE_MD = """##### G Cell 2: 对话状态 M_t（论文 §5.1）

定义 LangGraph 状态 `SimplifiedGraphRAGState` 与 `make_initial_state()`。

**概念层级（正交）**：
| 维度 | 字段 | 取值 |
|------|------|------|
| 顶层语义模块 | `target_subgraphs` → r | EBM / EEM / MPU |
| 路径抽象层级 | `path_level` → l | mid / low |
| 候选路径集 | `candidate_mp_ids` → C | 上一轮 P* |
| 结构转移 | `kappa` → κ | first_turn / drill_down / roll_up / sibling_nav / drill_across |

**多轮用法**：第二轮起保留 `candidate_mp_ids`、`path_level`、`target_subgraphs`，仅更新 `original_query`。
"""

STATE_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 2: State 定义（论文 §5.1 对话状态 M_t）
# ══════════════════════════════════════════════════════════════

from typing import TypedDict, List, Annotated
import operator

VALID_KAPPA = frozenset({
    "first_turn", "drill_down", "roll_up", "sibling_nav", "drill_across",
})
VALID_PATH_LEVELS = frozenset({"mid", "low"})
TOP_LEVEL_MODULES = frozenset({"MPU", "EEM", "EBM"})


class SimplifiedGraphRAGState(TypedDict):
    """
    对话状态 M_t = ⟨r_t, C_t, l_t⟩ + κ + 检索/答案字段。

    r_t  : target_subgraphs   — 顶层语义模块 {EBM,EEM,MPU}（非 path_level）
    C_t  : candidate_mp_ids   — 上一轮排序后候选 MetaPath 集合 P*
    l_t  : path_level         — 路径抽象层级 mid | low
    κ    : kappa                — 结构转移类型
    """

    original_query: str
    rewritten_query: str
    final_answer: str

    schema_info: str
    keywords_zh: List[str]
    keywords_en: List[str]
    keywords_both: List[str]

    # r — 顶层语义模块（实现字段名 target_subgraphs / subgraph）
    target_subgraphs: List[str]

    # M_t 核心
    path_level: str
    kappa: str
    candidate_mp_ids: List[str]   # C_{t-1} / C_t = P*
    anchor_mp_ids: List[str]      # 与 C 同步，兼容旧字段
    entity_ids: List[str]         # E_t = ⋃ V_p
    dialogue_turn: int

    # G_sub 构造结果（Node 3）
    gsub_mp_ids: List[str]
    gsub_size: int

    # 检索 / 答案
    retrieval_mp_ids: List[str]   # 本轮 P*
    retrieval_results: str

    generated_cypher: str
    cypher_valid: bool
    retry_count: Annotated[int, operator.add]
    error_log: List[str]


def make_initial_state(query: str) -> SimplifiedGraphRAGState:
    """首轮初始化；后续轮次应复用上轮 state 并更新 original_query。"""
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
        "gsub_mp_ids": [],
        "gsub_size": 0,
        "retrieval_mp_ids": [],
        "retrieval_results": "",
        "generated_cypher": "",
        "cypher_valid": False,
        "retry_count": 0,
        "error_log": [],
    }


print("✅ SimplifiedGraphRAGState（§5.1 M_t）")
print("   r=target_subgraphs (顶层 EBM/EEM/MPU)")
print("   l=path_level (mid/low), C=candidate_mp_ids")
'''

ROUTE_MD = """##### Node 2: Route(q, M_{t-1}) → (r, l, κ)

统一路由节点，替代原「仅选子图 + 固定 first_turn」逻辑。

- **首轮**（`dialogue_turn=0` 或无 C）：LLM 选顶层模块 r，`κ=first_turn`, `l=mid`
- **后续轮**：LLM 判定 κ 与 l；drill/roll 保持 r；sibling/drill_across 切换顶层模块视角
- **无兜底**：LLM 解析失败直接 `raise`
"""

ROUTE_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 2: Route(q, M_{t-1}) → (r, l, κ)
# ══════════════════════════════════════════════════════════════

import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))
from utilities.dialogue_routing import route_dialogue


def route_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 2: Route (r, l, κ)")
    print("=" * 60)

    query = state.get("rewritten_query") or state["original_query"]
    if not query or not query.strip():
        raise ValueError("Route 需要非空查询")

    print(f"查询: {query[:80]}")
    print(f"  M_{{t-1}}: r={state.get('target_subgraphs')} "
          f"l={state.get('path_level')} C={len(state.get('candidate_mp_ids') or [])} "
          f"turn={state.get('dialogue_turn', 0)}")

    routed = route_dialogue(llm, query, state)
    kappa = routed["kappa"]
    path_level = routed["path_level"]
    modules = routed["target_subgraphs"]

    print(f"  → κ={kappa}, l={path_level}, r={modules}")

    return {
        "target_subgraphs": modules,
        "path_level": path_level,
        "kappa": kappa,
    }


print("✅ Node 2 route_node 定义完成")
'''

OPS_MD = """##### G Cell 4: G_sub 算子与 sibling 边类型

从 `utilities/dialogue_routing.py` 导入论文 §5.1 算子：

| 算子 | κ | 说明 |
|------|---|------|
| `N_l(p)` | drill_down / roll_up | hasDetailPath / detailOf |
| `WF(p)` | sibling_nav | 经 MetaPath 关联实体的逻辑邻接边（非仅 whu_fellow） |
| `DA(p)` | drill_across | mid 上卷 → WF → low 下钻 |
| `build_gsub_mp_ids` | 全部 | 按 κ 构造 G_sub |
"""

OPS_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 4: G_sub 算子导入
# ══════════════════════════════════════════════════════════════

from utilities.dialogue_routing import (
    SIBLING_EDGE_TYPES,
    TOP_LEVEL_MODULES,
    VALID_KAPPA,
    VALID_PATH_LEVELS,
    N_l,
    WF,
    DA,
    build_gsub_mp_ids,
    fetch_metapath_rows,
    rerank_by_embedding,
)

print("✅ G_sub 算子已导入")
print(f"   sibling 边类型 ({len(SIBLING_EDGE_TYPES)}): {SIBLING_EDGE_TYPES[:4]}...")
print(f"   顶层模块: {sorted(TOP_LEVEL_MODULES)}")
'''

GSUB_MD = """##### Node 3: G_sub Builder

根据 Route 输出的 κ、l、r 与 C_{t-1} 构造语义子图 G_sub：

- `first_turn`：G_sub 为空（Node 4 在 r 模块内全库 hybrid 检索 + path_level 过滤）
- 其他 κ：Neo4j 算子展开 mp_id 列表写入 `gsub_mp_ids`；空集则 `raise`
"""

GSUB_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 3: G_sub Builder
# ══════════════════════════════════════════════════════════════


def gsub_builder_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 3: G_sub Builder")
    print("=" * 60)

    kappa = state["kappa"]
    path_level = state["path_level"]
    modules = state["target_subgraphs"]
    candidates = state.get("candidate_mp_ids") or []

    print(f"  κ={kappa}, l={path_level}, r={modules}")
    print(f"  |C|={len(candidates)}")

    gsub_ids = build_gsub_mp_ids(
        driver=neo4j_driver,
        kappa=kappa,
        candidate_mp_ids=candidates,
        active_modules=modules,
        path_level=path_level,
    )

    if kappa == "first_turn":
        print("  G_sub = ⋃ G_r (首轮：全模块 hybrid，不物化 mp_id 列表)")
    else:
        print(f"  G_sub = {len(gsub_ids)} 条 MetaPath")
        if not gsub_ids:
            raise RuntimeError(f"G_sub 为空: κ={kappa}")

    return {"gsub_mp_ids": gsub_ids, "gsub_size": len(gsub_ids)}


print("✅ Node 3 gsub_builder_node 定义完成")
'''

CYPHER_MD = """##### G Cell 6: MetaPath 检索 Cypher（path_level + G_sub）

- `_build_cypher_for_subgraph(sg, path_level)`：first_turn hybrid 检索
- `_build_cypher_for_gsub()`：κ≠first_turn 时在 G_sub 内取数
"""

CYPHER_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 6: MetaPath 检索 Cypher
# ══════════════════════════════════════════════════════════════


def _build_cypher_for_subgraph(subgraph: str, path_level: str = "mid") -> str:
    if path_level not in VALID_PATH_LEVELS:
        raise ValueError(f"无效 path_level: {path_level}")
    if subgraph not in TOP_LEVEL_MODULES:
        raise ValueError(f"无效顶层模块: {subgraph}")
    return f"""
WITH node
WHERE node.subgraph = '{subgraph}' AND node.path_level = '{path_level}'
OPTIONAL MATCH (node)-[r:metaPathRelation]->(entity)-[:FROM_CHUNK]->(chunk:Chunk)
WITH node, r.position AS position, chunk
ORDER BY position ASC
WITH node, COLLECT(chunk.text) AS chunk_texts_ordered
WITH node,
     reduce(acc = [], x IN chunk_texts_ordered |
            CASE WHEN x IN acc OR x IS NULL OR size(x) <= 10
                 THEN acc ELSE acc + x END) AS chunk_texts
RETURN
    node.metaPathText AS metapath_text,
    chunk_texts AS chunk_texts,
    COALESCE(node.maxPageRank, 0.0) AS graph_score,
    node.mp_id AS mp_id,
    node.path_level AS path_level,
    node.subgraph AS subgraph,
    node.path_type AS path_type,
    node.metaPathQuery AS meta_path_query
"""


def _build_cypher_for_gsub() -> str:
    return """
WITH node
WHERE node.mp_id IN $gsub_mp_ids
OPTIONAL MATCH (node)-[r:metaPathRelation]->(entity)-[:FROM_CHUNK]->(chunk:Chunk)
WITH node, r.position AS position, chunk
ORDER BY position ASC
WITH node, COLLECT(chunk.text) AS chunk_texts_ordered
WITH node,
     reduce(acc = [], x IN chunk_texts_ordered |
            CASE WHEN x IN acc OR x IS NULL OR size(x) <= 10
                 THEN acc ELSE acc + x END) AS chunk_texts
RETURN
    node.metaPathText AS metapath_text,
    chunk_texts AS chunk_texts,
    COALESCE(node.maxPageRank, 0.0) AS graph_score,
    node.mp_id AS mp_id,
    node.path_level AS path_level,
    node.subgraph AS subgraph,
    node.path_type AS path_type,
    node.metaPathQuery AS meta_path_query
"""


SUBGRAPH_CYPHER = {
    sg: _build_cypher_for_subgraph(sg, "mid") for sg in ["MPU", "EEM", "EBM"]
}

print("✅ MetaPath Cypher 定义完成")
'''

RETRIEVER_MD = """##### Node 4: Hybrid Retriever（G_sub 约束）

| κ | 检索策略 |
|---|----------|
| first_turn | 各 r 模块 hybrid 向量+全文，filter path_level=l |
| 其他 | 仅在 `gsub_mp_ids` 内 embedding rerank，不全库检索 |

输出 P* → `retrieval_mp_ids` / `candidate_mp_ids`（供下轮 C）
"""

RETRIEVER_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 4: Hybrid Retriever（G_sub + §5.2 候选排序）
# ══════════════════════════════════════════════════════════════

from neo4j_graphrag.retrievers import HybridCypherRetriever
import json
import re
from typing import Dict, List, Any

METAPATH_VECTOR_INDEX = "metapath_embedding_index"
METAPATH_FULLTEXT_INDEX = "metapath_fulltext_index"
TOP_K = 20


def sanitize_for_lucene(text: str) -> str:
    return re.sub(r'[+\-&|!(){}\[\]^"~*?:\\/—–]', ' ', text).strip()


def _search_single_subgraph(
    query_text: str, subgraph: str, path_level: str = "mid"
) -> List[Dict]:
    retrieval_query = _build_cypher_for_subgraph(subgraph, path_level)
    retriever = HybridCypherRetriever(
        driver=neo4j_driver,
        vector_index_name=METAPATH_VECTOR_INDEX,
        fulltext_index_name=METAPATH_FULLTEXT_INDEX,
        embedder=neo4j_embed_model,
        retrieval_query=retrieval_query,
    )
    retriever_result = retriever.search(query_text=query_text, top_k=TOP_K)
    results = _safe_convert_results(retriever_result)
    for r in results:
        r["_subgraph"] = subgraph
    return results


def _retriever_search_gsub(query_text: str, gsub_mp_ids: List[str]) -> List[Dict]:
    rows = fetch_metapath_rows(neo4j_driver, gsub_mp_ids)
    ranked = rerank_by_embedding(neo4j_embed_model, query_text, rows)
    for r in ranked:
        r["_subgraph"] = r.get("subgraph", "MPU")
    return ranked[:TOP_K]


def hybrid_retriever_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 4: HybridRetriever (G_sub)")
    print("=" * 60)

    query_text = sanitize_for_lucene(state["rewritten_query"])
    if not query_text:
        raise ValueError("检索查询为空")

    modules = state["target_subgraphs"]
    if not modules:
        raise ValueError("target_subgraphs 为空")

    kappa = state["kappa"]
    path_level = state["path_level"]
    gsub_ids = state.get("gsub_mp_ids") or []

    print(f"查询: {query_text[:80]}...")
    print(f"r={modules} | κ={kappa} | l={path_level} | |G_sub|={len(gsub_ids)}")

    if kappa == "first_turn":
        all_results: List[Dict] = []
        for sg in modules:
            print(f"\n  ── hybrid {sg} (l={path_level}) ──")
            batch = _search_single_subgraph(query_text, sg, path_level)
            print(f"  返回: {len(batch)}")
            all_results.extend(batch)
    else:
        if not gsub_ids:
            raise ValueError(f"κ={kappa} 但 gsub_mp_ids 为空")
        print(f"  G_sub 内 rerank ({len(gsub_ids)} ids)")
        all_results = _retriever_search_gsub(query_text, gsub_ids)

    if not all_results:
        raise RuntimeError(
            f"检索无结果: κ={kappa}, r={modules}, l={path_level}, |G_sub|={len(gsub_ids)}"
        )

    pr_values = [float(r.get("graph_score") or 0.0) for r in all_results]
    pr_min, pr_max = min(pr_values), max(pr_values)
    pr_range = (pr_max - pr_min) or 1.0
    for r in all_results:
        if "combined_score" not in r:
            pr_norm = ((float(r.get("graph_score") or 0.0)) - pr_min) / pr_range
            vec_norm = float(r.get("score") or 0.0)
            r["combined_score"] = 0.8 * vec_norm + 0.2 * pr_norm

    all_results.sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)
    merged = _deduplicate_by_mp_id(all_results)[:TOP_K]

    p_star = [r["mp_id"] for r in merged if r.get("mp_id")]
    if not p_star:
        raise RuntimeError("排序后 P* 为空")

    formatted = _format_retrieval_results(merged)

    return {
        "retrieval_results": json.dumps(formatted, ensure_ascii=False, indent=2),
        "retrieval_mp_ids": p_star,
        "candidate_mp_ids": p_star,
        "anchor_mp_ids": p_star[:5],
        "path_level": path_level,
        "kappa": kappa,
    }


def _deduplicate_by_mp_id(results: List[Dict]) -> List[Dict]:
    seen: set = set()
    merged: List[Dict] = []
    for item in results:
        mp_id = item.get("mp_id")
        if mp_id is None:
            merged.append(item)
        elif mp_id not in seen:
            seen.add(mp_id)
            merged.append(item)
    return merged


def _safe_convert_results(retriever_result: Any) -> List[Dict]:
    items = (
        retriever_result.items
        if hasattr(retriever_result, "items")
        else (
            retriever_result
            if isinstance(retriever_result, (list, tuple))
            else [retriever_result]
        )
    )
    results = []
    for item in items:
        converted = _convert_single_item(item)
        if converted:
            results.append(converted)
    return results


def _convert_single_item(item: Any) -> Dict:
    if hasattr(item, "data"):
        return dict(item.data())
    if isinstance(item, dict):
        return item
    if hasattr(item, "content") and isinstance(item.content, dict):
        return item.content
    raise TypeError(f"无法转换检索结果项: {type(item)}")


def _format_retrieval_results(results: List[Dict]) -> Dict:
    return {
        "status": "success",
        "count": len(results),
        "results": [
            {
                "rank": i + 1,
                "mp_id": item.get("mp_id"),
                "content": item,
                "preview": _generate_preview(item),
                "subgraph": item.get("_subgraph") or item.get("subgraph", "unknown"),
            }
            for i, item in enumerate(results)
        ],
    }


def _generate_preview(item: Dict) -> str:
    mp_text = (item.get("metapath_text") or "").strip()
    chunk_texts = item.get("chunk_texts") or []
    if mp_text:
        ctx = ""
        if isinstance(chunk_texts, list):
            parts = [str(c).strip()[:150] for c in chunk_texts[:2] if c]
            ctx = " | ".join(parts)
        return mp_text[:250] + (f"\n[Context] {ctx}" if ctx else "")
    raise ValueError(f"preview 缺少 metapath_text: mp_id={item.get('mp_id')}")


print("✅ Node 4 HybridRetriever (G_sub) 定义完成")
'''

ANSWER_MD = """##### Node 5: Path-grounded Evidence Context + 答案生成（§5.4）

对 P* 中每条路径构建 `Context(p) = ⟨T_struct, OrderedChunks⟩`，生成答案后写回：

`r_t, C_t=P*, l_t, E_t, dialogue_turn+1`
"""

ANSWER_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 5: §5.4 Evidence Context + Answer + 状态写回
# ══════════════════════════════════════════════════════════════

from typing import Dict, List
import json

from utilities.dialogue_routing import (
    build_context_for_paths,
    extract_entity_ids,
)


def answer_generator_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 5: Answer Generator (§5.4)")
    print("=" * 60)

    original_query = state["original_query"]
    modules = state.get("target_subgraphs") or []
    p_star = state.get("retrieval_mp_ids") or state.get("candidate_mp_ids") or []

    if not p_star:
        raise ValueError("answer_generator: 缺少 retrieval_mp_ids (P*)")

    print(f"原问题: {original_query}")
    print(f"r={modules} | |P*|={len(p_star)}")

    context = build_context_for_paths(neo4j_driver, p_star, max_paths=10)
    print(f"  Context(q) 长度: {len(context)} 字符")

    prompt = _build_answer_prompt(
        question=original_query,
        context=context,
        subgraphs=modules,
    )
    answer = _generate_answer_with_llm(prompt)
    entity_ids = extract_entity_ids(neo4j_driver, p_star)

    print(f"  |E_t|={len(entity_ids)}  ✅ 答案生成完成")

    return {
        "final_answer": answer,
        "target_subgraphs": modules,
        "candidate_mp_ids": p_star,
        "anchor_mp_ids": p_star[:5],
        "retrieval_mp_ids": p_star,
        "entity_ids": entity_ids,
        "path_level": state["path_level"],
        "kappa": state["kappa"],
        "dialogue_turn": int(state.get("dialogue_turn") or 0) + 1,
    }


def _build_answer_prompt(question: str, context: str, subgraphs: List[str]) -> str:
    hints = {
        "MPU": "论证与证据（声明、数据集、结论）",
        "EEM": "实验与方法（步骤、仪器、质控）",
        "EBM": "样本与材料（采集、环境、浓度）",
    }
    hint = "；".join(hints[s] for s in subgraphs if s in hints) or "综合各模块"
    return f"""你是科研助手。基于路径级证据 Context(q) 用中文回答。

用户问题：{question}

Context(q) 每条含 [T_struct]（实体-关系骨架）与 [OrderedChunks]（按路径顺序的原文）：
{context}

要求：
1. 重点维度：{hint}
2. 关键陈述标注 [编号]，对应 Context 中 [N]
3. 不足处明确说明缺失信息
4. 2-3 段，专业准确

答案："""


def _generate_answer_with_llm(prompt: str) -> str:
    response = llm.invoke(prompt)
    answer = response.content.strip() if hasattr(response, "content") else str(response).strip()
    if len(answer) < 10:
        raise RuntimeError("LLM 返回过短答案")
    return answer


print("✅ Node 5 (§5.4 + 状态写回) 定义完成")
'''

PIPELINE_MD = """##### G Cell 8: LangGraph Pipeline（Node1→2→3→4→5）

```
QueryRewriter → Route → G_sub → Retriever → Answer
```

含多轮对话测试：首轮 overview → drill_down → roll_up
"""

PIPELINE_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 8: Pipeline + 多轮测试
# ══════════════════════════════════════════════════════════════

from langgraph.graph import StateGraph, END
import json
import time


def build_graph_rag_pipeline():
    workflow = StateGraph(SimplifiedGraphRAGState)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("route", route_node)
    workflow.add_node("gsub_builder", gsub_builder_node)
    workflow.add_node("hybrid_retriever", hybrid_retriever_node)
    workflow.add_node("answer_generator", answer_generator_node)

    workflow.set_entry_point("query_rewriter")
    workflow.add_edge("query_rewriter", "route")
    workflow.add_edge("route", "gsub_builder")
    workflow.add_edge("gsub_builder", "hybrid_retriever")
    workflow.add_edge("hybrid_retriever", "answer_generator")
    workflow.add_edge("answer_generator", END)
    return workflow.compile()


def invoke_dialogue_turn(state: SimplifiedGraphRAGState) -> SimplifiedGraphRAGState:
    """单轮 invoke；多轮时传入上轮 state 并更新 original_query。"""
    return graph_app.invoke(state)


def test_multiturn_dialogue():
    print("\n" + "=" * 80)
    print("多轮对话测试 (§5.1 κ 序列)")
    print("=" * 80)

    turns = [
        ("大米中汞污染的整体情况", "first_turn / mid"),
        ("展开具体检测步骤细节", "drill_down / low"),
        ("回到概览层面", "roll_up / mid"),
    ]

    state = make_initial_state(turns[0][0])
    for i, (query, label) in enumerate(turns, 1):
        print(f"\n── Turn {i}: {label} ──")
        print(f"Q: {query}")
        if i > 1:
            state["original_query"] = query
            state["rewritten_query"] = ""
        state = invoke_dialogue_turn(state)
        print(f"  κ={state.get('kappa')} l={state.get('path_level')} "
              f"r={state.get('target_subgraphs')} |P*|={len(state.get('candidate_mp_ids') or [])}")

    print("\n✅ 多轮测试完成（若 LLM/Neo4j 不可用将 raise）")


graph_app = build_graph_rag_pipeline()

print("✅ Pipeline: Node1 → Route → G_sub → Retriever → Answer")
print("   运行 test_multiturn_dialogue() 进行多轮验证")
'''

OVERVIEW_MD = """# G 子图 Agentic Graph RAG（论文 §5.1 / §5.4）

**顶层语义模块** r ∈ {EBM, EEM, MPU}（非 path_level mid/low）

**流程**：QueryRewriter → **Route(r,l,κ)** → **G_sub** → Retriever → **Context(p)+Answer+写回 M_t**

| Node | 论文章节 | 职责 |
|------|----------|------|
| Node 2 | §5.1 Route | (r, l, κ) = Route(q, M_{t-1}) |
| Node 3 | §5.1 G_sub | N_l / WF / DA 算子 |
| Node 4 | §5.2 | G_sub 内候选检索排序 → P* |
| Node 5 | §5.4 | Context(p) + 写回 C_t, E_t |
"""


def patch_notebook() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    cells = nb["cells"]

    cells[1] = _md(OVERVIEW_MD)
    cells[8] = _md(STATE_MD)
    cells[9] = _code(STATE_CODE)
    cells[14] = _md(ROUTE_MD)
    cells[15] = _code(ROUTE_CODE)

    # Insert G Cell 4 + Node 3 after cell 15
    insert_at = 16
    new_cells = [
        _md(OPS_MD),
        _code(OPS_CODE),
        _md(GSUB_MD),
        _code(GSUB_CODE),
    ]
    for i, cell in enumerate(new_cells):
        cells.insert(insert_at + i, cell)

    # Indices shifted +4
    cells[21] = _md("##### G Cell 5: Node 4 Hybrid Retriever\n\n见下方代码 cell。")
    cells[22] = _md(CYPHER_MD)
    cells[23] = _code(CYPHER_CODE)
    cells[24] = _md(RETRIEVER_MD)
    cells[25] = _code(RETRIEVER_CODE)
    cells[26] = _md(ANSWER_MD)
    cells[27] = _code(ANSWER_CODE)

    # Remove old node5 test duplicate if present — find pipeline cell
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "def build_graph_rag_pipeline" in src and "gsub_builder" not in src:
            cells[i] = _md(PIPELINE_MD)
            cells[i + 1] = _code(PIPELINE_CODE)
            break
    else:
        # append pipeline before evaluation section
        eval_idx = next(
            (i for i, c in enumerate(cells) if "评估" in "".join(c.get("source", []))),
            len(cells),
        )
        cells.insert(eval_idx, _md(PIPELINE_MD))
        cells.insert(eval_idx + 1, _code(PIPELINE_CODE))

    # Remove obsolete cells: node2 test stub, duplicate node4 md, old cell 20 helpers dup
    cleaned: List[Dict] = []
    skip_patterns = (
        "node2 test",
        "对neo4j graph grag 原生检索的更改",
        "node 5 test",
    )
    for c in cells:
        src = "".join(c.get("source", []))
        if c["cell_type"] == "markdown" and any(p in src.lower() for p in skip_patterns):
            continue
        if "results = _search_single_subgraph" in src and "mercury methylation" in src:
            continue
        if "_CYPHER_CACHE = _load_cypher_queries" in src:
            continue
        cleaned.append(c)

    nb["cells"] = cleaned
    NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB_PATH} ({len(cleaned)} cells)")


if __name__ == "__main__":
    patch_notebook()
