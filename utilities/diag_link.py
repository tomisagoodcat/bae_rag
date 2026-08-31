import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parents[1].parent / "PaperExtract2" / "PaperExtract2" / ".env")

d = GraphDatabase.driver(
    os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "tomis1cat")),
)
queries = {
    "mid_count": "MATCH (m:MetaPath {path_level:'mid'}) RETURN count(m) AS c",
    "low_count": "MATCH (m:MetaPath {path_level:'low'}) RETURN count(m) AS c",
    "mid_plan": """
        MATCH (m:MetaPath {path_level:'mid'})-[:metaPathRelation]->(p)
        WHERE p:whu_Bio_chemical_Experiment OR p:whu_SpecimenCollection
        RETURN count(m) AS c
    """,
    "low_biochem_step": """
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st:whu_BioChemicalStep)
        RETURN count(l) AS c
    """,
    "plan_chain": """
        MATCH (m:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
        WHERE plan:whu_Bio_chemical_Experiment
        MATCH (st:whu_BioChemicalStep)-[:p_plan_isStepOfPlan]->(plan)
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st)
        RETURN count(*) AS c
    """,
    "part_chain": """
        MATCH (m:MetaPath {path_level:'mid'})-[:metaPathRelation]->(c:whu_SupportGraph)
        MATCH (c)-[:whu_hasPart]->(part)
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(part)
        RETURN count(*) AS c
    """,
    "steps_under_mid_plan": """
        MATCH (m:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
        WHERE plan:whu_Bio_chemical_Experiment
        OPTIONAL MATCH (st)-[:p_plan_isStepOfPlan]->(plan)
        RETURN m.mp_id, count(st) AS steps
        LIMIT 5
    """,
    "low_on_those_steps": """
        MATCH (m:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan:whu_Bio_chemical_Experiment)
        MATCH (st)-[:p_plan_isStepOfPlan]->(plan)
        OPTIONAL MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st)
        RETURN m.mp_id, count(DISTINCT st) AS st_cnt, count(l) AS low_cnt
        LIMIT 5
    """,
    "low_step_plan": """
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st)
        MATCH (st)-[:p_plan_isStepOfPlan]->(plan)
        RETURN count(*) AS c
    """,
    "full_chain": """
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st)
        MATCH (st)-[:p_plan_isStepOfPlan]->(plan)
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
        RETURN count(*) AS c
    """,
    "mid_plan_ids": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
        RETURN mid.mp_id, elementId(plan) AS pid, labels(plan)
        LIMIT 3
    """,
    "plan_reach": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
        MATCH (low:MetaPath {path_level:'low'})
        WHERE low.subgraph = mid.subgraph
        MATCH (low)-[:metaPathRelation]->(entity)
        WHERE EXISTS { MATCH (entity)-[*1..4]-(plan) }
        RETURN count(*) AS c
    """,
    "container_reach": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(container)
        WHERE container:whu_SupportGraph OR container:whu_ScienceEvidence
        MATCH (low:MetaPath {path_level:'low', subgraph:'MPU'})-[:metaPathRelation]->(entity)
        WHERE entity = container OR EXISTS { MATCH (container)-[:whu_hasPart*1..2]-(entity) }
        RETURN count(*) AS c
    """,
    "low_touches_container": """
        MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(c:whu_SupportGraph)
        MATCH (low:MetaPath {path_level:'low'})-[:metaPathRelation]->(c)
        RETURN count(*) AS c
    """,
    "step_overlap": """
        MATCH (st)-[:p_plan_isStepOfPlan]->()
        WITH collect(DISTINCT elementId(st)) AS plan_step_ids
        MATCH (l:MetaPath {path_level:'low'})-[:metaPathRelation]->(st)
        WITH plan_step_ids, collect(DISTINCT elementId(st)) AS low_step_ids
        RETURN size(plan_step_ids) AS plan_steps,
               size(low_step_ids) AS low_steps,
               size([x IN low_step_ids WHERE x IN plan_step_ids]) AS overlap
    """,
}
with d.session() as s:
    for name, q in queries.items():
        print(name, s.run(q).data())
d.close()
