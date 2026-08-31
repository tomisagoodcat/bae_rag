"""Patch 3_0_2 Retevie.ipynb: 6-node pipeline (recall + rerank), docs/mermaid sync."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"


def _src(code: str) -> list:
    if not code.endswith("\n"):
        code += "\n"
    return code.splitlines(keepends=True)


def _md(text: str) -> list:
    return _src(text)


# ── Markdown ──────────────────────────────────────────────────────────

G_INTRO = """# G 子图 Agentic Graph RAG（论文 §5.1 / §5.4）

**顶层语义模块** r ∈ {EBM, EEM, MPU}（非 path_level mid/low）

**六节点流程**：QueryRewriter → **Route(r,l,κ)** → **G_sub** → **Recall** → **Rerank** → **Context+Answer**

| Node | 论文章节 | 职责 |
|------|----------|------|
| Node 2 | §5.1 Route | (r, l, κ)；**首轮 l 由 LLM 选 mid/low** |
| Node 3 | §5.1 G_sub | N_l / WF / DA → `gsub_mp_ids`（空池不中断） |
| Node 4 | §5.2 Recall | 各 r 模块 hybrid 广召回 Top-50 |
| Node 5 | §5.2 Rerank | α·检索 + η·PageRank + γ·OLAP先验 → Top-10 |
| Node 6 | §5.4 | Context(p) + 写回 C_t |
"""

G_FLOW = """# 流程（论文 §5.1 / §5.4）

## 单轮 LangGraph 链路（6 Node）

```
M_{t-1} → Node1 QueryRewriter
        → Node2 Route(r, l, κ)
        → Node3 G_sub Builder
        → Node4 Recall (hybrid Top-50)
        → Node5 Rerank (无结构分) → P* Top-10
        → Node6 Context(p) + Answer → 写回 M_t
```

| 符号 | 字段 | 含义 |
|------|------|------|
| **r** | `target_subgraphs` | 顶层语义模块 {EBM, EEM, MPU} |
| **l** | `path_level` | MetaPath 抽象层级 {mid, low}；**首轮由 Route/LLM 选择** |
| **κ** | `kappa` | first_turn / drill_down / roll_up / sibling_nav / drill_across |
| **C** | `candidate_mp_ids` | 上一轮排序候选 P* |
| **G_sub** | `gsub_mp_ids` | OLAP 软先验池（Turn2+）；空则 γ 仍可用、先验=0.3 |

**实验开关**（G Cell 2）：`PIPELINE_VARIANT = "full" | "no_hierarchy"`

## 业务流程图

```mermaid
graph TB
    Start([用户问题 q<br/>多轮时携带 M_t-1]) --> N1

    subgraph S1["Node 1 · Query Rewriter"]
        N1[原问题 q] --> Lang{语言检测}
        Lang -->|中文| KW[关键词 + 英译]
        Lang -->|英文| RW[LLM 改写]
        KW --> RW
        RW --> Qr[rewritten_query]
    end

    Qr --> N2

    subgraph S2["Node 2 · Route §5.1"]
        N2[Route q, M_t-1] --> Turn{dialogue_turn / C?}
        Turn -->|首轮或无 C| R0[LLM 选 r + l mid/low<br/>κ=first_turn]
        Turn -->|多轮| R1[LLM 选 κ, l, r]
        R0 --> Var{PIPELINE_VARIANT}
        R1 --> Var
        Var -->|full| Routed[(r, l, κ)]
        Var -->|no_hierarchy 且 turn≥1| Flat[强制 κ=first_turn, l=mid<br/>重选 r]
        Flat --> Routed
    end

    Routed --> N3

    subgraph S3["Node 3 · G_sub §5.1"]
        N3{κ} -->|first_turn| G0[G_sub = ∅]
        N3 -->|drill_down / roll_up| Nl[N_l]
        N3 -->|sibling_nav| Wf[WF]
        N3 -->|drill_across| Da[DA]
        Nl --> Gids[gsub_mp_ids<br/>空则 warn 不中断]
        Wf --> Gids
        Da --> Gids
    end

    G0 --> N4
    Gids --> N4

    subgraph S4["Node 4 · Recall §5.2"]
        N4[各 r 模块 HybridCypherRetriever<br/>filter path_level=l] --> Pool[C_rec Top-50]
    end

    Pool --> N5

    subgraph S5["Node 5 · Rerank §5.2"]
        N5["s = α·s_search + η·s_pr + γ·s_olap<br/>无结构分；γ=0 当首轮"] --> Pstar[P* Top-10 mp_id]
    end

    Pstar --> N6

    subgraph S6["Node 6 · Evidence §5.4"]
        N6[Context(p)] --> Ans[答案 + 引用]
        Ans --> WB[写回 M_t]
    end

    WB --> End([final_answer])
```

## 检索 / 重排摘要

| 阶段 | 行为 |
|------|------|
| **Recall** | 在 r 各模块内 hybrid（向量+全文），按 **l** 过滤；合并去重 **Top-50** |
| **Rerank** | **仅** 检索分 + maxPageRank 图分 + OLAP 先验（在 G_sub=1.0，不在=0.3）；首轮 **γ=0** |
| **输出** | P* = **10** 条 `retrieval_mp_ids` |

**Turn2+**：不再「仅在 G_sub 内检索」；G_sub 仅作 rerank 软先验。G_sub 为空时流程继续，先验均为 0.3。
"""

G_NODE3 = """##### Node 3: 构造候选路径池（OLAP 软先验）

根据 **κ、l** 与上一轮短名单 `candidate_mp_ids` 构造 `gsub_mp_ids`：

| 情况 | 候选池 | 说明 |
|------|--------|------|
| **首轮** | 空 | Recall 仍按 r+l 全模块 hybrid；Rerank **γ=0** |
| **下钻/上卷/相邻/跨模块** | ID 列表（可空） | **空池仅 warn，不 raise**；Rerank 时不在池=0.3 |
"""

G_CELL5 = """##### G Cell 5: 检索子系统（Recall + Rerank）

| Node | 职责 |
|------|------|
| **Node 4 Recall** | 各 **MPU/EEM/EBM** 模块 hybrid，按 **l** 过滤 → 合并 **Top-50** |
| **Node 5 Rerank** | `s_final = α·s_search + η·s_pr + γ·s_olap`（**无**结构分）→ **Top-10** |

OLAP 先验：mp_id ∈ `gsub_mp_ids` → 1.0，否则 0.3；**首轮 γ=0**。
"""

G_CELL6 = """##### G Cell 6: MetaPath 检索 Cypher

- `_build_cypher_for_subgraph(sg, path_level)`：Recall 用；RETURN 含 `maxPageRank AS graph_score`（**无 COALESCE**）
- 已移除「仅在 G_sub 内 fetch」的 `_build_cypher_for_gsub` 检索路径
"""

G_NODE4 = """##### Node 4: Recall（广召回 Top-50）

对每个 `target_subgraphs` 模块执行 HybridCypherRetriever，Cypher 按 `path_level` 过滤 mid/low。
合并、按 `mp_id` 去重，保留 **50** 条写入 `recall_candidates`。
"""

G_NODE5 = """##### Node 5: Rerank（Top-10）

对 `recall_candidates` 计算：

- **s_search**：hybrid 分数（缺失则用 embedding 重算，非兜底）
- **s_pr**：`maxPageRank` 归一化（NULL 则 **raise**）
- **s_olap**：在 `gsub_mp_ids` 内 1.0 / 外 0.3；**κ=first_turn 时 γ=0**

输出 `retrieval_mp_ids` / `candidate_mp_ids`（10 条）。
"""

G_CELL7 = """##### G Cell 7: 组装 Pipeline

```
问题改写 → 路由 → 候选路径池 → 召回(50) → 重排(10) → 生成答案
```

多轮：`data/dialogue_test_cases.json`  
评估：`utilities/run_retrieval_eval.py`
"""

G_CELL4_IMPORTS = """# ══════════════════════════════════════════════════════════════
# G Cell 4: G_sub 算子 + Rerank 导入
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
)
from utilities.retrieval_rerank import (
    RECALL_TOP_K,
    OUTPUT_TOP_K,
    rerank_metapath_candidates,
)

print("✅ G_sub 算子 + rerank 已导入")
print(f"   RECALL_TOP_K={RECALL_TOP_K}, OUTPUT_TOP_K={OUTPUT_TOP_K}")
print(f"   顶层模块: {sorted(TOP_LEVEL_MODULES)}")
"""

GSUB_CODE = r'''from typing import Dict
import warnings

# ══════════════════════════════════════════════════════════════
# Node 3: G_sub Builder（空池 warn，不中断）
# ══════════════════════════════════════════════════════════════

from utilities.pipeline_config import get_pipeline_config


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

    cfg = get_pipeline_config()
    if not cfg.gsub_enabled:
        if kappa != "first_turn":
            raise RuntimeError(
                f"variant={cfg.variant} 禁用 G_sub，但 κ={kappa}（应为 first_turn）"
            )
        print("  G_sub = ∅ (variant 禁用多维度 / first_turn)")
        return {"gsub_mp_ids": [], "gsub_size": 0}

    gsub_ids = build_gsub_mp_ids(
        driver=neo4j_driver,
        kappa=kappa,
        candidate_mp_ids=candidates,
        active_modules=modules,
        path_level=path_level,
    )

    if kappa == "first_turn":
        print("  G_sub = ∅ (首轮：Recall 按 r+l hybrid；Rerank γ=0)")
    else:
        print(f"  G_sub = {len(gsub_ids)} 条 MetaPath（OLAP 软先验池）")
        if not gsub_ids:
            warnings.warn(
                f"G_sub 为空: κ={kappa}, l={path_level} — 流程继续，"
                "Rerank 时全部 mp_id 的 s_olap=0.3",
                stacklevel=2,
            )

    return {"gsub_mp_ids": gsub_ids, "gsub_size": len(gsub_ids)}


print("✅ Node 3 gsub_builder_node 定义完成")
'''

CYPHER_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 6: MetaPath 检索 Cypher（Recall）
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
    node.maxPageRank AS graph_score,
    node.mp_id AS mp_id,
    node.path_level AS path_level,
    node.subgraph AS subgraph,
    node.path_type AS path_type,
    node.metaPathQuery AS meta_path_query
"""


print("✅ MetaPath Recall Cypher 定义完成（graph_score = maxPageRank，无 COALESCE）")
'''

RECALL_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 4: Recall（hybrid Top-50，全 κ 统一广召回）
# ══════════════════════════════════════════════════════════════

from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.types import RetrieverResultItem
from utilities.pipeline_config import get_pipeline_config
import neo4j
import re
from typing import Dict, List, Any

METAPATH_VECTOR_INDEX = "metapath_embedding_index"
METAPATH_FULLTEXT_INDEX = "metapath_fulltext_index"
HYBRID_SCAN_TOP_K = {"mid": 300, "low": 60}


def sanitize_for_lucene(text: str) -> str:
    return re.sub(r'[+\-&|!(){}\[\]^"~*?:\\/—–]', ' ', text).strip()


def metapath_result_formatter(record: neo4j.Record) -> RetrieverResultItem:
    return RetrieverResultItem(content=dict(record), metadata=None)


def _search_single_subgraph(
    query_text: str, subgraph: str, path_level: str
) -> List[Dict]:
    retrieval_query = _build_cypher_for_subgraph(subgraph, path_level)
    retriever = HybridCypherRetriever(
        driver=neo4j_driver,
        vector_index_name=METAPATH_VECTOR_INDEX,
        fulltext_index_name=METAPATH_FULLTEXT_INDEX,
        embedder=neo4j_embed_model,
        retrieval_query=retrieval_query,
        result_formatter=metapath_result_formatter,
    )
    scan_k = HYBRID_SCAN_TOP_K.get(path_level, RECALL_TOP_K)
    retriever_result = retriever.search(query_text=query_text, top_k=scan_k)
    results = _safe_convert_results(retriever_result)
    for r in results:
        r["_subgraph"] = subgraph
    return results


def recall_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 4: Recall (hybrid Top-50)")
    print("=" * 60)

    query_text = sanitize_for_lucene(state["rewritten_query"])
    if not query_text:
        raise ValueError("检索查询为空")

    modules = state["target_subgraphs"]
    if not modules:
        raise ValueError("target_subgraphs 为空")

    path_level = state["path_level"]
    kappa = state["kappa"]
    cfg = get_pipeline_config()
    if not cfg.multi_dim_enabled and kappa != "first_turn":
        raise RuntimeError(f"variant={cfg.variant} 仅支持 first_turn 式 Recall")

    print(f"查询: {query_text[:80]}...")
    print(f"r={modules} | κ={kappa} | l={path_level}")

    all_results: List[Dict] = []
    for sg in modules:
        print(f"\n  ── hybrid {sg} (l={path_level}) ──")
        batch = _search_single_subgraph(query_text, sg, path_level)
        print(f"  返回: {len(batch)}")
        all_results.extend(batch)

    if not all_results:
        raise RuntimeError(
            f"Recall 无结果: r={modules}, l={path_level}, κ={kappa}"
        )

    all_results.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    merged = _deduplicate_by_mp_id(all_results)[:RECALL_TOP_K]

    print(f"  C_rec: {len(merged)} 条 (cap={RECALL_TOP_K})")

    return {
        "recall_candidates": merged,
        "recall_count": len(merged),
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
    if isinstance(item, dict):
        return item
    if hasattr(item, "data") and callable(getattr(item, "data", None)):
        try:
            return dict(item.data())
        except Exception:
            pass
    if hasattr(item, "content"):
        content = item.content
        if isinstance(content, dict):
            return content
        if isinstance(content, str) and content.startswith("<Record"):
            return {"raw_content": content}
        if content is not None:
            try:
                return dict(content)
            except Exception:
                return {"raw_content": str(content)}
    if hasattr(item, "metadata") and isinstance(item.metadata, dict):
        return item.metadata
    raise TypeError(f"无法转换检索结果项: {type(item)}")


print("✅ Node 4 recall_node 定义完成")
'''

RERANK_CODE = r'''# ══════════════════════════════════════════════════════════════
# Node 5: Rerank（α·检索 + η·PR + γ·OLAP → Top-10）
# ══════════════════════════════════════════════════════════════

import json
from typing import Dict, List, Any


def _format_retrieval_results(results: List[Dict]) -> Dict:
    return {
        "status": "success",
        "count": len(results),
        "results": [
            {
                "rank": i + 1,
                "mp_id": item.get("mp_id"),
                "combined_score": item.get("combined_score"),
                "s_search": item.get("s_search"),
                "s_pr": item.get("s_pr"),
                "s_olap": item.get("s_olap"),
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


def rerank_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 5: Rerank (Top-10)")
    print("=" * 60)

    query_text = sanitize_for_lucene(state["rewritten_query"])
    if not query_text:
        raise ValueError("Rerank 需要非空 rewritten_query")

    pool = state.get("recall_candidates") or []
    if not pool:
        raise ValueError("rerank_node: recall_candidates 为空")

    kappa = state["kappa"]
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

    p_star = [r["mp_id"] for r in top if r.get("mp_id")]
    if len(p_star) != len(top):
        raise RuntimeError("Rerank 结果存在缺失 mp_id 的行")

    formatted = _format_retrieval_results(top)
    print(f"  P* Top-{OUTPUT_TOP_K}: {p_star[:3]}...")

    return {
        "retrieval_results": json.dumps(formatted, ensure_ascii=False, indent=2),
        "retrieval_mp_ids": p_star,
        "candidate_mp_ids": p_star,
        "anchor_mp_ids": p_star[:5],
        "path_level": path_level,
        "kappa": kappa,
    }


print("✅ Node 5 rerank_node 定义完成")
'''

PIPELINE_CODE = r'''# ══════════════════════════════════════════════════════════════
# G Cell 7: Pipeline + 多轮测试（6 Node）
# ══════════════════════════════════════════════════════════════

from __future__ import annotations

from typing import List, Dict
from langgraph.graph import StateGraph, END
import json
import time


def build_graph_rag_pipeline():
    workflow = StateGraph(SimplifiedGraphRAGState)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("route", route_node)
    workflow.add_node("gsub_builder", gsub_builder_node)
    workflow.add_node("recall", recall_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("answer_generator", answer_generator_node)

    workflow.set_entry_point("query_rewriter")
    workflow.add_edge("query_rewriter", "route")
    workflow.add_edge("route", "gsub_builder")
    workflow.add_edge("gsub_builder", "recall")
    workflow.add_edge("recall", "rerank")
    workflow.add_edge("rerank", "answer_generator")
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
        ("大米中汞污染的整体情况", "first_turn"),
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

    print("\n✅ 多轮测试完成")


graph_app = build_graph_rag_pipeline()

print("✅ Pipeline: Rewriter → Route → G_sub → Recall(50) → Rerank(10) → Answer")

try:
    from IPython.display import Image, display
    display(Image(graph_app.get_graph().draw_mermaid_png()))
except Exception as exc:
    print(f"流程图渲染失败: {exc}")
'''

STATE_PATCH = (
    '    "retrieval_mp_ids": [],\n',
    '    "recall_candidates": [],\n    "recall_count": 0,\n    "retrieval_mp_ids": [],\n',
)

G_NODE2_MD = """##### Node 2: Route(q, M_{t-1}) → (r, l, κ)

统一路由节点。

- **首轮**（`dialogue_turn=0` 或无 C）：LLM 选 **r + l (mid|low)**，`κ=first_turn`（**不写死 l=mid**）
- **多轮**：LLM 选 κ、l、r；`drill_down`/`roll_up` 保持 r；`sibling_nav` 须切换模块
"""

ROUTE_IMPORT = "from utilities.dialogue_routing import route_dialogue, route_first_turn\n"


def _cleanup_duplicates(cells: list) -> None:
    seen_cypher = False
    to_drop: list[int] = []
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "Route(q, M_{t-1})" in src and c["cell_type"] == "markdown":
            c["source"] = _md(G_NODE2_MD)
        if "def route_node" in src:
            if "route_first_turn" not in src:
                src = src.replace(
                    "from utilities.dialogue_routing import route_dialogue, route_modules_first_turn\n",
                    "from utilities.dialogue_routing import route_dialogue, route_first_turn, route_modules_first_turn\n",
                )
                c["source"] = _src(src)
        if "_build_cypher_for_subgraph" in src and "def recall_node" not in src:
            if seen_cypher:
                to_drop.append(i)
            else:
                seen_cypher = True
    for idx in reversed(to_drop):
        del cells[idx]


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    rerank_inserted = False

    for i, c in enumerate(cells):
        cid = c.get("id")
        src = "".join(c.get("source", []))

        if cid == "3df025bb":
            c["source"] = _md(G_INTRO)
        elif cid == "edd9efa9":
            c["source"] = _md(G_FLOW)
        elif cid == "02db8baf":
            c["source"] = _md(G_NODE3)
        elif cid == "d6b4b4d4":
            c["source"] = _md(G_CELL5)
        elif cid == "034adf08":
            c["source"] = _md(G_CELL6)
        elif cid == "871be803":
            c["source"] = _md(G_CELL7)
        elif cid == "f9cfcece" or src.startswith("##### Node 4: 检索排序"):
            c["source"] = _md(G_NODE4)
        elif src.startswith("##### Node 4: Hybrid") or "Hybrid Retriever" in src[:80]:
            c["source"] = _md(G_NODE4)

        if "class SimplifiedGraphRAGState" in src:
            if "recall_candidates" not in src:
                src = src.replace(
                    "    retrieval_mp_ids: list[str]   # 本轮 P*\n",
                    "    recall_candidates: list  # Node4 C_rec\n"
                    "    recall_count: int\n"
                    "    retrieval_mp_ids: list[str]   # 本轮 P* (Top-10)\n",
                )
            if '"recall_candidates"' not in src:
                src = src.replace(STATE_PATCH[0], STATE_PATCH[1])
            c["source"] = _src(src)

        if "G Cell 4: G_sub" in src and "build_gsub_mp_ids" in src:
            c["source"] = _src(G_CELL4_IMPORTS)
        elif "def gsub_builder_node" in src:
            c["source"] = _src(GSUB_CODE)
        elif "G Cell 6: MetaPath" in src and "_build_cypher_for_subgraph" in src:
            c["source"] = _src(CYPHER_CODE)
        elif "def hybrid_retriever_node" in src or "def recall_node" in src:
            if "def recall_node" not in src:
                c["source"] = _src(RECALL_CODE)
                if not rerank_inserted:
                    cells.insert(
                        i + 1,
                        {
                            "cell_type": "markdown",
                            "metadata": {},
                            "id": "rerank_md_v2",
                            "source": _md(G_NODE5),
                        },
                    )
                    cells.insert(
                        i + 2,
                        {
                            "cell_type": "code",
                            "metadata": {},
                            "id": "rerank_code_v2",
                            "source": _src(RERANK_CODE),
                        },
                    )
                    rerank_inserted = True
            else:
                c["source"] = _src(RECALL_CODE)
        elif "def rerank_node" in src:
            c["source"] = _src(RERANK_CODE)
        elif "def build_graph_rag_pipeline" in src:
            c["source"] = _src(PIPELINE_CODE)

    # second pass: fix cells after insert
    cells = nb["cells"]
    for c in cells:
        src = "".join(c.get("source", []))
        if src.startswith("##### Node 5: Path-grounded") and "Node 6" not in src:
            c["source"] = _md(
                "##### Node 6: Path-grounded Evidence Context + 答案生成（§5.4）\n\n"
                "对 P*（Rerank Top-10）构建 `Context(p)`，生成答案并写回状态。\n"
            )
        if "def answer_generator_node" in src and "Node 5:" in src[:200]:
            c["source"] = _src(src.replace("Node 5:", "Node 6:"))

    _cleanup_duplicates(cells)
    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB} ({len(cells)} cells), rerank_inserted={rerank_inserted}")


if __name__ == "__main__":
    patch()
