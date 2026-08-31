"""Shared MetaPath hybrid Cypher builders for Recall / qrels annotation."""
from __future__ import annotations

from utilities.dialogue_routing import TOP_LEVEL_MODULES, VALID_PATH_LEVELS
from utilities.recall_flat import build_cypher_for_subgraph_flat


def build_cypher_for_subgraph(subgraph: str, path_level: str = "mid") -> str:
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

__all__ = ["build_cypher_for_subgraph", "build_cypher_for_subgraph_flat"]
