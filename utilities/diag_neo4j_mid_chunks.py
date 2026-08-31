import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env")

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)
with driver.session() as s:
    mid_total = s.run(
        "MATCH (mp:MetaPath {path_level:'mid'}) RETURN mp.subgraph AS sg, count(*) AS n ORDER BY sg"
    ).data()
    print("mid total:", mid_total)
    mid_chunk = s.run(
        """
        MATCH (mp:MetaPath {path_level:'mid'})-[:metaPathRelation]->(e)-[:FROM_CHUNK]->(:Chunk)
        RETURN mp.subgraph AS sg, count(DISTINCT mp) AS with_chunk ORDER BY sg
        """
    ).data()
    print("mid with chunk:", mid_chunk)
    sample = s.run(
        """
        MATCH (mp:MetaPath {path_level:'mid', subgraph:'MPU'})
        OPTIONAL MATCH (mp)-[:metaPathRelation]->(e)-[:FROM_CHUNK]->(c:Chunk)
        RETURN mp.mp_id AS mp_id, count(c) AS chunks LIMIT 5
        """
    ).data()
    print("samples:", sample)
driver.close()
