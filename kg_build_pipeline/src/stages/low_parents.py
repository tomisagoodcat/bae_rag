"""Enumerate mid parents for Low expand from PASS documents."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS


def list_pass_filenames(
    driver: Driver,
    database: str,
    *,
    filenames: Optional[List[str]] = None,
) -> List[str]:
    """Filenames whose Chunks carry mid_gate_status=PASS."""
    with driver.session(database=database) as session:
        if filenames:
            rows = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.filename IN $filenames
                  AND toUpper(coalesce(c.mid_gate_status, '')) = 'PASS'
                RETURN DISTINCT c.filename AS filename
                ORDER BY filename
                """,
                filenames=filenames,
            ).data()
        else:
            rows = session.run(
                """
                MATCH (c:Chunk)
                WHERE toUpper(coalesce(c.mid_gate_status, '')) = 'PASS'
                RETURN DISTINCT c.filename AS filename
                ORDER BY filename
                """
            ).data()
    return [str(r["filename"]) for r in rows if r.get("filename")]


def fetch_mid_parents_for_document(
    driver: Driver,
    database: str,
    filename: str,
) -> List[Dict[str, Any]]:
    """Mid-core parents with original_text and home FROM_CHUNK(s)."""
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    mid_labels = sorted(MID_CORE_ENTITY_LABELS)
    with driver.session(database=database) as session:
        rows = session.run(
            """
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $mid_labels)
              AND coalesce(n.whu_rejected, false) = false
              AND (
                n.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
                  WHERE c.filename = $filename
                }
              )
            OPTIONAL MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
            WHERE c.filename = $filename OR c.filename IS NULL
            WITH n, collect(DISTINCT {
              id: coalesce(c.id, elementId(c)),
              index: c.index,
              filename: c.filename,
              text: coalesce(c.text, '')
            }) AS chunks
            RETURN elementId(n) AS element_id,
                   labels(n) AS labels,
                   n.WHU_HASNAME AS name,
                   coalesce(n.WHU_HASORIGINALTEXT, '') AS original_text,
                   [x IN chunks WHERE x.text IS NOT NULL AND x.text <> ''] AS home_chunks
            ORDER BY name
            """,
            filename=filename,
            source_doc=source_doc,
            mid_labels=mid_labels,
        ).data()
    out: List[Dict[str, Any]] = []
    for r in rows:
        homes = [h for h in (r.get("home_chunks") or []) if isinstance(h, dict)]
        out.append(
            {
                "element_id": r.get("element_id"),
                "labels": list(r.get("labels") or []),
                "name": r.get("name"),
                "original_text": r.get("original_text") or "",
                "home_chunks": homes,
                "filename": filename,
            }
        )
    return out


def fetch_mid2low_children(
    driver: Driver,
    database: str,
    filename: str,
    parent_element_id: str,
    *,
    mid2low_rels: List[str],
    max_children: int = 30,
) -> List[Dict[str, Any]]:
    """Nodes linked to mid parent via any mid2low relation (either direction)."""
    if not parent_element_id or not mid2low_rels:
        return []
    # Sanitize rel type names for Cypher (schema labels only).
    safe_rels = [
        r for r in mid2low_rels if isinstance(r, str) and r.replace("_", "").isalnum()
    ]
    if not safe_rels:
        return []
    rel_union = "|".join(safe_rels)
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    with driver.session(database=database) as session:
        rows = session.run(
            f"""
            MATCH (p) WHERE elementId(p) = $pid
            MATCH (p)-[r:{rel_union}]-(c)
            WHERE elementId(c) <> elementId(p)
              AND coalesce(c.whu_rejected, false) = false
            OPTIONAL MATCH (ch:Chunk)-[:FROM_CHUNK]-(c)
            WHERE ch.filename = $filename OR ch.filename IS NULL
            WITH c, collect(DISTINCT {{
              id: coalesce(ch.id, elementId(ch)),
              index: ch.index,
              filename: ch.filename,
              text: coalesce(ch.text, '')
            }}) AS chunks
            RETURN elementId(c) AS element_id,
                   labels(c) AS labels,
                   c.WHU_HASNAME AS name,
                   coalesce(c.WHU_HASORIGINALTEXT, '') AS original_text,
                   [x IN chunks WHERE x.text IS NOT NULL AND x.text <> ''] AS home_chunks
            ORDER BY name
            LIMIT $limit
            """,
            pid=parent_element_id,
            filename=filename,
            limit=int(max_children),
        ).data()
    out: List[Dict[str, Any]] = []
    for r in rows:
        homes = [h for h in (r.get("home_chunks") or []) if isinstance(h, dict)]
        out.append(
            {
                "element_id": r.get("element_id"),
                "labels": list(r.get("labels") or []),
                "name": r.get("name"),
                "original_text": r.get("original_text") or "",
                "home_chunks": homes,
                "filename": filename,
                "source_doc": source_doc,
            }
        )
    return out


def fetch_neighbor_chunks(
    driver: Driver,
    database: str,
    filename: str,
    home_indices: List[int],
    *,
    window: int = 1,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return previous/next Chunk dicts within ±window of home indices."""
    if not home_indices:
        return {"previous": [], "next": []}
    idxs = sorted({int(i) for i in home_indices if i is not None})
    lo = min(idxs) - max(1, window)
    hi = max(idxs) + max(1, window)
    with driver.session(database=database) as session:
        rows = session.run(
            """
            MATCH (c:Chunk)
            WHERE c.filename = $filename
              AND c.index IS NOT NULL
              AND c.index >= $lo AND c.index <= $hi
            RETURN coalesce(c.id, elementId(c)) AS id,
                   c.index AS index,
                   c.filename AS filename,
                   coalesce(c.text, '') AS text
            ORDER BY c.index
            """,
            filename=filename,
            lo=lo,
            hi=hi,
        ).data()
    home_set = set(idxs)
    previous: List[Dict[str, Any]] = []
    nxt: List[Dict[str, Any]] = []
    for r in rows:
        idx = r.get("index")
        if idx is None or idx in home_set:
            continue
        if idx < min(idxs):
            previous.append(r)
        elif idx > max(idxs):
            nxt.append(r)
    return {"previous": previous, "next": nxt}
