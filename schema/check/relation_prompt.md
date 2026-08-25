# BAE Relation Schema — Description 审核稿

> **来源 Source：** `kg_build_pipeline/schema/relation.json`  
> **用途 Purpose：** 人工审核关系与属性 description（中英文对照）  
> **说明 Note：** English 为 JSON schema 原文；中文为审核对照译文。类名/关系名保留英文标签。

## 目录 Table of Contents

1. [`mp_supports`](#1-mp-supports)
2. [`whu_declaredUsed`](#2-whu-declaredused)
3. [`p_plan_correspondsToStep`](#3-p-plan-correspondstostep)
4. [`prov_atLocation`](#4-prov-atlocation)
5. [`cito_isCitedBy`](#5-cito-iscitedby)
6. [`whu_hasGoal`](#6-whu-hasgoal)
7. [`p_plan_isPrecededBy`](#7-p-plan-isprecededby)
8. [`whu_fellow`](#8-whu-fellow)
9. [`whu_hasTarget`](#9-whu-hastarget)
10. [`p_plan_isInputVarOf`](#10-p-plan-isinputvarof)
11. [`p_plan_isOutputVarOf`](#11-p-plan-isoutputvarof)
12. [`prov_wasDerivedFrom`](#12-prov-wasderivedfrom)
13. [`dcterms_hasPart`](#13-dcterms-haspart)
14. [`mp_challenges`](#14-mp-challenges)
15. [`iao_is_about`](#15-iao-is-about)
16. [`p_plan_isStepOfPlan`](#16-p-plan-isstepofplan)
17. [`prov_hadMember`](#17-prov-hadmember)
18. [`bfo_has_part`](#18-bfo-has-part)
19. [`whu_declaredInput`](#19-whu-declaredinput)
20. [`whu_declaredOutput`](#20-whu-declaredoutput)
21. [`whu_hasContext`](#21-whu-hascontext)

---

## 1. `mp_supports` {#1-mp-supports}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `mp_supports` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Positive argumentative relation: supporting Representation -> supported Representation.

**中文**

正向论证关系：支持方 Representation → 被支持方 Representation。


#### Extract when / 何时抽取

**English**

Explicit positive backing language (supports, demonstrates, confirms, provides evidence for, consistent with, indicates/suggests in argumentative use) appears in the **same original_text** as the linked nodes.

**中文**

当明确正向支撑语言（supports、demonstrates、confirms、provides evidence for、consistent with、论证性使用的 indicates/suggests）出现在与链接节点**相同的 original_text** 中时抽取。


#### Do not infer from / 禁止从…推断

**English**

Co-occurrence, citation alone, method use, or data production. Citation backing requires separate mp_supports evidence beyond cito_isCitedBy.

**中文**

不要从共现、单独引用、方法使用或数据产出推断。引用支撑需除 `cito_isCitedBy` 外另有独立 mp_supports 证据。


#### ScienceEvidence/SupportGraph / ScienceEvidence / SupportGraph

**English**

When ScienceEvidence mp_supports SupportGraph or Claim, the connector must appear in the shared argumentative span.

**中文**

当 ScienceEvidence mp_supports SupportGraph 或 Claim 时，连接词必须出现在共享论证片段中。


---

## 2. `whu_declaredUsed` {#2-whu-declaredused}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_declaredUsed` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a ResearchStep to Method, Device, Reagent, or Software explicitly used in **that step**.

**中文**

将 ResearchStep 链接到**该步骤**中明确使用的 Method、Device、Reagent 或 Software。


#### Direction / 方向

**English**

ResearchStep -> `whu_declaredUsed` -> Method/Device/Reagent/Software.

**中文**

ResearchStep → `whu_declaredUsed` → Method/Device/Reagent/Software。


#### Extract when / 何时抽取

**English**

The resource is assigned to a specific step in the step's original_text sub-span. Do not attach to Experiment-level nodes when the using step is identifiable.

**中文**

当资源被分配到步骤 original_text 子片段中的具体步骤时抽取。若使用步骤可识别，不要挂到 Experiment 级节点。


#### Low-level rule / 基层规则

**English**

Used entities must be grounded in the parent ResearchStep original_text only.

**中文**

Used 实体必须仅锚定于父 ResearchStep 的 original_text。


---

## 3. `p_plan_correspondsToStep` {#3-p-plan-correspondstostep}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `p_plan_correspondsToStep` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Corresponds to P-PLAN `correspondsToStep`: links an explicitly executed provenance activity to the plan-level/textual `whu_ResearchStep` it realizes.

**中文**

对应 P-PLAN `correspondsToStep`：将明确执行的溯源活动链接到其实现的计划级/文本级 `whu_ResearchStep`。


#### Extraction policy / 抽取策略

**English**

This relation is reserved for an external provenance/execution stage that supplies a `prov:Activity` (e.g. run log, execution timestamp, instrument-run identifier). It is not emitted from ordinary Methods prose when only the described ResearchStep is available.

**中文**

此关系保留给提供 `prov:Activity` 的外部溯源/执行阶段（如运行日志、执行时间戳、仪器运行标识）。在仅有描述性 ResearchStep 的普通方法正文中不发出。


#### Direction / 方向

**English**

prov:Activity -> `p_plan_correspondsToStep` -> whu:ResearchStep.

**中文**

prov:Activity → `p_plan_correspondsToStep` → whu:ResearchStep。


---

## 4. `prov_atLocation` {#4-prov-atlocation}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `prov_atLocation` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

`prov_atLocation` associates an organism or ResearchStep with the EnvironmentFeature where it is located or occurs.

**中文**

`prov_atLocation` 将 organism 或 ResearchStep 与其所在或发生的 EnvironmentFeature 关联。


#### Allowed schema patterns / 允许的 schema 模式

**English**

- obi_organism -> prov_atLocation -> whu_EnvironmentFeature
- whu_ResearchStep -> prov_atLocation -> whu_EnvironmentFeature

**中文**

- obi_organism → prov_atLocation → whu_EnvironmentFeature
- whu_ResearchStep → prov_atLocation → whu_EnvironmentFeature


#### Extract when / 何时抽取

**English**

The text explicitly names the site for the organism or step.

**中文**

当文本为 organism 或步骤明确命名站点时抽取。


#### Do not use for / 不用于

**English**

- Specimen positioning → use wasDerivedFrom or SpecimenCollection `whu_hasContext`
- material matrix mentions without a place → EnvironmentMaterial, not atLocation

**中文**

- Specimen 定位 → 用 wasDerivedFrom 或 SpecimenCollection `whu_hasContext`
- 无地点的物质基质提及 → EnvironmentMaterial，不用 atLocation


#### Example / 示例

**English**

“Rice plants were grown in the SWU paddy field.” -> organism atLocation EnvironmentFeature[SWU paddy field].

**中文**

“Rice plants were grown in the SWU paddy field.” → organism atLocation EnvironmentFeature[SWU paddy field]。


---

## 5. `cito_isCitedBy` {#5-cito-iscitedby}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `cito_isCitedBy` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

CiTO inverse citation: cited Reference -> citing Representation.

**中文**

CiTO 逆引用：被引 Reference → 引用方 Representation。


#### Direction / 方向

**English**

Reference -> `cito_isCitedBy` -> Claim/Statement/DataSet/Method.

**中文**

Reference → `cito_isCitedBy` → Claim/Statement/DataSet/Method。


#### Extract when / 何时抽取

**English**

An identifiable citation string is explicitly tied to the citing proposition.

**中文**

当可识别引用字符串与引用命题明确绑定时抽取。


#### Separate from support / 与支持关系区分

**English**

Citation records bibliographic linkage only. Add mp_supports only when the text uses the citation as evidential backing—not from citation presence alone.

**中文**

引用仅记录书目链接。仅当文本将引用用作证据支撑时才加 mp_supports——不能仅凭引用存在。


---

## 6. `whu_hasGoal` {#6-whu-hasgoal}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_hasGoal` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a BioChemical or Computational Experiment to an explicitly stated Goal.

**中文**

将 BioChemical 或 Computational Experiment 链接到明确陈述的 Goal。


#### Direction / 方向

**English**

BioChemical_Experiment/Computational_Experiment -> `whu_hasGoal` -> Goal.

**中文**

BioChemical_Experiment/Computational_Experiment → `whu_hasGoal` → Goal。


#### Emit iff / 发出条件

**English**

Goal and Experiment are **co-created in the same extraction pass** with explicit objective language in the Experiment's original_text. Do not add hasGoal retroactively to orphan Goals or Experiments.

**中文**

Goal 与 Experiment **在同一抽取轮次共创建**，且 Experiment 的 original_text 含明确目标语言。不要事后为孤立 Goal 或 Experiment 补 hasGoal。


#### Do not infer / 禁止推断

**English**

Background motivation does not justify hasGoal.

**中文**

背景动机不足以 justify hasGoal。


---

## 7. `p_plan_isPrecededBy` {#7-p-plan-isprecededby}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `p_plan_isPrecededBy` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Standard P-PLAN ordering relation used between `whu_ResearchStep` instances.

**中文**

P-PLAN 标准顺序关系，用于 `whu_ResearchStep` 实例之间。


#### Direction / 方向

**English**

later/downstream ResearchStep -> `p_plan_isPrecededBy` -> earlier/upstream ResearchStep.

**中文**

较晚/下游 ResearchStep → `p_plan_isPrecededBy` → 较早/上游 ResearchStep。


#### Extract when / 何时抽取

**English**

Emit for explicit temporal/logical ordering cues (after, following, then, subsequently, before) or an unambiguous immediate dependency between recorded steps.

**中文**

对明确时间/逻辑顺序提示（after、following、then、subsequently、before）或已记录步骤间无歧义直接依赖时发出。


#### Example / 示例

**English**

“After sieving, samples were digested.” -> ResearchStep[digestion] isPrecededBy ResearchStep[sieving].

**中文**

“After sieving, samples were digested.” → ResearchStep[digestion] isPrecededBy ResearchStep[sieving]。


---

## 8. `whu_fellow` {#8-whu-fellow}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_fellow` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

`whu_fellow(X,Y)`: Y is the immediate upstream mid-level predecessor/provider of X.

**中文**

`whu_fellow(X,Y)`：Y 是 X 的直接上游中层前驱/提供者。


#### Direction / 方向

**English**

downstream X -> `whu_fellow` -> upstream Y.

**中文**

下游 X → `whu_fellow` → 上游 Y。


#### Allowed signatures / 允许的签名

**English**

SpecimenPreprocessing fellow SpecimenCollection; BioChemical_Experiment fellow SpecimenPreprocessing; Computational_Experiment fellow BioChemical_Experiment; same-type experiment chains.

**中文**

SpecimenPreprocessing fellow SpecimenCollection；BioChemical_Experiment fellow SpecimenPreprocessing；Computational_Experiment fellow BioChemical_Experiment；同类型实验链。


#### Extract when / 何时抽取

**English**

Explicit temporal/dependency evidence or clear output→input transition between **mid-level** modules.

**中文**

对**中层**模块间有明确时间/依赖证据或清晰 output→input 过渡时抽取。


#### Do not use for / 不用于

**English**

- Step-to-Plan membership (use p_plan_isStepOfPlan)
- SpecimenCollection to EnvironmentFeature (use whu_hasContext)
- hallucinated adjacency without textual dependency

**中文**

- Step 与 Plan 成员关系（用 p_plan_isStepOfPlan）
- SpecimenCollection 与 EnvironmentFeature（用 whu_hasContext）
- 无文本依赖的臆造邻接


---

## 9. `whu_hasTarget` {#9-whu-hastarget}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_hasTarget` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a Goal to the TargetVariable it aims to measure, analyze, or predict.

**中文**

将 Goal 链接到其旨在测量、分析或预测的 TargetVariable。


#### Direction / 方向

**English**

Goal -> `whu_hasTarget` -> TargetVariable.

**中文**

Goal → `whu_hasTarget` → TargetVariable。


#### Extract when / 何时抽取

**English**

The **measurement-quantity phrase appears verbatim** in the Goal's WHU_HASORIGINALTEXT (e.g. “to quantify Hg concentration”).

**中文**

**测量量短语逐字出现**于 Goal 的 WHU_HASORIGINALTEXT 中（如“to quantify Hg concentration”）。


#### Do not extract when / 何时不抽取

**English**

Only a chemical symbol or substance appears; do not infer concentration/content/level from domain knowledge.

**中文**

仅出现化学符号或物质；不要凭领域知识推断 concentration/content/level。


#### Example / 示例

**English**

“To quantify Hg concentration in rice grain.” -> hasTarget TargetVariable[Hg concentration]. “To analyze Sb.” -> no hasTarget; use ChemicalEntity[Sb] in low-level expansion only if Sb appears.

**中文**

“To quantify Hg concentration in rice grain.” → hasTarget TargetVariable[Hg concentration]。“To analyze Sb.” → 无 hasTarget；若 Sb 出现，基层扩展中仅用 ChemicalEntity[Sb]。


---

## 10. `p_plan_isInputVarOf` {#10-p-plan-isinputvarof}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `p_plan_isInputVarOf` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Plan-level shortcut relation corresponding to P-PLAN `isInputVarOf`, used in this extraction schema to connect a concrete Specimen or ProcessedSpecimen directly to the Plan/Experiment for which it serves as input.

**中文**

对应 P-PLAN `isInputVarOf` 的计划级快捷关系；在本抽取 schema 中将具体 Specimen 或 ProcessedSpecimen 直接连到以其为输入的 Plan/Experiment。


#### Purpose / 用途

**English**

This is a plan-level projection that skips the intermediate ResearchStep for concise retrieval and MetaPath construction. The detailed step-level input relation remains `ResearchStep -> whu_declaredInput -> domain entity`.

**中文**

这是跳过中间 ResearchStep 的计划级投影，便于检索与 MetaPath 构建。详细步骤级输入关系仍为 `ResearchStep -> whu_declaredInput -> domain entity`。


#### Direction / 方向

**English**

input entity -> `p_plan_isInputVarOf` -> Plan/Experiment.

**中文**

input entity → `p_plan_isInputVarOf` → Plan/Experiment。


#### Allowed schema patterns / 允许的 schema 模式

**English**

- Specimen -> SpecimenPreprocessing
- ProcessedSpecimen -> BioChemical_Experiment

**中文**

- Specimen → SpecimenPreprocessing
- ProcessedSpecimen → BioChemical_Experiment


#### Extract when / 何时抽取

**English**

Emit only when the passage directly supports that the entity is used as input to the named preprocessing/experiment module.

**中文**

仅当段落直接支持该实体作为命名预处理/实验模块的输入时发出。


#### Example / 示例

**English**

“Processed powder was used for ICP-MS analysis.” -> ProcessedSpecimen `p_plan_isInputVarOf` BioChemical_Experiment.

**中文**

“Processed powder was used for ICP-MS analysis.” → ProcessedSpecimen `p_plan_isInputVarOf` BioChemical_Experiment。


---

## 11. `p_plan_isOutputVarOf` {#11-p-plan-isoutputvarof}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `p_plan_isOutputVarOf` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Plan-level shortcut relation corresponding to P-PLAN `isOutputVarOf`, used in this extraction schema to connect a concrete output entity directly to the Plan/Experiment that produces it.

**中文**

对应 P-PLAN `isOutputVarOf` 的计划级快捷关系；在本抽取 schema 中将具体输出实体直接连到产出它的 Plan/Experiment。


#### Purpose / 用途

**English**

This is a plan-level projection that skips the intermediate ResearchStep for concise retrieval and MetaPath construction. The detailed step-level output relation remains `ResearchStep -> whu_declaredOutput -> domain entity`.

**中文**

这是跳过中间 ResearchStep 的计划级投影，便于检索与 MetaPath 构建。详细步骤级输出关系仍为 `ResearchStep -> whu_declaredOutput -> domain entity`。


#### Direction / 方向

**English**

output entity -> `p_plan_isOutputVarOf` -> Plan/Experiment.

**中文**

output entity → `p_plan_isOutputVarOf` → Plan/Experiment。


#### Allowed schema patterns / 允许的 schema 模式

**English**

- Specimen -> SpecimenCollection
- ProcessedSpecimen -> SpecimenPreprocessing
- DataSet -> Computational_Experiment

**中文**

- Specimen → SpecimenCollection
- ProcessedSpecimen → SpecimenPreprocessing
- DataSet → Computational_Experiment


#### Extract when / 何时抽取

**English**

Emit only when the text directly supports that the entity is an output of the corresponding plan/experiment module.

**中文**

仅当文本直接支持该实体是对应 plan/experiment 模块的输出时发出。


#### Example / 示例

**English**

“The preprocessing produced a filtered digest.” -> ProcessedSpecimen `p_plan_isOutputVarOf` SpecimenPreprocessing.

**中文**

“The preprocessing produced a filtered digest.” → ProcessedSpecimen `p_plan_isOutputVarOf` SpecimenPreprocessing。


---

## 12. `prov_wasDerivedFrom` {#12-prov-wasderivedfrom}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `prov_wasDerivedFrom` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

`prov_wasDerivedFrom` records material/provenance derivation between a resulting entity and its source entity.

**中文**

`prov_wasDerivedFrom` 记录结果实体与其来源实体之间的物质/溯源派生。


#### Allowed schema patterns / 允许的 schema 模式

**English**

- Specimen -> EnvironmentFeature
- Specimen -> envo_EnvironmentMaterial
- Specimen -> obi_organism
- ProcessedSpecimen -> Specimen

**中文**

- Specimen → EnvironmentFeature
- Specimen → envo_EnvironmentMaterial
- Specimen → obi_organism
- ProcessedSpecimen → Specimen


#### Type-selection order / 类型选择顺序

**English**

Choose the **most specific** source explicitly supported: **organism > EnvironmentMaterial > EnvironmentFeature**. Do not label a sample name or matrix as EnvironmentFeature solely because collection is mentioned.

**中文**

选择文本明确支持的**最具体**来源：**organism > EnvironmentMaterial > EnvironmentFeature**。勿仅因提及采集而将样本名或基质标为 EnvironmentFeature。


#### Extraction rule / 抽取规则

**English**

For “soil samples from the paddy field”: Specimen[soil samples] wasDerivedFrom EnvironmentMaterial[surface soil] when matrix is explicit; wasDerivedFrom EnvironmentFeature only when the **named place** is the stated source and no more specific material/organism is given. Do not use wasDerivedFrom to justify mis-typing the source node.

**中文**

对“soil samples from the paddy field”：基质明确时 Specimen[soil samples] wasDerivedFrom EnvironmentMaterial[surface soil]；仅当**命名地点**被陈述为来源且无更具体物质/organism 时 wasDerivedFrom EnvironmentFeature。勿用 wasDerivedFrom 为误标来源节点辩护。


#### Examples / 示例

**English**

“Soil samples were taken from surface soil.” -> Specimen wasDerivedFrom EnvironmentMaterial[surface soil].
“Rice grain was sampled from rice plants.” -> Specimen wasDerivedFrom organism[rice plant].
“Samples were collected from the SWU paddy field.” -> Specimen wasDerivedFrom EnvironmentFeature[SWU paddy field] when only the site is explicit.

**中文**

“Soil samples were taken from surface soil.” → Specimen wasDerivedFrom EnvironmentMaterial[surface soil]。
“Rice grain was sampled from rice plants.” → Specimen wasDerivedFrom organism[rice plant]。
“Samples were collected from the SWU paddy field.” → 仅站点明确时 Specimen wasDerivedFrom EnvironmentFeature[SWU paddy field]。


---

## 13. `dcterms_hasPart` {#13-dcterms-haspart}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `dcterms_hasPart` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Uses `dcterms:hasPart` to represent a DataSet containing one or more `iao_DataItem` records.

**中文**

用 `dcterms:hasPart` 表示 DataSet 包含一个或多个 `iao_DataItem` 记录。


#### Direction / 方向

**English**

DataSet -> `dcterms_hasPart` -> DataItem.

**中文**

DataSet → `dcterms_hasPart` → DataItem。


#### Extraction note / 抽取说明

**English**

`iao_ScalarMeasurementDatum` is a subtype of DataItem. If the extraction runtime types a member specifically as ScalarMeasurementDatum, do not create an additional duplicate generic DataItem node solely to satisfy this relation.

**中文**

`iao_ScalarMeasurementDatum` 是 DataItem 子类型。若运行时将会员具体类型为 ScalarMeasurementDatum，不要仅为满足此关系再建重复通用 DataItem 节点。


---

## 14. `mp_challenges` {#14-mp-challenges}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `mp_challenges` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Negative argumentative relation: challenging Representation -> challenged Representation.

**中文**

负向论证关系：挑战方 Representation → 被挑战方 Representation。


#### Extract when / 何时抽取

**English**

Explicit challenge language (contradicts, refutes, inconsistent with, undermines, fails to confirm) in the same original_text.

**中文**

在同一 original_text 中出现明确挑战语言（contradicts、refutes、inconsistent with、undermines、fails to confirm）。


#### Do not infer / 禁止推断

**English**

Absence of support is not a challenge.

**中文**

缺乏支持不等于挑战。


#### ScienceEvidence/SupportGraph / ScienceEvidence / SupportGraph

**English**

Same co-text requirement as mp_supports.

**中文**

与 mp_supports 相同的共文本要求。


---

## 15. `iao_is_about` {#15-iao-is-about}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `iao_is_about` |
| 关系属性数 Property count | 1 |

### Relation Description 关系描述

#### Definition / 定义

**English**

`iao_is_about` expresses aboutness between an information-content entity and the entity or variable it describes.

**中文**

`iao_is_about` 表达信息内容实体与其所描述实体或变量之间的 aboutness。


#### Allowed schema patterns / 允许的 schema 模式

**English**

Resource-oriented: DataSet -> Reagent / Specimen / ProcessedSpecimen
Target-variable: TargetVariable -> ChemicalEntity; DataSet/DataItem/ScalarMeasurementDatum -> TargetVariable

**中文**

资源导向：DataSet → Reagent / Specimen / ProcessedSpecimen
目标变量：TargetVariable → ChemicalEntity；DataSet/DataItem/ScalarMeasurementDatum → TargetVariable


#### Lexical grounding for TargetVariable links / TargetVariable 链接的词面锚定

**English**

Emit DataSet/DataItem/ScalarMeasurementDatum -> TargetVariable only when the **full measurement-quantity phrase** appears in the text (e.g. “Hg content”, “THg concentration”). If only a bare symbol appears (Sb, Hg), link to ChemicalEntity only—**do not** create TargetVariable or is_about to an inferred concentration/content.

**中文**

仅当**完整测量量短语**出现在文本中（如“Hg content”“THg concentration”）时，发出 DataSet/DataItem/ScalarMeasurementDatum → TargetVariable。若仅裸符号（Sb、Hg），仅链接 ChemicalEntity——**不要**创建 TargetVariable 或推断 concentration/content 的 is_about。


#### Granularity rule / 粒度规则

**English**

Match the text's granularity. Do not force TargetVariable when only a specimen or reagent is mentioned.

**中文**

匹配文本粒度。仅提及样本或试剂时不要强行 TargetVariable。


#### Examples / 示例

**English**

“Mean Hg content was 28.4 ng/g.” -> ScalarMeasurementDatum is_about TargetVariable[Hg content]; TargetVariable[Hg content] is_about ChemicalEntity[Hg].
“Sb was analyzed.” -> ChemicalEntity[Sb] only; no TargetVariable, no is_about to inferred quantity.

**中文**

“Mean Hg content was 28.4 ng/g.” → ScalarMeasurementDatum is_about TargetVariable[Hg content]；TargetVariable[Hg content] is_about ChemicalEntity[Hg]。
“Sb was analyzed.” → 仅 ChemicalEntity[Sb]；无 TargetVariable，无推断量的 is_about。


### 关系属性 Relation Properties

##### 属性 Property：`whu_is_about_dimension`（`STRING`）

**English**

Optional controlled measurement-dimension tag for the aboutness relation. Choose only from an implementation-controlled vocabulary such as mass, volume, count, concentration, mass_concentration, molar_concentration, absorbance, intensity, ratio, rate, pH, conductivity, or turbidity. Assign only when the dimension is explicit or unambiguous from the reported unit/measure; otherwise omit.

**中文**

可选的 aboutness 测量维度标签；仅从实现受控词表选择；仅当维度由原文单位/测量明确或可无歧义推出时赋值，否则省略。


---

## 16. `p_plan_isStepOfPlan` {#16-p-plan-isstepofplan}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `p_plan_isStepOfPlan` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

P-PLAN membership: associates a ResearchStep with its organizing mid-level Plan/Experiment.

**中文**

P-PLAN 成员关系：将 ResearchStep 关联到组织它的中层 Plan/Experiment。


#### Direction / 方向

**English**

ResearchStep -> `p_plan_isStepOfPlan` -> SpecimenCollection | SpecimenPreprocessing | BioChemical_Experiment | Computational_Experiment

**中文**

ResearchStep → `p_plan_isStepOfPlan` → SpecimenCollection | SpecimenPreprocessing | BioChemical_Experiment | Computational_Experiment


#### Mandatory pairing / 强制配对

**English**

- Every ResearchStep **must** have exactly one isStepOfPlan target in the same extraction pass.
- Every BioChemical_Experiment or Computational_Experiment created at mid-level **must** have at least one ResearchStep linked in the same pass; otherwise do not create the Experiment.
- WHU_RESEARCHTYPE must be consistent with the target Plan type.

**中文**

- 每个 ResearchStep **必须**在同一抽取轮次有恰好一个 isStepOfPlan 目标。
- 中层创建的每个 BioChemical_Experiment 或 Computational_Experiment **必须**在同一轮次至少链接一个 ResearchStep；否则不要创建 Experiment。
- WHU_RESEARCHTYPE 须与目标 Plan 类型一致。


#### Constraint / 约束

**English**

Do not emit isStepOfPlan without co-created Step and Plan nodes.

**中文**

没有共创建的 Step 与 Plan 节点时不要发出 isStepOfPlan。


---

## 17. `prov_hadMember` {#17-prov-hadmember}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `prov_hadMember` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

PROV-O collection membership for ScienceEvidence and SupportGraph aggregates.

**中文**

ScienceEvidence 与 SupportGraph 聚合体的 PROV-O 集合成员关系。


#### Allowed schema patterns / 允许的 schema 模式

**English**

ScienceEvidence -> DataSet/Method; SupportGraph -> Claim/Statement/Attribution/Reference/ScienceEvidence

**中文**

ScienceEvidence → DataSet/Method；SupportGraph → Claim/Statement/Attribution/Reference/ScienceEvidence


#### Co-occurrence gates / 共现门控

**English**

- SupportGraph -> Claim: **required** when SupportGraph is created
- SupportGraph -> ScienceEvidence: **required** when ScienceEvidence is created in the same pass
- ScienceEvidence -> DataSet and/or Method: required for ScienceEvidence establishment

**中文**

- SupportGraph → Claim：创建 SupportGraph 时**必需**
- SupportGraph → ScienceEvidence：同一轮次创建 ScienceEvidence 时**必需**
- ScienceEvidence → DataSet 和/或 Method：ScienceEvidence 建立所必需


#### Semantics / 语义

**English**

Membership only; polarity is mp_supports/mp_challenges, not hadMember.

**中文**

仅表示成员关系；极性由 mp_supports/mp_challenges 表达，而非 hadMember。


#### Do not / 禁止

**English**

Create hadMember links to hallucinated members not supported in the same original_text.

**中文**

不要链接到同一 original_text 中无支撑的成员的臆造成员。


---

## 18. `bfo_has_part` {#18-bfo-has-part}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `bfo_has_part` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

BFO mereological relation: one entity physically contains another as a constituent part.

**中文**

BFO 部分论关系：一实体物理包含另一实体作为组成部分。


#### Allowed schema patterns / 允许的 schema 模式

**English**

- EnvironmentFeature -> EnvironmentMaterial
- Specimen -> ChemicalEntity
- organism -> ChemicalEntity
- EnvironmentMaterial -> ChemicalEntity

**中文**

- EnvironmentFeature → EnvironmentMaterial
- Specimen → ChemicalEntity
- organism → ChemicalEntity
- EnvironmentMaterial → ChemicalEntity


#### Extract when / 何时抽取

**English**

Emit only for explicit part/constituent relations in the text.

**中文**

仅对文本中明确的 part/constituent 关系发出。


#### Do not use for / 不用于

**English**

- sampling location or provenance (use wasDerivedFrom, atLocation, hasContext)
- analytical aboutness (use iao_is_about)
- Specimen -> EnvironmentFeature (forbidden)

**中文**

- 采样地点或溯源（用 wasDerivedFrom、atLocation、hasContext）
- 分析 aboutness（用 iao_is_about）
- Specimen → EnvironmentFeature（禁止）


#### Example / 示例

**English**

“Paddy soil contains elevated Hg.” -> EnvironmentMaterial[paddy soil] has_part ChemicalEntity[Hg] when presence is stated.

**中文**

“Paddy soil contains elevated Hg.” → 当存在性被陈述时 EnvironmentMaterial[paddy soil] has_part ChemicalEntity[Hg]。


---

## 19. `whu_declaredInput` {#19-whu-declaredinput}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_declaredInput` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a ResearchStep to Specimen, ProcessedSpecimen, or DataSet functioning as that step's input.

**中文**

将 ResearchStep 链接到作为该步骤输入的 Specimen、ProcessedSpecimen 或 DataSet。


#### Direction / 方向

**English**

ResearchStep -> `whu_declaredInput` -> Specimen/ProcessedSpecimen/DataSet.

**中文**

ResearchStep → `whu_declaredInput` → Specimen/ProcessedSpecimen/DataSet。


#### Extract when / 何时抽取

**English**

The input role is textually supported within the ResearchStep's original_text sub-span only. Do not infer inputs from general experiment context.

**中文**

输入角色仅在 ResearchStep 的 original_text 子片段内有文本支撑时抽取。不要从一般实验语境推断输入。


---

## 20. `whu_declaredOutput` {#20-whu-declaredoutput}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_declaredOutput` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a ResearchStep to Specimen, ProcessedSpecimen, or DataSet produced by that step.

**中文**

将 ResearchStep 链接到该步骤产出的 Specimen、ProcessedSpecimen 或 DataSet。


#### Direction / 方向

**English**

ResearchStep -> `whu_declaredOutput` -> Specimen/ProcessedSpecimen/DataSet.

**中文**

ResearchStep → `whu_declaredOutput` → Specimen/ProcessedSpecimen/DataSet。


#### Extract when / 何时抽取

**English**

The output/product relation is textually supported within the ResearchStep's original_text sub-span only.

**中文**

输出/产物关系仅在 ResearchStep 的 original_text 子片段内有文本支撑时抽取。


---

## 21. `whu_hasContext` {#21-whu-hascontext}

| 字段 Field | 值 Value |
|:--|:--|
| Relation Label | `whu_hasContext` |
| 关系属性数 Property count | 0 |

### Relation Description 关系描述

#### Definition / 定义

**English**

Links a SpecimenCollection Plan to the EnvironmentFeature providing its explicit sampling context.

**中文**

将 SpecimenCollection Plan 链接到提供其明确采样语境的 EnvironmentFeature。


#### Direction / 方向

**English**

SpecimenCollection -> `whu_hasContext` -> EnvironmentFeature.

**中文**

SpecimenCollection → `whu_hasContext` → EnvironmentFeature。


#### Extract when / 何时抽取

**English**

The collection's WHU_HASORIGINALTEXT explicitly names a bounded site/place tied to the collection procedure. The place name must appear in the text—not inferred from sample material alone.

**中文**

采集的 WHU_HASORIGINALTEXT 明确命名与采集程序绑定的有界站点/地点。地名必须出现在文本中——不能仅从样本材料推断。


#### Do not extract when / 何时不抽取

**English**

Only matrix or sample nouns appear without a distinct place name.

**中文**

仅出现基质或样本名词而无 distinct 地名时。


#### Example / 示例

**English**

“Topsoil samples were collected from the SWU paddy field.” -> SpecimenCollection hasContext EnvironmentFeature[SWU paddy field].

**中文**

“Topsoil samples were collected from the SWU paddy field.” → SpecimenCollection hasContext EnvironmentFeature[SWU paddy field]。


---
