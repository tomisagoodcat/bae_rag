"""Neo4j driver helpers (no torch/llama_index imports)."""
from __future__ import annotations

import time
from typing import Optional

from neo4j import Driver, GraphDatabase

from kg_build_pipeline.src.config import PipelineConfig


def build_neo4j_driver(cfg: PipelineConfig) -> Driver:
    return GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
        max_connection_lifetime=3600,
        max_connection_pool_size=20,
        connection_acquisition_timeout=120,
        connection_timeout=30,
        keep_alive=True,
    )


def neo4j_is_alive(driver: Driver, database: str) -> bool:
    try:
        with driver.session(database=database) as session:
            session.run("RETURN 1").consume()
        return True
    except Exception:
        return False


def wait_for_neo4j(driver: Driver, database: str, max_wait_sec: int = 120) -> bool:
    start = time.time()
    while time.time() - start < max_wait_sec:
        if neo4j_is_alive(driver, database):
            return True
        time.sleep(5)
    return False


def clear_neo4j(driver: Driver, database: str) -> None:
    with driver.session(database=database) as session:
        session.run("MATCH (n) DETACH DELETE n").consume()


def get_db_stats(driver: Driver, database: str) -> dict[str, int]:
    """Return node and relationship counts for the given database."""
    with driver.session(database=database) as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        relationships = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        chunks = session.run("MATCH (c:Chunk) RETURN count(c) AS c").single()["c"]
        metapaths = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
    return {
        "nodes": nodes,
        "relationships": relationships,
        "chunks": chunks,
        "metapaths": metapaths,
    }
