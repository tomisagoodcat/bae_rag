# BAE Entity Schema — Description 审核稿

> **来源 Source：** `kg_build_pipeline/schema/entity.json`  
> **用途 Purpose：** 人工审核实体与属性 description（中英文对照）  
> **说明 Note：** English 为 JSON schema 原文；中文为审核对照译文。类名/关系名保留英文标签。

## 目录 Table of Contents

1. [`mp_Attribution`](#1-mp-attribution)
2. [`mp_References`](#2-mp-references)
3. [`whu_Computational_Experiment`](#3-whu-computational-experiment)
4. [`envo_EnvironmentMaterial`](#4-envo-environmentmaterial)
5. [`whu_Reagent`](#5-whu-reagent)
6. [`iao_ScalarMeasurementDatum`](#6-iao-scalarmeasurementdatum)
7. [`whu_Software`](#7-whu-software)
8. [`whu_TargetVariable`](#8-whu-targetvariable)
9. [`whu_SpecimenCollection`](#9-whu-specimencollection)
10. [`mp_Claim`](#10-mp-claim)
11. [`whu_Goal`](#11-whu-goal)
12. [`mp_Statement`](#12-mp-statement)
13. [`whu_BioChemical_Experiment`](#13-whu-biochemical-experiment)
14. [`whu_Device`](#14-whu-device)
15. [`whu_EnvironmentFeature`](#15-whu-environmentfeature)
16. [`mp_Method`](#16-mp-method)
17. [`whu_SpecimenPreprocessing`](#17-whu-specimenpreprocessing)
18. [`whu_ProcessedSpecimen`](#18-whu-processedspecimen)
19. [`whu_DataSet`](#19-whu-dataset)
20. [`whu_Specimen`](#20-whu-specimen)
21. [`whu_ScienceEvidence`](#21-whu-scienceevidence)
22. [`whu_ResearchStep`](#22-whu-researchstep)
23. [`obi_organism`](#23-obi-organism)
24. [`whu_ChemicalEntity`](#24-whu-chemicalentity)
25. [`whu_SupportGraph`](#25-whu-supportgraph)
26. [`iao_DataItem`](#26-iao-dataitem)

---

## 1. `mp_Attribution` {#1-mp-attribution}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `mp_Attribution` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

`mp_Attribution` records who is responsible for, asserted, created, or curated another Representation. It is not the person or organization itself.

**中文**

`mp_Attribution` 记录谁对另一 Representation 负责、断言、创建或策展；它本身不是个人或组织实体。


#### Extract when / 何时抽取

**English**

Create only when the text explicitly identifies an accountable source in an attribution or argumentation chain, or when that Attribution will be a `prov_hadMember` of a SupportGraph.

**中文**

仅当文本在归因或论证链中明确指认可归责来源，或该 Attribution 将作为 SupportGraph 的 `prov_hadMember` 成员时创建。


#### Do not extract when / 何时不抽取

**English**

Do not create for vague agency (“researchers believe”) or inferred authorship from document metadata alone.

**中文**

不要为模糊主体（如“研究者认为”）创建，也不要仅凭文档元数据推断作者身份。


#### WHU_HASORIGINALTEXT / WHU_HASORIGINALTEXT

**English**

Must be the verbatim attribution fragment (e.g. “According to NOM-Lab…”).

**中文**

必须是逐字归因片段（例如“According to NOM-Lab…”）。


#### Relations / 关系

**English**

May mp_supports the qualified Representation; may be SupportGraph member.

**中文**

可 `mp_supports` 被限定的 Representation；可为 SupportGraph 成员。


#### Example / 示例

**English**

“According to the NOM-Lab at Southwest University, …” -> Attribution[NOM-Lab].

**中文**

“According to the NOM-Lab at Southwest University, …” → Attribution[NOM-Lab]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 2. `mp_References` {#2-mp-references}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `mp_References` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

`mp_References` is an explicitly cited bibliographic or external source record (author–year, numbered citation, DOI, URL).

**中文**

`mp_References` 是文本中明确引用的书目或外部来源记录（作者–年份、编号引用、DOI、URL）。


#### Extract when / 何时抽取

**English**

Create one identifiable Reference per cited source when it participates in citation or SupportGraph structure.

**中文**

当可识别的引用来源参与引用结构或 SupportGraph 时，为每个来源创建一个 Reference。


#### Do not extract when / 何时不抽取

**English**

Do not create for “previous studies” without an identifiable source. Do not merge multiple works into one Reference.

**中文**

不要为无具体来源的“以往研究”创建；不要将多篇文献合并为一个 Reference。


#### WHU_HASORIGINALTEXT / WHU_HASORIGINALTEXT

**English**

Must be the verbatim citation string from the text.

**中文**

必须是文本中的逐字引用字符串。


#### Relations / 关系

**English**

Reference -> `cito_isCitedBy` citing Representation; mp_supports only when used as evidential backing.

**中文**

Reference → `cito_isCitedBy` 引用它的 Representation；仅当作为证据支撑时才 `mp_supports`。


#### Example / 示例

**English**

“Biochar reduces Hg bioavailability (Smith et al., 2020).” -> Reference[Smith et al., 2020].

**中文**

“Biochar reduces Hg bioavailability (Smith et al., 2020).” → Reference[Smith et al., 2020]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 3. `whu_Computational_Experiment` {#3-whu-computational-experiment}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Computational_Experiment` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Mid-level (Plan). Establish at mid-level extraction with a defined WHU_HASORIGINALTEXT scope before low-level expansion.

**中文**

中层（Plan）。在中层抽取阶段建立，并先定义 WHU_HASORIGINALTEXT 范围，再进行基层扩展。


#### Definition / 定义

**English**

A `whu_Computational_Experiment` is a mid-level planned analytical module for statistical, computational, modeling, or data-transformation procedures, organized as a Plan rather than a single atomic step.

**中文**

`whu_Computational_Experiment` 是用于组织统计、计算、建模或数据变换程序的中层计划性分析模块，以 Plan 而非单一原子步骤建模。


#### WHU_HASORIGINALTEXT scope / WHU_HASORIGINALTEXT 范围

**English**

The smallest contiguous span describing the computational analysis unit (e.g. statistical tests, modeling procedure, simulation).

**中文**

描述该计算分析单元的最小连续片段（如统计检验、建模流程、模拟）。


#### Establishment gate / 建立门控

**English**

Create **only when** the same extraction context identifies **at least one** attributable Computational `whu_ResearchStep` with explicit operations (performed PCA, conducted regression, ran ANOVA). **Do not create an orphan Experiment.** Do not hallucinate Steps.

**中文**

仅当同一抽取上下文中识别出**至少一个**可归因的计算类 `whu_ResearchStep` 且含明确操作（performed PCA、conducted regression、ran ANOVA）时创建。**禁止创建孤立 Experiment。** 不得臆造 Step。


#### If no Step / 若无 ResearchStep

**English**

Do not create Computational_Experiment.

**中文**

不要创建 Computational_Experiment。


#### Expected low-level children / 预期基层子实体

**English**

Computational ResearchStep(s); Method/Software via declaredUsed; DataSet via declaredInput/Output—from this Experiment's original_text only.

**中文**

计算 ResearchStep；Method/Software 经 declaredUsed；DataSet 经 declaredInput/Output——均仅来自该 Experiment 的 original_text。


#### Relations / 关系

**English**

ResearchSteps -> `p_plan_isStepOfPlan`; optional `whu_hasGoal`; `whu_fellow` for mid-level adjacency.

**中文**

ResearchSteps → `p_plan_isStepOfPlan`；可选 `whu_hasGoal`；中层邻接用 `whu_fellow`。


#### Example / 示例

**English**

“PCA and Kruskal–Wallis tests were conducted in R 4.2.2.” -> Computational_Experiment with Computational ResearchStep(s).

**中文**

“PCA and Kruskal–Wallis tests were conducted in R 4.2.2.” → Computational_Experiment 及对应计算 ResearchStep(s)。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 4. `envo_EnvironmentMaterial` {#4-envo-environmentmaterial}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `envo_EnvironmentMaterial` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Extract from the WHU_HASORIGINALTEXT of a parent SpecimenCollection, SpecimenPreprocessing, or BioChemical_Experiment during low-level expansion.

**中文**

基层（基础型）。在从父级 SpecimenCollection、SpecimenPreprocessing 或 BioChemical_Experiment 的 WHU_HASORIGINALTEXT 进行基层扩展时抽取。


#### Definition / 定义

**English**

`envo_EnvironmentMaterial` is an ENVO-aligned **material phase or environmental matrix type** present in the environment (soil, sediment, pore water, air, particulate matter). It is a **category of substance**, not an individual collected sample, not a living organism, and not a named site.

**中文**

`envo_EnvironmentMaterial` 是与 ENVO 对齐的**物质相或环境基质类型**（土壤、沉积物、孔隙水、空气、颗粒物）。它是**物质类别**，不是单个采集样本，不是生物体，也不是命名地点。


#### Extract when / 何时抽取

**English**

Create when the text names the matrix/medium itself with substance-type semantics (surface soil, river water, overlying water).

**中文**

当文本以物质类型语义命名基质/介质本身时创建（如 surface soil、river water、overlying water）。


#### Do not extract when / 何时不抽取

**English**

- “soil samples / soil specimens / water sample” → `whu_Specimen`
- “rice plants / fish / bacteria” → `obi_organism`
- a named field, pond, station, or site → `whu_EnvironmentFeature`
- dried, sieved, digested, or otherwise processed sample products → `whu_ProcessedSpecimen`

**中文**

- “soil samples / soil specimens / water sample” → `whu_Specimen`
- “rice plants / fish / bacteria” → `obi_organism`
- 命名字段、池塘、站点或地点 → `whu_EnvironmentFeature`
- 干燥、筛分、消解等加工后的样品产物 → `whu_ProcessedSpecimen`


#### Naming / 命名规则

**English**

WHU_HASNAME must use the verbatim material phrase from the text. Do not append sample, specimen, or site words not present.

**中文**

WHU_HASNAME 必须使用文本中的逐字物质短语。不得附加原文未出现的 sample、specimen 或 site 等词。


#### Relations / 关系

**English**

`whu_EnvironmentFeature -> bfo_has_part -> envo_EnvironmentMaterial`; Specimen may `prov_wasDerivedFrom` EnvironmentMaterial; EnvironmentMaterial may `bfo_has_part` ChemicalEntity.

**中文**

`whu_EnvironmentFeature -> bfo_has_part -> envo_EnvironmentMaterial`；Specimen 可 `prov_wasDerivedFrom` EnvironmentMaterial；EnvironmentMaterial 可 `bfo_has_part` ChemicalEntity。


#### Example / 示例

**English**

“Surface soil was collected from the paddy field.” -> EnvironmentMaterial[surface soil]; EnvironmentFeature[paddy field] only if the field is named as a place.

**中文**

“Surface soil was collected from the paddy field.” → EnvironmentMaterial[surface soil]；仅当田地作为地点被命名时才建 EnvironmentFeature[paddy field]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 5. `whu_Reagent` {#5-whu-reagent}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Reagent` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_Reagent` is a chemical or biological reagent, standard, solution, reference material, buffer, or other consumable explicitly used in a recorded research step.

**中文**

`whu_Reagent` 是在已记录研究步骤中明确使用的化学或生物试剂、标准品、溶液、参考物质、缓冲液或其他消耗品。


#### Extract when / 何时抽取

**English**

Create a Reagent when the passage names the reagent or gives identifying details such as concentration, grade, supplier, or formulation.

**中文**

当段落命名试剂或给出浓度、等级、供应商、配方等识别信息时创建 Reagent。


#### Relations / 关系

**English**

Link it from the using `whu_ResearchStep` via `whu_declaredUsed`.

**中文**

从使用的 `whu_ResearchStep` 经 `whu_declaredUsed` 链接。


#### Example / 示例

**English**

“Samples were digested with 65% suprapure HNO3.” -> Reagent[65% suprapure HNO3].

**中文**

“Samples were digested with 65% suprapure HNO3.” → Reagent[65% suprapure HNO3]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 6. `iao_ScalarMeasurementDatum` {#6-iao-scalarmeasurementdatum}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `iao_ScalarMeasurementDatum` |
| 属性数量 Property count | 5 |

### Entity Description 实体描述

#### Definition / 定义

**English**

An `iao_ScalarMeasurementDatum` is a scalar measurement datum represented by a single numeric magnitude together with its measurement unit; it is treated as a subtype of `iao_DataItem`.

**中文**

`iao_ScalarMeasurementDatum` 是由单一数值及其计量单位表示的标量测量数据项，视为 `iao_DataItem` 的子类型。


#### Extract when / 何时抽取

**English**

Use this class when the passage reports a specific scalar value such as “28.4 ng/g”, optionally with an explicit comparator. If the record is categorical, composite, or not reducible to one scalar value plus unit, use `iao_DataItem`.

**中文**

当段落报告具体标量值（如“28.4 ng/g”），可选带明确比较符时使用。若记录为分类、复合或无法归约为“单值+单位”，则用 `iao_DataItem`。


#### Relations / 关系

**English**

Link to the measured/analyzed `whu_TargetVariable` via `iao_is_about`. A DataSet contains DataItem-level records via `dcterms_hasPart`.

**中文**

经 `iao_is_about` 链接被测/被分析的 `whu_TargetVariable`；DataSet 经 `dcterms_hasPart` 包含 DataItem 级记录。


#### Example / 示例

**English**

“Mean THg concentration was 28.4 ng/g.” -> ScalarMeasurementDatum[value=28.4, unit=ng/g] is_about TargetVariable[THg concentration].

**中文**

“Mean THg concentration was 28.4 ng/g.” → ScalarMeasurementDatum[value=28.4, unit=ng/g] is_about TargetVariable[THg concentration]。


### 属性 Properties 属性描述

##### 属性 Property：`whu_hascomparator`（`STRING`）

**English**

Extract only an explicit comparison operator or qualifier attached to the scalar value, e.g. '<', '<=', '>', '>=', '=', 'approximately'. Return null/omit when no comparator is stated.

**中文**

仅提取明确附于标量值的比较运算符或限定词，如 <、<=、>、>=、=、approximately；无比较符时返回 null/省略。


##### 属性 Property：`iao_hasMeasurementUnit`（`STRING`）

**English**

Extract the measurement unit exactly as written in the source text (e.g. ng/g, mg/L, %, °C). Do not convert or normalize units during extraction.

**中文**

按原文精确提取计量单位（如 ng/g、mg/L、%、°C）；抽取阶段不得换算单位。


##### 属性 Property：`iao_hasMeasurementValue`（`FLOAT`）

**English**

Extract only the numeric magnitude as a FLOAT, excluding the unit and comparator. Preserve the reported numerical value; do not perform unit conversion.

**中文**

仅提取数值部分（FLOAT），不含单位与比较符；保留报告数值，不得换算。


##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 7. `whu_Software` {#7-whu-software}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Software` |
| 属性数量 Property count | 4 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_Software` entity represents named software, a software package, computational environment, or analysis application explicitly used in a computational research step.

**中文**

`whu_Software` 表示在计算研究步骤中明确使用的命名软件、软件包、计算环境或分析应用。


#### Extract when / 何时抽取

**English**

Create Software when a software name is explicit; capture vendor/brand and version only when stated.

**中文**

当软件名称明确时创建 Software；仅在原文陈述时捕获厂商/品牌与版本。


#### Relations / 关系

**English**

Link from the using `whu_ResearchStep` via `whu_declaredUsed`.

**中文**

从使用的 `whu_ResearchStep` 经 `whu_declaredUsed` 链接。


#### Example / 示例

**English**

“Statistical analyses were performed in R version 4.2.2.” -> Software[R], version=4.2.2.

**中文**

“Statistical analyses were performed in R version 4.2.2.” → Software[R]，version=4.2.2。


### 属性 Properties 属性描述

##### 属性 Property：`whu_brand`（`STRING`）

**English**

Extract the software vendor, provider, or product brand only when explicitly stated. Do not infer a vendor from the software name.

**中文**

仅当原文明确陈述时提取软件厂商/提供商/品牌；不得从软件名推断。


##### 属性 Property：`schema_softwareVersion`（`STRING`）

**English**

Extract the software version/release exactly as stated (e.g. 4.2.2, 26, R2021b). Omit when no version is provided.

**中文**

按原文精确提取软件版本（如 4.2.2、R2021b）；无版本则省略。


##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 8. `whu_TargetVariable` {#8-whu-targetvariable}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_TargetVariable` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Extract only from parent mid-level original_text in Goal, DataSet, or measurement contexts.

**中文**

基层（基础型）。仅从父级中层 original_text 中的 Goal、DataSet 或测量语境抽取。


#### Definition / 定义

**English**

A `whu_TargetVariable` is a **measurable quantity or variable** being measured, analyzed, compared, or predicted. It must correspond to an explicit measurement-quantity expression in the text.

**中文**

`whu_TargetVariable` 是被测量、分析、比较或预测的**可测量量或变量**；必须对应文本中明确的测量量表达。


#### Extract when / 何时抽取

**English**

The text contains a complete measurement-quantity phrase (THg concentration, MeHg content, methylation rate) or a variable name explicitly tied to a reported unit in the same span.

**中文**

文本含完整测量量短语（THg concentration、MeHg content、methylation rate），或变量名在同一片段内与报告单位明确关联。


#### Do not extract when / 何时不抽取

**English**

- only a chemical symbol or substance name appears (Sb, mercury) → ChemicalEntity only
- concentration/content/level/rate must be inferred from domain knowledge → **do not extract**
- a Goal names an action without a measurement phrase → do not create TargetVariable or hasTarget link

**中文**

- 仅出现化学符号或物质名（Sb、mercury）→ 仅 ChemicalEntity
- concentration/content/level/rate 需凭领域知识推断 → **不要抽取**
- Goal 仅命名动作而无测量短语 → 不要创建 TargetVariable 或 hasTarget 链接


#### Lexical rule / 词面规则

**English**

WHU_HASNAME must be a verbatim substring of WHU_HASORIGINALTEXT or a contiguous measurement noun phrase present in the source. Never insert dimension words not in the text.

**中文**

WHU_HASNAME 必须是 WHU_HASORIGINALTEXT 的逐字子串，或原文中连续出现的测量名词短语。绝不可插入原文未出现的维度词。


#### Relations / 关系

**English**

Goal -> `whu_hasTarget` -> TargetVariable only when the measurement phrase is in the Goal original_text; TargetVariable -> `iao_is_about` -> ChemicalEntity when both are text-supported.

**中文**

仅当测量短语出现在 Goal original_text 中时，Goal → `whu_hasTarget` → TargetVariable；当二者均有文本支撑时，TargetVariable → `iao_is_about` → ChemicalEntity。


#### Example / 示例

**English**

“Hg concentration in rice grain was quantified.” -> TargetVariable[Hg concentration] is_about ChemicalEntity[Hg]. “Sb was analyzed.” -> ChemicalEntity[Sb] only; no TargetVariable.

**中文**

“Hg concentration in rice grain was quantified.” → TargetVariable[Hg concentration] is_about ChemicalEntity[Hg]。“Sb was analyzed.” → 仅 ChemicalEntity[Sb]；无 TargetVariable。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name grounded only in the source text. The name must appear verbatim in WHU_HASORIGINALTEXT or as a contiguous measurement-quantity noun phrase in the source. If the text only names a chemical symbol or substance (e.g. “Sb”, “Hg”), do NOT expand it to “Sb concentration”, “Hg content”, or similar—omit TargetVariable instead. No unit inference; no dimension-word insertion. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。名称须为 WHU_HASORIGINALTEXT 的逐字子串，或原文中连续出现的测量量名词短语。若原文仅出现化学符号或物质名（如 Sb、Hg），禁止扩写为 “Sb concentration”“Hg content” 等——应省略 TargetVariable。禁止推断单位；禁止插入维度词。禁止语义扩写。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 9. `whu_SpecimenCollection` {#9-whu-specimencollection}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_SpecimenCollection` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_SpecimenCollection` is a mid-level sampling Plan composed of one or more collection-type `whu_ResearchStep` instances and representing acquisition of a physical specimen from an environmental or biological source.

**中文**

`whu_SpecimenCollection` 是由一个或多个采集类 `whu_ResearchStep` 组成的中层采样 Plan，表示从环境或生物来源获取物理样本。


#### Extract when / 何时抽取

**English**

Create one when the passage describes a coherent sampling/collection procedure, including site, depth, timing, design, or sampling method.

**中文**

当段落描述连贯的采样/采集程序（含地点、深度、时间、设计或采样方法）时创建一个。


#### Relations / 关系

**English**

Collection ResearchSteps belong via `p_plan_isStepOfPlan` and produce `whu_Specimen` via `whu_declaredOutput`. The collection Plan links to its environmental context via `whu_hasContext`. At the plan-level shortcut view, an extracted Specimen may link back to the collection Plan through `p_plan_isOutputVarOf`.

**中文**

采集 ResearchStep 经 `p_plan_isStepOfPlan` 归属，并经 `whu_declaredOutput` 产出 `whu_Specimen`；采集 Plan 经 `whu_hasContext` 链接环境语境。在 plan 级快捷视图中，已抽取 Specimen 可经 `p_plan_isOutputVarOf` 回连采集 Plan。


#### Example / 示例

**English**

“Topsoil (0–20 cm) was collected from paddy fields using a stainless-steel auger.” -> SpecimenCollection; SpecimenCollection hasContext EnvironmentFeature[paddy field]; ResearchStep[collection] declaredOutput Specimen[topsoil].

**中文**

“Topsoil (0–20 cm) was collected from paddy fields using a stainless-steel auger.” → SpecimenCollection；SpecimenCollection hasContext EnvironmentFeature[paddy field]；ResearchStep[collection] declaredOutput Specimen[topsoil]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 10. `mp_Claim` {#10-mp-claim}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `mp_Claim` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

An `mp_Claim` is a principal scientific assertion functioning as the focal proposition in argumentation. It is more central than `mp_Statement`.

**中文**

`mp_Claim` 是论证中的核心科学断言，作为焦点命题；比 `mp_Statement` 更中心。


#### Extract when / 何时抽取

**English**

Create a Claim when the passage presents a principal conclusion, hypothesis, or interpretation that is—or will be within the same pass—organized in a `whu_SupportGraph` as the **focal** proposition.

**中文**

当段落呈现主要结论、假设或解释，且在同一轮抽取中将（或已经）作为 `whu_SupportGraph` 的**焦点**命题组织时创建 Claim。


#### Do not extract when / 何时不抽取

**English**

Use `mp_Statement` for ordinary observations or intermediate propositions that are not the focal claim of an argument graph.

**中文**

普通观察或中间命题、非论证图焦点时使用 `mp_Statement`。


#### Relations / 关系

**English**

May receive mp_supports/mp_challenges; must be prov_hadMember of SupportGraph when that graph is created.

**中文**

可接收 mp_supports/mp_challenges；创建 SupportGraph 时必须为 prov_hadMember。


#### Example / 示例

**English**

“Modified biochar significantly reduced MeHg production in paddy soil.” -> focal Claim in a SupportGraph.

**中文**

“Modified biochar significantly reduced MeHg production in paddy soil.” → SupportGraph 中的焦点 Claim。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 11. `whu_Goal` {#11-whu-goal}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Goal` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Mid-level adjunct (dependent on Experiment). Never extract as an isolated node.

**中文**

中层附属（依赖 Experiment）。绝不可作为孤立节点抽取。


#### Definition / 定义

**English**

A `whu_Goal` is an explicitly stated scientific objective of a BioChemical or Computational Experiment.

**中文**

`whu_Goal` 是 BioChemical 或 Computational Experiment 中明确陈述的科学目标。


#### Establishment gate / 建立门控

**English**

Create **only when** (1) a `whu_BioChemical_Experiment` or `whu_Computational_Experiment` is created in the **same extraction pass**, and (2) the text contains explicit objective language (to quantify, to assess, to compare, to determine, to predict, aimed to, in order to). The Goal **must** be linked by `whu_hasGoal` from that Experiment.

**中文**

仅当 (1) 同一抽取轮次创建了 `whu_BioChemical_Experiment` 或 `whu_Computational_Experiment`，且 (2) 文本含明确目标语言（to quantify、to assess、to compare、to determine、to predict、aimed to、in order to）时创建。Goal **必须**由该 Experiment 经 `whu_hasGoal` 链接。


#### Do not extract when / 何时不抽取

**English**

- no parent Experiment exists in the same pass
- only background motivation or significance is stated
- the objective is inferred rather than linguistically explicit

**中文**

- 同一轮次无父 Experiment
- 仅陈述背景动机或意义
- 目标靠推断而非语言显式表达


#### WHU_HASORIGINALTEXT / WHU_HASORIGINALTEXT

**English**

The objective clause itself. TargetVariable children only when the objective clause contains a verbatim measurement-quantity phrase.

**中文**

目标从句本身。仅当目标从句含逐字测量量短语时才建 TargetVariable 子节点。


#### Relations / 关系

**English**

Experiment -> `whu_hasGoal` -> Goal; Goal -> `whu_hasTarget` -> TargetVariable only with lexical support in the Goal span.

**中文**

Experiment → `whu_hasGoal` → Goal；仅当 Goal 片段有词面支撑时，Goal → `whu_hasTarget` → TargetVariable。


#### Example / 示例

**English**

“To quantify Hg concentration in rice grain.” -> Goal linked to BioChemical_Experiment; hasTarget only if “Hg concentration” appears in the goal clause.

**中文**

“To quantify Hg concentration in rice grain.” → Goal 链接 BioChemical_Experiment；仅当目标从句出现 “Hg concentration” 时才 hasTarget。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 12. `mp_Statement` {#12-mp-statement}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `mp_Statement` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

An `mp_Statement` is a complete proposition with evaluable content (observation, fact, interpretation, intermediate conclusion). A Claim is a specialized focal Statement.

**中文**

`mp_Statement` 是具有可评估内容的完整命题（观察、事实、解释、中间结论）。Claim 是特化的焦点 Statement。


#### Extract when / 何时抽取

**English**

Create when the passage expresses a complete proposition that may support or challenge a Claim but is **not** the focal Claim of a SupportGraph.

**中文**

当段落表达完整命题，可支持或挑战 Claim，但**不是** SupportGraph 的焦点 Claim 时创建。


#### Do not extract when / 何时不抽取

**English**

Do not create for fragments, headings, or non-propositional phrases.

**中文**

不要为片段、标题或非命题性短语创建。


#### Relations / 关系

**English**

May be `prov_hadMember` of SupportGraph as non-focal member; may mp_supports/mp_challenges Claims per schema.

**中文**

可作为 SupportGraph 的非焦点 `prov_hadMember`；按 schema 可 mp_supports/mp_challenges Claims。


#### Example / 示例

**English**

“Cadmium concentrations were higher in roots than in grains.” -> Statement supporting a focal Claim.

**中文**

“Cadmium concentrations were higher in roots than in grains.” → 支持焦点 Claim 的 Statement。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 13. `whu_BioChemical_Experiment` {#13-whu-biochemical-experiment}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_BioChemical_Experiment` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Mid-level (Plan). Establish at mid-level extraction with a defined WHU_HASORIGINALTEXT scope before low-level expansion.

**中文**

中层（Plan）。在中层抽取阶段建立，并先定义 WHU_HASORIGINALTEXT 范围，再进行基层扩展。


#### Definition / 定义

**English**

A `whu_BioChemical_Experiment` is a mid-level planned experimental module organizing one or more laboratory/biochemical/analytical `whu_ResearchStep` instances.

**中文**

`whu_BioChemical_Experiment` 是组织一个或多个实验室/生化/分析类 `whu_ResearchStep` 的中层计划性实验模块。


#### WHU_HASORIGINALTEXT scope / WHU_HASORIGINALTEXT 范围

**English**

The smallest contiguous span describing this experimental unit, including its method chain or analytical purpose in the same passage.

**中文**

描述该实验单元的最小连续片段，含同段中的方法链或分析目的。


#### Establishment gate / 建立门控

**English**

Create **only when** the same extraction context identifies **at least one** attributable `whu_ResearchStep` with explicit operations (digest, extract, measure, assay, quantify). **Do not create an orphan Experiment.** Do not hallucinate ResearchSteps to complete an Experiment.

**中文**

仅当同一抽取上下文识别出**至少一个**可归因 `whu_ResearchStep` 且含明确操作（digest、extract、measure、assay、quantify）时创建。**禁止创建孤立 Experiment。** 不得臆造 ResearchStep 以补全 Experiment。


#### If no Step / 若无 ResearchStep

**English**

Do not create BioChemical_Experiment; treat as incomplete mid-level extraction requiring text-scope review.

**中文**

不要创建 BioChemical_Experiment；视为需复核文本范围的不完整中层抽取。


#### Expected low-level children / 预期基层子实体

**English**

ResearchStep(s); optional Goal; Method/Device/Reagent via declaredUsed; Specimen/ProcessedSpecimen/DataSet via declaredInput/Output—all from this Experiment's original_text only.

**中文**

ResearchStep(s)；可选 Goal；Method/Device/Reagent 经 declaredUsed；Specimen/ProcessedSpecimen/DataSet 经 declaredInput/Output——均仅来自该 Experiment 的 original_text。


#### Low-level expansion / 基层扩展规则

**English**

Child steps and entities must be extracted from within this Experiment's WHU_HASORIGINALTEXT; do not span Chunks.

**中文**

子步骤与实体必须在该 Experiment 的 WHU_HASORIGINALTEXT 内抽取；不得跨 Chunk。


#### Relations / 关系

**English**

ResearchSteps -> `p_plan_isStepOfPlan` -> Experiment; optional `whu_hasGoal`; `whu_fellow` for mid-level adjacency only.

**中文**

ResearchSteps → `p_plan_isStepOfPlan` → Experiment；可选 `whu_hasGoal`；`whu_fellow` 仅用于中层邻接。


#### Example / 示例

**English**

“THg and MeHg were quantified by CVAFS after acid digestion.” -> BioChemical_Experiment with digestion and measurement ResearchSteps in the same pass.

**中文**

“THg and MeHg were quantified by CVAFS after acid digestion.” → 同一轮次含消解与测量 ResearchStep 的 BioChemical_Experiment。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 14. `whu_Device` {#14-whu-device}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Device` |
| 属性数量 Property count | 5 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_Device` is a scientific instrument, measurement device, processing apparatus, or laboratory tool explicitly used in a ResearchStep.

**中文**

`whu_Device` 是在 ResearchStep 中明确使用的科学仪器、测量设备、处理装置或实验室工具。


#### Extract when / 何时抽取

**English**

Create a Device when a concrete instrument/tool is named. Capture brand/manufacturer, model, and serial number only if explicitly stated.

**中文**

当命名具体仪器/工具时创建 Device；仅在原文明确陈述时捕获品牌/制造商、型号、序列号。


#### Relations / 关系

**English**

Link from the using `whu_ResearchStep` via `whu_declaredUsed`.

**中文**

从使用的 `whu_ResearchStep` 经 `whu_declaredUsed` 链接。


#### Example / 示例

**English**

“Samples were analyzed using an Agilent 7700 ICP-MS.” -> Device[Agilent 7700 ICP-MS].

**中文**

“Samples were analyzed using an Agilent 7700 ICP-MS.” → Device[Agilent 7700 ICP-MS]。


### 属性 Properties 属性描述

##### 属性 Property：`schema_hasBrand`（`STRING`）

**English**

Extract the explicit device brand or manufacturer name. Do not infer it from a model code.

**中文**

提取明确的设备品牌或制造商名称；不得从型号推断。


##### 属性 Property：`schema_hasModel`（`STRING`）

**English**

Extract the explicit device model designation, preserving letters, hyphens, and numbers.

**中文**

提取明确的设备型号，保留字母、连字符与数字。


##### 属性 Property：`schema_hasSerialNumber`（`STRING`）

**English**

Extract a serial number or unique instrument identifier only when explicitly stated.

**中文**

仅当原文明确陈述时提取序列号或唯一仪器标识。


##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 15. `whu_EnvironmentFeature` {#15-whu-environmentfeature}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_EnvironmentFeature` |
| 属性数量 Property count | 6 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). In Mid→Low extraction, extract from the WHU_HASORIGINALTEXT of a parent `whu_SpecimenCollection` or field `whu_ResearchStep`.

**中文**

基层（基础型）。在中→低抽取中，从父级 `whu_SpecimenCollection` 或野外 `whu_ResearchStep` 的 WHU_HASORIGINALTEXT 抽取。


#### Definition / 定义

**English**

A `whu_EnvironmentFeature` is a named, locatable environmental place or geographic-ecological unit (field, wetland, river reach, sampling station, experimental site). It denotes **WHERE** something occurs or is sampled, not **WHAT** was collected.

**中文**

`whu_EnvironmentFeature` 是具名、可定位的环境地点或地理–生态单元（田地、湿地、河段、采样站、实验站点）。表示**在何处**发生或采样，而非**采集了什么**。


#### Extract when / 何时抽取

**English**

Create one when the text names a site/place/location and uses it as the environmental setting for sampling, organism location, or a recorded field ResearchStep. Coordinates may be captured as properties when explicit.

**中文**

当文本命名站点/地点/位置，并将其作为采样、生物体位置或已记录野外 ResearchStep 的环境背景时创建一个。坐标可在原文明确时作为属性捕获。


#### Do not extract when / 何时不抽取

**English**

- The phrase refers to a **collected individual sample** → use `whu_Specimen` or `whu_ProcessedSpecimen`.
- The phrase names an **environmental matrix/substance** without an independent place name (soil, water, sediment) → use `envo_EnvironmentMaterial`.
- The phrase refers to a **living organism** → use `obi_organism`.
- The text only says material was collected (e.g. “soil was collected”) without a distinct place name → use Specimen + EnvironmentMaterial, **not** EnvironmentFeature, unless a separate site name is explicit (e.g. “from the SWU paddy field”).

**中文**

- 短语指**已采集的单个样本** → 用 `whu_Specimen` 或 `whu_ProcessedSpecimen`
- 短语命名**环境基质/物质**而无独立地名（soil、water、sediment）→ 用 `envo_EnvironmentMaterial`
- 短语指**生物体** → 用 `obi_organism`
- 文本仅说采集了材料（如“soil was collected”）而无 distinct 地名 → 用 Specimen + EnvironmentMaterial，**不要**建 EnvironmentFeature，除非另有明确站点名（如“from the SWU paddy field”）


#### Decision test / 判定测试

**English**

Can the phrase replace X in “at/from the [X]” where X remains a place? If not, do not use EnvironmentFeature.

**中文**

该短语能否替换 X 于“at/from the [X]”且 X 仍为地点？若不能，则不要用 EnvironmentFeature。


#### Relations / 关系

**English**

EnvironmentFeature -> `bfo_has_part` -> EnvironmentMaterial expresses site-level containment of a material phase, not sampling provenance. SpecimenCollection -> `whu_hasContext` -> EnvironmentFeature; organism/ResearchStep may -> `prov_atLocation` -> EnvironmentFeature. A Specimen may `prov_wasDerivedFrom` EnvironmentFeature only when the site itself is stated as the provenance source and no more specific material or organism source is supported.

**中文**

EnvironmentFeature → `bfo_has_part` → EnvironmentMaterial 表示站点级物质相包含，而非采样溯源。SpecimenCollection → `whu_hasContext` → EnvironmentFeature；organism/ResearchStep 可 → `prov_atLocation` → EnvironmentFeature。仅当站点本身被陈述为溯源来源且无更具体的物质/生物来源支撑时，Specimen 可 `prov_wasDerivedFrom` EnvironmentFeature。


#### Example / 示例

**English**

“Topsoil was sampled from the SWU paddy field (29.8°N, 106.4°E).” -> EnvironmentFeature[SWU paddy field]; Specimen[topsoil] wasDerivedFrom EnvironmentMaterial[surface soil] or EnvironmentFeature as text supports.

**中文**

“Topsoil was sampled from the SWU paddy field (29.8°N, 106.4°E).” → EnvironmentFeature[SWU paddy field]；Specimen[topsoil] wasDerivedFrom EnvironmentMaterial[surface soil] 或 EnvironmentFeature，依文本支撑。


### 属性 Properties 属性描述

##### 属性 Property：`gn_population`（`INTEGER`）

**English**

Extract an explicitly stated population count associated with the named geographic/environmental feature. Do not infer or look up population externally.

**中文**

提取与命名地理/环境要素关联的明确人口数；不得外部查询推断。


##### 属性 Property：`geo_alt`（`FLOAT`）

**English**

Extract explicit altitude/elevation as a numeric value. Use the value as stated; do not infer from coordinates.

**中文**

提取明确海拔/高程数值；不得从坐标推断。


##### 属性 Property：`geo_lat`（`FLOAT`）

**English**

Extract explicit latitude as a decimal numeric value when present in the text.

**中文**

提取明确纬度十进制数值。


##### 属性 Property：`geo_long`（`FLOAT`）

**English**

Extract explicit longitude as a decimal numeric value when present in the text.

**中文**

提取明确经度十进制数值。


##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 16. `mp_Method` {#16-mp-method}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `mp_Method` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

An `mp_Method` is a named or describable scientific method, protocol, analytical technique, statistical procedure, or standard represented as information content rather than as a physical device.

**中文**

`mp_Method` 是作为信息内容而非物理设备表示的命名或可描述科学方法、协议、分析技术、统计程序或标准。


#### Extract when / 何时抽取

**English**

Create a Method for methods such as ICP-MS analysis, EPA 3052 digestion protocol, PCA, regression, or a named standard/procedure.

**中文**

为 ICP-MS 分析、EPA 3052 消解协议、PCA、回归或命名标准/程序等方法创建 Method。


#### Distinguish from / 与…区分

**English**

Use `whu_Device` for the physical instrument and `whu_Software` for the software implementation.

**中文**

物理仪器用 `whu_Device`；软件实现用 `whu_Software`。


#### Relations / 关系

**English**

Link from the using ResearchStep via `whu_declaredUsed`. A Method may be aggregated with a DataSet in `whu_ScienceEvidence` via `prov_hadMember`.

**中文**

从使用的 ResearchStep 经 `whu_declaredUsed` 链接。Method 可与 DataSet 在 `whu_ScienceEvidence` 中经 `prov_hadMember` 聚合。


#### Example / 示例

**English**

“Digestion followed EPA 3052.” -> Method[EPA 3052].

**中文**

“Digestion followed EPA 3052.” → Method[EPA 3052]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 17. `whu_SpecimenPreprocessing` {#17-whu-specimenpreprocessing}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_SpecimenPreprocessing` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_SpecimenPreprocessing` is a mid-level preparation Plan composed of one or more preprocessing-type ResearchSteps that transform a raw `whu_Specimen` into a `whu_ProcessedSpecimen`.

**中文**

`whu_SpecimenPreprocessing` 是由一个或多个预处理类 ResearchStep 组成的中层制备 Plan，将原始 `whu_Specimen` 转化为 `whu_ProcessedSpecimen`。


#### Extract when / 何时抽取

**English**

Create one for coherent preparation procedures such as drying, grinding, sieving, filtration, preservation, digestion, or extraction before downstream analysis.

**中文**

为干燥、研磨、筛分、过滤、保存、消解、提取等连贯制备程序（下游分析前）创建一个。


#### Relations / 关系

**English**

ResearchSteps belong via `p_plan_isStepOfPlan`; they use `whu_declaredInput` for the raw Specimen and `whu_declaredOutput` for the ProcessedSpecimen. `whu_fellow(X,Y)` means the upstream SpecimenCollection is Y when preprocessing X follows collection.

**中文**

ResearchStep 经 `p_plan_isStepOfPlan` 归属；对 raw Specimen 用 `whu_declaredInput`，对 ProcessedSpecimen 用 `whu_declaredOutput`。`whu_fellow(X,Y)` 表示当预处理 X 在采集 Y 之后时，上游 SpecimenCollection 为 Y。


#### Example / 示例

**English**

“Soils were air-dried, ground, and passed through a 2-mm sieve.” -> SpecimenPreprocessing with corresponding ResearchStep(s).

**中文**

“Soils were air-dried, ground, and passed through a 2-mm sieve.” → 含对应 ResearchStep(s) 的 SpecimenPreprocessing。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 18. `whu_ProcessedSpecimen` {#18-whu-processedspecimen}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_ProcessedSpecimen` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Extract from the WHU_HASORIGINALTEXT of `whu_SpecimenPreprocessing` or `whu_BioChemical_Experiment`.

**中文**

基层（基础型）。从 `whu_SpecimenPreprocessing` 或 `whu_BioChemical_Experiment` 的 WHU_HASORIGINALTEXT 抽取。


#### Definition / 定义

**English**

A `whu_ProcessedSpecimen` is a **specific sample after a recorded preprocessing step** (dried soil, sieved powder, acid digest, extract, filtrate, homogenized tissue).

**中文**

`whu_ProcessedSpecimen` 是**经已记录预处理步骤后的具体样本**（干燥土壤、筛分粉末、酸消解液、提取液、滤液、均质组织等）。


#### Extract when / 何时抽取

**English**

The text names a prepared sample product resulting from an explicit processing operation in the same parent original_text.

**中文**

当文本在同一父级 original_text 中命名由明确加工操作产生的制备样品产物时创建。


#### Do not extract when / 何时不抽取

**English**

- only a generic matrix type is named without processing evidence → EnvironmentMaterial or Specimen
- only a site or organism is named → EnvironmentFeature or organism
- no ResearchStep(SpecimenProcessing) or wasDerivedFrom Specimen evidence exists in the same extraction context → do not create ProcessedSpecimen in low-level expansion

**中文**

- 仅命名通用基质类型而无加工证据 → EnvironmentMaterial 或 Specimen
- 仅命名站点或生物体 → EnvironmentFeature 或 organism
- 同一抽取上下文无 ResearchStep(SpecimenProcessing) 或 wasDerivedFrom Specimen 证据 → 基层扩展中不要创建 ProcessedSpecimen


#### Structural note / 结构说明

**English**

Should be supported by a SpecimenProcessing ResearchStep `whu_declaredOutput` or `prov_wasDerivedFrom` Specimen. Do not hallucinate ProcessedSpecimen to complete a preprocessing chain.

**中文**

应由 SpecimenProcessing ResearchStep 的 `whu_declaredOutput` 或 `prov_wasDerivedFrom` Specimen 支撑。不得臆造 ProcessedSpecimen 以补全预处理链。


#### Relations / 关系

**English**

ProcessedSpecimen -> `prov_wasDerivedFrom` -> Specimen; linked via declaredInput/declaredOutput to ResearchSteps; may `p_plan_isOutputVarOf` SpecimenPreprocessing and `p_plan_isInputVarOf` BioChemical_Experiment.

**中文**

ProcessedSpecimen → `prov_wasDerivedFrom` → Specimen；经 declaredInput/declaredOutput 链接 ResearchStep；可 `p_plan_isOutputVarOf` SpecimenPreprocessing 且 `p_plan_isInputVarOf` BioChemical_Experiment。


#### Example / 示例

**English**

“Dried and sieved soil powder was used for Hg determination.” -> ProcessedSpecimen[dried and sieved soil powder].

**中文**

“Dried and sieved soil powder was used for Hg determination.” → ProcessedSpecimen[dried and sieved soil powder]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 19. `whu_DataSet` {#19-whu-dataset}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_DataSet` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

A `whu_DataSet` is a scientific data collection generated by or used in one or more ResearchSteps. In BAE it carries both dataset semantics and an evidential/argumentative role.

**中文**

`whu_DataSet` 是在一个或多个 ResearchStep 中生成或使用的科学数据集合。在 BAE 中同时承载数据集语义与证据/论证角色。


#### Extract when / 何时抽取

**English**

Create a DataSet when the passage explicitly reports a coherent data artifact such as a table, figure, measurement set, spectrum set, modeled result set, or analysis output.

**中文**

当段落明确报告连贯数据产物（表格、图、测量集、谱图集、建模结果集、分析输出等）时创建 DataSet。


#### Relations / 关系

**English**

ResearchStep -> `whu_declaredInput`/`whu_declaredOutput` -> DataSet. At the plan-level shortcut view, a DataSet may `p_plan_isOutputVarOf` a Computational_Experiment where the text directly presents the experiment-level output. DataSet -> `dcterms_hasPart` -> DataItem.

`iao_is_about` may be used at two complementary levels:
- DataSet -> Reagent / Specimen / ProcessedSpecimen, when the dataset concerns those research resources;
- DataSet -> TargetVariable, when the dataset concerns a measured/analyzed target variable.
DataItem/ScalarMeasurementDatum may also `iao_is_about` TargetVariable at finer granularity.

ScienceEvidence -> `prov_hadMember` -> DataSet. A DataSet may directly `mp_supports`/`mp_challenges` a Claim or Statement only when the text explicitly establishes that argumentative relation.

**中文**

ResearchStep → `whu_declaredInput`/`whu_declaredOutput` → DataSet。在 plan 级快捷视图中，当文本直接呈现实验级输出时，DataSet 可 `p_plan_isOutputVarOf` Computational_Experiment。DataSet → `dcterms_hasPart` → DataItem。

`iao_is_about` 可在两个互补层级使用：
- DataSet → Reagent / Specimen / ProcessedSpecimen，当数据集涉及这些研究资源；
- DataSet → TargetVariable，当数据集涉及被测/被分析目标变量。
DataItem/ScalarMeasurementDatum 也可在更细粒度 `iao_is_about` TargetVariable。

ScienceEvidence → `prov_hadMember` → DataSet。仅当文本明确建立该论证关系时，DataSet 才可直链 `mp_supports`/`mp_challenges` Claim 或 Statement。


#### Example / 示例

**English**

“Figure 4 reports MeHg concentrations in rice tissues after biochar treatment.” -> DataSet[Figure 4 MeHg concentrations], which may be about the relevant Specimen and TargetVariable when those links are textually supported.

**中文**

“Figure 4 reports MeHg concentrations in rice tissues after biochar treatment.” → DataSet[Figure 4 MeHg concentrations]；当链接有文本支撑时可 about 相关 Specimen 与 TargetVariable。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---

## 20. `whu_Specimen` {#20-whu-specimen}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_Specimen` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Primarily extract from the WHU_HASORIGINALTEXT of `whu_SpecimenCollection` during low-level expansion.

**中文**

基层（基础型）。主要从 `whu_SpecimenCollection` 的 WHU_HASORIGINALTEXT 在基层扩展时抽取。


#### Definition / 定义

**English**

A `whu_Specimen` is a **specific physical sample** obtained by collection—an individual countable research object (soil samples, rice grain, fish tissue, water sample) that enters preparation or analysis.

**中文**

`whu_Specimen` 是采集获得的**具体物理样本**——可计数的个体研究对象（soil samples、rice grain、fish tissue、water sample），进入制备或分析流程。


#### Extract when / 何时抽取

**English**

The text uses sample/specimen/tissue/grain or similar collected-object language, or explicitly describes material that was collected/taken.

**中文**

文本使用 sample/specimen/tissue/grain 等采集对象语言，或明确描述被采集/取样的材料时创建。


#### Do not extract when / 何时不抽取

**English**

- only a place/site is named → EnvironmentFeature
- only a matrix type without individual sample semantics → EnvironmentMaterial
- the material is explicitly post-preprocessing (dried, sieved, digest, extract) → ProcessedSpecimen

**中文**

- 仅命名地点/站点 → EnvironmentFeature
- 仅基质类型而无个体样本语义 → EnvironmentMaterial
- 材料明确为加工后（dried、sieved、digest、extract）→ ProcessedSpecimen


#### Provenance / 溯源

**English**

Specimen may `prov_wasDerivedFrom` the most specific supported source: organism > EnvironmentMaterial > EnvironmentFeature. Do not relabel a source node as Specimen because a Specimen links to it.

**中文**

Specimen 可 `prov_wasDerivedFrom` 最具体且有支撑的来源：organism > EnvironmentMaterial > EnvironmentFeature。勿因 Specimen 链接某节点而将该来源节点改标为 Specimen。


#### Naming / 命名规则

**English**

Use the verbatim collected-object phrase (e.g. “soil samples”). Do not expand into site or material class names not in the text.

**中文**

使用逐字采集对象短语（如“soil samples”）。勿扩写为原文未出现的站点或物质类名。


#### Relations / 关系

**English**

ResearchSteps connect via `whu_declaredOutput` (collection) and `whu_declaredInput` (preprocessing/analysis). Specimen may `p_plan_isOutputVarOf` SpecimenCollection and `p_plan_isInputVarOf` SpecimenPreprocessing.

**中文**

ResearchStep 经 `whu_declaredOutput`（采集）与 `whu_declaredInput`（预处理/分析）连接。Specimen 可 `p_plan_isOutputVarOf` SpecimenCollection 且 `p_plan_isInputVarOf` SpecimenPreprocessing。


#### Example / 示例

**English**

“Soil samples were collected from the paddy field.” -> Specimen[soil samples]; wasDerivedFrom EnvironmentFeature[paddy field] when only the site is explicit.

**中文**

“Soil samples were collected from the paddy field.” → Specimen[soil samples]；仅当站点明确时 wasDerivedFrom EnvironmentFeature[paddy field]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 21. `whu_ScienceEvidence` {#21-whu-scienceevidence}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_ScienceEvidence` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Mid-level argumentative composite. Requires co-occurring argument structure.

**中文**

中层论证复合体。需要共现的论证结构。


#### Definition / 定义

**English**

A `whu_ScienceEvidence` binds identifiable data/results with method/analytical basis in an explicit argumentative role.

**中文**

`whu_ScienceEvidence` 在明确论证角色中将可识别数据/结果与方法/分析基础绑定。


#### Establishment gate / 建立门控

**English**

Create only when **all** hold in the same argumentative original_text:
1. identifiable DataSet or results reference
2. identifiable Method or analytical basis
3. explicit argumentative connector (support, demonstrate, indicate, contradict, challenge, etc.)
4. a co-created `whu_SupportGraph` in the same pass, with ScienceEvidence linked via `mp_supports`/`mp_challenges` to that SupportGraph and/or its focal Claim (not via `prov_hadMember`)

**中文**

仅当同一论证 original_text 中**全部**满足时创建：
1. 可识别 DataSet 或结果引用
2. 可识别 Method 或分析基础
3. 明确论证连接词（support、demonstrate、indicate、contradict、challenge 等）
4. 同一轮次共创建 `whu_SupportGraph`，且 ScienceEvidence 经 `mp_supports`/`mp_challenges` 链接到该 SupportGraph 和/或其焦点 Claim（**不要**用 `prov_hadMember`）


#### Do not extract when / 何时不抽取

**English**

- data are reported without argumentative role → DataSet only
- no focal Claim and no SupportGraph can be co-created
- Method and DataSet merely co-occur without argumentative language

**中文**

- 仅报告数据而无论证角色 → 仅 DataSet
- 无法共创建焦点 Claim 与 SupportGraph
- Method 与 DataSet 仅共现而无论证语言


#### No orphan rule / 禁止孤立节点

**English**

Do not create ScienceEvidence first and add SupportGraph later. Do not hallucinate members to complete evidence. Do not use SupportGraph -> `prov_hadMember` -> ScienceEvidence.

**中文**

不要先建 ScienceEvidence 后补 SupportGraph。不要臆造成员以补全证据。不要使用 SupportGraph → `prov_hadMember` → ScienceEvidence。


#### WHU_HASORIGINALTEXT / WHU_HASORIGINALTEXT

**English**

Smallest contiguous span containing evidential content **and** the argumentative connector.

**中文**

包含证据内容与论证连接词的最小连续片段。


#### Example / 示例

**English**

“CVAFS measurements showed a 42% decrease in grain MeHg, supporting the biochar hypothesis.” -> ScienceEvidence mp_supports Claim/SupportGraph; SupportGraph hadMember Claim (not ScienceEvidence).

**中文**

“CVAFS measurements showed a 42% decrease in grain MeHg, supporting the biochar hypothesis.” → ScienceEvidence mp_supports Claim/SupportGraph；SupportGraph hadMember Claim（不是 ScienceEvidence）。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 22. `whu_ResearchStep` {#22-whu-researchstep}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_ResearchStep` |
| 属性数量 Property count | 3 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level relative to parent Plan/Experiment. Extract only from the parent mid-level WHU_HASORIGINALTEXT.

**中文**

相对父 Plan/Experiment 为基层。仅从父级中层 WHU_HASORIGINALTEXT 抽取。


#### Definition / 定义

**English**

A `whu_ResearchStep` is the atomic recorded operation in a research workflow, modeled as `p-plan:Step`.

**中文**

`whu_ResearchStep` 是研究工作流中建模为 `p-plan:Step` 的原子记录操作。


#### Structural dependency / 结构依赖

**English**

Every ResearchStep **must** link via `p_plan_isStepOfPlan` to exactly one mid-level Plan (SpecimenCollection, SpecimenPreprocessing, BioChemical_Experiment, or Computational_Experiment). **Orphan ResearchSteps are forbidden.**

**中文**

每个 ResearchStep **必须**经 `p_plan_isStepOfPlan` 链接到恰好一个中层 Plan（SpecimenCollection、SpecimenPreprocessing、BioChemical_Experiment 或 Computational_Experiment）。**禁止孤立 ResearchStep。**


#### Extract when / 何时抽取

**English**

The parent original_text contains a single verb-driven operation (collected, dried, digested, measured, analyzed, performed PCA).

**中文**

父级 original_text 含单一动词驱动操作（collected、dried、digested、measured、analyzed、performed PCA）时抽取。


#### Do not extract when / 何时不抽取

**English**

- only an experiment module title or method name appears without an operational clause → do not create Step or parent Experiment
- the operation cannot be assigned to a parent Plan in the same extraction pass

**中文**

- 仅出现实验模块标题或方法名而无操作从句 → 不要创建 Step 或父 Experiment
- 操作无法在同一抽取轮次分配到父 Plan


#### Relations / 关系

**English**

declaredUsed/declaredInput/declaredOutput; `p_plan_isPrecededBy`; `prov_atLocation` when site is explicit for the step.

**中文**

declaredUsed/declaredInput/declaredOutput；`p_plan_isPrecededBy`；步骤站点明确时用 `prov_atLocation`。


#### Example / 示例

**English**

“After sieving, soil was digested with HNO3 and Hg was measured by CVAFS.” -> separate ResearchSteps within the same parent Experiment original_text.

**中文**

“After sieving, soil was digested with HNO3 and Hg was measured by CVAFS.” → 同一父 Experiment original_text 内的多个 ResearchStep。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


##### 属性 Property：`WHU_RESEARCHTYPE`（`STRING`）

**English**

Assign exactly one value: 'SpecimenCollection', 'SpecimenProcessing', 'BioChemical', or 'Computational'. Must be consistent with the p_plan_isStepOfPlan target Plan type. Choose from the described operation in the step's original_text, not from section title alone.

**中文**

赋值唯一受控值：SpecimenCollection、SpecimenProcessing、BioChemical 或 Computational。须与 p_plan_isStepOfPlan 目标 Plan 类型一致。根据步骤 original_text 中的操作语义赋值，不得仅凭章节标题。


---

## 23. `obi_organism` {#23-obi-organism}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `obi_organism` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Extract only when the parent mid-level WHU_HASORIGINALTEXT contains an explicit biological referent.

**中文**

基层（基础型）。仅当父级中层 WHU_HASORIGINALTEXT 含明确生物指称时抽取。


#### Definition / 定义

**English**

`obi_organism` is a living biological individual, species, or population explicitly mentioned (plant, animal, microorganism). It denotes the **living source**, not its collected tissues, secretions, or environmental matrix.

**中文**

`obi_organism` 是明确提及的活的生物个体、物种或群体（植物、动物、微生物）。表示**活体来源**，而非其采集组织、分泌物或环境基质。


#### Extract when / 何时抽取

**English**

Create when a taxon, species, cultivar, or biological group is named as a living entity (rice plants, common carp, E. coli).

**中文**

当分类单元、物种、 cultivar 或生物群作为活体实体被命名时创建（rice plants、common carp、E. coli）。


#### Do not extract when / 何时不抽取

**English**

- grain, root tissue, fish muscle, leaf sample → `whu_Specimen` (Specimen may `prov_wasDerivedFrom` organism)
- soil, sediment, water → `envo_EnvironmentMaterial`
- field, wetland, pond → `whu_EnvironmentFeature`

**中文**

- grain、root tissue、fish muscle、leaf sample → `whu_Specimen`（Specimen 可 `prov_wasDerivedFrom` organism）
- soil、sediment、water → `envo_EnvironmentMaterial`
- field、wetland、pond → `whu_EnvironmentFeature`


#### Low-level rule / 基层规则

**English**

Do not infer an organism from chemical-analysis context when no biological referent appears in the parent mid-level original_text.

**中文**

当父级中层 original_text 无生物指称时，不要从化学分析语境推断 organism。


#### Relations / 关系

**English**

Specimen -> `prov_wasDerivedFrom` -> organism; organism -> `prov_atLocation` -> EnvironmentFeature; organism -> `bfo_has_part` -> ChemicalEntity when constituent presence is explicit.

**中文**

Specimen → `prov_wasDerivedFrom` → organism；organism → `prov_atLocation` → EnvironmentFeature；成分存在明确时 organism → `bfo_has_part` → ChemicalEntity。


#### Example / 示例

**English**

“Rice plants grown in the paddy field were sampled for grain.” -> organism[rice plants]; Specimen[grain] wasDerivedFrom organism.

**中文**

“Rice plants grown in the paddy field were sampled for grain.” → organism[rice plants]；Specimen[grain] wasDerivedFrom organism。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 24. `whu_ChemicalEntity` {#24-whu-chemicalentity}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_ChemicalEntity` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Low-level (foundational). Extract only from the parent mid-level WHU_HASORIGINALTEXT; do not use external chemical knowledge.

**中文**

基层（基础型）。仅从父级中层 WHU_HASORIGINALTEXT 抽取；勿用外部化学知识。


#### Definition / 定义

**English**

A `whu_ChemicalEntity` is a chemical element, ion, compound, or identifiable substance **as named in the text** (Hg, MeHg, Sb, Cd²⁺). It is the **substance entity**, not a measured quantity.

**中文**

`whu_ChemicalEntity` 是文本中**按名出现**的化学元素、离子、化合物或可识别物质（Hg、MeHg、Sb、Cd²⁺）。它是**物质实体**，不是测量量。


#### Extract when / 何时抽取

**English**

The text names a chemical symbol, formula, or compound with substance semantics.

**中文**

当文本以物质语义命名化学符号、分子式或化合物时创建。


#### Do not extract when / 何时不抽取

**English**

- the phrase includes measurement-dimension words (concentration, content, level, rate, flux, amount) → `whu_TargetVariable` only if the full measurement phrase appears verbatim; otherwise omit TargetVariable
- only a measured value with unit appears without a separable substance name → handle via ScalarMeasurementDatum/DataItem, not ChemicalEntity alone

**中文**

- 短语含测量维度词（concentration、content、level、rate、flux、amount）→ 仅当完整测量短语逐字出现时才用 `whu_TargetVariable`；否则省略 TargetVariable
- 仅出现带单位的测量值而无可分物质名 → 经 ScalarMeasurementDatum/DataItem 处理，不要单独 ChemicalEntity


#### Bare symbol rule / 裸符号规则

**English**

If the text contains only “Sb”, “Hg”, or similar symbols without measurement-dimension words, create **ChemicalEntity[Sb]** and **do not** create TargetVariable.

**中文**

若文本仅含 “Sb”“Hg” 等符号而无测量维度词，创建 **ChemicalEntity[Sb]** 且**不要**创建 TargetVariable。


#### Relations / 关系

**English**

Specimen, organism, EnvironmentMaterial may `bfo_has_part` ChemicalEntity; TargetVariable -> `iao_is_about` -> ChemicalEntity only when both are independently text-supported.

**中文**

Specimen、organism、EnvironmentMaterial 可 `bfo_has_part` ChemicalEntity；仅当二者均有独立文本支撑时，TargetVariable → `iao_is_about` → ChemicalEntity。


#### Example / 示例

**English**

“Total mercury and methylmercury were measured.” -> ChemicalEntity[mercury], ChemicalEntity[methylmercury]; TargetVariable only if “concentration/content” etc. appear in the text.

**中文**

“Total mercury and methylmercury were measured.” → ChemicalEntity[mercury]、ChemicalEntity[methylmercury]；仅当文本出现 “concentration/content” 等时才建 TargetVariable。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Low-level: the span must fall within the WHU_HASORIGINALTEXT of the parent mid-level entity from which this node is expanded.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。基层：片段须落在所属中层实体 WHU_HASORIGINALTEXT 范围内。


---

## 25. `whu_SupportGraph` {#25-whu-supportgraph}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `whu_SupportGraph` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Tier / 层级

**English**

Mid-level argumentative container.

**中文**

中层论证容器。


#### Definition / 定义

**English**

A `whu_SupportGraph` is an argumentative aggregate organized around one focal `mp_Claim`.

**中文**

`whu_SupportGraph` 是围绕一个焦点 `mp_Claim` 组织的论证聚合体。


#### Establishment gate / 建立门控

**English**

Create only when:
1. a focal `mp_Claim` is identified in the same extraction pass, and
2. at least one additional argumentative participant exists (Statement, ScienceEvidence linked by mp_supports/mp_challenges, Reference, Attribution)

**中文**

仅当同时满足时创建：
1. 同一抽取轮次识别出焦点 `mp_Claim`，且
2. 存在至少一个额外论证参与者（Statement、经 mp_supports/mp_challenges 链接的 ScienceEvidence、Reference、Attribution）


#### Mandatory members / 必选成员

**English**

SupportGraph -> `prov_hadMember` -> Claim (required). ScienceEvidence is **not** a `prov_hadMember` of SupportGraph; attach it with `mp_supports`/`mp_challenges` instead.

**中文**

SupportGraph → `prov_hadMember` → Claim（必需）。ScienceEvidence **不是** SupportGraph 的 `prov_hadMember`；应使用 `mp_supports`/`mp_challenges` 挂接。


#### Do not extract when / 何时不抽取

**English**

- only an isolated Claim without supporting/challenging material
- only DataSet/results without a focal Claim

**中文**

- 仅有孤立 Claim 而无支持/挑战材料
- 仅有 DataSet/结果而无焦点 Claim


#### WHU_HASORIGINALTEXT / WHU_HASORIGINALTEXT

**English**

Span covering the focal Claim and its immediate argumentative neighbors in one contiguous passage.

**中文**

覆盖焦点 Claim 及其直接论证邻居的单段连续片段。


#### Relations / 关系

**English**

`prov_hadMember` to Claim/Statement/Attribution/Reference only. ScienceEvidence polarity via `mp_supports`/`mp_challenges` (ScienceEvidence -> SupportGraph or Claim).

**中文**

`prov_hadMember` 仅链接 Claim/Statement/Attribution/Reference。ScienceEvidence 极性经 `mp_supports`/`mp_challenges`（ScienceEvidence → SupportGraph 或 Claim）。


#### Example / 示例

**English**

Claim about biochar reducing MeHg with ScienceEvidence mp_supports Claim, and cited References as SupportGraph members.

**中文**

关于 biochar 降低 MeHg 的 Claim，由 ScienceEvidence mp_supports Claim，引用文献作为 SupportGraph 成员。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans. Mid-level: the span must cover the full contiguous evidence needed to establish this mid-level entity.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。中层：片段须覆盖建立该中层实体所需的完整连续证据。


---

## 26. `iao_DataItem` {#26-iao-dataitem}

| 字段 Field | 值 Value |
|:--|:--|
| Neo4j Label | `iao_DataItem` |
| 属性数量 Property count | 2 |

### Entity Description 实体描述

#### Definition / 定义

**English**

An `iao_DataItem` is an individually reportable information-content item contained within a DataSet, including categorical records, counts, concentrations, statistical summaries, or other data records. `iao_ScalarMeasurementDatum` is used for the more specific single-value-plus-unit case.

**中文**

`iao_DataItem` 是 DataSet 内可单独报告的信息内容项，含分类记录、计数、浓度、统计摘要或其他数据记录。更具体的单值+单位情形用 `iao_ScalarMeasurementDatum`。


#### Extract when / 何时抽取

**English**

Create a DataItem when a distinct reportable record is present but cannot or should not be represented as a single scalar measurement datum.

**中文**

当存在 distinct 可报告记录，但不宜或不能表示为单一标量测量数据项时创建 DataItem。


#### Relations / 关系

**English**

DataSet -> `dcterms_hasPart` -> DataItem; DataItem may -> `iao_is_about` -> TargetVariable.

**中文**

DataSet → `dcterms_hasPart` → DataItem；DataItem 可 → `iao_is_about` → TargetVariable。


#### Example / 示例

**English**

“Soil pH was classified as acidic, neutral, or alkaline across sites.” -> DataItem[pH classification].

**中文**

“Soil pH was classified as acidic, neutral, or alkaline across sites.” → DataItem[pH classification]。


### 属性 Properties 属性描述

##### 属性 Property：`WHU_HASNAME`（`STRING`）

**English**

Return a concise canonical name for this entity, grounded only in the source text. Prefer a short noun phrase (typically 2–12 words), preserve meaningful scientific abbreviations and identifiers, and do not add information that is not stated or unambiguously recoverable from the text. Do not return a full sentence. No semantic expansion: do not add concentration, content, sample, site, or organism words not present in the span.

**中文**

返回基于原文的简短规范名称。优先使用 2–12 词名词短语，保留科学缩写与标识符，不得添加原文未明确陈述的信息。不得返回完整句子。禁止语义扩写：不得添加原文片段中未出现的 concentration、content、sample、site、organism 等词。


##### 属性 Property：`WHU_HASORIGINALTEXT`（`STRING`）

**English**

Copy the smallest contiguous source-text span that explicitly supports creation of this entity. Preserve the wording verbatim, including symbols, numbers, and units. Do not paraphrase, summarize, normalize, or combine non-contiguous spans.

**中文**

复制支持创建该实体的最小连续原文片段，逐字保留符号、数字与单位；不得改写、概括、规范化或合并非连续片段。


---
