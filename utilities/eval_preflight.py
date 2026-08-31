"""Preflight checks before OLAP evaluation (fail loud, no silent skip)."""
from __future__ import annotations

import os
from typing import Any, Dict, List

from neo4j import GraphDatabase


class EvalPreflightError(RuntimeError):
    """Evaluation cannot proceed; infrastructure or data missing."""


def check_neo4j_ready(
    driver: Any,
    *,
    min_metapaths: int = 1,
    require_vector_index: bool = True,
) -> Dict[str, Any]:
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        mp_count = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
        emb_count = session.run(
            "MATCH (mp:MetaPath) WHERE mp.embedding IS NOT NULL RETURN count(mp) AS c"
        ).single()["c"]
        indexes: List[Dict[str, Any]] = session.run(
            "SHOW INDEXES YIELD name, type, state "
            "WHERE name CONTAINS 'metapath' RETURN name, type, state"
        ).data()

    index_names = {row["name"] for row in indexes}
    report = {
        "node_count": node_count,
        "metapath_count": mp_count,
        "metapath_with_embedding": emb_count,
        "indexes": indexes,
    }

    errors: List[str] = []
    if node_count == 0:
        errors.append("Neo4j 数据库为空（0 节点）。请先导入 KG 并运行 MetaPath 构建 pipeline。")
    if mp_count < min_metapaths:
        errors.append(
            f"MetaPath 数量不足: {mp_count} < {min_metapaths}。"
            "请运行 1_2_1_2pagerankMetapath.ipynb 或 utilities/run_metapath_pipeline.py。"
        )
    if emb_count < min_metapaths:
        errors.append(
            f"带 embedding 的 MetaPath 不足: {emb_count}。"
            "请运行 F3 embedding + 索引创建。"
        )
    if require_vector_index and "metapath_embedding_index" not in index_names:
        errors.append(
            "缺少向量索引 metapath_embedding_index。"
            "HybridRetriever 无法运行。"
        )
    if require_vector_index and "metapath_fulltext_index" not in index_names:
        errors.append(
            "缺少全文索引 metapath_fulltext_index。"
            "HybridRetriever 无法运行。"
        )

    if errors:
        msg = "评估前置检查失败:\n" + "\n".join(f"  - {e}" for e in errors)
        raise EvalPreflightError(msg)
    return report


def check_neo4j_from_env() -> Dict[str, Any]:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        return check_neo4j_ready(driver)
    finally:
        driver.close()
