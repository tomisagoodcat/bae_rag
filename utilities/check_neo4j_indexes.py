"""Check Neo4j MetaPath / index readiness for retrieval eval."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env")

uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
user = os.environ.get("NEO4J_USERNAME", "neo4j")
pwd = os.environ.get("NEO4J_PASSWORD", "")

driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session() as s:
    mp = s.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
    emb = s.run(
        "MATCH (mp:MetaPath) WHERE mp.embedding IS NOT NULL RETURN count(mp) AS c"
    ).single()["c"]
    idx = s.run(
        "SHOW INDEXES YIELD name, type WHERE name CONTAINS 'metapath' RETURN name, type"
    ).data()

print("MetaPath count:", mp)
print("With embedding:", emb)
print("Indexes:", idx)
driver.close()
