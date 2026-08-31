"""Patch notebooks for P-Plan schema migration."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUBGRAPH_CONFIGS_NEW = '''SUBGRAPH_CONFIGS = {
    "mpu": {
        "projection": "mpu_projection",
        "nodes": [
            "mp_Claim", "whu_DataSet", "mp_Statement",
            "mp_Attribution", "mp_References", "whu_Method", "whu_Goal",
            "whu_ScienceEvidence", "whu_SupportGraph",
        ],
        "relationships": {
            "MP_SUPPORTS":   {"type": "mp_supports",   "orientation": "NATURAL"},
            "MP_CHALLENGES": {"type": "mp_challenges",  "orientation": "NATURAL"},
            "CITO_CITED":    {"type": "cito_isCitedBy", "orientation": "NATURAL"},
            "HAS_PART":      {"type": "whu_hasPart",    "orientation": "NATURAL"},
            "WAS_DERIVED":   {"type": "prov_wasDerivedFrom", "orientation": "NATURAL"},
        }
    },
    "eem": {
        "projection": "eem_projection",
        "nodes": [
            "whu_ProcessedSpecimen", "whu_Bio_chemical_Experiment",
            "whu_BioChemicalStep", "whu_ComputationalStep",
            "whu_Computational_Experiment", "whu_DataSet",
            "whu_Goal", "whu_Target_analyte", "whu_Reagent",
            "whu_Device", "whu_Software", "whu_ScalarMeasurementDatum", "whu_Method",
            "whu_ScienceEvidence",
        ],
        "relationships": {
            "STEP_OF_PLAN":  {"type": "p_plan_isStepOfPlan",  "orientation": "NATURAL"},
            "HAS_INPUT":     {"type": "p_plan_hasInputVar",   "orientation": "NATURAL"},
            "HAS_OUTPUT":    {"type": "p_plan_hasOutputVar",  "orientation": "NATURAL"},
            "PRECEDED_BY":   {"type": "p_plan_isPrecededBy",  "orientation": "NATURAL"},
            "FELLOW":        {"type": "whu_fellow",           "orientation": "NATURAL"},
            "HAS_GOAL":      {"type": "whu_hasGoal",          "orientation": "NATURAL"},
            "TARGET":        {"type": "whu_target",           "orientation": "NATURAL"},
            "DECLARE_USED":  {"type": "whu_declareUsed",      "orientation": "NATURAL"},
            "HAS_PART":      {"type": "dcterms_hasPart",      "orientation": "NATURAL"},
            "IS_ABOUT":      {"type": "iao_is_about",         "orientation": "NATURAL"},
            "WAS_DERIVED":   {"type": "prov_wasDerivedFrom",  "orientation": "NATURAL"},
        }
    },
    "ebm": {
        "projection": "ebm_projection",
        "nodes": [
            "whu_Specimen", "whu_ProcessedSpecimen", "whu_SpecimenCollection",
            "whu_SpecimenPreprocessing", "whu_EnvironmentFeature",
            "whu_Specimen_CollectionStep", "whu_Specimen_ProcessingStep",
            "whu_Device", "envo_Material", "whu_Method", "whu_DataSet",
        ],
        "relationships": {
            "HAS_CONTEXT":   {"type": "whu_hasContext",       "orientation": "NATURAL"},
            "AT_LOCATION":   {"type": "whu_atLocation",       "orientation": "NATURAL"},
            "FELLOW":        {"type": "whu_fellow",           "orientation": "NATURAL"},
            "STEP_OF_PLAN":  {"type": "p_plan_isStepOfPlan",  "orientation": "NATURAL"},
            "DECLARE_USED":  {"type": "whu_declareUsed",      "orientation": "NATURAL"},
            "HAS_INPUT":     {"type": "p_plan_hasInputVar",   "orientation": "NATURAL"},
            "HAS_OUTPUT":    {"type": "p_plan_hasOutputVar",  "orientation": "NATURAL"},
            "PRECEDED_BY":   {"type": "p_plan_isPrecededBy",  "orientation": "NATURAL"},
            "DERIVED_FROM":  {"type": "prov_wasDerivedFrom",  "orientation": "NATURAL"},
        }
    }
}'''

SUBGRAPH_RELATIONS_NEW = '''SUBGRAPH_RELATIONS = {
    "MPU": [
        ("mp_References", "cito_isCitedBy", "whu_DataSet"),
        ("mp_References", "cito_isCitedBy", "whu_Method"),
        ("mp_References", "cito_isCitedBy", "mp_Claim"),
        ("mp_References", "cito_isCitedBy", "mp_Statement"),
        ("whu_DataSet", "mp_challenges", "mp_Claim"),
        ("whu_DataSet", "mp_challenges", "mp_Statement"),
        ("mp_Statement", "mp_challenges", "mp_Claim"),
        ("mp_Claim", "mp_challenges", "mp_Claim"),
        ("whu_DataSet", "mp_supports", "mp_Claim"),
        ("whu_DataSet", "mp_supports", "mp_Statement"),
        ("whu_Method", "mp_supports", "whu_DataSet"),
        ("mp_Statement", "mp_supports", "mp_Claim"),
        ("mp_Attribution", "mp_supports", "whu_DataSet"),
        ("mp_Attribution", "mp_supports", "whu_Method"),
        ("mp_Attribution", "mp_supports", "mp_Claim"),
        ("mp_Attribution", "mp_supports", "mp_References"),
        ("mp_Attribution", "mp_supports", "mp_Statement"),
        ("whu_ScienceEvidence", "prov_wasDerivedFrom", "whu_Computational_Experiment"),
        ("whu_ScienceEvidence", "mp_supports", "whu_SupportGraph"),
        ("whu_SupportGraph", "mp_supports", "mp_Claim"),
    ],
    "EEM": [
        ("whu_BioChemicalStep", "p_plan_isStepOfPlan", "whu_Bio_chemical_Experiment"),
        ("whu_ComputationalStep", "p_plan_isStepOfPlan", "whu_Computational_Experiment"),
        ("whu_BioChemicalStep", "p_plan_hasOutputVar", "whu_DataSet"),
        ("whu_ComputationalStep", "p_plan_hasInputVar", "whu_DataSet"),
        ("whu_ComputationalStep", "p_plan_hasOutputVar", "whu_DataSet"),
        ("whu_BioChemicalStep", "p_plan_hasInputVar", "whu_ProcessedSpecimen"),
        ("whu_Bio_chemical_Experiment", "whu_hasGoal", "whu_Goal"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Method"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Device"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Reagent"),
        ("whu_Computational_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment"),
        ("whu_ComputationalStep", "whu_declareUsed", "whu_Software"),
    ],
    "EBM": [
        ("whu_SpecimenCollection", "whu_hasContext", "whu_EnvironmentFeature"),
        ("whu_Specimen_CollectionStep", "p_plan_isStepOfPlan", "whu_SpecimenCollection"),
        ("whu_Specimen_ProcessingStep", "p_plan_isStepOfPlan", "whu_SpecimenPreprocessing"),
        ("whu_Specimen_CollectionStep", "whu_atLocation", "whu_EnvironmentFeature"),
        ("whu_Specimen_CollectionStep", "p_plan_hasOutputVar", "whu_Specimen"),
        ("whu_Specimen_ProcessingStep", "p_plan_hasInputVar", "whu_Specimen"),
        ("whu_Specimen_ProcessingStep", "p_plan_hasOutputVar", "whu_ProcessedSpecimen"),
        ("whu_ProcessedSpecimen", "prov_wasDerivedFrom", "whu_Specimen"),
        ("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection"),
        ("whu_Specimen_CollectionStep", "whu_declareUsed", "whu_Device"),
        ("whu_Specimen_ProcessingStep", "whu_declareUsed", "whu_Method"),
    ],
}'''

SCHEMA_MANAGER_INIT_PATCH = '''        self.entities = self._load_json("entity.json")
        self.relations = self._load_json("relation.json")
        self.triples = self._load_json("potential_schema.json")
        self._entities_by_label = self._index_entities(self.entities)
        self._relations_by_label = self._index_relations(self.relations)
'''

SCHEMA_MANAGER_HELPERS = '''
    def _index_entities(self, data):
        if isinstance(data, dict) and "entities" in data:
            return {e["label"]: e for e in data["entities"]}
        if isinstance(data, dict):
            return data
        return {}

    def _index_relations(self, data):
        if isinstance(data, dict) and "relations" in data:
            return {r["label"]: r for r in data["relations"]}
        if isinstance(data, dict):
            return data
        return {}
'''

EXTRACT_ENTITIES_NEW = '''    def _extract_entities(self, subgraph: str) -> Dict:
        """提取子图实体"""
        entities = {}
        entity_index = getattr(self, "_entities_by_label", {})

        if self.subgraph_mapping:
            entity_names = self.subgraph_mapping.get(subgraph, [])
            for name in entity_names:
                info = entity_index.get(name, {})
                if self.live_schema:
                    for label_info in self.live_schema["labels"]:
                        if label_info["label"] == name:
                            if not info:
                                info = {}
                            info["count"] = label_info["count"]
                            break
                entities[name] = info if info else {"label": name}
        else:
            for name, info in entity_index.items():
                if self._belongs_to_subgraph_by_keyword(name, subgraph):
                    entities[name] = info

        return entities
'''

EXTRACT_RELATIONS_NEW = '''    def _extract_relations(self, subgraph: str, entities: Dict) -> Dict:
        """提取子图关系"""
        relations = {}
        entity_names = set(entities.keys())
        rel_index = getattr(self, "_relations_by_label", self.relations)

        for rel_name, rel_info in rel_index.items():
            if self._relation_belongs_to_entities(rel_name, entity_names):
                relations[rel_name] = rel_info

        return relations
'''

TRIPLE_BELONGS_NEW = '''    def _triple_belongs_to_entities(self, triple, entity_names: set) -> bool:
        """判断三元组是否属于实体集合"""
        if isinstance(triple, (list, tuple)) and len(triple) >= 2:
            head, tail = triple[0], triple[2] if len(triple) > 2 else ""
            return head in entity_names or tail in entity_names
        if isinstance(triple, dict):
            head = triple.get("head", triple.get("source", ""))
            tail = triple.get("tail", triple.get("target", ""))
            return head in entity_names or tail in entity_names
        if isinstance(triple, str):
            return any(entity in triple for entity in entity_names)
        return False
'''


def replace_in_cell_source(source: list[str], old: str, new: str) -> bool:
    text = "".join(source)
    if old not in text:
        return False
    new_text = text.replace(old, new, 1)
    source[:] = [line + "\n" for line in new_text.splitlines(True)]
    if source and not source[-1].endswith("\n"):
        source[-1] += "\n"
    return True


def patch_retrieve_notebook(path: Path):
    nb = json.loads(path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", [])
        text = "".join(src)
        if "SUBGRAPH_CONFIGS = {" in text and "mpu_projection" in text:
            if "whu_BioChemicalStep" in text and "p_plan_isStepOfPlan" in text:
                continue  # already patched
            start = text.index("SUBGRAPH_CONFIGS = {")
            end = text.find("\ndef _drop_if_exists", start)
            if end < 0:
                continue
            text = text[:start] + SUBGRAPH_CONFIGS_NEW + "\n" + text[end:]
            cell["source"] = [line + "\n" for line in text.splitlines(True)]
        if "SUBGRAPH_RELATIONS = {" in text and '"MPU":' in text:
            if "whu_BioChemicalStep" in text and "p_plan_isStepOfPlan" in text:
                continue
            start = text.index("SUBGRAPH_RELATIONS = {")
            end = text.find("\n# 子图", start)
            if end < 0:
                end = text.find("\n}\n\n", start + 1)
            if end < 0:
                continue
            text = text[:start] + SUBGRAPH_RELATIONS_NEW + text[end:]
            cell["source"] = [line + "\n" for line in text.splitlines(True)]
        if "class Neo4jSchemaManager:" in text:
            text = "".join(cell.get("source", []))
            if "_entities_by_label" not in text:
                text = text.replace(
                    '        self.triples = self._load_json("potential_schema.json")\n        \n        # 加载Neo4j实时Schema',
                    '        self.triples = self._load_json("potential_schema.json")\n        self._entities_by_label = self._index_entities(self.entities)\n        self._relations_by_label = self._index_relations(self.relations)\n        \n        # 加载Neo4j实时Schema',
                )
            if "def _index_entities" not in text:
                text = text.replace(
                    "    def _build_subgraph_schemas(self)",
                    SCHEMA_MANAGER_HELPERS + "\n    def _build_subgraph_schemas(self)",
                )
            import re
            text = re.sub(
                r"    def _extract_entities\(self, subgraph: str\) -> Dict:.*?        return entities\n",
                EXTRACT_ENTITIES_NEW + "\n",
                text,
                flags=re.DOTALL,
                count=1,
            )
            text = re.sub(
                r"    def _extract_relations\(self, subgraph: str, entities: Dict\) -> Dict:.*?        return relations\n",
                EXTRACT_RELATIONS_NEW + "\n",
                text,
                flags=re.DOTALL,
                count=1,
            )
            text = re.sub(
                r"    def _triple_belongs_to_entities\(self, triple: Union\[Dict, str\], entity_names: set\) -> bool:.*?        return False\n",
                TRIPLE_BELONGS_NEW + "\n",
                text,
                flags=re.DOTALL,
                count=1,
            )
            cell["source"] = [line + "\n" for line in text.splitlines(True)]
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {path}")


def patch_build_notebook(path: Path):
    text = path.read_text(encoding="utf-8")
    text = text.replace("whu_ComputationalExperiment", "whu_Computational_Experiment")
    text = text.replace("whu_BiochemicalExperiment", "whu_Bio_chemical_Experiment")
    text = text.replace("whu_BioChemicalActivityStep", "whu_BioChemicalStep")
    text = text.replace("whu_ComputationalActivityStep", "whu_ComputationalStep")
    text = text.replace("whu_Specimen_Collection_Activity", "whu_Specimen_CollectionStep")
    text = text.replace("whu_Specimen_Processing_Activity", "whu_Specimen_ProcessingStep")
    path.write_text(text, encoding="utf-8")
    print(f"Patched {path}")


def main():
    patch_retrieve_notebook(ROOT / "3_0_2 Retevie.ipynb")
    patch_build_notebook(ROOT / "1_2_0_2build_kg__neo4j.ipynb")


if __name__ == "__main__":
    main()
