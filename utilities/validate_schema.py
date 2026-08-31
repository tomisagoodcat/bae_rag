"""
Validate BAE schema JSON consistency (legacy P-Plan or v5 ResearchStep model).
Usage: python utilities/validate_schema.py [--dir output|kg_build_pipeline/schema]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Legacy (output/ P-Plan migration, four Step classes) ──────────────────

LEGACY_STEP_LABELS = {
    "whu_Specimen_CollectionStep",
    "whu_Specimen_ProcessingStep",
    "whu_BioChemicalStep",
    "whu_ComputationalStep",
}

LEGACY_DEPRECATED_ON_STEP = {
    "prov_used",
    "prov_generated",
    "prov_wasInformedBy",
    "prov_atLocation",
    "whu_hasActivity",
}

LEGACY_FELLOW_ALLOWED = {
    ("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection"),
    ("whu_Bio_chemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment"),
    ("whu_Bio_chemical_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment"),
}

LEGACY_PLAN_LABELS = {
    "whu_SpecimenCollection",
    "whu_SpecimenPreprocessing",
    "whu_Bio_chemical_Experiment",
    "whu_Computational_Experiment",
}

LEGACY_REQUIRED_RELATIONS = (
    "whu_hasContext",
    "whu_atLocation",
    "p_plan_isStepOfPlan",
    "p_plan_hasOutputVar",
)

# ── v5 (kg_build_pipeline/schema, unified ResearchStep) ───────────────────

V5_STEP_LABELS = {"whu_ResearchStep"}

V5_DEPRECATED_ON_STEP = {
    "prov_used",
    "prov_generated",
    "prov_wasInformedBy",
    "whu_hasActivity",
    "whu_atLocation",
    "p_plan_hasInputVar",
    "p_plan_hasOutputVar",
    "whu_declareUsed",
}

V5_FELLOW_ALLOWED = {
    ("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection"),
    ("whu_BioChemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
    ("whu_BioChemical_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment"),
}

V5_PLAN_LABELS = {
    "whu_SpecimenCollection",
    "whu_SpecimenPreprocessing",
    "whu_BioChemical_Experiment",
    "whu_Computational_Experiment",
}

V5_REQUIRED_RELATIONS = (
    "whu_hasContext",
    "prov_atLocation",
    "p_plan_isStepOfPlan",
    "p_plan_isOutputVarOf",
    "p_plan_isInputVarOf",
    "whu_declaredInput",
    "whu_declaredOutput",
    "whu_declaredUsed",
)

V5_FORBIDDEN_ENTITIES = LEGACY_STEP_LABELS | {"whu_Bio_chemical_Experiment"}

V5_PLAN_OUTPUT_VAR_ALLOWED = {
    ("whu_Specimen", "p_plan_isOutputVarOf", "whu_SpecimenCollection"),
    ("whu_ProcessedSpecimen", "p_plan_isOutputVarOf", "whu_SpecimenPreprocessing"),
    ("whu_DataSet", "p_plan_isOutputVarOf", "whu_Computational_Experiment"),
}

V5_PLAN_INPUT_VAR_ALLOWED = {
    ("whu_Specimen", "p_plan_isInputVarOf", "whu_SpecimenPreprocessing"),
    ("whu_ProcessedSpecimen", "p_plan_isInputVarOf", "whu_BioChemical_Experiment"),
}

FORBIDDEN_FELLOW = {
    ("whu_SpecimenCollection", "whu_fellow", "whu_EnvironmentFeature"),
}

OLD_ACTIVITY_LABELS = {
    "whu_Specimen_Collection_Activity",
    "whu_Specimen_Processing_Activity",
    "whu_BioChemicalActivityStep",
    "whu_ComputationalActivityStep",
}

TABLE3_SECTION_ROLES = frozenset({
    "Abstract",
    "Introduction",
    "Methods_Materials",
    "Results",
    "Discussion",
    "Conclusion",
    "References",
    "Other",
})

BAE_ROLE_NAMES = frozenset({"EBM", "EEM", "MPU"})


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def detect_schema_version(entity_labels: set[str]) -> str:
    if "whu_ResearchStep" in entity_labels:
        return "v5"
    return "legacy"


def validate(schema_dir: Path) -> list[str]:
    errors: list[str] = []

    entities_data = load_json(schema_dir / "entity.json")
    relations_data = load_json(schema_dir / "relation.json")
    ps_data = load_json(schema_dir / "potential_schema.json")
    map_data = load_json(schema_dir / "subgraph_mapping.json")

    entity_labels = {e["label"] for e in entities_data.get("entities", [])}
    relation_labels = {r["label"] for r in relations_data.get("relations", [])}
    version = detect_schema_version(entity_labels)

    ent_list = [e["label"] for e in entities_data.get("entities", [])]
    if len(ent_list) != len(set(ent_list)):
        errors.append("Duplicate entity labels in entity.json")

    rel_list = [r["label"] for r in relations_data.get("relations", [])]
    if len(rel_list) != len(set(rel_list)):
        errors.append("Duplicate relation labels in relation.json")

    if entity_labels & OLD_ACTIVITY_LABELS:
        errors.append(f"Old activity labels still present: {entity_labels & OLD_ACTIVITY_LABELS}")

    if version == "v5":
        errors.extend(_validate_v5(entity_labels, relation_labels, ps_data, map_data, schema_dir))
    else:
        errors.extend(_validate_legacy(entity_labels, relation_labels, ps_data, map_data, schema_dir))

    return errors


def _validate_legacy(
    entity_labels: set[str],
    relation_labels: set[str],
    ps_data: dict,
    map_data: dict,
    schema_dir: Path,
) -> list[str]:
    errors: list[str] = []

    for req in LEGACY_REQUIRED_RELATIONS:
        if req not in relation_labels:
            errors.append(f"Missing required relation: {req}")

    for step in LEGACY_STEP_LABELS:
        if step not in entity_labels:
            errors.append(f"Missing step entity: {step}")

    if "whu_ResearchStep" in entity_labels:
        errors.append("Mixed schema: whu_ResearchStep present in legacy mode")

    _validate_potential_schema(
        errors,
        ps_data,
        entity_labels,
        relation_labels,
        step_labels=LEGACY_STEP_LABELS,
        deprecated_on_step=LEGACY_DEPRECATED_ON_STEP,
        fellow_allowed=LEGACY_FELLOW_ALLOWED,
        plan_labels=LEGACY_PLAN_LABELS,
    )
    _validate_subgraph_mapping(errors, map_data, entity_labels)
    _validate_table3_section_bae(errors, schema_dir)
    return errors


def _validate_v5(
    entity_labels: set[str],
    relation_labels: set[str],
    ps_data: dict,
    map_data: dict,
    schema_dir: Path,
) -> list[str]:
    errors: list[str] = []

    for req in V5_REQUIRED_RELATIONS:
        if req not in relation_labels:
            errors.append(f"Missing required relation: {req}")

    for step in V5_STEP_LABELS:
        if step not in entity_labels:
            errors.append(f"Missing step entity: {step}")

    forbidden = entity_labels & V5_FORBIDDEN_ENTITIES
    if forbidden:
        errors.append(f"Legacy labels must not appear in v5 schema: {forbidden}")

    _validate_potential_schema(
        errors,
        ps_data,
        entity_labels,
        relation_labels,
        step_labels=V5_STEP_LABELS,
        deprecated_on_step=V5_DEPRECATED_ON_STEP,
        fellow_allowed=V5_FELLOW_ALLOWED,
        plan_labels=V5_PLAN_LABELS,
    )

    triples = ps_data.get("potential_schema", [])
    for i, t in enumerate(triples):
        if not isinstance(t, list) or len(t) < 3:
            continue
        key = (t[0], t[1], t[2])
        if t[1] == "p_plan_isOutputVarOf" and key not in V5_PLAN_OUTPUT_VAR_ALLOWED:
            errors.append(f"potential_schema[{i}]: isOutputVarOf triple not in whitelist: {key}")
        if t[1] == "p_plan_isInputVarOf" and key not in V5_PLAN_INPUT_VAR_ALLOWED:
            errors.append(f"potential_schema[{i}]: isInputVarOf triple not in whitelist: {key}")

    _validate_subgraph_mapping(errors, map_data, entity_labels)
    _validate_table3_section_bae(errors, schema_dir)
    return errors


def _validate_potential_schema(
    errors: list[str],
    ps_data: dict,
    entity_labels: set[str],
    relation_labels: set[str],
    *,
    step_labels: set[str],
    deprecated_on_step: set[str],
    fellow_allowed: set[tuple[str, str, str]],
    plan_labels: set[str],
) -> None:
    triples = ps_data.get("potential_schema", [])
    for i, t in enumerate(triples):
        if not isinstance(t, list) or len(t) < 3:
            errors.append(f"potential_schema[{i}]: invalid triple format")
            continue
        e1, r, e2 = t[0], t[1], t[2]
        if e1 not in entity_labels:
            errors.append(f"potential_schema[{i}]: unknown head entity {e1}")
        if e2 not in entity_labels:
            errors.append(f"potential_schema[{i}]: unknown tail entity {e2}")
        if r not in relation_labels:
            errors.append(f"potential_schema[{i}]: unknown relation {r}")

        if e1 in step_labels and r in deprecated_on_step:
            errors.append(f"potential_schema[{i}]: deprecated relation {r} on step subject")

        key = (e1, r, e2)
        if key in FORBIDDEN_FELLOW:
            errors.append(f"potential_schema[{i}]: forbidden fellow(Collection, Environment)")

        if r == "whu_fellow" and key not in fellow_allowed:
            errors.append(f"potential_schema[{i}]: fellow triple not in whitelist: {key}")

        if r == "p_plan_isStepOfPlan":
            if e1 not in step_labels:
                errors.append(
                    f"potential_schema[{i}]: isStepOfPlan subject must be a Step, got {e1}"
                )
            if e2 not in plan_labels:
                errors.append(
                    f"potential_schema[{i}]: isStepOfPlan object must be a Plan, got {e2}"
                )

        if len(t) < 5:
            errors.append(
                f"potential_schema[{i}]: missing tier (expected 5th element mid|low|mid2low)"
            )
        elif t[4] not in {"mid", "low", "mid2low"}:
            errors.append(
                f"potential_schema[{i}]: invalid tier {t[4]!r} (expected mid|low|mid2low)"
            )


def _validate_subgraph_mapping(
    errors: list[str], map_data: dict, entity_labels: set[str]
) -> None:
    mappings = map_data.get("mappings", {})
    for sg, labels in mappings.items():
        for lbl in labels:
            if lbl.endswith("Master"):
                errors.append(f"subgraph_mapping {sg}: Master ghost label {lbl}")
            if lbl not in entity_labels:
                errors.append(f"subgraph_mapping {sg}: unknown entity {lbl}")

    for lbl in map_data.get("notes", {}).get("cross_subgraph_entities", []):
        if lbl not in entity_labels:
            errors.append(f"cross_subgraph_entities: unknown {lbl}")


def _validate_table3_section_bae(errors: list[str], schema_dir: Path) -> None:
    path = schema_dir / "table3_section_bae.json"
    if not path.is_file():
        return
    data = load_json(path)
    mappings = data.get("mappings")
    if not isinstance(mappings, dict):
        errors.append("table3_section_bae.json: mappings must be an object")
        return
    if not TABLE3_SECTION_ROLES.issubset(set(mappings.keys())):
        missing = TABLE3_SECTION_ROLES - set(mappings.keys())
        errors.append(f"table3_section_bae.json: missing section_role keys {sorted(missing)}")
    for role, entry in mappings.items():
        if not isinstance(entry, dict):
            errors.append(f"table3_section_bae.json: {role} entry must be an object")
            continue
        prior = entry.get("bae_roles_prior", [])
        if not isinstance(prior, list):
            errors.append(f"table3_section_bae.json: {role}.bae_roles_prior must be a list")
            continue
        for r in prior:
            if r not in BAE_ROLE_NAMES:
                errors.append(f"table3_section_bae.json: {role} has invalid BAE role {r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="output", help="Schema directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    schema_dir = root / args.dir

    entity_labels = {
        e["label"] for e in load_json(schema_dir / "entity.json").get("entities", [])
    }
    version = detect_schema_version(entity_labels)

    errors = validate(schema_dir)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("OK: schema validation passed")
    print(f"  dir: {schema_dir}")
    print(f"  version: {version}")


if __name__ == "__main__":
    main()

