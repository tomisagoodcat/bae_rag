"""Document-level cross-parent linking after local Low Accept."""
from __future__ import annotations

from typing import Any, Dict, List

from neo4j import Driver


def run_cross_parent_linker(
    driver: Driver,
    database: str,
    filename: str,
) -> Dict[str, Any]:
    """Deterministic Specimen / Data / Argument chains + light same-name align.

    Does not call full LLM entity extraction.
    """
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    stats = {
        "specimen_links": 0,
        "data_links": 0,
        "argument_links": 0,
        "name_align_merges": 0,
        "filename": filename,
    }
    with driver.session(database=database) as session:
        # Specimen chain: Specimen -fellow-> ProcessedSpecimen across parents (same doc)
        r1 = session.run(
            """
            MATCH (a:whu_Specimen), (b:whu_ProcessedSpecimen)
            WHERE coalesce(a.whu_rejected,false)=false
              AND coalesce(b.whu_rejected,false)=false
              AND (
                a.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(a) WHERE c.filename = $filename
                }
              )
              AND (
                b.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(b) WHERE c.filename = $filename
                }
              )
              AND a.WHU_HASNAME IS NOT NULL
              AND b.WHU_HASNAME IS NOT NULL
              AND toLower(a.WHU_HASNAME) = toLower(b.WHU_HASNAME)
            MERGE (b)-[:whu_fellow]->(a)
            RETURN count(*) AS cnt
            """,
            filename=filename,
            source_doc=source_doc,
        ).single()
        stats["specimen_links"] = int(r1["cnt"]) if r1 else 0

        # Data chain: DataSet name-align under ScienceEvidence members
        r2 = session.run(
            """
            MATCH (d1:whu_DataSet), (d2:whu_DataSet)
            WHERE elementId(d1) < elementId(d2)
              AND coalesce(d1.whu_rejected,false)=false
              AND coalesce(d2.whu_rejected,false)=false
              AND d1.WHU_HASNAME IS NOT NULL
              AND toLower(d1.WHU_HASNAME) = toLower(d2.WHU_HASNAME)
              AND (
                d1.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(d1) WHERE c.filename = $filename
                }
              )
              AND (
                d2.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(d2) WHERE c.filename = $filename
                }
              )
            MERGE (d1)-[:whu_fellow]->(d2)
            RETURN count(*) AS cnt
            """,
            filename=filename,
            source_doc=source_doc,
        ).single()
        stats["data_links"] = int(r2["cnt"]) if r2 else 0

        # Argument chain: Statement/Attribution supporting same Claim via SupportGraph
        r3 = session.run(
            """
            MATCH (sg:whu_SupportGraph)-[:mp_supports|mp_challenges]->(cl:mp_Claim)
            WHERE coalesce(sg.whu_rejected,false)=false
              AND (
                sg.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(sg) WHERE c.filename = $filename
                }
              )
            MATCH (sg)-[:prov_hadMember]->(m)
            WHERE any(l IN labels(m) WHERE l IN ['mp_Statement','mp_Attribution','mp_Reference'])
            WITH cl, collect(DISTINCT m) AS members
            UNWIND members AS m1
            UNWIND members AS m2
            WITH cl, m1, m2
            WHERE elementId(m1) < elementId(m2)
            MERGE (m1)-[:mp_supports]->(cl)
            RETURN count(*) AS cnt
            """,
            filename=filename,
            source_doc=source_doc,
        ).single()
        stats["argument_links"] = int(r3["cnt"]) if r3 else 0

        # Light same-name Method align (link, not full merge)
        r4 = session.run(
            """
            MATCH (a:mp_Method), (b:mp_Method)
            WHERE elementId(a) < elementId(b)
              AND coalesce(a.whu_rejected,false)=false
              AND coalesce(b.whu_rejected,false)=false
              AND a.WHU_HASNAME IS NOT NULL
              AND toLower(a.WHU_HASNAME) = toLower(b.WHU_HASNAME)
              AND (
                a.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(a) WHERE c.filename = $filename
                }
              )
              AND (
                b.source_doc = $source_doc OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(b) WHERE c.filename = $filename
                }
              )
            MERGE (a)-[:whu_fellow]->(b)
            RETURN count(*) AS cnt
            """,
            filename=filename,
            source_doc=source_doc,
        ).single()
        stats["name_align_merges"] = int(r4["cnt"]) if r4 else 0

    return stats
