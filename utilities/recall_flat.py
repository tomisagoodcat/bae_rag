"""Stateless Recall: hybrid over MetaPath without path_level (mid/low) filter."""
from __future__ import annotations

from utilities.dialogue_routing import TOP_LEVEL_MODULES

# Per-module hybrid scan when not filtering by l (mid+low mixed in index)
HYBRID_SCAN_FLAT_PER_MODULE = 300


def build_cypher_for_subgraph_flat(subgraph: str) -> str:
    """Cypher projection after hybrid retrieval; no path_level filter."""
    if subgraph not in TOP_LEVEL_MODULES:
        raise ValueError(f"无效顶层模块: {subgraph}")
    return f"""
WITH node
WHERE node.subgraph = '{subgraph}'
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
