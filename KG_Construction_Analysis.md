# 知识图谱构建与本体使用分析

## 📋 概述

本文档详细分析 `1_2_0_2build_kg__neo4j.ipynb` 中的知识图谱构建流程，重点说明：
1. **本体Schema的定义与加载机制**
2. **文档处理与实体/关系提取流程**
3. **Neo4j图谱构建的技术细节**

---

## 1. 本体Schema系统架构

### 1.1 Schema定义文件结构

知识图谱的本体（Ontology）定义通过三个JSON文件管理：

```
schema_base_path/
├── entity.json          # 实体类型定义
├── relation.json        # 关系类型定义
└── potential_schema.json # Schema组合（三元组模板）
```

**加载机制**：
```python
from utilities.schema_loader import SchemaLoader

loader = SchemaLoader(base_path=r".\output")
entities, relations, potential_schema = loader.load_all()
```

**示例输出**：
- 实体类型数量：24种（如 `whu_DataSet`, `mp_Claim`, `whu_Method`等）
- 关系类型数量：若干种（如 `supports`, `uses`, `declaresUsed`等）
- Schema组合数量：~70种（预定义的三元组模板）

### 1.2 实体类型（Entity Types）

**命名空间**：
- `whu_`：武汉大学自定义实体类型
  - 例如：`whu_DataSet`, `whu_Method`, `whu_Pollutant`, `whu_Instrument`
- `mp_`：MetaPaper相关实体类型
  - 例如：`mp_Claim`, `mp_Statement`, `mp_References`
- `prov_`：PROV（Provenance）标准实体类型
  - 例如：`prov_Activity`, `prov_Agent`, `prov_Entity`

**Entity JSON结构**（推测）：
```json
{
  "entities": [
    {
      "label": "whu_DataSet",
      "description": "数据集实体",
      "properties": ["WHU_HASNAME", "WHU_HASORIGINALTEXT"],
      ...
    },
    ...
  ]
}
```

### 1.3 关系类型（Relation Types）

**命名规则**：
- 使用驼峰命名或下划线分隔
- 例如：`supports`, `uses`, `declaresUsed`, `prov_used`

**Relation JSON结构**（推测）：
```json
{
  "relations": [
    {
      "label": "supports",
      "description": "支持关系",
      "source_entity": "whu_Method",
      "target_entity": "whu_DataSet",
      ...
    },
    ...
  ]
}
```

### 1.4 Potential Schema（三元组模板）

**Schema定义格式**：
```python
schema = [e1, r, e2, sections]  # 或 [e1, r, e2]
# e1: 源实体类型
# r: 关系类型
# e2: 目标实体类型
# sections: 可选，允许的文档section列表
```

**示例Schema**：
```python
# 示例1：Method支持DataSet（所有section）
["whu_Method", "supports", "whu_DataSet"]

# 示例2：Statement支持Claim（仅Methods和Results section）
["mp_Statement", "supports", "mp_Claim", ["Methods_Materials", "Results"]]
```

**Schema的作用**：
- **约束抽取范围**：只抽取符合预定义schema的三元组
- **Section过滤**：限制某些schema只在特定文档section中生效
- **保证语义一致性**：避免随意抽取导致的关系混乱

---

## 2. 文档处理流程

### 2.1 第一阶段：DC元数据提取（Agent-based）

**实现方式**：使用LangGraph构建的Agent，自动选择工具提取元数据

**Agent工具**：
1. **`search_crossref`**：英文论文（通过CrossRef API）
   - 提取：DOI、标题、作者、期刊、发表日期等
2. **`search_chinese_metadata`**：中文论文（通过CNKI或其他API）

**元数据标准**：Dublin Core (DC)核心元数据
```python
dc_metadata = {
    "dc_title": "论文标题",
    "dc_creator": "作者",
    "dc_identifier": "DOI或唯一标识",
    "dc_date": "发表日期",
    "dcterms_abstract": "摘要",
    ...
}
```

**为什么需要DC元数据？**
- **溯源能力**：每个节点/关系都能追溯到原始论文
- **同论文分析**：支持按论文聚合的查询和分析
- **学术规范性**：符合学术文献元数据标准

### 2.2 第二阶段：文档加载与粗切分

**函数**：`load_markdown_with_agent_metadata(directory_path)`

**流程**：
1. 扫描Markdown文件目录
2. 每个文件调用Agent提取DC元数据
3. 创建Document对象（包含text和metadata）

**粗切分**：`create_nodes_with_metadata(doc)`
- **策略**：按Markdown结构分割（`split_by_structure`）
- **目标块大小**：800字符
- **分割规则**：
  1. 优先在标题处分割（保持章节完整性）
  2. 其次在段落边界分割（保持段落完整性）

**标题路径标注**：`add_header_paths(nodes, original_text)`
- 为每个节点分配`header_path`属性
- 表示该节点所属的章节标题路径

### 2.3 第三阶段：语义细切分与Section Role推断

**组件**：`SafeSemanticSplitter`（继承自`SemanticSplitterNodeParser`）

**技术栈**：
- **嵌入模型**：`maidalun1020/bce-embedding-base_v1`（中文BCE模型）
- **分割阈值**：`similarity_threshold=0.72`
- **块大小**：`chunk_size=300`，`window_size=2`

**Section Role推断**：混合式方案（规则 + LLM）

**规则匹配**（覆盖80%标准标题）：
```python
# 示例规则
if 'abstract' in header_lower:
    return 'Abstract'
if 'method' in header_lower:
    return 'Methods_Materials'
if 'result' in header_lower:
    return 'Results'
```

**LLM兜底**（处理20%疑难标题）：
- 使用DeepSeek ChatOpenAI进行推断
- 只有在规则失败时才调用LLM

**Section Role类型**：
- `Abstract`：摘要
- `Introduction`：引言
- `Methods_Materials`：方法与材料
- `Results`：结果
- `Discussion`：讨论
- `Conclusion`：结论
- `Other`：其他

**规范化**：`canonical_section(role)`
- 将变体统一为标准类型（如"方法"→"Methods_Materials"）

---

## 3. 知识图谱构建核心流程

### 3.1 处理单个文档：`process_document()`

**完整流程**：

```python
async def process_document(
    doc: Document,
    splitter: SafeSemanticSplitter,
    custom_prompt: str,
    potential_schema: List,
    entities: List,
    relations: List,
    llm, neo4j_driver, embed_model, weight_llm
) -> int:
```

#### **阶段0：提取DC元数据**
```python
dc_metadata = {
    k: v for k, v in doc.metadata.items() 
    if k.startswith('dc_') or k.startswith('dcterms_')
}
```

#### **阶段1：结构级粗切 + 标题路径**
```python
nodes = create_nodes_with_metadata(doc)
add_header_paths(nodes, doc.text)
```

#### **阶段2：转换为Document格式**
```python
doc_blocks = [
    Document(text=n.get_content(), metadata=dict(n.metadata or {})) 
    for n in nodes
]
```

#### **阶段3：语义细切 + section_role标注**
```python
final_nodes = splitter.get_nodes_from_documents(doc_blocks)
```

#### **阶段4：规范化section_role**
```python
for n in final_nodes:
    md['section_role'] = canonical_section(md.get('section_role', 'Other'))
```

#### **阶段5：按Schema构建KG（核心）**

**关键代码**：
```python
for schema in potential_schema:
    e1, r, e2 = schema[0], schema[1], schema[2]
    sections = schema[3] if len(schema) > 3 else []
    allowed = schema_allowed_set(sections)
    
    # 筛选实体和关系定义
    _entities = [e for e in entities if e.get("label") in (e1, e2)]
    _relations = [rel for rel in relations if rel.get("label") == r]
    
    # 过滤节点（按section_role）
    if '__ALL__' in allowed:
        selected = final_nodes
    else:
        selected = [
            n for n in final_nodes 
            if canonical_section((n.metadata or {}).get('section_role')) in allowed
        ]
    
    # 构建KG
    kg_builder = SimpleKGPipeline(
        llm=llm,
        driver=neo4j_driver,
        embedder=embed_model,
        entities=_entities,
        relations=_relations,
        text_splitter=None,
        potential_schema=[schema[:3]],
        perform_entity_resolution=True,
        prompt_template=custom_prompt
    )
    
    await kg_builder.run_async(text=join_nodes_text(selected))
```

**要点**：
1. **迭代处理每个Schema**：不是一次性提取所有三元组，而是按Schema逐个处理
2. **Section过滤**：只使用符合条件的section中的节点文本
3. **Entity Resolution**：启用实体消歧（合并重复实体）
4. **自定义Prompt**：使用`custom_prompt.md`模板指导LLM抽取

#### **阶段5.5：补充Chunk元数据**
```python
# 为Neo4j中的Chunk节点补充header_path和section_role
MATCH (c:Chunk)
WHERE c.text CONTAINS $text_preview
SET c.header_path = $header_path,
    c.section_role = $section_role
```

#### **阶段6：后处理 - 元数据更新**
```python
update_metadata_batch(neo4j_driver, filename, dc_metadata)
# 为所有节点和关系添加DC元数据
```

---

## 4. Neo4j存储结构

### 4.1 节点类型

**Chunk节点**（文本块）：
```cypher
CREATE (c:Chunk {
    text: "文本内容",
    filename: "doc_01.md",
    chunk_id: 0,
    header_path: "2. Methods",
    section_role: "Methods_Materials",
    dc_title: "论文标题",
    dc_identifier: "DOI:xxx",
    ...
})
```

**实体节点**（Entity Nodes）：
```cypher
CREATE (e:whu_DataSet:__Master__ {
    WHU_HASNAME: "数据集名称",
    WHU_HASORIGINALTEXT: "原始文本片段",
    dc_title: "论文标题",
    ...
})
```

**标签层级**：
- **第一层标签**：实体类型（如`whu_DataSet`, `mp_Claim`）
- **第二层标签**：`__Master__`（表示这是主实体节点，经过entity resolution）

### 4.2 关系类型

**FROM_CHUNK关系**（Chunk → Entity）：
```cypher
(c:Chunk)-[:FROM_CHUNK]->(e:whu_DataSet)
```

**实体间关系**（Entity → Entity）：
```cypher
(m:whu_Method)-[:supports]->(d:whu_DataSet)
```

**关系属性**：
```cypher
CREATE ()-[r:supports {
    WHU_HASORIGINALTEXT: "支持关系的原始文本",
    WHU_HASNAME: "supports",
    llm_weight: 0.85,  # LLM评估的权重
    dc_identifier: "DOI:xxx",
    ...
}]->()
```

### 4.3 关键属性命名

**节点属性**：
- `WHU_HASNAME`：实体名称
- `WHU_HASORIGINALTEXT`：原始文本片段（用于追溯和展示）
- `dc_*`, `dcterms_*`：Dublin Core元数据

**关系属性**：
- `WHU_HASORIGINALTEXT`：关系文本（**重要**：关系也保留原始文本）
- `WHU_HASNAME`：关系名称（通常与关系类型相同）
- `llm_weight`：LLM评估的关系权重（0-1）

---

## 5. 本体使用机制总结

### 5.1 Schema-driven Extraction（Schema驱动抽取）

**不是开放式抽取**，而是**受控的、基于本体的抽取**：

```
输入文本 → Schema过滤 → LLM抽取（按Schema约束） → Neo4j存储
```

**优势**：
1. **语义一致性**：只抽取符合领域本体的三元组
2. **质量保证**：避免噪声和无关关系
3. **可扩展性**：通过修改Schema定义即可调整抽取范围

### 5.2 Section-aware Extraction（Section感知抽取）

**不同Schema作用于不同文档section**：

```python
# Schema定义中包含section约束
schema = ["whu_Method", "supports", "whu_DataSet", ["Methods_Materials", "Results"]]

# 只从Methods_Materials和Results section抽取
```

**意义**：
- **准确率提升**：避免从Abstract中抽取实验方法
- **语义对齐**：确保抽取的实体关系与文档结构一致

### 5.3 Entity Resolution（实体消歧）

**SimpleKGPipeline的`perform_entity_resolution=True`**：
- **功能**：合并相同或相似的实体节点
- **实现**：基于名称相似度和嵌入相似度
- **结果**：生成`__Master__`标签的主实体节点

**示例**：
```cypher
# 抽取前：多个Chunk分别创建了"汞含量"节点
(doc1_chunk)-[:FROM_CHUNK]->(hg1:whu_DataSet)
(doc2_chunk)-[:FROM_CHUNK]->(hg2:whu_DataSet)

# 消歧后：合并为主节点
(hg1:whu_DataSet:__Master__)  # 保留hg1
(hg2)-[:MERGE_TO]->(hg1)      # hg2指向hg1
```

---

## 6. 关键技术特点

### 6.1 混合式文本处理

1. **粗切分**：结构感知（Markdown标题）
2. **细切分**：语义感知（嵌入相似度）
3. **Section推断**：规则+LLM混合

### 6.2 元数据全程传递

```
Document (DC元数据)
  ↓ 继承
TextNode (DC元数据 + chunk_id + header_path)
  ↓ 继承
Chunk节点 (Neo4j中的DC元数据 + section_role)
  ↓ 关联
Entity节点 (DC元数据)
  ↓ 关联
Relation (DC元数据)
```

**溯源链路**：
- 任意节点/关系 → `dc_identifier` → 原始论文
- 任意节点/关系 → `WHU_HASORIGINALTEXT` → 原始文本片段

### 6.3 多层过滤机制

1. **Schema级过滤**：只处理预定义的Schema
2. **Section级过滤**：只使用符合条件的section文本
3. **Entity Resolution**：合并重复实体
4. **后处理**：补充元数据，合并重复Chunk

---

## 7. 与OSEG构建的衔接

### 7.1 本体的层次关系

```
OSEG本体定义 (entity.json + relation.json)
  ↓
Potential Schema (三元组模板)
  ↓
文档抽取 (按Schema约束)
  ↓
Neo4j存储 (节点+关系)
  ↓
GNN学习 (生成hidden embeddings) [见2_1 gnn.ipynb]
  ↓
检索与推理 (使用embeddings) [见3_0 Retevie.ipynb]
```

### 7.2 本体在检索中的角色

在`3_0 Retevie.ipynb`的Pipeline D中：

1. **子图投影**：基于本体定义节点类型和关系类型
   ```cypher
   CALL gds.graph.project(
       'G_EBM',
       ['whu_DataSet', 'mp_Claim', ...],  # 实体类型
       ['supports', 'contradicts', ...]   # 关系类型
   )
   ```

2. **Meta-path模板**：基于本体的关系类型定义路径
   ```python
   # Meta-path: Method-[:uses]->DataSet-[:supports]->Claim
   # 这些都是本体中定义的关系类型
   ```

3. **节点类型过滤**：基于本体标签进行查询
   ```cypher
   MATCH (n:whu_DataSet:__Master__)
   # 使用本体定义的标签
   ```

---

## 8. 潜在问题与改进建议

### 8.1 当前问题

1. **Schema数量限制**：~70个Schema，可能需要手动维护
2. **Section推断准确率**：规则+LLM混合可能仍有误差
3. **Entity Resolution质量**：依赖名称相似度，可能误合并

### 8.2 改进方向

1. **自动化Schema生成**：基于本体自动生成所有合法三元组组合
2. **强化Section推断**：使用更强的LLM或微调模型
3. **改进Entity Resolution**：结合上下文和嵌入相似度

---

## 9. 总结

**本体使用方式**：
- ✅ **显式定义**：通过JSON文件明确定义实体和关系类型
- ✅ **Schema约束**：通过potential_schema限制抽取范围
- ✅ **Section感知**：结合文档结构过滤抽取范围
- ✅ **元数据传递**：DC元数据贯穿整个流程

**KG构建流程**：
```
文档 → DC元数据提取 → 粗切分 → 细切分 → Section标注 
  → 按Schema抽取 → Entity Resolution → Neo4j存储 → 后处理
```

**核心创新点**：
1. **Schema-driven extraction**：不是盲目抽取，而是按本体约束抽取
2. **Section-aware filtering**：结合文档结构提升抽取质量
3. **全程元数据**：DC元数据确保可溯源

---

## 📚 参考文献

- Dublin Core Metadata Initiative: https://www.dublincore.org/
- PROV Data Model: https://www.w3.org/TR/prov-dm/
- Neo4j GraphRAG: https://github.com/neo4j-labs/neo4j-graphrag

