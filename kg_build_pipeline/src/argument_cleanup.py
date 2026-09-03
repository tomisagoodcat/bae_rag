"""Deterministic cleanup of cloned argument spans and lexically invalid challenges."""
from __future__ import annotations

from typing import Any, Dict, List

from neo4j import Driver

from kg_build_pipeline.src.argument_polarity import text_has_challenge_language


def _source_doc(filename: str) -> str:
    return filename[:-3] if filename.endswith(".md") else filename


def original_texts_equal(left: str | None, right: str | None) -> bool:
    a = (left or "").strip()
    b = (right or "").strip()
    return bool(a) and a == b


def is_proper_substring(inner: str | None, outer: str | None) -> bool:
    """True when inner is a strictly shorter contiguous substring of outer."""
    child = (inner or "").strip()
    parent = (outer or "").strip()
    if not child or not parent:
        return False
    if child == parent:
        return False
    return child in parent


def _scope_where(alias: str) -> str:
    return f"""
    (
      {alias}.source_doc = $source_doc
      OR EXISTS {{
        MATCH (c:Chunk)-[:FROM_CHUNK]-({alias})
        WHERE c.filename = $filename
      }}
    )
    AND coalesce({alias}.whu_rejected, false) = false
    """


def scrub_cloned_argument_spans(
    driver: Driver,
    database: str,
    filename: str,
) -> Dict[str, int]:
    """Delete SG/Claim and SE/SG polarity edges whose original_text is identical.

    Also delete ``mp_challenges`` edges whose node/relation text has no refute cue.
    """
    params = {"filename": filename, "source_doc": _source_doc(filename)}
    deleted_clone = 0
    deleted_challenge = 0
    with driver.session(database=database) as session:
        clone_q = f"""
        MATCH (a)-[r:mp_supports|mp_challenges]->(b)
        WHERE {_scope_where("a")}
          AND (
            ('whu_SupportGraph' IN labels(a) AND 'mp_Claim' IN labels(b))
            OR ('whu_ScienceEvidence' IN labels(a) AND 'whu_SupportGraph' IN labels(b))
          )
          AND trim(toString(coalesce(a.WHU_HASORIGINALTEXT, ''))) <> ''
          AND trim(toString(a.WHU_HASORIGINALTEXT))
              = trim(toString(coalesce(b.WHU_HASORIGINALTEXT, '')))
        WITH collect(r) AS rels
        FOREACH (rel IN rels | DELETE rel)
        RETURN size(rels) AS n
        """
        rec = session.run(clone_q, **params).single()
        deleted_clone = int(rec["n"]) if rec else 0

        rows: List[Dict[str, Any]] = list(
            session.run(
                f"""
                MATCH (a)-[r:mp_challenges]->(b)
                WHERE {_scope_where("a")}
                RETURN elementId(r) AS rid,
                       a.WHU_HASORIGINALTEXT AS aot,
                       b.WHU_HASORIGINALTEXT AS bot,
                       r.WHU_HASORIGINALTEXT AS rot
                """,
                **params,
            )
        )
        drop_ids = [
            row["rid"]
            for row in rows
            if not text_has_challenge_language(
                " ".join(
                    str(x or "")
                    for x in (row.get("aot"), row.get("bot"), row.get("rot"))
                )
            )
        ]
        if drop_ids:
            session.run(
                """
                MATCH ()-[r:mp_challenges]->()
                WHERE elementId(r) IN $ids
                DELETE r
                """,
                ids=drop_ids,
            ).consume()
            deleted_challenge = len(drop_ids)
    return {
        "deleted_identical_ot": deleted_clone,
        "deleted_challenges_no_lexicon": deleted_challenge,
    }
