"""Frozen metric definitions for KG intrinsic judgement (no LLM)."""
from __future__ import annotations

from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS

INFRA_LABELS = frozenset(
    {
        "Chunk",
        "MetaPath",
        "__Entity__",
        "__KGBuilder__",
        "__Relationship__",
        "AttributionMaster",
        "whu_ExternalConcept",
        "Document",
    }
)

EXCLUDED_REL_TYPES = frozenset(
    {
        "FROM_CHUNK",
        "whu_normalizedTo",
        "similarTo",
        "SIMILAR",
        "HAS_REFERENCE",
        "skos_exactMatch",
        "skos_closeMatch",
        "skos_relatedMatch",
        "owl_sameAs",
    }
)

EVIDENCE_LABELS = frozenset(
    {
        "whu_ScienceEvidence",
        "whu_SupportGraph",
        "mp_Claim",
        "mp_Statement",
        "mp_References",
        "mp_Attribution",
        "whu_DataSet",
        "mp_Method",
    }
)

ORPHAN_RULES = frozenset(
    {
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M13",
        "H01",
        "H01-B",
        "H01B",
        "H09",
        "H09-A",
        "H09A",
    }
)

ORPHAN_ELIGIBLE_LABELS = frozenset(
    {
        "whu_SpecimenCollection",
        "whu_SpecimenPreprocessing",
        "whu_BioChemical_Experiment",
        "whu_Computational_Experiment",
        "whu_ScienceEvidence",
        "whu_SupportGraph",
        "whu_ResearchStep",
        "whu_Goal",
    }
)

SITE_MATRIX_LABELS = frozenset(
    {
        "whu_EnvironmentFeature",
        "envo_EnvironmentMaterial",
        "obi_organism",
        "whu_Specimen",
        "whu_ProcessedSpecimen",
    }
)

SITE_MATRIX_RELS = frozenset(
    {
        "whu_hasContext",
        "prov_wasDerivedFrom",
        "prov_atLocation",
        "bfo_has_part",
    }
)

SAMPLE_LIMIT = 25

METRIC_GLOSSARY: tuple[dict[str, str], ...] = (
    {
        "id": "Class Population",
        "definition": "各可实例化 BAE 类的实例数（entity.json 中的 26 个 label）。",
        "direction": "描述性。空类计 0，不解释为越好或越差。",
        "method": "节点须带对应 BAE label，排除基础设施标签与 whu_rejected=true。",
    },
    {
        "id": "Class Richness (CR)",
        "definition": "有实例的可实例化类数 / 全部可实例化类数（26）。",
        "direction": "描述 Schema 利用，不简单解释为越高越好。",
        "method": "分子为 Class Population>0 的类数。",
    },
    {
        "id": "Average Population (AP)",
        "definition": "BAE 实例总数 / 可实例化类数（26）。",
        "direction": "描述性。",
        "method": "分子为所有可实例化类实例之和（一类一节点只计一次）。",
    },
    {
        "id": "SHACL Conformance Rate (SCR)",
        "definition": "无 Hard violation 的受检节点 / 全部受检节点。",
        "direction": "↑，核心。",
        "method": "只读重跑 mid_validate；若图中存在 whu_ResearchStep 再跑 low_validate.validate_low_document_final。不执行 pyshacl、不写库。受检节点=该文 BAE 实例。",
    },
    {
        "id": "Orphan Rate (OR)",
        "definition": "缺少 Schema 规定必要父节点/关系的节点 / 应具有该结构的节点。",
        "direction": "↓。",
        "method": "规则宇宙仅 M01–M06/M13 与 H01/H09（含 H01-B、H09-A）。不用 M10 孤立节点当作全部 orphan。应具结构类：Collection/Preprocessing/Bio/Comp Experiment、ScienceEvidence、SupportGraph、ResearchStep、Goal。",
    },
    {
        "id": "Document Connectivity (DC)",
        "definition": "每篇论文 BAE 证据图最大弱连通分量节点数 / 该文全部证据节点数。",
        "direction": "↑。",
        "method": "证据节点冻结为 ScienceEvidence、SupportGraph、Claim、Statement、References、Attribution、DataSet、Method。边排除 FROM_CHUNK、whu_normalizedTo、similarTo/SKOS 等映射关系。",
    },
    {
        "id": "Mid-level Connectivity (MC)",
        "definition": "每篇论文中层最大弱连通分量节点数 / 全部中层节点数。",
        "direction": "↑。",
        "method": "中层节点=MID_CORE_ENTITY_LABELS。连通边同样排除映射/FROM_CHUNK。",
    },
    {
        "id": "Multi-hop Path Coverage (MPC)",
        "definition": "存在至少 1 条合法 ≥3 跳 BAE 证据路径的论文数 / 可评价论文数。",
        "direction": "↑。",
        "method": "只沿 potential_schema 合法有向三元组走；跳数=关系条数。禁止用原始任意路径总数。映射边不参与。无合法 3 跳则该文计 0。",
    },
    {
        "id": "Duplicate Entity Rate (DER)",
        "definition": "高置信重复实体 / 可评价实体。",
        "direction": "↓。本模块不计算比率。",
        "method": "NOT_COMPUTABLE：禁止用 original_text 相同直接判重复；HASNAME 为 LLM 标题，不能作高置信键。附录仅列出同文+同类+同 FROM_CHUNK 共现组，不作判定。",
    },
    {
        "id": "Relation Schema Conformance (RSC)",
        "definition": "符合 potential_schema 的关系 / 全部待评价 BAE 关系。",
        "direction": "↑，核心。",
        "method": "两端均有 BAE 主 label 的边；(src_label, rel, tgt_label) ∈ potential_schema。排除 FROM_CHUNK 与映射关系。",
    },
    {
        "id": "Relation Conflict Rate (RCR)",
        "definition": "重复 (s,p,o)、非法方向、自环 / 全部待评价 BAE 关系。",
        "direction": "↓。互斥冲突 NOT_COMPUTABLE。",
        "method": "重复=同一 (elementId(s), type, elementId(o)) 多于 1 条。非法=三元组不在 potential_schema。自环=s=t。同一对节点上多种关系类型（如 supports 与 challenges 并存）不记为错误。schema 无互斥表，互斥项标 NOT_COMPUTABLE。",
    },
    {
        "id": "Provenance Coverage (PC)",
        "definition": "具有完整来源的实体 / 应具来源实体。",
        "direction": "↑。",
        "method": "完整来源=非空 WHU_HASORIGINALTEXT，且 (source_doc 非空 或 至少一条 FROM_CHUNK→Chunk.filename)。图中无 Document 节点不视为失败。应具来源=全部 BAE 实例。",
    },
)

LIMITATIONS_FIXED = """\
本模块衡量 Schema 利用、结构一致性、证据连通性、冗余线索与来源完整性，不替代 Gold Standard 下的实体/关系 P-R-F1。
不修改现有 KG，不重新抽取，不调用 LLM。无法可靠计算的指标标记 NOT_COMPUTABLE，不得补造数据。
"""

assert MID_CORE_ENTITY_LABELS
