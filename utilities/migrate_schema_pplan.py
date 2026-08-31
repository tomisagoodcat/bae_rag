"""
One-shot migration: P-Plan / whu_fellow schema (entity, relation, potential_schema, subgraph_mapping).
Run: python utilities/migrate_schema_pplan.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

LABEL_RENAMES = {
    "whu_Specimen_Collection_Activity": "whu_Specimen_CollectionStep",
    "whu_Specimen_Processing_Activity": "whu_Specimen_ProcessingStep",
    "whu_BioChemicalActivityStep": "whu_BioChemicalStep",
    "whu_ComputationalActivityStep": "whu_ComputationalStep",
}

TEXT_REPLACEMENTS = [
    ("whu_Specimen_Collection_Activity", "whu_Specimen_CollectionStep"),
    ("whu_Specimen_Processing_Activity", "whu_Specimen_ProcessingStep"),
    ("whu_BioChemicalActivityStep", "whu_BioChemicalStep"),
    ("whu_ComputationalActivityStep", "whu_ComputationalStep"),
    ("SpecimenCollectionActivity", "SpecimenCollectionStep"),
    ("SpecimenProcessingActivity", "SpecimenProcessingStep"),
    ("BioChemicalActivityStep", "BioChemicalStep"),
    ("ComputationalActivityStep", "ComputationalStep"),
    ("whu:ActivityStep", "p-plan:Step"),
    ("whu:hasActivity", "p_plan_isStepOfPlan"),
    ("whu_hasActivity", "p_plan_isStepOfPlan"),
    ("prov:used", "whu_declareUsed (for resources) or p_plan_hasInputVar (for variables)"),
    ("prov:generated", "p_plan_hasOutputVar"),
    ("prov:wasInformedBy", "p_plan_isPrecededBy"),
    ("prov:atLocation", "whu_atLocation"),
]

STEP_DESCRIPTIONS = {
    "whu_Specimen_CollectionStep": """### Define
A **p-plan:Step** subclass: the minimal atomic act of **specimen collection** (grab sampling, coring, harvest, water sampling).

### Semantic links (extract in the same pass when triggered)
- `p_plan_isStepOfPlan` → `whu_SpecimenCollection` (this step belongs to the collection plan)
- `p_plan_isPrecededBy` → prior `whu_Specimen_CollectionStep` only when text describes ordered sub-steps (**different instances**, never self)
- `whu_atLocation` → `whu_EnvironmentFeature` (where sampling was performed)
- `whu_declareUsed` → `whu_Method`, `whu_Device`, `envo_Material` (protocol/instrument/matrix declared as used)
- `p_plan_hasOutputVar` → `whu_Specimen` (specimen produced)

### Context
Extract when the text describes an explicit sampling/collection action. Do NOT extract for vague mentions without a concrete collection act.

### Do NOT
Use `prov:used`, `prov:generated`, `prov:wasInformedBy`, `prov:atLocation`, or `whu_hasActivity` on this class.

### Examples
- "Surface water was sampled using a Van Dorn sampler at Site A." → CollectionStep + atLocation + hasOutputVar(Specimen)
- "Soil was collected from the plough layer (0–20 cm)." → CollectionStep + hasOutputVar(Specimen)""",
    "whu_Specimen_ProcessingStep": """### Define
A **p-plan:Step** subclass: the minimal atomic act of **post-collection specimen handling** (drying, grinding, sieving, filtration, preservation).

### Semantic links
- `p_plan_isStepOfPlan` → `whu_SpecimenPreprocessing`
- `p_plan_isPrecededBy` → prior `whu_Specimen_ProcessingStep` or `whu_Specimen_CollectionStep` (distinct instances)
- `whu_declareUsed` → `whu_Method`, `whu_Device`, `envo_Material`
- `p_plan_hasInputVar` → `whu_Specimen`
- `p_plan_hasOutputVar` → `whu_ProcessedSpecimen`

### Context
Extract for explicit post-collection handling operations. Atomic: one processing operation per step node.

### Do NOT
Use PROV `used`/`generated` or `whu_hasActivity`.

### Examples
- "Soils were air-dried and passed through a 2 mm sieve." → ProcessingStep + hasInputVar(Specimen) + hasOutputVar(ProcessedSpecimen)""",
    "whu_BioChemicalStep": """### Define
A **p-plan:Step** subclass: the minimal atomic **wet-lab / biochemical** operation (digestion, extraction, instrumental measurement producing data or processed material).

### Semantic links
- `p_plan_isStepOfPlan` → `whu_Bio_chemical_Experiment`
- `p_plan_isPrecededBy` → prior `whu_BioChemicalStep` or `whu_Specimen_ProcessingStep` (distinct instances)
- `whu_declareUsed` → `whu_Method`, `whu_Device`, `whu_Reagent`, `whu_DataSet` (when cited)
- `p_plan_hasInputVar` → `whu_ProcessedSpecimen`, `whu_DataSet`
- `p_plan_hasOutputVar` → `whu_DataSet`, `whu_ProcessedSpecimen`

### Context
Extract for explicit laboratory/analytical actions (ICP-MS, digestion, chromatography, etc.).

### Do NOT
Use `prov:used`, `prov:generated`, `prov:wasInformedBy`, or `whu_hasActivity`.

### Examples
- "Soil was digested with aqua regia and analyzed by ICP-MS." → BioChemicalStep + declareUsed(Method) + hasOutputVar(DataSet)""",
    "whu_ComputationalStep": """### Define
A **p-plan:Step** subclass: the minimal atomic **computational** operation (statistics, transformation, modeling) in software.

### Semantic links
- `p_plan_isStepOfPlan` → `whu_Computational_Experiment`
- `p_plan_isPrecededBy` → prior `whu_ComputationalStep` or `whu_BioChemicalStep` (distinct instances)
- `whu_declareUsed` → `whu_Method`, `whu_Software`, `whu_DataSet` (**include external datasets** used as input)
- `p_plan_hasInputVar` → `whu_DataSet`
- `p_plan_hasOutputVar` → `whu_DataSet`

### Context
Extract for explicit computational actions (ANOVA, PCA, correlation, HQ calculation, etc.).

### Do NOT
Use `prov:used`, `prov:generated`, or `whu_hasActivity`.

### Examples
- "Kruskal-Wallis test was performed in R 4.1.0." → ComputationalStep + declareUsed(Software) + hasOutputVar(DataSet)
- "Analysis used published reference concentrations (Smith 2020)." → ComputationalStep + declareUsed(DataSet)""",
}

PLAN_PATCHES = {
    "whu_SpecimenCollection": (
        "composed of one or more `whu:ActivityStep`",
        "composed of one or more `whu_Specimen_CollectionStep` (`p-plan:Step`)",
    ),
    "whu_SpecimenPreprocessing": (
        "whu:hasActivity",
        "p_plan_isStepOfPlan (via ProcessingStep)",
    ),
}

METHODS_SECTIONS = ["Methods_Materials", "Experiment"]
ALL_SECTIONS = ["All"]
RESULTS_SECTIONS = ["Methods_Materials", "Results", "Experiment"]


def apply_text_replacements(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def migrate_entities(data: dict) -> dict:
    entities = data["entities"]
    by_label = {e["label"]: e for e in entities}

    for old, new in LABEL_RENAMES.items():
        if old in by_label:
            ent = by_label.pop(old)
            ent["label"] = new
            by_label[new] = ent

    for label, desc in STEP_DESCRIPTIONS.items():
        if label in by_label:
            by_label[label]["description"] = desc

    for label, ent in by_label.items():
        if label in STEP_DESCRIPTIONS:
            continue
        desc = ent.get("description", "")
        patch = PLAN_PATCHES.get(label)
        if patch:
            desc = desc.replace(patch[0], patch[1])
        ent["description"] = apply_text_replacements(desc)

    data["entities"] = list(by_label.values())
    return data


def migrate_relations(data: dict) -> dict:
    relations = {r["label"]: r for r in data["relations"]}

    new_relations = [
        {
            "label": "whu_hasContext",
            "description": "Define: Links a **specimen collection plan** to the **environmental context** from which specimens originate (site, matrix, habitat)—not the exact GPS of a single action.\n\nDirection: `whu_SpecimenCollection` → `whu_EnvironmentFeature`.\n\nContext: Extract when text ties the sampling campaign/design to a location or environmental setting (field, river, paddy, province) as **source context**.\n\nDo NOT use for step-level execution site (use `whu_atLocation` on `whu_Specimen_CollectionStep`).\n\nExamples:\n- \"Rice was sampled from paddy fields in Nanjing.\" → SpecimenCollection hasContext EnvironmentFeature(Nanjing paddy).",
        },
        {
            "label": "whu_atLocation",
            "description": "Define: The **execution location** of a collection step.\n\nDirection: `whu_Specimen_CollectionStep` → `whu_EnvironmentFeature`.\n\nContext: Extract when a **specific collection act** occurred at/near a named place (site, lab, coordinates).\n\nExamples:\n- \"Water was sampled at Site A on the Yangtze.\" → CollectionStep atLocation EnvironmentFeature(Site A).",
        },
        {
            "label": "p_plan_isStepOfPlan",
            "description": "Define: A **p-plan:Step** is a component step of a parent **p-plan:Plan** (experiment or specimen plan).\n\nDirection: `*_Step` → parent Plan/Experiment (`whu_SpecimenCollection`, `whu_SpecimenPreprocessing`, `whu_Bio_chemical_Experiment`, `whu_Computational_Experiment`).\n\nReplaces deprecated `whu_hasActivity` (which pointed Plan→Step).\n\nAllowed signatures:\n- whu_Specimen_CollectionStep → whu_SpecimenCollection\n- whu_Specimen_ProcessingStep → whu_SpecimenPreprocessing\n- whu_BioChemicalStep → whu_Bio_chemical_Experiment\n- whu_ComputationalStep → whu_Computational_Experiment\n\nExamples:\n- \"As part of soil collection, cores were taken...\" → CollectionStep isStepOfPlan SpecimenCollection.",
        },
        {
            "label": "p_plan_hasOutputVar",
            "description": "Define: A step **produces** a plan variable (specimen, processed specimen, or dataset).\n\nDirection: `*_Step` → `whu_Specimen` | `whu_ProcessedSpecimen` | `whu_DataSet`.\n\nReplaces deprecated `prov:generated` on steps.\n\nExamples:\n- \"The digestion yielded concentration data.\" → BioChemicalStep hasOutputVar DataSet.",
        },
    ]
    for nr in new_relations:
        relations[nr["label"]] = nr

    relations["whu_fellow"]["description"] = """## Define

`whu_fellow(X, Y)` means **Y is the immediate predecessor of X** in the workflow (Y occurs before X; X depends on Y). **Plan-level only** (not for Steps).

## Allowed signatures (only these)

1. `(whu_SpecimenPreprocessing) -[:whu_fellow]-> (whu_SpecimenCollection)`
2. `(whu_Bio_chemical_Experiment) -[:whu_fellow]-> (whu_SpecimenPreprocessing)`
3. `(whu_Computational_Experiment) -[:whu_fellow]-> (whu_Bio_chemical_Experiment)`
4. `(whu_Bio_chemical_Experiment) -[:whu_fellow]-> (whu_Bio_chemical_Experiment)` — **distinct plan instances only**
5. `(whu_Computational_Experiment) -[:whu_fellow]-> (whu_Computational_Experiment)` — **distinct plan instances only**

**Forbidden:** same WHU_HASNAME on subject and object; no Collection→Collection; no Preprocessing→Preprocessing; no fellow(Collection, Environment)—use `whu_hasContext` instead.

## Context
Temporal cues: after, then, following, subsequently; or X consumes outputs of Y.

## Examples
- Preprocessing fellow Collection: collection then drying/sieving.
- Bio_exp_B fellow Bio_exp_A: two sequential biochemical campaigns."""

    relations["whu_declareUsed"]["description"] = """Define: Declares that a **p-plan:Step** used a resource (method, dataset, device, reagent, or software).

Direction: `*_Step` → `whu_Method` | `whu_DataSet` | `whu_Device` | `whu_Reagent` | `whu_Software`.

Context:
- **Method**: protocol/standard explicitly followed (EPA, ISO, named procedure).
- **DataSet**: especially **external or prior data** used in computational steps.
- **Device / Reagent / Software**: instrument, chemical, or program employed.

Do NOT use `p_plan_hasInputVar` for Device/Reagent/Software—use declareUsed.

Examples:
- \"Following EPA 3052...\" → declareUsed(Method)
- \"Analyzed in R 4.2.2\" → declareUsed(Software)
- \"Using published data from Smith (2020)\" → declareUsed(DataSet)"""

    relations["p_plan_isPrecededBy"]["description"] = """Define: **Step-level** execution order (p-plan:isPrecededBy).

Direction: later `*_Step` → earlier `*_Step` (subject occurs after object).

Context: Use for sequential sub-steps within or across plans. **Subject and object must be different instances** (different WHU_HASNAME).

Do NOT use for Plan-level order (use `whu_fellow`).

Examples:
- \"After digestion, ICP-MS was run.\" → ICPMS_Step isPrecededBy Digestion_Step."""

    relations["p_plan_hasInputVar"]["description"] = """Define: A **p-plan:Step** consumes a variable entity (specimen, processed specimen, dataset).

Direction: `*_Step` → `whu_Specimen` | `whu_ProcessedSpecimen` | `whu_DataSet`.

Do NOT use for Device/Reagent/Software (use `whu_declareUsed`).

Examples:
- \"Digestion used homogenized soil.\" → BioChemicalStep hasInputVar ProcessedSpecimen."""

    relations["prov_wasDerivedFrom"]["description"] = """Define: Entity B was derived from entity A.

Allowed:
- `whu_ProcessedSpecimen` → `whu_Specimen`
- `whu_Specimen` → `whu_EnvironmentFeature` (when text states specimen from environment)
- `whu_ScienceEvidence` → `whu_Computational_Experiment` (evidence derived from computational experiment)

Examples:
- \"Processed powder from collected grains.\" → ProcessedSpecimen wasDerivedFrom Specimen
- \"Risk assessment based on statistical analysis.\" → ScienceEvidence wasDerivedFrom Computational_Experiment"""

    deprecated_note = "DEPRECATED for p-plan:Step subjects. "
    for dep in ("whu_hasActivity", "prov_used", "prov_generated", "prov_wasInformedBy", "prov_atLocation"):
        if dep in relations and not relations[dep]["description"].startswith("DEPRECATED"):
            relations[dep]["description"] = deprecated_note + relations[dep]["description"]

    data["relations"] = list(relations.values())
    return data


def build_potential_schema() -> list:
    M = METHODS_SECTIONS
    R = RESULTS_SECTIONS
    A = ALL_SECTIONS

    ps = [
        # MPU (unchanged)
        ["mp_Attribution", "mp_supports", "whu_DataSet", ["Results", "Discussion"]],
        ["mp_Attribution", "mp_supports", "whu_Method", ["Methods_Materials", "Discussion"]],
        ["mp_Attribution", "mp_supports", "mp_Claim", ["Results", "Discussion"]],
        ["mp_Attribution", "mp_supports", "mp_References", ["References", "Introduction"]],
        ["mp_Attribution", "mp_supports", "mp_Statement", ["Results", "Discussion", "Introduction"]],
        # EBM / EEM workflow
        ["whu_SpecimenCollection", "whu_hasContext", "whu_EnvironmentFeature", M],
        ["whu_Specimen_CollectionStep", "p_plan_isStepOfPlan", "whu_SpecimenCollection", M],
        ["whu_Specimen_CollectionStep", "whu_atLocation", "whu_EnvironmentFeature", M],
        ["whu_Specimen_CollectionStep", "whu_declareUsed", "whu_Method", M],
        ["whu_Specimen_CollectionStep", "whu_declareUsed", "whu_Device", M],
        ["whu_Specimen_CollectionStep", "whu_declareUsed", "envo_Material", M],
        ["whu_Specimen_CollectionStep", "p_plan_hasOutputVar", "whu_Specimen", M],
        ["whu_Specimen_CollectionStep", "p_plan_isPrecededBy", "whu_Specimen_CollectionStep", M],
        ["whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection", M],
        ["whu_Specimen_ProcessingStep", "p_plan_isStepOfPlan", "whu_SpecimenPreprocessing", M],
        ["whu_Specimen_ProcessingStep", "whu_declareUsed", "whu_Method", M],
        ["whu_Specimen_ProcessingStep", "whu_declareUsed", "whu_Device", M],
        ["whu_Specimen_ProcessingStep", "whu_declareUsed", "envo_Material", M],
        ["whu_Specimen_ProcessingStep", "p_plan_hasInputVar", "whu_Specimen", M],
        ["whu_Specimen_ProcessingStep", "p_plan_hasOutputVar", "whu_ProcessedSpecimen", M],
        ["whu_Specimen_ProcessingStep", "p_plan_isPrecededBy", "whu_Specimen_CollectionStep", M],
        ["whu_Specimen_ProcessingStep", "p_plan_isPrecededBy", "whu_Specimen_ProcessingStep", M],
        ["whu_Bio_chemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing", M + ["Experiment"]],
        ["whu_Bio_chemical_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_isStepOfPlan", "whu_Bio_chemical_Experiment", M + ["Experiment"]],
        ["whu_Bio_chemical_Experiment", "whu_hasGoal", "whu_Goal", ["Abstract", "Introduction", "Experiment"]],
        ["whu_BioChemicalStep", "whu_declareUsed", "whu_Method", M + ["Experiment"]],
        ["whu_BioChemicalStep", "whu_declareUsed", "whu_Device", M + ["Experiment"]],
        ["whu_BioChemicalStep", "whu_declareUsed", "whu_Reagent", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_hasInputVar", "whu_ProcessedSpecimen", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_hasInputVar", "whu_DataSet", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_hasOutputVar", "whu_DataSet", R],
        ["whu_BioChemicalStep", "p_plan_hasOutputVar", "whu_ProcessedSpecimen", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_isPrecededBy", "whu_Specimen_ProcessingStep", M + ["Experiment"]],
        ["whu_BioChemicalStep", "p_plan_isPrecededBy", "whu_BioChemicalStep", M + ["Experiment"]],
        ["whu_Computational_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment", M + ["Experiment"]],
        ["whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment", M + ["Experiment"]],
        ["whu_ComputationalStep", "p_plan_isStepOfPlan", "whu_Computational_Experiment", M + ["Experiment"]],
        ["whu_Computational_Experiment", "whu_hasGoal", "whu_Goal", ["Abstract", "Introduction", "Methods_Materials", "Experiment"]],
        ["whu_ComputationalStep", "whu_declareUsed", "whu_Method", M + ["Experiment"]],
        ["whu_ComputationalStep", "whu_declareUsed", "whu_Software", M + ["Experiment"]],
        ["whu_ComputationalStep", "whu_declareUsed", "whu_DataSet", M + ["Experiment"]],
        ["whu_ComputationalStep", "p_plan_hasInputVar", "whu_DataSet", M + ["Experiment"]],
        ["whu_ComputationalStep", "p_plan_hasOutputVar", "whu_DataSet", R],
        ["whu_ComputationalStep", "p_plan_isPrecededBy", "whu_BioChemicalStep", M + ["Experiment"]],
        ["whu_ComputationalStep", "p_plan_isPrecededBy", "whu_ComputationalStep", M + ["Experiment"]],
        # References & goals
        ["mp_References", "cito_isCitedBy", "whu_DataSet", A],
        ["mp_References", "cito_isCitedBy", "whu_Method", A],
        ["mp_References", "cito_isCitedBy", "mp_Claim", A],
        ["mp_References", "cito_isCitedBy", "mp_Statement", A],
        ["whu_Goal", "whu_target", "whu_Target_analyte", M + ["Experiment"]],
        # Material derivation (inverse vars removed)
        ["whu_Specimen", "prov_wasDerivedFrom", "whu_EnvironmentFeature", M],
        ["whu_ProcessedSpecimen", "prov_wasDerivedFrom", "whu_Specimen", M],
        # Data / argumentation
        ["whu_DataSet", "dcterms_hasPart", "whu_ScalarMeasurementDatum", A],
        ["whu_DataSet", "mp_challenges", "mp_Claim", ["Results", "Discussion"]],
        ["whu_DataSet", "mp_supports", "mp_Claim", ["Results", "Discussion"]],
        ["whu_DataSet", "mp_challenges", "mp_Statement", ["Results", "Discussion"]],
        ["whu_DataSet", "mp_supports", "mp_Statement", ["Results", "Discussion"]],
        ["whu_DataSet", "iao_is_about", "whu_Reagent", M + ["Experiment"]],
        ["whu_DataSet", "iao_is_about", "whu_Specimen", M],
        ["whu_DataSet", "iao_is_about", "whu_ProcessedSpecimen", M],
        ["whu_Method", "mp_supports", "whu_DataSet", A],
        ["mp_Statement", "mp_supports", "mp_Claim", A],
        ["mp_Statement", "mp_challenges", "mp_Claim", A],
        ["mp_Claim", "mp_supports", "mp_Claim", A],
        ["mp_Claim", "mp_challenges", "mp_Claim", A],
        ["whu_ScienceEvidence", "whu_hasPart", "whu_DataSet", A],
        ["whu_ScienceEvidence", "whu_hasPart", "whu_Method", A],
        ["whu_ScienceEvidence", "prov_wasDerivedFrom", "whu_Computational_Experiment", A],
        ["whu_SupportGraph", "whu_hasPart", "mp_Statement", A],
        ["whu_SupportGraph", "whu_hasPart", "mp_Attribution", A],
        ["whu_SupportGraph", "whu_hasPart", "mp_References", A],
        ["whu_SupportGraph", "whu_hasPart", "whu_ScienceEvidence", A],
        ["whu_ScienceEvidence", "mp_supports", "whu_SupportGraph", A],
        ["whu_ScienceEvidence", "mp_challenges", "whu_SupportGraph", A],
        ["whu_SupportGraph", "mp_challenges", "mp_Claim", A],
        ["whu_SupportGraph", "mp_supports", "mp_Claim", A],
    ]
    return ps


def migrate_subgraph_mapping(data: dict) -> dict:
    rename = LABEL_RENAMES
    master_suffix = "Master"

    def clean_list(lst: list) -> list:
        out = []
        seen = set()
        for x in lst:
            if x.endswith(master_suffix):
                continue
            x = rename.get(x, x)
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    for key in ("MPU", "EBM", "EEM"):
        data["mappings"][key] = clean_list(data["mappings"].get(key, []))

    for extra in ("whu_ScienceEvidence", "whu_SupportGraph"):
        if extra not in data["mappings"]["MPU"]:
            data["mappings"]["MPU"].append(extra)

    for sg in ("EBM", "EEM"):
        for label in (
            "whu_Specimen_CollectionStep",
            "whu_Specimen_ProcessingStep",
            "whu_BioChemicalStep",
            "whu_ComputationalStep",
        ):
            if label not in data["mappings"][sg]:
                data["mappings"][sg].append(label)

    cross = clean_list(data["notes"].get("cross_subgraph_entities", []))
    data["notes"]["cross_subgraph_entities"] = cross
    data["version"] = "1.1"
    return data


def main():
    entity_path = OUTPUT / "entity.json"
    relation_path = OUTPUT / "relation.json"
    ps_path = OUTPUT / "potential_schema.json"
    map_path = OUTPUT / "subgraph_mapping.json"

    with open(entity_path, encoding="utf-8") as f:
        entities = migrate_entities(json.load(f))
    with open(relation_path, encoding="utf-8") as f:
        relations = migrate_relations(json.load(f))

    potential_schema = {"potential_schema": build_potential_schema()}

    with open(map_path, encoding="utf-8") as f:
        mapping = migrate_subgraph_mapping(json.load(f))

    for p, obj in [
        (entity_path, entities),
        (relation_path, relations),
        (ps_path, potential_schema),
        (map_path, mapping),
    ]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"Wrote {p}")

    print(f"Entities: {len(entities['entities'])}")
    print(f"Relations: {len(relations['relations'])}")
    print(f"Potential schema triples: {len(potential_schema['potential_schema'])}")


if __name__ == "__main__":
    main()
