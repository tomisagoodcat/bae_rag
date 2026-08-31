"""Generate entity_prompt.md and relation_prompt.md — bilingual review docs."""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1]
CHECK = Path(__file__).resolve().parent

SECTION_ZH = {
    "Tier": "层级",
    "Definition": "定义",
    "Extract when": "何时抽取",
    "Do not extract when": "何时不抽取",
    "Distinguish from": "与…区分",
    "Relations": "关系",
    "Example": "示例",
    "WHU_HASORIGINALTEXT scope": "WHU_HASORIGINALTEXT 范围",
    "Establishment gate": "建立门控",
    "If no Step": "若无 ResearchStep",
    "Expected low-level children": "预期基层子实体",
    "Low-level expansion": "基层扩展规则",
    "Structural dependency": "结构依赖",
    "Structural note": "结构说明",
    "Provenance": "溯源",
    "Naming": "命名规则",
    "Lexical rule": "词面规则",
    "Decision test": "判定测试",
    "Bare symbol rule": "裸符号规则",
    "Low-level rule": "基层规则",
    "Mandatory members": "必选成员",
    "No orphan rule": "禁止孤立节点",
    "WHU_HASORIGINALTEXT": "WHU_HASORIGINALTEXT",
    "Extract/construct when": "何时抽取/构建",
    "Extraction boundary": "抽取边界",
    "Direction": "方向",
    "Allowed schema patterns": "允许的 schema 模式",
    "Allowed targets": "允许的目标类型",
    "Allowed signatures": "允许的签名",
    "Mandatory pairing": "强制配对",
    "Constraint": "约束",
    "Emit iff": "发出条件",
    "Do not infer": "禁止推断",
    "Do not infer from": "禁止从…推断",
    "Do not use for": "不用于",
    "Type-selection order": "类型选择顺序",
    "Extraction rule": "抽取规则",
    "Extraction policy": "抽取策略",
    "Extraction note": "抽取说明",
    "Granularity rule": "粒度规则",
    "Lexical grounding for TargetVariable links": "TargetVariable 链接的词面锚定",
    "Co-occurrence gates": "共现门控",
    "Semantics": "语义",
    "Do not": "禁止",
    "Purpose": "用途",
    "Separate from support": "与支持关系区分",
    "ScienceEvidence/SupportGraph": "ScienceEvidence / SupportGraph",
    "Examples": "示例",
}

PROP_ZH = {
    "WHU_HASNAME": (
        "返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，"
        "不得添加原文未明确陈述的信息。不得返回完整句子。"
        "禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。"
    ),
    "WHU_HASNAME (TargetVariable)": (
        "返回基于原文的简短规范名称。名称须为 WHU_HASORIGINALTEXT 的逐字子串，"
        "或原文中连续出现的测量量名词短语。若原文仅出现化学符号或物质名（如 Sb、Hg），"
        "禁止扩写为 “Sb concentration”“Hg content” 等——应省略 TargetVariable。"
        "禁止推断单位；禁止插入维度词。禁止语义扩写。"
    ),
    "WHU_HASORIGINALTEXT (default)": (
        "复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；"
        "不得改写、概括、规范化或合并非连续片段。"
    ),
    "WHU_HASORIGINALTEXT (mid)": (
        "复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；"
        "不得改写、概括、规范化或合并非连续片段。"
        "中层：片段须覆盖建立该中层实体所需的完整连续证据。"
    ),
    "WHU_HASORIGINALTEXT (low)": (
        "复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；"
        "不得改写、概括、规范化或合并非连续片段。"
        "基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。"
    ),
    "WHU_RESEARCHTYPE": (
        "赋值唯一受控值：SpecimenCollection、SpecimenProcessing、BioChemical 或 Computational。"
        "须与 p_plan_isStepOfPlan 目标 Plan 类型一致。根据步骤 original_text 中的操作语义赋值，"
        "不得仅凭章节标题。"
    ),
    "whu_hascomparator": (
        "仅提取明确附于标量值的比较运算符或限定词，如 <、<=、>、>=、=、approximately；"
        "无比较符时返回 null/省略。"
    ),
    "iao_hasMeasurementUnit": (
        "按原文精确提取计量单位（如 ng/g、mg/L、%、°C）；抽取阶段不得换算单位。"
    ),
    "iao_hasMeasurementValue": (
        "仅提取数值部分（FLOAT），不含单位与比较符；保留报告数值，不得换算。"
    ),
    "whu_brand": "仅当原文明确陈述时提取软件厂商/提供商/品牌；不得从软件名推断。",
    "schema_softwareVersion": "按原文精确提取软件版本（如 4.2.2、R2021b）；无版本则省略。",
    "schema_hasBrand": "提取明确的设备品牌或制造商名称；不得从型号推断。",
    "schema_hasModel": "提取明确的设备型号，保留字母、连字符与数字。",
    "schema_hasSerialNumber": "仅当原文明确陈述时提取序列号或唯一仪器标识。",
    "gn_population": "提取与命名地理/环境要素关联的明确人口数；不得外部查询推断。",
    "geo_alt": "提取明确海拔/高程数值；不得从坐标推断。",
    "geo_lat": "提取明确纬度十进制数值。",
    "geo_long": "提取明确经度十进制数值。",
    "whu_is_about_dimension": (
        "可选的 aboutness 测量维度标签；仅从实现受控词表选择；"
        "仅当维度由原文单位/测量明确或可无歧义推出时赋值，否则省略。"
    ),
}


def split_sections(desc: str) -> list[tuple[str, str]]:
    parts = re.split(r"\n### ", desc.strip())
    sections: list[tuple[str, str]] = []
    for i, part in enumerate(parts):
        if i == 0 and part.startswith("### "):
            part = part[4:]
        if "\n" in part:
            title, body = part.split("\n", 1)
        else:
            title, body = part, ""
        sections.append((title.strip(), body.strip()))
    return sections


def section_block(title: str, body_en: str, body_zh: str) -> str:
    title_zh = SECTION_ZH.get(title, title)
    return (
        f"#### {title} / {title_zh}\n\n"
        f"**English**\n\n{body_en}\n\n"
        f"**中文**\n\n{body_zh}\n"
    )


def prop_block(prop: dict, parent_label: str) -> str:
    name = prop["name"]
    typ = prop.get("type", "")
    desc_en = prop.get("description", "").strip()
    if parent_label == "whu_TargetVariable" and name == "WHU_HASNAME":
        desc_zh = PROP_ZH["WHU_HASNAME (TargetVariable)"]
    elif name == "WHU_HASNAME":
        desc_zh = PROP_ZH["WHU_HASNAME"]
    elif name == "WHU_HASORIGINALTEXT":
        if "Mid-level:" in desc_en:
            desc_zh = PROP_ZH["WHU_HASORIGINALTEXT (mid)"]
        elif "Low-level:" in desc_en:
            desc_zh = PROP_ZH["WHU_HASORIGINALTEXT (low)"]
        else:
            desc_zh = PROP_ZH["WHU_HASORIGINALTEXT (default)"]
    elif name in PROP_ZH:
        desc_zh = PROP_ZH[name]
    else:
        desc_zh = "（见英文描述）"
    return (
        f"##### 属性 Property：`{name}`（`{typ}`）\n\n"
        f"**English**\n\n{desc_en}\n\n"
        f"**中文**\n\n{desc_zh}\n"
    )


def load_zh_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_md(
    items: list[dict],
    kind: str,
    zh_map: dict[str, dict[str, str]],
) -> str:
    title = "Entity" if kind == "entity" else "Relation"
    src = "entity.json" if kind == "entity" else "relation.json"
    label_key = "Neo4j Label" if kind == "entity" else "Relation Label"
    prop_label = "属性数量 Property count" if kind == "entity" else "关系属性数 Property count"

    lines = [
        f"# BAE {title} Schema — Description 审核稿",
        "",
        f"> **来源 Source：** `kg_build_pipeline/schema/{src}`  ",
        f"> **用途 Purpose：** 人工审核{('实体' if kind == 'entity' else '关系')}与属性 description（中英文对照）  ",
        "> **说明 Note：** English 为 JSON schema 原文；中文为审核对照译文。类名/关系名保留英文标签。",
        "",
        "## 目录 Table of Contents",
        "",
    ]
    for i, item in enumerate(items, 1):
        anchor = f"{i}-{item['label'].lower().replace('_', '-')}"
        lines.append(f"{i}. [`{item['label']}`](#{anchor})")
    lines.extend(["", "---", ""])

    for i, item in enumerate(items, 1):
        label = item["label"]
        anchor = f"{i}-{label.lower().replace('_', '-')}"
        sections = split_sections(item.get("description", ""))
        zh_sections = zh_map.get(label, {})

        lines.append(f"## {i}. `{label}` {{#{anchor}}}")
        lines.append("")
        lines.append("| 字段 Field | 值 Value |")
        lines.append("|:--|:--|")
        lines.append(f"| {label_key} | `{label}` |")
        lines.append(f"| {prop_label} | {len(item.get('properties') or [])} |")
        lines.append("")
        lines.append(f"### {title} Description {'实体描述' if kind == 'entity' else '关系描述'}")
        lines.append("")

        for title_s, body_en in sections:
            body_zh = zh_sections.get(title_s, "（本节中文对照见 `zh_sections.json`，或对照上方 English 审阅。）")
            lines.append(section_block(title_s, body_en, body_zh))
            lines.append("")

        props = item.get("properties") or []
        if props:
            lines.append("### 属性 Properties 属性描述" if kind == "entity" else "### 关系属性 Relation Properties")
            lines.append("")
            for p in props:
                lines.append(prop_block(p, label))
                lines.append("")

        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    entities = json.loads((SCHEMA / "entity.json").read_text(encoding="utf-8"))["entities"]
    relations = json.loads((SCHEMA / "relation.json").read_text(encoding="utf-8"))["relations"]
    zh_entities = load_zh_map(CHECK / "zh_entity_sections.json")
    zh_relations = load_zh_map(CHECK / "zh_relation_sections.json")

    (CHECK / "entity_prompt.md").write_text(build_md(entities, "entity", zh_entities), encoding="utf-8")
    (CHECK / "relation_prompt.md").write_text(build_md(relations, "relation", zh_relations), encoding="utf-8")
    print("Wrote entity_prompt.md and relation_prompt.md")
    if not zh_entities:
        print("Note: zh_entity_sections.json missing — run with translations")


if __name__ == "__main__":
    main()
