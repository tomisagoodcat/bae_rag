import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parents[1].parent / "PaperExtract2" / "PaperExtract2" / ".env")

d = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", os.environ.get("NEO4J_PASSWORD", "tomis1cat")),
)
with d.session() as s:
    print("=== path_level counts ===")
    print(s.run(
        "MATCH (mp:MetaPath) RETURN mp.path_level AS level, count(*) AS c ORDER BY level"
    ).data())
    print("hasDetailPath", s.run(
        "MATCH ()-[h:hasDetailPath]->() RETURN count(h) AS c"
    ).single())
    print("with metaPathQuery", s.run(
        "MATCH (mp:MetaPath) WHERE mp.metaPathQuery IS NOT NULL RETURN count(mp) AS c"
    ).single())
    print("with embedding", s.run(
        "MATCH (mp:MetaPath) WHERE mp.embedding IS NOT NULL RETURN count(mp) AS c"
    ).single())
    print("indexes", s.run("SHOW INDEXES YIELD name, type, state WHERE name CONTAINS 'metapath' RETURN name, state").data())
d.close()
