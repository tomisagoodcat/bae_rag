# BAE_v3_clean Schema Alignment Report

## 1. Alignment policy

Authoritative execution schema:
- `entity(3).json`
- `relation(3).json`
- `potential_schema(2).json`

Alignment rules applied:
1. Schema JSON is the source of truth.
2. Existing TTL content that is not in conflict with the schema is preserved.
3. Existing extra TTL attributes/anchors/comments are not removed merely because they are absent from the JSON.
4. `whu:prompt` on entity classes and object properties is synchronized to the corresponding JSON `description`.
5. No extraction-pattern meta-model or additional operational ontology layer is introduced.

`subgraph_mapping(2).json` was inspected as an operational routing/mapping file, but it was not used to add/remove ontology axioms because the requested source-of-truth schema consists of entity/relation/potential-schema definitions.

## 2. Entity prompt synchronization

26 schema entities were checked.

### Updated entity prompts (24)

- mp_Attribution
- mp_References
- whu_Computational_Experiment
- envo_EnvironmentMaterial
- whu_Reagent
- iao_ScalarMeasurementDatum
- whu_Software
- whu_TargetVariable
- mp_Claim
- whu_Goal
- mp_Statement
- whu_BioChemical_Experiment
- whu_Device
- whu_EnvironmentFeature
- mp_Method
- whu_ProcessedSpecimen
- whu_DataSet
- whu_Specimen
- whu_ScienceEvidence
- whu_ResearchStep
- obi_organism
- whu_ChemicalEntity
- whu_SupportGraph
- iao_DataItem

### Already aligned; unchanged (2)

- whu_SpecimenCollection
- whu_SpecimenPreprocessing

Important semantic updates now reflected in TTL prompts include:
- stricter EnvironmentFeature / EnvironmentMaterial / Specimen / organism discrimination;
- lexical grounding for TargetVariable;
- no-orphan rules for Experiment, Goal, ResearchStep, ScienceEvidence and SupportGraph;
- explicit mid-level / low-level extraction tier guidance;
- revised ScienceEvidence–SupportGraph semantics.

## 3. Relation prompt synchronization

21 schema relations were checked.

### Updated relation prompts (16)

- mp_supports
- whu_declaredUsed
- prov_atLocation
- cito_isCitedBy
- whu_hasGoal
- whu_fellow
- whu_hasTarget
- prov_wasDerivedFrom
- mp_challenges
- iao_is_about
- p_plan_isStepOfPlan
- prov_hadMember
- bfo_has_part
- whu_declaredInput
- whu_declaredOutput
- whu_hasContext

### Already aligned; unchanged (5)

- p_plan_correspondsToStep
- p_plan_isPrecededBy
- p_plan_isInputVarOf
- p_plan_isOutputVarOf
- dcterms_hasPart

## 4. Structural RDF conflict corrected

The current `potential_schema(2).json` explicitly permits:

`whu_ScienceEvidence -> prov_wasDerivedFrom -> whu_Computational_Experiment`

The original TTL's `prov:wasDerivedFrom` domain/range did not permit that signature.

### Before

```turtle
rdfs:domain [ a owl:Class ;
    owl:unionOf ( whu:Specimen whu:ProcessedSpecimen ) ] ;

rdfs:range [ a owl:Class ;
    owl:unionOf (
        whu:EnvironmentFeature
        envo:00010483
        obi:0100026
        whu:Specimen
    ) ] ;
```

### After

```turtle
rdfs:domain [ a owl:Class ;
    owl:unionOf (
        whu:Specimen
        whu:ProcessedSpecimen
        whu:ScienceEvidence
    ) ] ;

rdfs:range [ a owl:Class ;
    owl:unionOf (
        whu:EnvironmentFeature
        envo:00010483
        obi:0100026
        whu:Specimen
        whu:ComputationalExperiment
    ) ] ;
```

No other object-property domain/range declaration was found to exclude a currently allowed potential-schema signature.

## 5. SupportGraph membership conflict resolved through prompt alignment

The old TTL prompt for `prov:hadMember` allowed:

`SupportGraph -> prov_hadMember -> ScienceEvidence`

The current relation schema explicitly forbids that pattern and the current potential schema no longer includes it.

The aligned TTL therefore now states:
- SupportGraph membership: Claim / Statement / Attribution / Reference;
- ScienceEvidence connects to SupportGraph only using `mp:supports` / `mp:challenges` (never directly to Claim);
- SupportGraph connects to focal Claim using `mp:supports` / `mp:challenges`;
- no `SupportGraph -> prov:hadMember -> ScienceEvidence`.

There was no explicit OWL restriction in the original TTL requiring SupportGraph to contain ScienceEvidence, so no structural axiom needed deletion.

## 6. Datatype-property prompt alignment

Two global datatype-property prompts were updated:

- `whu:hasName`: synchronized to the common/default `WHU_HASNAME` rule, including the new “no semantic expansion” constraint.
- `whu:researchType`: synchronized to the revised `WHU_RESEARCHTYPE` description.

`whu:hasOriginalText` already matched the common/base rule and was not semantically changed.

The JSON contains class-specific variants of `WHU_HASNAME` and `WHU_HASORIGINALTEXT` (for example TargetVariable and mid-/low-level span rules). Because the TTL represents these as one global datatype property, those class-specific constraints are retained in each entity's class-level `whu:prompt`; no new property or SHACL structure was introduced during this alignment.

## 7. Content deliberately left unchanged

To comply with “only modify conflicts”:
- class hierarchy was not rewritten;
- existing BFO / IAO / PROV / P-PLAN / MP anchors were retained;
- labels and comments not conflicting with the schema were retained;
- additional TTL attributes absent from the JSON were retained;
- existing OWL restrictions for ScienceEvidence and SupportGraph were retained;
- no new extraction-schema individuals or TriplePattern structures were created;
- `mid` / `low` / `mid2low` routing tags from `potential_schema` were not converted into new RDF ontology properties.

## 8. Validation

- RDFLib Turtle parse: **PASS**
- Final RDF triples: **549**
- Entity `whu:prompt` exact match to entity JSON `description`: **26/26**
- Relation `whu:prompt` exact match to relation JSON `description`: **21/21**
- Potential-schema structural conflict checked: `ScienceEvidence -> prov:wasDerivedFrom -> ComputationalExperiment` is now compatible with the TTL domain/range.
