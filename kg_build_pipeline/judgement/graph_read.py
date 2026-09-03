"""Read-only Neo4j snapshot for judgement (MATCH/RETURN only)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set

from neo4j import Driver

from kg_build_pipeline.judgement.constants import EXCLUDED_REL_TYPES
from kg_build_pipeline.judgement.schema_view import primary_bae_label

_WRITE_TOKENS = (" SET ", " DELETE ", " CREATE ", " MERGE ", " REMOVE ", " DROP ")


def assert_readonly_cypher(cypher: str) -> None:
    upper = f" {cypher.upper()} "
    for tok in _WRITE_TOKENS:
        if tok in upper:
            raise ValueError(f"judgement queries must be read-only; found {tok.strip()}: {cypher[:120]}")


@dataclass
class NodeRec:
    eid: str
    labels: List[str]
    bae_label: Optional[str]
    name: str
    original_text: str
    source_doc: str
    filenames: List[str]
    rejected: bool


@dataclass
class EdgeRec:
    eid: str
    src: str
    tgt: str
    rel_type: str
    src_label: Optional[str]
    tgt_label: Optional[str]


@dataclass
class GraphSnapshot:
    nodes: List[NodeRec]
    edges: List[EdgeRec]
    filenames: List[str]
    research_step_count: int
    uri: str
    database: str


CYPHER_QUERIES = {
    "nodes": """
MATCH (n)
WHERE coalesce(n.whu_rejected, false) = false
  AND any(l IN labels(n) WHERE l IN $instantiable)
OPTIONAL MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
WITH n, collect(DISTINCT c.filename) AS filenames
RETURN elementId(n) AS eid,
       labels(n) AS labels,
       coalesce(n.WHU_HASNAME, '') AS name,
       coalesce(n.WHU_HASORIGINALTEXT, '') AS original_text,
       coalesce(n.source_doc, '') AS source_doc,
       [f IN filenames WHERE f IS NOT NULL AND trim(toString(f)) <> ''] AS filenames
""",
    "edges": """
MATCH (a)-[r]->(b)
WHERE coalesce(a.whu_rejected, false) = false
  AND coalesce(b.whu_rejected, false) = false
  AND any(l IN labels(a) WHERE l IN $instantiable)
  AND any(l IN labels(b) WHERE l IN $instantiable)
  AND NOT type(r) IN $excluded
RETURN elementId(r) AS eid,
       elementId(a) AS src,
       elementId(b) AS tgt,
       type(r) AS rel_type,
       labels(a) AS src_labels,
       labels(b) AS tgt_labels
""",
    "files": """
MATCH (c:Chunk)
WHERE c.filename IS NOT NULL AND trim(c.filename) <> ''
RETURN DISTINCT c.filename AS filename
ORDER BY filename
""",
    "step_count": """
MATCH (s:whu_ResearchStep)
WHERE coalesce(s.whu_rejected, false) = false
RETURN count(s) AS n
""",
    "site_matrix": """
MATCH (a)-[r]->(b)
WHERE type(r) IN $rels
  AND coalesce(a.whu_rejected, false) = false
  AND coalesce(b.whu_rejected, false) = false
RETURN elementId(a) AS src, elementId(b) AS tgt, type(r) AS rel_type,
       labels(a) AS src_labels, labels(b) AS tgt_labels,
       a.WHU_HASNAME AS src_name, b.WHU_HASNAME AS tgt_name
""",
    "research_steps": """
MATCH (s:whu_ResearchStep)
WHERE coalesce(s.whu_rejected, false) = false
OPTIONAL MATCH (s)-[:p_plan_isStepOfPlan]->(p)
WITH s, collect(DISTINCT elementId(p)) AS parent_ids,
     collect(DISTINCT labels(p)) AS parent_label_lists
RETURN elementId(s) AS id,
       s.WHU_HASNAME AS name,
       labels(s) AS labels,
       s.WHU_RESEARCHTYPE AS research_type,
       parent_ids,
       reduce(acc = [], labs IN parent_label_lists | acc + labs) AS parent_labels
""",
    "materials": """
MATCH (m:envo_EnvironmentMaterial)
WHERE coalesce(m.whu_rejected, false) = false
RETURN elementId(m) AS id, m.WHU_HASNAME AS name, labels(m) AS labels
""",
}

for _q in CYPHER_QUERIES.values():
    assert_readonly_cypher(_q)


def fetch_snapshot(
    driver: Driver,
    database: str,
    instantiable: Sequence[str],
    *,
    uri: str = "",
) -> GraphSnapshot:
    instantiable = list(instantiable)
    excluded = list(EXCLUDED_REL_TYPES)
    with driver.session(database=database) as session:
        nodes: List[NodeRec] = []
        for rec in session.run(CYPHER_QUERIES["nodes"], instantiable=instantiable):
            labels = list(rec["labels"] or [])
            bae = primary_bae_label(labels, instantiable)
            if not bae:
                continue
            nodes.append(
                NodeRec(
                    eid=str(rec["eid"]),
                    labels=labels,
                    bae_label=bae,
                    name=str(rec.get("name") or ""),
                    original_text=str(rec.get("original_text") or ""),
                    source_doc=str(rec.get("source_doc") or ""),
                    filenames=list(rec.get("filenames") or []),
                    rejected=False,
                )
            )
        by_id = {n.eid: n for n in nodes}
        edges: List[EdgeRec] = []
        for rec in session.run(
            CYPHER_QUERIES["edges"], instantiable=instantiable, excluded=excluded
        ):
            src = str(rec["src"])
            tgt = str(rec["tgt"])
            if src not in by_id or tgt not in by_id:
                continue
            edges.append(
                EdgeRec(
                    eid=str(rec["eid"]),
                    src=src,
                    tgt=tgt,
                    rel_type=str(rec["rel_type"]),
                    src_label=by_id[src].bae_label,
                    tgt_label=by_id[tgt].bae_label,
                )
            )
        files = [str(r["filename"]) for r in session.run(CYPHER_QUERIES["files"])]
        step_n = int(session.run(CYPHER_QUERIES["step_count"]).single()["n"])
    extra_docs: Set[str] = set(files)
    for n in nodes:
        extra_docs.update(n.filenames)
        if n.source_doc:
            extra_docs.add(_as_filename(n.source_doc))
    filenames = sorted(f for f in extra_docs if f)
    return GraphSnapshot(
        nodes=nodes,
        edges=edges,
        filenames=filenames,
        research_step_count=step_n,
        uri=uri,
        database=database,
    )


def _as_filename(source_doc: str) -> str:
    raw = source_doc.strip()
    if raw.endswith(".md"):
        return raw
    return f"{raw}.md"


def node_docs(node: NodeRec) -> List[str]:
    docs = list(node.filenames)
    if node.source_doc:
        fn = _as_filename(node.source_doc)
        if fn not in docs:
            docs.append(fn)
    return docs


def fetch_site_matrix_rows(
    driver: Driver,
    database: str,
    instantiable: Sequence[str],
) -> List[Dict[str, Any]]:
    from kg_build_pipeline.judgement.constants import SITE_MATRIX_RELS

    rows: List[Dict[str, Any]] = []
    with driver.session(database=database) as session:
        for rec in session.run(CYPHER_QUERIES["site_matrix"], rels=list(SITE_MATRIX_RELS)):
            rows.append(
                {
                    "src": str(rec["src"]),
                    "tgt": str(rec["tgt"]),
                    "rel_type": str(rec["rel_type"]),
                    "src_label": primary_bae_label(rec["src_labels"] or [], instantiable),
                    "tgt_label": primary_bae_label(rec["tgt_labels"] or [], instantiable),
                    "src_name": rec.get("src_name"),
                    "tgt_name": rec.get("tgt_name"),
                    "src_labels": list(rec["src_labels"] or []),
                    "tgt_labels": list(rec["tgt_labels"] or []),
                }
            )
    return rows


def fetch_research_steps(driver: Driver, database: str) -> List[Dict[str, Any]]:
    with driver.session(database=database) as session:
        return [dict(r) for r in session.run(CYPHER_QUERIES["research_steps"])]


def fetch_materials(driver: Driver, database: str) -> List[Dict[str, Any]]:
    with driver.session(database=database) as session:
        return [dict(r) for r in session.run(CYPHER_QUERIES["materials"])]
