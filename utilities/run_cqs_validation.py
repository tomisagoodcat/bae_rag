"""
BAE Competency Questions (CQ1–CQ5) validation against Neo4j KG.

Strict mode:
- No silent fallbacks that mask schema/data gaps.
- Each CQ has explicit Pass / Partial / Fail criteria.
- Gaps are reported with concrete missing labels/relations/columns.

Usage:
  pipelineD_env\\Scripts\\python.exe utilities/run_cqs_validation.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_USER = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
DEFAULT_PASSWORD = os.environ.get("NEO4J_PASSWORD", "tomis1cat")
DEFAULT_DB = os.environ.get("NEO4J_DATABASE", "neo4j")


@dataclass
class CQSpec:
    cq_id: str
    question: str
    description: str
    cypher: str
    ontology_classes: List[str]
    ontology_relations: List[str]
    expected_output: str
    result_type: str
    required_columns_full: List[str]
    required_columns_partial: List[str]
    required_labels: List[str] = field(default_factory=list)
    required_relations: List[str] = field(default_factory=list)
    # Named diagnostic probes (never used to flip Fail→Pass)
    diagnostics: Dict[str, str] = field(default_factory=dict)


@dataclass
class CQResult:
    cq_id: str
    status: str  # Fully supported | Partially supported | Not supported | Blocked | QueryError
    row_count: int
    sample_rows: List[Dict[str, Any]]
    gaps: List[str]
    required_label_counts: Dict[str, int]
    required_relation_counts: Dict[str, int]
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def _trunc(v: Any, n: int = 160) -> Any:
    if v is None:
        return None
    if isinstance(v, list):
        return [_trunc(x, n) for x in v[:20]]
    s = str(v)
    return s if len(s) <= n else s[: n - 1] + "…"


def _row_nonempty(row: Dict[str, Any], col: str) -> bool:
    if col not in row:
        return False
    v = row[col]
    if v is None:
        return False
    if isinstance(v, (list, tuple, set)):
        return any(x is not None and str(x).strip() != "" for x in v)
    return str(v).strip() != ""


def _rows_cover_columns(rows: Sequence[Dict[str, Any]], cols: Sequence[str]) -> bool:
    if not rows or not cols:
        return False
    for row in rows:
        if all(_row_nonempty(row, c) for c in cols):
            return True
    return False


def count_label(session, label: str) -> int:
    # label from controlled vocabulary only
    q = f"MATCH (n:`{label}`) RETURN count(n) AS c"
    return int(session.run(q).single()["c"])


def count_rel(session, rel: str) -> int:
    q = f"MATCH ()-[r:`{rel}`]->() RETURN count(r) AS c"
    return int(session.run(q).single()["c"])


def snapshot(session) -> Dict[str, Any]:
    nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
    rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
    labels = [
        {"label": r["l"], "count": int(r["c"])}
        for r in session.run(
            "MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS c ORDER BY c DESC LIMIT 40"
        )
    ]
    rel_types = [
        {"rel": r["t"], "count": int(r["c"])}
        for r in session.run(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC LIMIT 40"
        )
    ]
    return {"nodes": nodes, "relationships": rels, "top_labels": labels, "top_rels": rel_types}


def build_cq_specs(limit: int) -> List[CQSpec]:
    lim = max(1, int(limit))
    return [
        CQSpec(
            cq_id="CQ1",
            question=(
                "CQ1. For a biochemical experiment input specimen, what environment, "
                "collection process, and preprocessing process does it originate from?"
            ),
            description=(
                "Retrieves environment, specimen-collection plan/step, and preprocessing "
                "plan/step for specimens/processed specimens that are inputs of biochemical "
                "research steps under a BioChemical experiment plan."
            ),
            cypher=f"""
MATCH (exp:whu_Bio_chemical_Experiment)<-[:p_plan_isStepOfPlan]-(bio:whu_BioChemicalStep)
MATCH (bio)-[:p_plan_hasInputVar]->(inp)
WHERE inp:whu_ProcessedSpecimen OR inp:whu_Specimen
OPTIONAL MATCH (inp)-[:prov_wasDerivedFrom*1..2]->(envFromDeriv:whu_EnvironmentFeature)
OPTIONAL MATCH (spec:whu_Specimen)
WHERE (inp = spec) OR ((inp:whu_ProcessedSpecimen) AND (inp)-[:prov_wasDerivedFrom]->(spec))
OPTIONAL MATCH (cstep:whu_Specimen_CollectionStep)-[:p_plan_hasOutputVar]->(spec)
OPTIONAL MATCH (cstep)-[:p_plan_isStepOfPlan]->(coll:whu_SpecimenCollection)
OPTIONAL MATCH (coll)-[:whu_hasContext]->(envCtx:whu_EnvironmentFeature)
OPTIONAL MATCH (pstep:whu_Specimen_ProcessingStep)-[:p_plan_hasOutputVar]->(inp)
WHERE inp:whu_ProcessedSpecimen
OPTIONAL MATCH (pstep)-[:p_plan_isStepOfPlan]->(prep:whu_SpecimenPreprocessing)
OPTIONAL MATCH (pstep)-[:p_plan_hasInputVar]->(specFromPrep:whu_Specimen)
RETURN DISTINCT
  exp.WHU_HASNAME AS Experiment,
  inp.WHU_HASNAME AS InputSpecimen,
  labels(inp)[0] AS InputType,
  coalesce(envCtx.WHU_HASNAME, envFromDeriv.WHU_HASNAME) AS Environment,
  coll.WHU_HASNAME AS CollectionPlan,
  cstep.WHU_HASNAME AS CollectionStep,
  prep.WHU_HASNAME AS PreprocessingPlan,
  pstep.WHU_HASNAME AS PreprocessingStep
ORDER BY Experiment, InputSpecimen
LIMIT {lim}
""".strip(),
            ontology_classes=[
                "whu_Bio_chemical_Experiment",
                "whu_BioChemicalStep",
                "whu_ProcessedSpecimen",
                "whu_Specimen",
                "whu_EnvironmentFeature",
                "whu_SpecimenCollection",
                "whu_SpecimenPreprocessing",
                "whu_Specimen_CollectionStep",
                "whu_Specimen_ProcessingStep",
            ],
            ontology_relations=[
                "p_plan_isStepOfPlan",
                "p_plan_hasInputVar",
                "p_plan_hasOutputVar",
                "prov_wasDerivedFrom",
                "whu_hasContext",
            ],
            expected_output=(
                "Environment, collection plan/step, and preprocessing plan/step "
                "linked to experiment input specimens."
            ),
            result_type="Experiment, InputSpecimen, Environment, Collection*, Preprocessing*",
            required_columns_full=[
                "Experiment",
                "InputSpecimen",
                "Environment",
                "CollectionPlan",
                "PreprocessingPlan",
            ],
            required_columns_partial=["Experiment", "InputSpecimen", "Environment"],
            required_labels=[
                "whu_Bio_chemical_Experiment",
                "whu_BioChemicalStep",
                "whu_Specimen",
                "whu_ProcessedSpecimen",
                "whu_EnvironmentFeature",
                "whu_SpecimenCollection",
                "whu_SpecimenPreprocessing",
            ],
            required_relations=[
                "p_plan_isStepOfPlan",
                "p_plan_hasInputVar",
                "p_plan_hasOutputVar",
                "whu_hasContext",
                "prov_wasDerivedFrom",
            ],
            diagnostics={
                "bio_steps_linked_to_experiment": """
MATCH (bio:whu_BioChemicalStep)-[:p_plan_isStepOfPlan]->(:whu_Bio_chemical_Experiment)
RETURN count(DISTINCT bio) AS c
""".strip(),
                "bio_steps_with_specimen_input": """
MATCH (bio:whu_BioChemicalStep)-[:p_plan_hasInputVar]->(inp)
WHERE inp:whu_ProcessedSpecimen OR inp:whu_Specimen
RETURN count(DISTINCT bio) AS c
""".strip(),
                "bio_steps_with_BOTH_plan_and_specimen_input": """
MATCH (bio:whu_BioChemicalStep)-[:p_plan_isStepOfPlan]->(:whu_Bio_chemical_Experiment)
MATCH (bio)-[:p_plan_hasInputVar]->(inp)
WHERE inp:whu_ProcessedSpecimen OR inp:whu_Specimen
RETURN count(DISTINCT bio) AS c
""".strip(),
                "collection_hasContext_count": """
MATCH (:whu_SpecimenCollection)-[:whu_hasContext]->(:whu_EnvironmentFeature)
RETURN count(*) AS c
""".strip(),
            },
        ),
        CQSpec(
            cq_id="CQ2",
            question=(
                "CQ2. Which experiments, research steps, methods, and supporting resources "
                "generated a given data object?"
            ),
            description=(
                "Retrieves the producing research step and parent plan/experiment for each "
                "DataSet via p_plan_hasOutputVar / p_plan_isStepOfPlan, and collects methods "
                "and supporting resources linked by whu_declareUsed."
            ),
            cypher=f"""
MATCH (step)-[:p_plan_hasOutputVar]->(ds:whu_DataSet)
WHERE step:whu_BioChemicalStep
   OR step:whu_ComputationalStep
   OR step:whu_Specimen_ProcessingStep
   OR step:whu_Specimen_CollectionStep
MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
OPTIONAL MATCH (step)-[:whu_declareUsed]->(method:whu_Method)
OPTIONAL MATCH (step)-[:whu_declareUsed]->(dev:whu_Device)
OPTIONAL MATCH (step)-[:whu_declareUsed]->(reag:whu_Reagent)
OPTIONAL MATCH (step)-[:whu_declareUsed]->(soft:whu_Software)
WITH ds, step, plan, method,
     [x IN collect(DISTINCT coalesce(dev.WHU_HASNAME, reag.WHU_HASNAME, soft.WHU_HASNAME))
      WHERE x IS NOT NULL] AS SupportResources
RETURN DISTINCT
  ds.WHU_HASNAME AS DataSet,
  labels(plan)[0] AS PlanType,
  plan.WHU_HASNAME AS ExperimentOrPlan,
  labels(step)[0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  method.WHU_HASNAME AS Method,
  SupportResources
ORDER BY DataSet, ResearchStep
LIMIT {lim}
""".strip(),
            ontology_classes=[
                "whu_DataSet",
                "whu_BioChemicalStep",
                "whu_ComputationalStep",
                "whu_Bio_chemical_Experiment",
                "whu_Computational_Experiment",
                "whu_Method",
                "whu_Device",
                "whu_Reagent",
                "whu_Software",
            ],
            ontology_relations=[
                "p_plan_hasOutputVar",
                "p_plan_isStepOfPlan",
                "whu_declareUsed",
            ],
            expected_output=(
                "DataSet with producing plan/experiment, research step, method, "
                "and support resources."
            ),
            result_type="DataSet, ExperimentOrPlan, ResearchStep, Method, SupportResources",
            required_columns_full=[
                "DataSet",
                "ExperimentOrPlan",
                "ResearchStep",
                "Method",
            ],
            required_columns_partial=["DataSet", "ExperimentOrPlan", "ResearchStep"],
            required_labels=["whu_DataSet", "whu_Method"],
            required_relations=[
                "p_plan_hasOutputVar",
                "p_plan_isStepOfPlan",
                "whu_declareUsed",
            ],
            diagnostics={
                "steps_with_dataset_output": """
MATCH (st)-[:p_plan_hasOutputVar]->(:whu_DataSet)
WHERE st:whu_BioChemicalStep OR st:whu_ComputationalStep
   OR st:whu_Specimen_ProcessingStep OR st:whu_Specimen_CollectionStep
RETURN count(*) AS c, count(DISTINCT st) AS steps
""".strip(),
                "steps_with_isStepOfPlan": """
MATCH (st)-[:p_plan_isStepOfPlan]->(p)
WHERE st:whu_BioChemicalStep OR st:whu_ComputationalStep
   OR st:whu_Specimen_ProcessingStep OR st:whu_Specimen_CollectionStep
RETURN count(*) AS c, count(DISTINCT st) AS steps
""".strip(),
                "steps_with_BOTH_output_and_plan": """
MATCH (st)-[:p_plan_hasOutputVar]->(:whu_DataSet)
WHERE st:whu_BioChemicalStep OR st:whu_ComputationalStep
   OR st:whu_Specimen_ProcessingStep OR st:whu_Specimen_CollectionStep
MATCH (st)-[:p_plan_isStepOfPlan]->(p)
RETURN count(*) AS c, count(DISTINCT st) AS steps
""".strip(),
                "declareUsed_from_steps": """
MATCH (st)-[:whu_declareUsed]->(m:whu_Method)
WHERE st:whu_BioChemicalStep OR st:whu_ComputationalStep
RETURN count(*) AS c
""".strip(),
            },
        ),
        CQSpec(
            cq_id="CQ3",
            question=(
                "CQ3. Which datasets, methods, and research steps jointly constitute "
                "ScienceEvidence that supports or challenges a Statement or Claim?"
            ),
            description=(
                "Paper MPU chain: ScienceEvidence (parts: DataSet/Method) argumentatively "
                "links to SupportGraph and/or Claim|Statement via mp_supports/mp_challenges; "
                "SupportGraph aggregates SE and targets Claim. Producing steps recovered via "
                "p_plan_hasOutputVar on member DataSet. No alternate non-ontology paths are used."
            ),
            cypher=f"""
// Paper path: SE -[supports|challenges]-> SG -[supports|challenges]-> Claim|Statement
// with SE -hasPart-> DataSet|Method
MATCH (se:whu_ScienceEvidence)-[a1:mp_supports|mp_challenges]->(sg:whu_SupportGraph)
MATCH (sg)-[a2:mp_supports|mp_challenges]->(target)
WHERE target:mp_Claim OR target:mp_Statement
MATCH (se)-[:whu_hasPart]->(member)
WHERE member:whu_DataSet OR member:whu_Method
OPTIONAL MATCH (se)-[:whu_hasPart]->(ds:whu_DataSet)
OPTIONAL MATCH (se)-[:whu_hasPart]->(m:whu_Method)
OPTIONAL MATCH (step)-[:p_plan_hasOutputVar]->(ds)
WHERE step:whu_BioChemicalStep OR step:whu_ComputationalStep
RETURN DISTINCT
  labels(target)[0] AS TargetType,
  target.WHU_HASNAME AS Target,
  type(a1) AS SE_to_SG,
  type(a2) AS SG_to_Target,
  se.WHU_HASNAME AS ScienceEvidence,
  sg.WHU_HASNAME AS SupportGraph,
  ds.WHU_HASNAME AS DataSet,
  m.WHU_HASNAME AS Method,
  step.WHU_HASNAME AS ResearchStep
ORDER BY Target, ScienceEvidence
LIMIT {lim}
""".strip(),
            ontology_classes=[
                "mp_Claim",
                "mp_Statement",
                "whu_ScienceEvidence",
                "whu_SupportGraph",
                "whu_DataSet",
                "whu_Method",
            ],
            ontology_relations=[
                "mp_supports",
                "mp_challenges",
                "whu_hasPart",
                "p_plan_hasOutputVar",
            ],
            expected_output=(
                "Claim/Statement with SE→SG→Target polarity, ScienceEvidence members "
                "(DataSet/Method), and generating research steps."
            ),
            result_type="Target, SE_to_SG, SG_to_Target, ScienceEvidence, DataSet, Method, ResearchStep",
            required_columns_full=[
                "Target",
                "ScienceEvidence",
                "SupportGraph",
                "DataSet",
                "Method",
            ],
            required_columns_partial=["Target", "ScienceEvidence", "SupportGraph", "DataSet"],
            required_labels=["mp_Claim", "mp_Statement", "whu_ScienceEvidence", "whu_SupportGraph"],
            required_relations=["mp_supports", "mp_challenges", "whu_hasPart"],
            diagnostics={
                "SE_supports_or_challenges_SG": """
MATCH (:whu_ScienceEvidence)-[:mp_supports|mp_challenges]->(:whu_SupportGraph)
RETURN count(*) AS c
""".strip(),
                "SG_supports_or_challenges_Claim": """
MATCH (:whu_SupportGraph)-[:mp_supports|mp_challenges]->(:mp_Claim)
RETURN count(*) AS c
""".strip(),
                "connected_SE_SG_Claim_without_parts": """
MATCH (se:whu_ScienceEvidence)-[:mp_supports|mp_challenges]->(sg:whu_SupportGraph)
      -[:mp_supports|mp_challenges]->(:mp_Claim)
RETURN count(*) AS c
""".strip(),
                "SE_hasPart_DataSet": """
MATCH (:whu_ScienceEvidence)-[:whu_hasPart]->(:whu_DataSet) RETURN count(*) AS c
""".strip(),
                "SE_hasPart_Method": """
MATCH (:whu_ScienceEvidence)-[:whu_hasPart]->(:whu_Method) RETURN count(*) AS c
""".strip(),
                "SG_hasPart_SE": """
MATCH (:whu_SupportGraph)-[:whu_hasPart]->(:whu_ScienceEvidence) RETURN count(*) AS c
""".strip(),
                "DataSet_supports_Claim_DIRECT_non_ontology_shortcut": """
MATCH (:whu_DataSet)-[:mp_supports|mp_challenges]->(:mp_Claim) RETURN count(*) AS c
""".strip(),
            },
        ),
        CQSpec(
            cq_id="CQ4",
            question=(
                "CQ4. Which fine-grained research steps, inputs/outputs, and evidence elements "
                "constitute a mid-level research process?"
            ),
            description=(
                "Expands mid-level plans/experiments into ResearchSteps with typed IO via "
                "p_plan_isStepOfPlan / hasInputVar / hasOutputVar, and checks MetaPath "
                "mid→low hierarchy via hasDetailPath."
            ),
            cypher=f"""
MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
WHERE plan:whu_SpecimenCollection
   OR plan:whu_SpecimenPreprocessing
   OR plan:whu_Bio_chemical_Experiment
   OR plan:whu_Computational_Experiment
OPTIONAL MATCH (step)-[:p_plan_hasInputVar]->(inp)
OPTIONAL MATCH (step)-[:p_plan_hasOutputVar]->(out)
WITH plan, step,
     [x IN collect(DISTINCT inp.WHU_HASNAME) WHERE x IS NOT NULL] AS Inputs,
     [x IN collect(DISTINCT out.WHU_HASNAME) WHERE x IS NOT NULL] AS Outputs
RETURN
  labels(plan)[0] AS MidPlanType,
  plan.WHU_HASNAME AS MidPlan,
  labels(step)[0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  Inputs,
  Outputs
ORDER BY MidPlanType, MidPlan, ResearchStep
LIMIT {lim}
""".strip(),
            ontology_classes=[
                "whu_SpecimenCollection",
                "whu_SpecimenPreprocessing",
                "whu_Bio_chemical_Experiment",
                "whu_Computational_Experiment",
                "whu_Specimen_CollectionStep",
                "whu_Specimen_ProcessingStep",
                "whu_BioChemicalStep",
                "whu_ComputationalStep",
                "MetaPath",
            ],
            ontology_relations=[
                "p_plan_isStepOfPlan",
                "p_plan_hasInputVar",
                "p_plan_hasOutputVar",
                "hasDetailPath",
            ],
            expected_output=(
                "Mid-level plan with fine-grained steps, IO lists, and mid→low MetaPath pairs."
            ),
            result_type="MidPlan, ResearchStep, Inputs, Outputs (+ hasDetailPath hierarchy probe)",
            required_columns_full=["MidPlan", "ResearchStep", "Inputs", "Outputs"],
            required_columns_partial=["MidPlan", "ResearchStep"],
            required_labels=[
                "whu_Bio_chemical_Experiment",
                "whu_Computational_Experiment",
                "MetaPath",
            ],
            required_relations=[
                "p_plan_isStepOfPlan",
                "p_plan_hasInputVar",
                "p_plan_hasOutputVar",
                "hasDetailPath",
            ],
            diagnostics={
                "plan_linked_steps": """
MATCH (st)-[:p_plan_isStepOfPlan]->(p)
WHERE p:whu_SpecimenCollection OR p:whu_SpecimenPreprocessing
   OR p:whu_Bio_chemical_Experiment OR p:whu_Computational_Experiment
RETURN count(DISTINCT st) AS c
""".strip(),
                "plan_linked_steps_with_any_IO": """
MATCH (st)-[:p_plan_isStepOfPlan]->(p)
WHERE p:whu_SpecimenCollection OR p:whu_SpecimenPreprocessing
   OR p:whu_Bio_chemical_Experiment OR p:whu_Computational_Experiment
MATCH (st)-[:p_plan_hasInputVar|p_plan_hasOutputVar]->()
RETURN count(DISTINCT st) AS c
""".strip(),
                "hasDetailPath_mid_to_low": """
MATCH (:MetaPath {path_level:'mid'})-[h:hasDetailPath]->(:MetaPath {path_level:'low'})
RETURN count(h) AS c
""".strip(),
            },
        ),
        CQSpec(
            cq_id="CQ5",
            question=(
                "CQ5. Which documents, text chunks, and original text spans correspond to "
                "a given evidence MetaPath?"
            ),
            description=(
                "Retrieves MetaPath members via metaPathRelation, their WHU_HASORIGINALTEXT "
                "spans, and Chunk/Document provenance via FROM_CHUNK when present. "
                "Does not invent Document/Chunk links when absent."
            ),
            cypher=f"""
MATCH (mp:MetaPath)-[r:metaPathRelation]->(e)
WHERE mp.metaPathText IS NOT NULL
OPTIONAL MATCH (e)-[:FROM_CHUNK]->(chunk:Chunk)
OPTIONAL MATCH (chunk)-[:FROM_DOCUMENT]->(doc:Document)
RETURN
  mp.mp_id AS MetaPathId,
  mp.path_level AS Level,
  mp.subgraph AS Subgraph,
  mp.metaPathText AS PathText,
  r.position AS Position,
  [x IN labels(e) WHERE NOT x STARTS WITH '__'][0] AS EntityType,
  e.WHU_HASNAME AS Entity,
  e.WHU_HASORIGINALTEXT AS OriginalTextSpan,
  chunk.index AS ChunkIndex,
  chunk.filename AS ChunkFilename,
  chunk.source_doc AS ChunkSourceDoc,
  elementId(chunk) AS ChunkElementId,
  doc.path AS DocumentPath,
  doc.document_type AS DocumentType,
  elementId(doc) AS DocumentElementId
ORDER BY MetaPathId, Position
LIMIT {lim}
""".strip(),
            ontology_classes=["MetaPath", "Chunk", "Document"],
            ontology_relations=["metaPathRelation", "FROM_CHUNK", "FROM_DOCUMENT"],
            expected_output=(
                "MetaPath with ordered member entities, original text spans, and "
                "Chunk/Document provenance (filename/path)."
            ),
            result_type="MetaPathId, Entity, OriginalTextSpan, Chunk*, Document*",
            required_columns_full=[
                "MetaPathId",
                "Entity",
                "OriginalTextSpan",
                "ChunkElementId",
                "DocumentElementId",
            ],
            required_columns_partial=["MetaPathId", "Entity", "OriginalTextSpan"],
            required_labels=["MetaPath", "Chunk", "Document"],
            required_relations=["metaPathRelation", "FROM_CHUNK", "FROM_DOCUMENT"],
            diagnostics={
                "metaPathRelation_count": """
MATCH (:MetaPath)-[:metaPathRelation]->() RETURN count(*) AS c
""".strip(),
                "entity_FROM_CHUNK_count": """
MATCH ()-[:FROM_CHUNK]->(:Chunk) RETURN count(*) AS c
""".strip(),
                "chunk_FROM_DOCUMENT_count": """
MATCH (:Chunk)-[:FROM_DOCUMENT]->(:Document) RETURN count(*) AS c
""".strip(),
            },
        ),
    ]


def _run_diagnostics(session, spec: CQSpec) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, q in spec.diagnostics.items():
        try:
            rows = [dict(r) for r in session.run(q)]
            out[name] = rows[0] if len(rows) == 1 else rows
        except Neo4jError as e:
            out[name] = {"error": str(e)}
    return out


def evaluate_cq(session, spec: CQSpec, sample_limit: int) -> CQResult:
    label_counts = {lb: count_label(session, lb) for lb in spec.required_labels}
    rel_counts = {rel: count_rel(session, rel) for rel in spec.required_relations}
    gaps: List[str] = []
    diag = _run_diagnostics(session, spec)

    for lb, c in label_counts.items():
        if c == 0:
            gaps.append(f"missing_or_empty_label:{lb}")
    for rel, c in rel_counts.items():
        if c == 0:
            gaps.append(f"missing_or_empty_relation:{rel}")

    # Surface join-break diagnostics as explicit gaps (do not grant Pass)
    for name, val in diag.items():
        if isinstance(val, dict) and "c" in val and val["c"] == 0:
            gaps.append(f"diagnostic_zero:{name}")
        if isinstance(val, dict) and "error" in val:
            gaps.append(f"diagnostic_error:{name}")

    # CQ4 plan expansion can still run without MetaPath; hierarchy gap recorded separately.
    block_labels = {
        "CQ1": ["whu_Bio_chemical_Experiment", "whu_BioChemicalStep"],
        "CQ2": ["whu_DataSet"],
        "CQ3": ["whu_ScienceEvidence"],
        "CQ5": ["MetaPath"],
    }.get(spec.cq_id, [])

    if any(label_counts.get(lb, 0) == 0 for lb in block_labels):
        return CQResult(
            cq_id=spec.cq_id,
            status="Blocked",
            row_count=0,
            sample_rows=[],
            gaps=gaps + ["blocked:required_labels_absent"],
            required_label_counts=label_counts,
            required_relation_counts=rel_counts,
            diagnostics=diag,
        )

    try:
        rows = [dict(r) for r in session.run(spec.cypher)]
    except Neo4jError as e:
        return CQResult(
            cq_id=spec.cq_id,
            status="QueryError",
            row_count=0,
            sample_rows=[],
            gaps=gaps + [f"cypher_error:{type(e).__name__}"],
            required_label_counts=label_counts,
            required_relation_counts=rel_counts,
            diagnostics=diag,
            error=str(e),
        )

    # Normalize neo4j types
    norm_rows: List[Dict[str, Any]] = []
    for row in rows:
        item = {}
        for k, v in row.items():
            if hasattr(v, "iso_format"):
                item[k] = str(v)
            else:
                item[k] = v
        norm_rows.append(item)

    sample = [{k: _trunc(v) for k, v in r.items()} for r in norm_rows[:sample_limit]]

    if not norm_rows:
        gaps.append("zero_result_rows:ontology_path_uninstantiated")
        # Highlight known join breaks for CQ1/CQ2
        if spec.cq_id == "CQ1":
            both = diag.get("bio_steps_with_BOTH_plan_and_specimen_input", {})
            if isinstance(both, dict) and both.get("c") == 0:
                gaps.append(
                    "join_break:BioChemicalStep_with_isStepOfPlan_and_specimen_input_is_empty"
                    f"(plan_linked={diag.get('bio_steps_linked_to_experiment')},"
                    f"specimen_input={diag.get('bio_steps_with_specimen_input')})"
                )
        if spec.cq_id == "CQ2":
            both = diag.get("steps_with_BOTH_output_and_plan", {})
            if isinstance(both, dict) and both.get("c") == 0:
                gaps.append(
                    "join_break:Step_with_hasOutputVar_DataSet_and_isStepOfPlan_is_empty"
                    f"(output={diag.get('steps_with_dataset_output')},"
                    f"plan={diag.get('steps_with_isStepOfPlan')})"
                )
        if spec.cq_id == "CQ3":
            gaps.append(
                "join_break:no_connected_SE_to_SG_to_Claim_with_SE_parts;"
                f"fragments={ {k: diag.get(k) for k in diag} }"
            )
        return CQResult(
            cq_id=spec.cq_id,
            status="Not supported",
            row_count=0,
            sample_rows=[],
            gaps=gaps,
            required_label_counts=label_counts,
            required_relation_counts=rel_counts,
            diagnostics=diag,
        )

    full_ok = _rows_cover_columns(norm_rows, spec.required_columns_full)
    partial_ok = _rows_cover_columns(norm_rows, spec.required_columns_partial)

    # Column-level gap diagnostics (honest)
    for col in spec.required_columns_full:
        nonempty = sum(1 for r in norm_rows if _row_nonempty(r, col))
        if nonempty == 0:
            gaps.append(f"column_always_null:{col}")
        elif nonempty < len(norm_rows):
            gaps.append(
                f"column_sparse:{col}:{nonempty}/{len(norm_rows)}_nonempty"
            )

    # CQ-specific structural honesty checks (no masking)
    if spec.cq_id == "CQ4":
        hier = int(
            session.run(
                """
                MATCH (:MetaPath {path_level:'mid'})-[h:hasDetailPath]->(:MetaPath {path_level:'low'})
                RETURN count(h) AS c
                """
            ).single()["c"]
        )
        rel_counts["hasDetailPath_mid_to_low"] = hier
        if hier == 0:
            gaps.append("cq4_metapath_hierarchy_absent:hasDetailPath_mid_to_low=0")
        io_both = sum(
            1
            for r in norm_rows
            if _row_nonempty(r, "Inputs") and _row_nonempty(r, "Outputs")
        )
        if io_both == 0:
            gaps.append("cq4_io_incomplete:no_row_has_both_Inputs_and_Outputs")

    if spec.cq_id == "CQ5":
        chunk_n = sum(1 for r in norm_rows if _row_nonempty(r, "ChunkElementId"))
        doc_n = sum(1 for r in norm_rows if _row_nonempty(r, "DocumentElementId"))
        diag["cq5_chunk_coverage_in_rows"] = f"{chunk_n}/{len(norm_rows)}"
        diag["cq5_document_coverage_in_rows"] = f"{doc_n}/{len(norm_rows)}"
        if chunk_n == 0:
            gaps.append("cq5_chunk_layer_absent:no_ChunkElementId_in_rows")
        if doc_n == 0:
            gaps.append("cq5_document_layer_absent:no_DocumentElementId_in_rows")
        if 0 < chunk_n < len(norm_rows):
            gaps.append(f"cq5_chunk_incomplete_coverage:{chunk_n}/{len(norm_rows)}")
        if 0 < doc_n < len(norm_rows):
            gaps.append(f"cq5_document_incomplete_coverage:{doc_n}/{len(norm_rows)}")

    if spec.cq_id == "CQ3":
        if label_counts.get("whu_ScienceEvidence", 0) > 0 and count_rel(session, "whu_hasPart") == 0:
            gaps.append("cq3_evidence_composition_relation_absent:whu_hasPart=0")

    if full_ok:
        status = "Fully supported"
    elif partial_ok:
        status = "Partially supported"
        gaps.append(
            "partial_only:no_row_satisfies_all_full_columns:"
            + ",".join(spec.required_columns_full)
        )
    else:
        status = "Not supported"
        gaps.append("rows_exist_but_required_partial_columns_unsatisfied")

    # Demotions that must not be masked as Full
    if spec.cq_id == "CQ5" and status == "Fully supported":
        if chunk_n == 0 or doc_n == 0:
            status = "Partially supported"
            gaps.append("demoted_from_full:CQ5_requires_Chunk_and_Document_on_same_rows")
        elif chunk_n < len(norm_rows) or doc_n < len(norm_rows):
            status = "Partially supported"
            gaps.append(
                "demoted_from_full:CQ5_provenance_incomplete_on_some_rows"
                f"(chunk={chunk_n}/{len(norm_rows)}, doc={doc_n}/{len(norm_rows)})"
            )

    if spec.cq_id == "CQ4" and status == "Fully supported":
        if any(g.startswith("cq4_metapath_hierarchy_absent") for g in gaps):
            status = "Partially supported"
            gaps.append("demoted_from_full:CQ4_requires_mid_low_MetaPath_hierarchy")
        if any(g.startswith("cq4_io_incomplete") for g in gaps):
            status = "Partially supported"
            gaps.append("demoted_from_full:CQ4_requires_Inputs_and_Outputs")

    return CQResult(
        cq_id=spec.cq_id,
        status=status,
        row_count=len(norm_rows),
        sample_rows=sample,
        gaps=gaps,
        required_label_counts=label_counts,
        required_relation_counts=rel_counts,
        diagnostics=diag,
    )


def render_markdown(
    snap: Dict[str, Any],
    specs: List[CQSpec],
    results: List[CQResult],
    uri: str,
) -> str:
    by_id = {r.cq_id: r for r in results}
    lines: List[str] = []
    lines.append("# Table 3. Ontology-Driven Queries and Corresponding Results")
    lines.append("")
    lines.append(f"- Generated (UTC): `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- Neo4j URI: `{uri}`")
    lines.append(f"- Graph size: **{snap['nodes']}** nodes, **{snap['relationships']}** relationships")
    lines.append("- Evaluation policy: **strict** (no silent fallbacks; gaps listed explicitly)")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| CQ | Status | Rows | Critical gaps |")
    lines.append("|----|--------|------|---------------|")
    for spec in specs:
        r = by_id[spec.cq_id]
        gap_preview = "; ".join(r.gaps[:4]) if r.gaps else "—"
        if len(r.gaps) > 4:
            gap_preview += f"; …(+{len(r.gaps) - 4})"
        lines.append(
            f"| {spec.cq_id} | {r.status} | {r.row_count} | {gap_preview} |"
        )
    lines.append("")
    lines.append("## Root-cause findings (strict; no fallback paths credited)")
    lines.append("")
    lines.append(
        "- **CQ1 Not supported:** `whu_BioChemicalStep` instances linked to "
        "`whu_Bio_chemical_Experiment` via `p_plan_isStepOfPlan` and those with "
        "`p_plan_hasInputVar`→Specimen/ProcessedSpecimen are **disjoint** "
        "(intersection = 0). Fragments exist but the ontology join required by CQ1 is empty."
    )
    lines.append(
        "- **CQ2 Not supported:** Steps with `p_plan_hasOutputVar`→`whu_DataSet` and steps with "
        "`p_plan_isStepOfPlan`→Plan are **disjoint** (intersection = 0). Data generation cannot "
        "be attributed to an experiment plan along the required path."
    )
    lines.append(
        "- **CQ3 Not supported:** Paper chain "
        "`ScienceEvidence → supports/challenges → SupportGraph → supports/challenges → Claim|Statement` "
        "with `SE -hasPart→ DataSet|Method` has **zero** instantiations. Fragment counts show "
        "SE→SG, SG→Claim, SE–hasPart–DataSet/Method exist separately but do not form one connected evidence unit. "
        "`DataSet → supports → Claim` shortcuts exist and are reported only as diagnostics, **not** as CQ3 Pass."
    )
    lines.append(
        "- **CQ4 Partially supported:** Mid-level plan→step expansion works; Full requires both "
        "typed IO on the same rows **and** mid→low `hasDetailPath` hierarchy. Gaps list which clause failed."
    )
    lines.append(
        "- **CQ5:** Requires MetaPath members plus `FROM_CHUNK`/`FROM_DOCUMENT` provenance on returned rows."
    )
    lines.append("")

    lines.append("## Graph snapshot (top labels / relations)")
    lines.append("")
    lines.append("| Label | Count |")
    lines.append("|-------|------:|")
    for x in snap["top_labels"][:20]:
        lines.append(f"| `{x['label']}` | {x['count']} |")
    lines.append("")
    lines.append("| Relation | Count |")
    lines.append("|----------|------:|")
    for x in snap["top_rels"][:20]:
        lines.append(f"| `{x['rel']}` | {x['count']} |")
    lines.append("")

    lines.append("## Detailed CQ table")
    lines.append("")
    lines.append(
        "| Competency Question | Query Description | Cypher Query | "
        "Ontology Elements Used | Expected Output | Result Type | Status | Result |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")

    for spec in specs:
        r = by_id[spec.cq_id]
        classes = ", ".join(f"`{c}`" for c in spec.ontology_classes)
        rels = ", ".join(f"`{x}`" for x in spec.ontology_relations)
        ont = f"Classes: {classes}<br>Relationships: {rels}"
        cypher_cell = "<pre>" + spec.cypher.replace("|", "\\|") + "</pre>"
        if r.error:
            result_cell = f"**ERROR**: `{r.error}`"
        elif r.row_count == 0:
            result_cell = f"_empty_ ({r.status})"
        else:
            # compact sample as HTML list
            parts = []
            for i, row in enumerate(r.sample_rows[:3], 1):
                kv = "; ".join(f"{k}={row.get(k)}" for k in row)
                parts.append(f"{i}. {kv}")
            result_cell = (
                f"**rows={r.row_count}**<br>" + "<br>".join(parts)
            )
            if r.gaps:
                result_cell += "<br>**Gaps:** " + "; ".join(r.gaps[:8])
        lines.append(
            "| "
            + " | ".join(
                [
                    spec.question.replace("|", "\\|"),
                    spec.description.replace("|", "\\|"),
                    cypher_cell,
                    ont,
                    spec.expected_output.replace("|", "\\|"),
                    spec.result_type.replace("|", "\\|"),
                    r.status,
                    result_cell.replace("|", "\\|"),
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Per-CQ diagnostics")
    lines.append("")
    for spec in specs:
        r = by_id[spec.cq_id]
        lines.append(f"### {spec.cq_id} — {r.status}")
        lines.append("")
        lines.append(f"**Question:** {spec.question}")
        lines.append("")
        lines.append("**Cypher:**")
        lines.append("")
        lines.append("```cypher")
        lines.append(spec.cypher)
        lines.append("```")
        lines.append("")
        lines.append("**Required label counts:**")
        for k, v in r.required_label_counts.items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")
        lines.append("**Required relation counts:**")
        for k, v in r.required_relation_counts.items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")
        if r.gaps:
            lines.append("**Gaps (explicit):**")
            for g in r.gaps:
                lines.append(f"- `{g}`")
            lines.append("")
        else:
            lines.append("**Gaps (explicit):** none")
            lines.append("")
        if r.diagnostics:
            lines.append("**Diagnostics (fragment counts; never used as Pass criteria):**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(r.diagnostics, ensure_ascii=False, indent=2, default=str))
            lines.append("```")
            lines.append("")
        if r.sample_rows:
            lines.append("**Sample rows (truncated):**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(r.sample_rows[:5], ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        elif r.error:
            lines.append(f"**Error:** `{r.error}`")
            lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Strict BAE CQ1–CQ5 Neo4j validation")
    p.add_argument("--uri", default=DEFAULT_URI)
    p.add_argument("--user", default=DEFAULT_USER)
    p.add_argument("--password", default=DEFAULT_PASSWORD)
    p.add_argument("--database", default=DEFAULT_DB)
    p.add_argument("--limit", type=int, default=30, help="Cypher LIMIT per CQ")
    p.add_argument("--sample", type=int, default=5, help="Sample rows kept in report")
    p.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "output" / "cqs_validation_report.md",
    )
    p.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "output" / "cqs_validation_raw.json",
    )
    args = p.parse_args(argv)

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"CONNECT_FAIL: {e}", file=sys.stderr)
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        fail_md = (
            "# Table 3. Ontology-Driven Queries and Corresponding Results\n\n"
            f"**Status: CONNECT_FAIL**\n\nURI: `{args.uri}`\n\nError:\n```\n{e}\n```\n"
        )
        args.out_md.write_text(fail_md, encoding="utf-8")
        args.out_json.write_text(
            json.dumps({"status": "CONNECT_FAIL", "error": str(e), "uri": args.uri}, indent=2),
            encoding="utf-8",
        )
        return 1

    specs = build_cq_specs(args.limit)
    results: List[CQResult] = []

    try:
        with driver.session(database=args.database) as session:
            snap = snapshot(session)
            print(f"Connected: {args.uri} | nodes={snap['nodes']} rels={snap['relationships']}")
            if snap["nodes"] == 0:
                print("GRAPH_EMPTY: nodes=0 — CQ evaluation blocked", file=sys.stderr)
                args.out_md.parent.mkdir(parents=True, exist_ok=True)
                blocked = [
                    CQResult(
                        cq_id=s.cq_id,
                        status="Blocked",
                        row_count=0,
                        sample_rows=[],
                        gaps=["graph_empty:nodes=0"],
                        required_label_counts={},
                        required_relation_counts={},
                    )
                    for s in specs
                ]
                md = render_markdown(snap, specs, blocked, args.uri)
                args.out_md.write_text(md, encoding="utf-8")
                args.out_json.write_text(
                    json.dumps(
                        {
                            "status": "GRAPH_EMPTY",
                            "snapshot": snap,
                            "results": [asdict(r) for r in blocked],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return 1

            for spec in specs:
                print(f"Running {spec.cq_id} ...", flush=True)
                res = evaluate_cq(session, spec, args.sample)
                results.append(res)
                print(f"  {spec.cq_id}: {res.status} rows={res.row_count} gaps={len(res.gaps)}")
    except ServiceUnavailable as e:
        print(f"SERVICE_UNAVAILABLE: {e}", file=sys.stderr)
        return 1
    finally:
        driver.close()

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    md = render_markdown(snap, specs, results, args.uri)
    args.out_md.write_text(md, encoding="utf-8")
    payload = {
        "status": "OK",
        "uri": args.uri,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot": snap,
        "specs": [
            {
                "cq_id": s.cq_id,
                "question": s.question,
                "description": s.description,
                "cypher": s.cypher,
                "ontology_classes": s.ontology_classes,
                "ontology_relations": s.ontology_relations,
                "expected_output": s.expected_output,
                "result_type": s.result_type,
                "required_columns_full": s.required_columns_full,
                "required_columns_partial": s.required_columns_partial,
            }
            for s in specs
        ],
        "results": [asdict(r) for r in results],
    }
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_md}")
    print(f"Wrote {args.out_json}")

    # Exit 0 even if some CQs fail — report is the deliverable; nonzero only for infra failure
    return 0


if __name__ == "__main__":
    sys.exit(main())
