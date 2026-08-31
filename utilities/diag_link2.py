import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parents[1].parent / "PaperExtract2" / "PaperExtract2" / ".env")

d = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", os.environ.get("NEO4J_PASSWORD", "tomis1cat")),
)
with d.session() as s:
    q1 = """
    MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(c:whu_SupportGraph)
    MATCH (low:MetaPath {path_level:'low'})-[:metaPathRelation]->(c)
    RETURN count(*) AS c
    """
    q2 = """
    MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(container)
    WHERE container:whu_SupportGraph OR container:whu_ScienceEvidence
    MATCH (low:MetaPath {path_level:'low', subgraph:'MPU'})-[:metaPathRelation]->(entity)
    WHERE entity = container
    RETURN count(*) AS c
    """
    q3 = """
    MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(container)
    MATCH (container)-[:whu_hasPart]->(part)
    MATCH (low:MetaPath {path_level:'low'})-[:metaPathRelation]->(part)
    RETURN count(*) AS c
    """
    print("low->same SupportGraph as mid", s.run(q1).single()["c"])
    print("low->container entity", s.run(q2).single()["c"])
    print("low->hasPart part", s.run(q3).single()["c"])
d.close()
