"""Minimal entity resolution (from 1_2_1_1): exact match + optional WCC master."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.paths import ensure_repo_on_syspath


async def _exact_match_async(cfg: PipelineConfig, driver: Driver, prop: str) -> str:
    from neo4j_graphrag.experimental.components.resolver import SinglePropertyExactMatchResolver

    resolver = SinglePropertyExactMatchResolver(
        driver=driver,
        neo4j_database=cfg.neo4j_database,
        resolve_property=prop,
    )
    await resolver.run()
    return "completed"


def run_entity_merge(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Exact-match resolver on WHU_HASNAME; optional Attribution WCC masters."""
    ensure_repo_on_syspath()
    stats: Dict[str, Any] = {}
    prop = cfg.entity_merge.get("exact_match_property", "WHU_HASNAME")

    stats["exact_match"] = asyncio.run(_exact_match_async(cfg, driver, prop))

    if cfg.entity_merge.get("wcc_attribution_master", True):
        stats["wcc_attribution"] = _wcc_attribution_masters(driver, cfg.neo4j_database)
    return stats


def _wcc_attribution_masters(driver: Driver, database: str) -> Dict[str, Any]:
    """Build AttributionMaster nodes via WCC on mp_Attribution (notebook B2 pattern)."""
    graph_name = "kg-pipeline-identity-wcc"
    with driver.session(database=database) as session:
        session.run(
            """
            CALL gds.graph.project.cypher($name,
              'MATCH (n:mp_Attribution) RETURN id(n) AS id',
              'MATCH (a:mp_Attribution)-[:SIMILAR]-(b:mp_Attribution) RETURN id(a) AS source, id(b) AS target',
              {validateRelationships: false})
            """,
            name=graph_name,
        ).consume()
        result = session.run(
            """
            CALL gds.wcc.stream($name)
            YIELD nodeId, componentId
            WITH componentId, collect(nodeId) AS nodes
            WHERE size(nodes) > 1
            MERGE (pg:AttributionMaster {componentId: componentId})
            WITH pg, nodes
            UNWIND nodes AS nid
            MATCH (mp:mp_Attribution) WHERE id(mp) = nid
            MERGE (pg)-[:HAS_REFERENCE]->(mp)
            RETURN count(DISTINCT pg) AS masters, count(*) AS links
            """,
            name=graph_name,
        ).single()
        try:
            session.run("CALL gds.graph.drop($name)", name=graph_name).consume()
        except Exception:
            pass
    return dict(result) if result else {"masters": 0, "links": 0}
