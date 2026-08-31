"""Replace auto-generated SUBGRAPH_RELATIONS cell with hand-written version."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "1_2_1_2pagerankMetapath.ipynb"

F1_MD = """\
## F1 关系清单（手写，对齐 potential_schema.json v1.2）

1. 下方 `SUBGRAPH_RELATIONS` 为手写定义（方向 `source -[relation]-> target`）
2. 不含 F4 层级边（见 `F4_RELATIONS`）
3. 运行验收 cell 确认 Neo4j 匹配后，再执行 `build_all_metapaths(neo4j_driver)`
"""

SUBGRAPH_RELATIONS_CODE = r'''# ══════════════════════════════════════════════════════════════
# F1 关系清单（手写，对齐 potential_schema.json v1.2）
# 方向：source -[relation]-> target
# 不含 F4：p_plan_isStepOfPlan / whu_hasPart（见 F4_RELATIONS）
# ══════════════════════════════════════════════════════════════

SUBGRAPH_RELATIONS = {
    "MPU": [
        # mp_supports (12)
        ("mp_Attribution", "mp_supports", "whu_DataSet"),
        ("mp_Attribution", "mp_supports", "whu_Method"),
        ("mp_Attribution", "mp_supports", "mp_Claim"),
        ("mp_Attribution", "mp_supports", "mp_References"),
        ("mp_Attribution", "mp_supports", "mp_Statement"),
        ("whu_DataSet", "mp_supports", "mp_Claim"),
        ("whu_DataSet", "mp_supports", "mp_Statement"),
        ("whu_Method", "mp_supports", "whu_DataSet"),
        ("mp_Statement", "mp_supports", "mp_Claim"),
        ("mp_Claim", "mp_supports", "mp_Claim"),
        ("whu_ScienceEvidence", "mp_supports", "whu_SupportGraph"),
        ("whu_SupportGraph", "mp_supports", "mp_Claim"),
        # mp_challenges (6)
        ("whu_DataSet", "mp_challenges", "mp_Claim"),
        ("whu_DataSet", "mp_challenges", "mp_Statement"),
        ("mp_Statement", "mp_challenges", "mp_Claim"),
        ("mp_Claim", "mp_challenges", "mp_Claim"),
        ("whu_ScienceEvidence", "mp_challenges", "whu_SupportGraph"),
        ("whu_SupportGraph", "mp_challenges", "mp_Claim"),
        # cito_isCitedBy (4)
        ("mp_References", "cito_isCitedBy", "whu_DataSet"),
        ("mp_References", "cito_isCitedBy", "whu_Method"),
        ("mp_References", "cito_isCitedBy", "mp_Claim"),
        ("mp_References", "cito_isCitedBy", "mp_Statement"),
    ],
    "EBM": [
        ("whu_SpecimenCollection", "whu_hasContext", "whu_EnvironmentFeature"),
        ("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection"),
        ("whu_Specimen", "prov_wasDerivedFrom", "whu_EnvironmentFeature"),
        ("whu_ProcessedSpecimen", "prov_wasDerivedFrom", "whu_Specimen"),
        ("whu_Bio_chemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
        ("whu_Specimen_CollectionStep", "whu_atLocation", "whu_EnvironmentFeature"),
        ("whu_Specimen_CollectionStep", "whu_declareUsed", "whu_Method"),
        ("whu_Specimen_CollectionStep", "whu_declareUsed", "whu_Device"),
        ("whu_Specimen_CollectionStep", "whu_declareUsed", "envo_Material"),
        ("whu_Specimen_CollectionStep", "p_plan_hasOutputVar", "whu_Specimen"),
        ("whu_Specimen_CollectionStep", "p_plan_isPrecededBy", "whu_Specimen_CollectionStep"),
        ("whu_Specimen_ProcessingStep", "whu_declareUsed", "whu_Method"),
        ("whu_Specimen_ProcessingStep", "whu_declareUsed", "whu_Device"),
        ("whu_Specimen_ProcessingStep", "whu_declareUsed", "envo_Material"),
        ("whu_Specimen_ProcessingStep", "p_plan_hasInputVar", "whu_Specimen"),
        ("whu_Specimen_ProcessingStep", "p_plan_hasOutputVar", "whu_ProcessedSpecimen"),
        ("whu_Specimen_ProcessingStep", "p_plan_isPrecededBy", "whu_Specimen_CollectionStep"),
        ("whu_Specimen_ProcessingStep", "p_plan_isPrecededBy", "whu_Specimen_ProcessingStep"),
        ("whu_BioChemicalStep", "p_plan_isPrecededBy", "whu_Specimen_ProcessingStep"),
        ("whu_DataSet", "dcterms_hasPart", "whu_ScalarMeasurementDatum"),
        ("whu_DataSet", "iao_is_about", "whu_Reagent"),
        ("whu_DataSet", "iao_is_about", "whu_Specimen"),
        ("whu_DataSet", "iao_is_about", "whu_ProcessedSpecimen"),
    ],
    "EEM": [
        ("whu_Bio_chemical_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment"),
        ("whu_Bio_chemical_Experiment", "whu_hasGoal", "whu_Goal"),
        ("whu_Computational_Experiment", "whu_fellow", "whu_Bio_chemical_Experiment"),
        ("whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment"),
        ("whu_Computational_Experiment", "whu_hasGoal", "whu_Goal"),
        ("whu_Bio_chemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
        ("whu_Goal", "whu_target", "whu_Target_analyte"),
        ("whu_ScienceEvidence", "prov_wasDerivedFrom", "whu_Computational_Experiment"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Method"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Device"),
        ("whu_BioChemicalStep", "whu_declareUsed", "whu_Reagent"),
        ("whu_BioChemicalStep", "p_plan_hasInputVar", "whu_ProcessedSpecimen"),
        ("whu_BioChemicalStep", "p_plan_hasInputVar", "whu_DataSet"),
        ("whu_BioChemicalStep", "p_plan_hasOutputVar", "whu_DataSet"),
        ("whu_BioChemicalStep", "p_plan_hasOutputVar", "whu_ProcessedSpecimen"),
        ("whu_BioChemicalStep", "p_plan_isPrecededBy", "whu_BioChemicalStep"),
        ("whu_ComputationalStep", "whu_declareUsed", "whu_Method"),
        ("whu_ComputationalStep", "whu_declareUsed", "whu_Software"),
        ("whu_ComputationalStep", "whu_declareUsed", "whu_DataSet"),
        ("whu_ComputationalStep", "p_plan_hasInputVar", "whu_DataSet"),
        ("whu_ComputationalStep", "p_plan_hasOutputVar", "whu_DataSet"),
        ("whu_ComputationalStep", "p_plan_isPrecededBy", "whu_BioChemicalStep"),
        ("whu_ComputationalStep", "p_plan_isPrecededBy", "whu_ComputationalStep"),
    ],
}

F4_RELATIONS = [
    ("whu_Specimen_CollectionStep", "p_plan_isStepOfPlan", "whu_SpecimenCollection"),
    ("whu_Specimen_ProcessingStep", "p_plan_isStepOfPlan", "whu_SpecimenPreprocessing"),
    ("whu_BioChemicalStep", "p_plan_isStepOfPlan", "whu_Bio_chemical_Experiment"),
    ("whu_ComputationalStep", "p_plan_isStepOfPlan", "whu_Computational_Experiment"),
    ("whu_ScienceEvidence", "whu_hasPart", "whu_DataSet"),
    ("whu_ScienceEvidence", "whu_hasPart", "whu_Method"),
    ("whu_SupportGraph", "whu_hasPart", "mp_Statement"),
    ("whu_SupportGraph", "whu_hasPart", "mp_Attribution"),
    ("whu_SupportGraph", "whu_hasPart", "mp_References"),
    ("whu_SupportGraph", "whu_hasPart", "whu_ScienceEvidence"),
]

PAGERANK_PROP = {
    "MPU": "mpu_pagerank",
    "EEM": "eem_pagerank",
    "EBM": "ebm_pagerank",
}

total = sum(len(v) for v in SUBGRAPH_RELATIONS.values())
print(f"✅ 关系清单：MPU={len(SUBGRAPH_RELATIONS['MPU'])}, "
      f"EBM={len(SUBGRAPH_RELATIONS['EBM'])}, "
      f"EEM={len(SUBGRAPH_RELATIONS['EEM'])}, 分配总计={total}")
print(f"   F4 层级边: {len(F4_RELATIONS)} 条（不进 F1 MetaPath 模板）")
'''

VALIDATE_CODE = r'''# ══════════════════════════════════════════════════════════════
# F1 验收：SUBGRAPH_RELATIONS 在 Neo4j 中的匹配情况
# ══════════════════════════════════════════════════════════════

import pandas as pd

rows = []
with neo4j_driver.session() as session:
    for sg, triples in SUBGRAPH_RELATIONS.items():
        for source, relation, target in triples:
            q = f"MATCH (s:{source})-[r:{relation}]->(t:{target}) RETURN count(*) AS c"
            count = session.run(q).single()["c"]
            rows.append({
                "subgraph": sg,
                "source": source,
                "relation": relation,
                "target": target,
                "count": count,
                "ok": count > 0,
            })

df = pd.DataFrame(rows)
ok = df["ok"].sum()
total = len(df)
zero = df[~df["ok"]]

print("=" * 60)
print(f"F1 关系模板验收: {ok}/{total} 条在 Neo4j 有实例 (count>0)")
print("=" * 60)

for sg in ["MPU", "EBM", "EEM"]:
    sub = df[df["subgraph"] == sg]
    sg_ok = sub["ok"].sum()
    print(f"  {sg}: {sg_ok}/{len(sub)} 有实例")

if len(zero):
    print(f"\n⚠️  无匹配实例 ({len(zero)} 条) — 可能 KG 未抽取到，或 label/关系名不一致:")
    for _, row in zero.iterrows():
        print(
            f"   [{row['subgraph']}] {row['source']}-[{row['relation']}]->{row['target']}"
        )
else:
    print("\n✅ 所有 F1 关系模板均在 Neo4j 中有至少 1 条实例")
'''

E_CODE_HEADER = '''# ══════════════════════════════════════════════════════════════
# 三子图中心性计算与写回（SUBGRAPH_CONFIGS 对齐 subgraph_mapping v1.2）
# ══════════════════════════════════════════════════════════════

from graphdatascience import GraphDataScience
import pandas as pd

'''


def _rel_spec(types: list[str]) -> dict:
    spec = {}
    for rt in types:
        key = rt.upper().replace("-", "_")
        spec[key] = {"type": rt, "orientation": "NATURAL"}
    return spec


def build_e_cell() -> str:
    configs = {
        "mpu": {
            "projection": "mpu_projection",
            "nodes": [
                "whu_Goal", "mp_References", "whu_DataSet", "mp_Claim",
                "mp_Statement", "whu_Method", "mp_Attribution",
                "whu_ScienceEvidence", "whu_SupportGraph",
            ],
            "relationships": _rel_spec(["mp_supports", "mp_challenges", "cito_isCitedBy"]),
        },
        "ebm": {
            "projection": "ebm_projection",
            "nodes": [
                "whu_DataSet", "whu_Specimen_ProcessingStep", "whu_Specimen_CollectionStep",
                "whu_ProcessedSpecimen", "whu_ScalarMeasurementDatum", "whu_Device",
                "whu_Specimen", "whu_EnvironmentFeature", "whu_SpecimenCollection",
                "whu_SpecimenPreprocessing", "whu_Reagent", "whu_Software", "envo_Material",
                "whu_BioChemicalStep", "whu_ComputationalStep", "whu_Bio_chemical_Experiment",
            ],
            "relationships": _rel_spec([
                "whu_hasContext", "whu_fellow", "prov_wasDerivedFrom", "whu_atLocation",
                "whu_declareUsed", "p_plan_hasOutputVar", "p_plan_isPrecededBy",
                "p_plan_hasInputVar", "dcterms_hasPart", "iao_is_about",
            ]),
        },
        "eem": {
            "projection": "eem_projection",
            "nodes": [
                "whu_DataSet", "whu_BioChemicalStep", "whu_Method", "whu_ComputationalStep",
                "whu_ProcessedSpecimen", "whu_ScalarMeasurementDatum", "whu_Device",
                "whu_Bio_chemical_Experiment", "whu_Specimen", "whu_Computational_Experiment",
                "whu_Goal", "whu_Reagent", "whu_Target_analyte", "whu_Software",
                "envo_Material", "whu_SupportGraph", "whu_ScienceEvidence",
                "whu_Specimen_CollectionStep", "whu_Specimen_ProcessingStep",
            ],
            "relationships": _rel_spec([
                "whu_fellow", "whu_hasGoal", "whu_target", "prov_wasDerivedFrom",
                "whu_declareUsed", "p_plan_hasInputVar", "p_plan_hasOutputVar",
                "p_plan_isPrecededBy",
            ]),
        },
    }
    import pprint

    body = E_CODE_HEADER + "SUBGRAPH_CONFIGS = "
    body += pprint.pformat(configs, width=100, sort_dicts=False)
    body += "\n\n"
    # append rest from original E cell (from url = ... onwards)
    nb = json.loads(NB.read_text(encoding="utf-8"))
    old = "".join(nb["cells"][2]["source"])
    idx = old.find('url      = "bolt://localhost:7687"')
    if idx == -1:
        idx = old.find('url = "bolt://localhost:7687"')
    body += old[idx:]
    body = body.replace(
        'print("SUBGRAPH_CONFIGS（自动生成）:"',
        'print("SUBGRAPH_CONFIGS:"',
    )
    return body


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    intro = cells[0]["source"]
    if isinstance(intro, list):
        intro = "".join(intro)
    intro = intro.replace(
        "| `output/potential_schema.json` | 生成 `SUBGRAPH_RELATIONS` 三元组（主数据源） |",
        "| `output/potential_schema.json` | F1 手写清单的对照来源 |",
    ).replace(
        "**执行顺序**：E → F1 生成关系清单 → F1 验收 → F1 构建 MetaPath → F2 → F3 → F4",
        "**执行顺序**：E → F1 手写关系清单 → F1 验收 → F1 构建 MetaPath → F2 → F3 → F4",
    )
    cells[0]["source"] = intro

    cells[1]["source"] = (
        "# E 分子图图分析并赋值\n\n"
        "对 MPU / EBM / EEM 三子图分别做 GDS 投影，计算中心性并写回 `{sg}_pagerank`。\n\n"
        "- **节点**：`subgraph_mapping.json` v1.2（手写 `SUBGRAPH_CONFIGS`）\n"
        "- **关系**：与 F1 手写清单一致的非 F4 关系类型\n"
    )

    cells[2]["source"] = build_e_cell()
    cells[5]["source"] = F1_MD
    cells[8]["source"] = SUBGRAPH_RELATIONS_CODE
    cells[9]["source"] = VALIDATE_CODE

    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB}")


if __name__ == "__main__":
    main()
