"""Fix corrupted recall_node cell in notebook."""
from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"

RECALL_CELL = r'''# ══════════════════════════════════════════════════════════════
# Node 4: Recall（hybrid Top-50，全 κ 统一广召回）
# ══════════════════════════════════════════════════════════════

from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.types import RetrieverResultItem
from utilities.pipeline_config import get_pipeline_config
from utilities.session_config import is_stateless
from utilities.recall_flat import (
    build_cypher_for_subgraph_flat,
    HYBRID_SCAN_FLAT_PER_MODULE,
)
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

    if is_stateless(state):
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


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code" and "def recall_node" in "".join(cell.get("source", [])):
            cell["source"] = RECALL_CELL.splitlines(keepends=True)
            break
    else:
        raise RuntimeError("recall_node cell not found")
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print("✅ fixed recall_node")


if __name__ == "__main__":
    main()
