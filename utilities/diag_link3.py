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
queries = {
    "chunk_plan": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(anchor)
        MATCH (low:MetaPath {path_level:'low'})
        WHERE low.subgraph = mid.subgraph
        MATCH (low)-[:metaPathRelation]->(entity)
        WHERE EXISTS {
          MATCH (anchor)-[:FROM_CHUNK]->(c:Chunk)<-[:FROM_CHUNK]-(entity)
        }
        RETURN count(*) AS c
    """,
    "chunk_container": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(anchor)
        WHERE anchor:whu_SupportGraph OR anchor:whu_ScienceEvidence
              OR anchor:whu_SpecimenCollection OR anchor:whu_Bio_chemical_Experiment
        MATCH (low:MetaPath {path_level:'low'})
        WHERE low.subgraph = mid.subgraph
        MATCH (low)-[:metaPathRelation]->(entity)
        WHERE EXISTS {
          MATCH (anchor)-[:FROM_CHUNK]->(c:Chunk)<-[:FROM_CHUNK]-(entity)
        }
        RETURN count(*) AS c
    """,
}
with d.session() as s:
    for k, q in queries.items():
        print(k, s.run(q).single()["c"])
d.close()
