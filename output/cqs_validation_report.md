# Table 3. Ontology-Driven Queries and Corresponding Results

- Generated (UTC): `2026-08-04T06:35:52.217653+00:00`
- Neo4j URI: `bolt://localhost:7687`
- Graph size: **10570** nodes, **24928** relationships
- Evaluation policy: **strict** (no silent fallbacks; gaps listed explicitly)

## Summary

| CQ | Status | Rows | Critical gaps |
|----|--------|------|---------------|
| CQ1 | Not supported | 0 | diagnostic_zero:full_cq1_chain_count; zero_result_rows:ontology_path_uninstantiated |
| CQ2 | Not supported | 0 | diagnostic_zero:full_cq2_chain_count; zero_result_rows:ontology_path_uninstantiated |
| CQ3 | Not supported | 0 | diagnostic_zero:full_cq3_chain_count; zero_result_rows:ontology_path_uninstantiated; join_break:no_connected_SE_to_SG_to_Claim_with_SE_parts;fragments={'full_cq3_chain_count': {'c': 0}} |
| CQ4 | Not supported | 0 | diagnostic_zero:plan_step_with_both_IO; zero_result_rows:ontology_path_uninstantiated |
| CQ5 | Fully supported | 30 | — |

## Root-cause findings (strict; no fallback paths credited)

- **CQ1 Not supported:** `whu_BioChemicalStep` instances linked to `whu_Bio_chemical_Experiment` via `p_plan_isStepOfPlan` and those with `p_plan_hasInputVar`→Specimen/ProcessedSpecimen are **disjoint** (intersection = 0). Fragments exist but the ontology join required by CQ1 is empty.
- **CQ2 Not supported:** Steps with `p_plan_hasOutputVar`→`whu_DataSet` and steps with `p_plan_isStepOfPlan`→Plan are **disjoint** (intersection = 0). Data generation cannot be attributed to an experiment plan along the required path.
- **CQ3 Not supported:** Paper chain `ScienceEvidence → supports/challenges → SupportGraph → supports/challenges → Claim|Statement` with `SE -hasPart→ DataSet|Method` has **zero** instantiations. Fragment counts show SE→SG, SG→Claim, SE–hasPart–DataSet/Method exist separately but do not form one connected evidence unit. `DataSet → supports → Claim` shortcuts exist and are reported only as diagnostics, **not** as CQ3 Pass.
- **CQ4:** Requires plan→step with **both** `hasInputVar` and `hasOutputVar` on the same step (no OPTIONAL). Empty result means IO is missing on plan-linked steps.
- **CQ5:** Requires MetaPath→entity→Chunk→Document with non-null original text (all MATCH; no OPTIONAL provenance).

## Graph snapshot (top labels / relations)

| Label | Count |
|-------|------:|
| `__KGBuilder__` | 8563 |
| `__Entity__` | 8137 |
| `MetaPath` | 2007 |
| `mp_References` | 1850 |
| `mp_Statement` | 1436 |
| `whu_DataSet` | 1103 |
| `mp_Claim` | 850 |
| `mp_Attribution` | 595 |
| `whu_BioChemicalStep` | 386 |
| `whu_Method` | 336 |
| `Document` | 231 |
| `whu_SupportGraph` | 231 |
| `whu_Specimen_ProcessingStep` | 228 |
| `whu_ScalarMeasurementDatum` | 219 |
| `Chunk` | 195 |
| `whu_ScienceEvidence` | 159 |
| `whu_ProcessedSpecimen` | 106 |
| `whu_ComputationalStep` | 86 |
| `whu_Device` | 81 |
| `whu_Computational_Experiment` | 74 |

| Relation | Count |
|----------|------:|
| `FROM_CHUNK` | 8143 |
| `detailOf` | 4432 |
| `hasDetailPath` | 4432 |
| `metaPathRelation` | 3838 |
| `FROM_DOCUMENT` | 1720 |
| `mp_supports` | 743 |
| `cito_isCitedBy` | 390 |
| `whu_hasPart` | 252 |
| `NEXT_CHUNK` | 192 |
| `whu_declareUsed` | 172 |
| `dcterms_hasPart` | 104 |
| `p_plan_isStepOfPlan` | 79 |
| `iao_is_about` | 79 |
| `p_plan_hasOutputVar` | 73 |
| `prov_wasDerivedFrom` | 64 |
| `p_plan_isPrecededBy` | 57 |
| `mp_challenges` | 49 |
| `p_plan_hasInputVar` | 44 |
| `whu_fellow` | 26 |
| `whu_hasContext` | 16 |

## Detailed CQ table

| Competency Question | Query Description | Cypher Query | Ontology Elements Used | Expected Output | Result Type | Status | Result |
|---|---|---|---|---|---|---|---|
| CQ1. Which environment, collection process, and preprocessing process does an experiment’s input specimen originate from? | Follows the EBM chain from a biochemical experiment input (ProcessedSpecimen) back through preprocessing and collection to EnvironmentFeature. All edges are required MATCH. | <pre>MATCH (exp:whu_Bio_chemical_Experiment)<-[:p_plan_isStepOfPlan]-(bio:whu_BioChemicalStep)
MATCH (bio)-[:p_plan_hasInputVar]->(ps:whu_ProcessedSpecimen)
MATCH (pstep:whu_Specimen_ProcessingStep)-[:p_plan_hasOutputVar]->(ps)
MATCH (pstep)-[:p_plan_isStepOfPlan]->(prep:whu_SpecimenPreprocessing)
MATCH (pstep)-[:p_plan_hasInputVar]->(spec:whu_Specimen)
MATCH (cstep:whu_Specimen_CollectionStep)-[:p_plan_hasOutputVar]->(spec)
MATCH (cstep)-[:p_plan_isStepOfPlan]->(coll:whu_SpecimenCollection)
MATCH (coll)-[:whu_hasContext]->(env:whu_EnvironmentFeature)
RETURN
  exp.WHU_HASNAME AS Experiment,
  ps.WHU_HASNAME AS ProcessedSpecimen,
  spec.WHU_HASNAME AS Specimen,
  env.WHU_HASNAME AS Environment,
  coll.WHU_HASNAME AS CollectionPlan,
  cstep.WHU_HASNAME AS CollectionStep,
  prep.WHU_HASNAME AS PreprocessingPlan,
  pstep.WHU_HASNAME AS PreprocessingStep
ORDER BY Experiment, ProcessedSpecimen
LIMIT 30</pre> | Classes: `whu_Bio_chemical_Experiment`, `whu_BioChemicalStep`, `whu_ProcessedSpecimen`, `whu_Specimen`, `whu_EnvironmentFeature`, `whu_SpecimenCollection`, `whu_SpecimenPreprocessing`, `whu_Specimen_CollectionStep`, `whu_Specimen_ProcessingStep`<br>Relationships: `p_plan_isStepOfPlan`, `p_plan_hasInputVar`, `p_plan_hasOutputVar`, `whu_hasContext` | Experiment input specimens with environment, collection plan/step, and preprocessing plan/step. | Experiment, ProcessedSpecimen, Specimen, Environment, CollectionPlan, CollectionStep, PreprocessingPlan, PreprocessingStep | Not supported | _empty_ (Not supported) |
| CQ2. Which experiments, research steps, methods, and supporting resources generated a given data object? | Binds each DataSet to its producing research step, parent experiment, and a declared resource (Method/Device/Reagent/Software). All edges required. | <pre>MATCH (step)-[:p_plan_hasOutputVar]->(ds:whu_DataSet)
WHERE step:whu_BioChemicalStep OR step:whu_ComputationalStep
MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
WHERE plan:whu_Bio_chemical_Experiment OR plan:whu_Computational_Experiment
MATCH (step)-[:whu_declareUsed]->(resource)
WHERE resource:whu_Method
   OR resource:whu_Device
   OR resource:whu_Reagent
   OR resource:whu_Software
RETURN
  ds.WHU_HASNAME AS DataSet,
  [x IN labels(plan) WHERE NOT x STARTS WITH '__'][0] AS PlanType,
  plan.WHU_HASNAME AS Experiment,
  [x IN labels(step) WHERE NOT x STARTS WITH '__'][0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  [x IN labels(resource) WHERE NOT x STARTS WITH '__'][0] AS ResourceType,
  resource.WHU_HASNAME AS Resource
ORDER BY DataSet, ResearchStep, ResourceType
LIMIT 30</pre> | Classes: `whu_DataSet`, `whu_BioChemicalStep`, `whu_ComputationalStep`, `whu_Bio_chemical_Experiment`, `whu_Computational_Experiment`, `whu_Method`, `whu_Device`, `whu_Reagent`, `whu_Software`<br>Relationships: `p_plan_hasOutputVar`, `p_plan_isStepOfPlan`, `whu_declareUsed` | Datasets with generating experiment, research step, and declared resources. | DataSet, Experiment, ResearchStep, ResourceType, Resource | Not supported | _empty_ (Not supported) |
| CQ3. Which datasets, methods, and research steps jointly constitute ScienceEvidence that supports or challenges a Statement or Claim? | MPU chain with required edges only: ScienceEvidence -supports/challenges-> SupportGraph -supports/challenges-> Claim\|Statement; ScienceEvidence -hasPart-> DataSet and Method; DataSet <-hasOutputVar- ResearchStep. | <pre>MATCH (se:whu_ScienceEvidence)-[r1:mp_supports\|mp_challenges]->(sg:whu_SupportGraph)
MATCH (sg)-[r2:mp_supports\|mp_challenges]->(target)
WHERE target:mp_Claim OR target:mp_Statement
MATCH (se)-[:whu_hasPart]->(ds:whu_DataSet)
MATCH (se)-[:whu_hasPart]->(m:whu_Method)
MATCH (step)-[:p_plan_hasOutputVar]->(ds)
WHERE step:whu_BioChemicalStep OR step:whu_ComputationalStep
RETURN
  [x IN labels(target) WHERE NOT x STARTS WITH '__'][0] AS TargetType,
  target.WHU_HASNAME AS Target,
  type(r1) AS EvidenceToGraph,
  type(r2) AS GraphToTarget,
  se.WHU_HASNAME AS ScienceEvidence,
  sg.WHU_HASNAME AS SupportGraph,
  ds.WHU_HASNAME AS DataSet,
  m.WHU_HASNAME AS Method,
  step.WHU_HASNAME AS ResearchStep
ORDER BY Target, ScienceEvidence
LIMIT 30</pre> | Classes: `mp_Claim`, `mp_Statement`, `whu_ScienceEvidence`, `whu_SupportGraph`, `whu_DataSet`, `whu_Method`, `whu_BioChemicalStep`, `whu_ComputationalStep`<br>Relationships: `mp_supports`, `mp_challenges`, `whu_hasPart`, `p_plan_hasOutputVar` | Claims/Statements with ScienceEvidence composition (DataSet, Method), SupportGraph polarity, and producing research steps. | Target, EvidenceToGraph, GraphToTarget, ScienceEvidence, SupportGraph, DataSet, Method, ResearchStep | Not supported | _empty_ (Not supported) |
| CQ4. Which fine-grained research steps, inputs/outputs, and evidence elements constitute a mid-level research process? | Expands a mid-level plan/experiment into research steps that must have both a typed input and a typed output. No OPTIONAL MATCH. | <pre>MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
WHERE plan:whu_SpecimenCollection
   OR plan:whu_SpecimenPreprocessing
   OR plan:whu_Bio_chemical_Experiment
   OR plan:whu_Computational_Experiment
MATCH (step)-[:p_plan_hasInputVar]->(inp)
MATCH (step)-[:p_plan_hasOutputVar]->(out)
RETURN
  [x IN labels(plan) WHERE NOT x STARTS WITH '__'][0] AS MidPlanType,
  plan.WHU_HASNAME AS MidPlan,
  [x IN labels(step) WHERE NOT x STARTS WITH '__'][0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  [x IN labels(inp) WHERE NOT x STARTS WITH '__'][0] AS InputType,
  inp.WHU_HASNAME AS Input,
  [x IN labels(out) WHERE NOT x STARTS WITH '__'][0] AS OutputType,
  out.WHU_HASNAME AS Output
ORDER BY MidPlanType, MidPlan, ResearchStep
LIMIT 30</pre> | Classes: `whu_SpecimenCollection`, `whu_SpecimenPreprocessing`, `whu_Bio_chemical_Experiment`, `whu_Computational_Experiment`, `whu_Specimen_CollectionStep`, `whu_Specimen_ProcessingStep`, `whu_BioChemicalStep`, `whu_ComputationalStep`, `whu_Specimen`, `whu_ProcessedSpecimen`, `whu_DataSet`<br>Relationships: `p_plan_isStepOfPlan`, `p_plan_hasInputVar`, `p_plan_hasOutputVar` | Mid-level plans with fine-grained steps and explicit input/output elements. | MidPlan, ResearchStep, InputType, Input, OutputType, Output | Not supported | _empty_ (Not supported) |
| CQ5. Which documents, text chunks, and original text spans correspond to a given evidence MetaPath? | Traces MetaPath members to Chunk and Document with required provenance edges and a non-null original text span. | <pre>MATCH (mp:MetaPath)-[r:metaPathRelation]->(e)
MATCH (e)-[:FROM_CHUNK]->(chunk:Chunk)
MATCH (chunk)-[:FROM_DOCUMENT]->(doc:Document)
WHERE mp.metaPathText IS NOT NULL
  AND e.WHU_HASORIGINALTEXT IS NOT NULL
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
  chunk.source_doc AS SourceDoc,
  doc.path AS DocumentPath,
  doc.document_type AS DocumentType
ORDER BY MetaPathId, Position
LIMIT 30</pre> | Classes: `MetaPath`, `Chunk`, `Document`<br>Relationships: `metaPathRelation`, `FROM_CHUNK`, `FROM_DOCUMENT` | MetaPaths with member entities, original text spans, chunks, and documents. | MetaPathId, Entity, OriginalTextSpan, ChunkFilename, SourceDoc, DocumentPath | Fully supported | **rows=30**<br>1. MetaPathId=EBM_000001; Level=low; Subgraph=EBM; PathText=[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …; Position=1; EntityType=whu_SpecimenCollection; Entity=Rice Sample Collection; OriginalTextSpan=Twenty-six (26) rice samples were analyzed for a total of 36 elements.; ChunkIndex=1; ChunkFilename=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md; SourceDoc=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market; DocumentPath=document.txt; DocumentType=inline_text<br>2. MetaPathId=EBM_000001; Level=low; Subgraph=EBM; PathText=[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …; Position=1; EntityType=whu_SpecimenCollection; Entity=Rice Sample Collection; OriginalTextSpan=Twenty-six (26) rice samples were analyzed for a total of 36 elements.; ChunkIndex=1; ChunkFilename=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md; SourceDoc=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market; DocumentPath=document.txt; DocumentType=inline_text<br>3. MetaPathId=EBM_000001; Level=low; Subgraph=EBM; PathText=[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …; Position=1; EntityType=whu_SpecimenCollection; Entity=Rice Sample Collection; OriginalTextSpan=Twenty-six (26) rice samples were analyzed for a total of 36 elements.; ChunkIndex=1; ChunkFilename=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md; SourceDoc=doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market; DocumentPath=document.txt; DocumentType=inline_text |

## Per-CQ diagnostics

### CQ1 — Not supported

**Question:** CQ1. Which environment, collection process, and preprocessing process does an experiment’s input specimen originate from?

**Cypher:**

```cypher
MATCH (exp:whu_Bio_chemical_Experiment)<-[:p_plan_isStepOfPlan]-(bio:whu_BioChemicalStep)
MATCH (bio)-[:p_plan_hasInputVar]->(ps:whu_ProcessedSpecimen)
MATCH (pstep:whu_Specimen_ProcessingStep)-[:p_plan_hasOutputVar]->(ps)
MATCH (pstep)-[:p_plan_isStepOfPlan]->(prep:whu_SpecimenPreprocessing)
MATCH (pstep)-[:p_plan_hasInputVar]->(spec:whu_Specimen)
MATCH (cstep:whu_Specimen_CollectionStep)-[:p_plan_hasOutputVar]->(spec)
MATCH (cstep)-[:p_plan_isStepOfPlan]->(coll:whu_SpecimenCollection)
MATCH (coll)-[:whu_hasContext]->(env:whu_EnvironmentFeature)
RETURN
  exp.WHU_HASNAME AS Experiment,
  ps.WHU_HASNAME AS ProcessedSpecimen,
  spec.WHU_HASNAME AS Specimen,
  env.WHU_HASNAME AS Environment,
  coll.WHU_HASNAME AS CollectionPlan,
  cstep.WHU_HASNAME AS CollectionStep,
  prep.WHU_HASNAME AS PreprocessingPlan,
  pstep.WHU_HASNAME AS PreprocessingStep
ORDER BY Experiment, ProcessedSpecimen
LIMIT 30
```

**Required label counts:**
- `whu_Bio_chemical_Experiment`: 40
- `whu_BioChemicalStep`: 386
- `whu_ProcessedSpecimen`: 106
- `whu_Specimen`: 62
- `whu_EnvironmentFeature`: 66
- `whu_SpecimenCollection`: 19
- `whu_SpecimenPreprocessing`: 21

**Required relation counts:**
- `p_plan_isStepOfPlan`: 79
- `p_plan_hasInputVar`: 44
- `p_plan_hasOutputVar`: 73
- `whu_hasContext`: 16

**Gaps (explicit):**
- `diagnostic_zero:full_cq1_chain_count`
- `zero_result_rows:ontology_path_uninstantiated`

**Diagnostics (fragment counts; never used as Pass criteria):**

```json
{
  "full_cq1_chain_count": {
    "c": 0
  }
}
```

### CQ2 — Not supported

**Question:** CQ2. Which experiments, research steps, methods, and supporting resources generated a given data object?

**Cypher:**

```cypher
MATCH (step)-[:p_plan_hasOutputVar]->(ds:whu_DataSet)
WHERE step:whu_BioChemicalStep OR step:whu_ComputationalStep
MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
WHERE plan:whu_Bio_chemical_Experiment OR plan:whu_Computational_Experiment
MATCH (step)-[:whu_declareUsed]->(resource)
WHERE resource:whu_Method
   OR resource:whu_Device
   OR resource:whu_Reagent
   OR resource:whu_Software
RETURN
  ds.WHU_HASNAME AS DataSet,
  [x IN labels(plan) WHERE NOT x STARTS WITH '__'][0] AS PlanType,
  plan.WHU_HASNAME AS Experiment,
  [x IN labels(step) WHERE NOT x STARTS WITH '__'][0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  [x IN labels(resource) WHERE NOT x STARTS WITH '__'][0] AS ResourceType,
  resource.WHU_HASNAME AS Resource
ORDER BY DataSet, ResearchStep, ResourceType
LIMIT 30
```

**Required label counts:**
- `whu_DataSet`: 1103
- `whu_Method`: 336

**Required relation counts:**
- `p_plan_hasOutputVar`: 73
- `p_plan_isStepOfPlan`: 79
- `whu_declareUsed`: 172

**Gaps (explicit):**
- `diagnostic_zero:full_cq2_chain_count`
- `zero_result_rows:ontology_path_uninstantiated`

**Diagnostics (fragment counts; never used as Pass criteria):**

```json
{
  "full_cq2_chain_count": {
    "c": 0
  }
}
```

### CQ3 — Not supported

**Question:** CQ3. Which datasets, methods, and research steps jointly constitute ScienceEvidence that supports or challenges a Statement or Claim?

**Cypher:**

```cypher
MATCH (se:whu_ScienceEvidence)-[r1:mp_supports|mp_challenges]->(sg:whu_SupportGraph)
MATCH (sg)-[r2:mp_supports|mp_challenges]->(target)
WHERE target:mp_Claim OR target:mp_Statement
MATCH (se)-[:whu_hasPart]->(ds:whu_DataSet)
MATCH (se)-[:whu_hasPart]->(m:whu_Method)
MATCH (step)-[:p_plan_hasOutputVar]->(ds)
WHERE step:whu_BioChemicalStep OR step:whu_ComputationalStep
RETURN
  [x IN labels(target) WHERE NOT x STARTS WITH '__'][0] AS TargetType,
  target.WHU_HASNAME AS Target,
  type(r1) AS EvidenceToGraph,
  type(r2) AS GraphToTarget,
  se.WHU_HASNAME AS ScienceEvidence,
  sg.WHU_HASNAME AS SupportGraph,
  ds.WHU_HASNAME AS DataSet,
  m.WHU_HASNAME AS Method,
  step.WHU_HASNAME AS ResearchStep
ORDER BY Target, ScienceEvidence
LIMIT 30
```

**Required label counts:**
- `mp_Claim`: 850
- `mp_Statement`: 1436
- `whu_ScienceEvidence`: 159
- `whu_SupportGraph`: 231

**Required relation counts:**
- `mp_supports`: 743
- `mp_challenges`: 49
- `whu_hasPart`: 252

**Gaps (explicit):**
- `diagnostic_zero:full_cq3_chain_count`
- `zero_result_rows:ontology_path_uninstantiated`
- `join_break:no_connected_SE_to_SG_to_Claim_with_SE_parts;fragments={'full_cq3_chain_count': {'c': 0}}`

**Diagnostics (fragment counts; never used as Pass criteria):**

```json
{
  "full_cq3_chain_count": {
    "c": 0
  }
}
```

### CQ4 — Not supported

**Question:** CQ4. Which fine-grained research steps, inputs/outputs, and evidence elements constitute a mid-level research process?

**Cypher:**

```cypher
MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
WHERE plan:whu_SpecimenCollection
   OR plan:whu_SpecimenPreprocessing
   OR plan:whu_Bio_chemical_Experiment
   OR plan:whu_Computational_Experiment
MATCH (step)-[:p_plan_hasInputVar]->(inp)
MATCH (step)-[:p_plan_hasOutputVar]->(out)
RETURN
  [x IN labels(plan) WHERE NOT x STARTS WITH '__'][0] AS MidPlanType,
  plan.WHU_HASNAME AS MidPlan,
  [x IN labels(step) WHERE NOT x STARTS WITH '__'][0] AS StepType,
  step.WHU_HASNAME AS ResearchStep,
  [x IN labels(inp) WHERE NOT x STARTS WITH '__'][0] AS InputType,
  inp.WHU_HASNAME AS Input,
  [x IN labels(out) WHERE NOT x STARTS WITH '__'][0] AS OutputType,
  out.WHU_HASNAME AS Output
ORDER BY MidPlanType, MidPlan, ResearchStep
LIMIT 30
```

**Required label counts:**
- `whu_Bio_chemical_Experiment`: 40
- `whu_Computational_Experiment`: 74

**Required relation counts:**
- `p_plan_isStepOfPlan`: 79
- `p_plan_hasInputVar`: 44
- `p_plan_hasOutputVar`: 73

**Gaps (explicit):**
- `diagnostic_zero:plan_step_with_both_IO`
- `zero_result_rows:ontology_path_uninstantiated`

**Diagnostics (fragment counts; never used as Pass criteria):**

```json
{
  "plan_step_with_both_IO": {
    "c": 0
  }
}
```

### CQ5 — Fully supported

**Question:** CQ5. Which documents, text chunks, and original text spans correspond to a given evidence MetaPath?

**Cypher:**

```cypher
MATCH (mp:MetaPath)-[r:metaPathRelation]->(e)
MATCH (e)-[:FROM_CHUNK]->(chunk:Chunk)
MATCH (chunk)-[:FROM_DOCUMENT]->(doc:Document)
WHERE mp.metaPathText IS NOT NULL
  AND e.WHU_HASORIGINALTEXT IS NOT NULL
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
  chunk.source_doc AS SourceDoc,
  doc.path AS DocumentPath,
  doc.document_type AS DocumentType
ORDER BY MetaPathId, Position
LIMIT 30
```

**Required label counts:**
- `MetaPath`: 2007
- `Chunk`: 195
- `Document`: 231

**Required relation counts:**
- `metaPathRelation`: 3838
- `FROM_CHUNK`: 8143
- `FROM_DOCUMENT`: 1720

**Gaps (explicit):** none

**Diagnostics (fragment counts; never used as Pass criteria):**

```json
{
  "full_cq5_chain_count": {
    "c": 86635
  },
  "cq5_chunk_coverage_in_rows": "30/30",
  "cq5_document_coverage_in_rows": "30/30"
}
```

**Sample rows (truncated):**

```json
[
  {
    "MetaPathId": "EBM_000001",
    "Level": "low",
    "Subgraph": "EBM",
    "PathText": "[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …",
    "Position": "1",
    "EntityType": "whu_SpecimenCollection",
    "Entity": "Rice Sample Collection",
    "OriginalTextSpan": "Twenty-six (26) rice samples were analyzed for a total of 36 elements.",
    "ChunkIndex": "1",
    "ChunkFilename": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md",
    "SourceDoc": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market",
    "DocumentPath": "document.txt",
    "DocumentType": "inline_text"
  },
  {
    "MetaPathId": "EBM_000001",
    "Level": "low",
    "Subgraph": "EBM",
    "PathText": "[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …",
    "Position": "1",
    "EntityType": "whu_SpecimenCollection",
    "Entity": "Rice Sample Collection",
    "OriginalTextSpan": "Twenty-six (26) rice samples were analyzed for a total of 36 elements.",
    "ChunkIndex": "1",
    "ChunkFilename": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md",
    "SourceDoc": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market",
    "DocumentPath": "document.txt",
    "DocumentType": "inline_text"
  },
  {
    "MetaPathId": "EBM_000001",
    "Level": "low",
    "Subgraph": "EBM",
    "PathText": "[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …",
    "Position": "1",
    "EntityType": "whu_SpecimenCollection",
    "Entity": "Rice Sample Collection",
    "OriginalTextSpan": "Twenty-six (26) rice samples were analyzed for a total of 36 elements.",
    "ChunkIndex": "1",
    "ChunkFilename": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md",
    "SourceDoc": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market",
    "DocumentPath": "document.txt",
    "DocumentType": "inline_text"
  },
  {
    "MetaPathId": "EBM_000001",
    "Level": "low",
    "Subgraph": "EBM",
    "PathText": "[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …",
    "Position": "1",
    "EntityType": "whu_SpecimenCollection",
    "Entity": "Rice Sample Collection",
    "OriginalTextSpan": "Twenty-six (26) rice samples were analyzed for a total of 36 elements.",
    "ChunkIndex": "1",
    "ChunkFilename": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md",
    "SourceDoc": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market",
    "DocumentPath": "document.txt",
    "DocumentType": "inline_text"
  },
  {
    "MetaPathId": "EBM_000001",
    "Level": "low",
    "Subgraph": "EBM",
    "PathText": "[whu_SpecimenCollection: Rice Sample Collection] Twenty-six (26) rice samples were analyzed for a total of 36 elements. -[whu_hasContext] Twenty-six (26) rice …",
    "Position": "1",
    "EntityType": "whu_SpecimenCollection",
    "Entity": "Rice Sample Collection",
    "OriginalTextSpan": "Twenty-six (26) rice samples were analyzed for a total of 36 elements.",
    "ChunkIndex": "1",
    "ChunkFilename": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market.md",
    "SourceDoc": "doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market",
    "DocumentPath": "document.txt",
    "DocumentType": "inline_text"
  }
]
```
