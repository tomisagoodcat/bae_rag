# Pipeline D 详细说明

## 概述

Pipeline D 是一个基于 Graph-aware 的检索和 Re-ranking 系统，用于回答用户的自然语言查询。它结合了向量检索、图结构分析和 GNN hidden embeddings 来提供高质量的答案。

## 一、用户自然语言输入的处理流程

### 用户输入示例

```python
query_text = "请给出对HG的相关数据，以及其支持的结论，并给出表格形式的总结"
```

### 完整的10步处理流程

```
用户输入 (query_text: 自然语言)
          ↓
[Step 1-2] 初始检索 (HybridCypherRetriever)
          ├─→ 向量检索: query_text → embedding → 向量索引查询
          └─→ 全文检索: query_text → BM25 → 全文索引查询
          ↓
      Top-K 候选节点 (elementIDs)
          ↓
[Step 3] 构造结构锚点 z_seed
          ↓
[Step 4] 构造查询子图 G_q
          ↓
[Step 5] 计算结构得分
          ↓
[Step 6] 抽取证据路径
          ↓
[Step 7-8] 计算路径语义得分
          ↓
[Step 9] Graph-aware Re-ranking
          ↓
[Step 10] LLM生成最终答案
          ↓
      自然语言答案 (返回给用户)
```

## 二、Step 1-2: 初始检索（Hybrid Retrieval）

### 2.1 用户输入与初始检索的关系

**关键组件**: `HybridCypherRetriever`

```python
HCretriever = HybridCypherRetriever(
    driver=neo4j_driver,
    vector_index_name="SEG_static_emb_index",     # 向量索引
    fulltext_index_name="SEG_FULLTEXT_INDEX_CHUNK", # 全文索引
    embedder=embed_model,                          # 用于query embedding
    retrieval_query=retrieval_query3,              # 预定义的Cypher查询
)

# 用户输入
query_text = "请给出对HG的相关数据，以及其支持的结论"

# 执行检索
rs = HCretriever.search(query_text=query_text, top_k=20)
```

### 2.2 处理流程详解

#### Step 2.2.1: Query Embedding

```
query_text: "请给出对HG的相关数据..."
     ↓ (embed_model)
query_vector: [0.12, -0.03, ..., 0.45]  # 768维向量
```

#### Step 2.2.2: 双通道检索

**A. 向量通道** (语义相似度)

```cypher
# 内部执行（由HybridCypherRetriever自动完成）
CALL db.index.vector.queryNodes(
    'SEG_static_emb_index',     # 索引名
    $top_k_vector,              # 返回数量
    $query_vector               # query的embedding
)
YIELD node, score
```

**B. 全文通道** (关键词匹配，如"HG")

```cypher
# 内部执行
CALL db.index.fulltext.queryNodes(
    'SEG_FULLTEXT_INDEX_CHUNK',
    $query_text                 # "请给出对HG的相关数据..."
)
YIELD node, score
```

#### Step 2.2.3: 分数融合与Cypher扩展

```
向量结果 + 全文结果
     ↓ (归一化 + 加权融合)
融合后的Top-K节点
     ↓ (使用 retrieval_query)
执行自定义Cypher查询扩展
```

**自定义Cypher查询** (retrieval_query3):

```cypher
# 这是预定义的查询模板
MATCH (n:whu_DataSetMaster)-[:MASTER_mp_supports]->(m:mp_ClaimMaster)
RETURN
  elementId(n) AS n_eid,              # 源节点ID
  n.WHU_HASORIGINALTEXT AS n_text,   # 源节点文本
  elementId(m) AS m_eid,              # 目标节点ID
  m.WHU_HASORIGINALTEXT AS m_text    # 目标节点文本
```

**关键点**:

- 这个Cypher模板定义了**特定的关系模式**：`DataSet -supports-> Claim`
- 不是meta path，而是**预定义的语义查询模板**
- 针对用户query返回的节点，扩展其支持关系

### 2.3 输出结果

```python
# 返回的结果结构
uniq_hits = [
    PairHit(n_eid="4:xxx:1234", m_eid="4:yyy:5678", ...),
    PairHit(n_eid="4:xxx:2345", m_eid="4:yyy:6789", ...),
    ...
]
```

## 三、路径查询的实现（Step 6）

### 3.1 路径查询与用户输入的关系

**用户输入的作用**:

1. Step 1-2: 通过query找到初始候选节点
2. Step 3: 选择Top-M节点作为"种子锚点"（seed）
3. **Step 6**: 查询**从seed到其他候选节点的路径**

### 3.2 路径查询的具体实现

#### 代码实现

```python
def step6_get_paths_edges(driver, v_eid: str, seed_eid: str, max_paths: int = 5):
    """
    Step 6: 对每个候选节点 v，抽取其证据路径 P_v
    返回从seed到v的路径上的边信息
    """
    cypher = f"""
    MATCH (seed:{MASTER_LABEL}) WHERE elementId(seed) = $seed_eid
    MATCH (v:{MASTER_LABEL}) WHERE elementId(v) = $v_eid
    MATCH p=shortestPath((seed)-[*1..2]-(v))
    WITH relationships(p) AS rels LIMIT $k
    UNWIND rels AS r
    RETURN elementId(r) AS rid, type(r) AS reltype,
           r.{PROP_E} AS e_embedding,
           elementId(startNode(r)) AS start_eid,
           elementId(endNode(r)) AS end_eid
    """
    with driver.session() as s:
        rows = s.run(cypher, v_eid=v_eid, seed_eid=seed_eid, k=max_paths).data()
    return rows
```

#### 路径查询详解

```
用户query: "HG的相关数据..."
      ↓ (Step 1-2)
初始候选: [n1, n2, n3, ..., n20]  # Top-K=20
      ↓ (Step 3)
选择种子: seed = Top-M的均值节点  # M=3
      ↓ (Step 6)
对每个候选节点 v：
  查询: shortestPath((seed)-[*1..2]-(v))
  返回: 路径上的所有边及其embedding
```

**示例场景**:

```
假设用户query找到了关于HG的数据节点和结论节点：
- seed: 最相关的"HG测量数据"节点
- v1: "HG浓度结论"节点
- v2: "HG分析方法"节点

查询seed→v1的路径：
  seed(HG数据) -[MASTER_mp_supports]-> v1(HG结论)
  返回: 边的embedding，用于评估证据质量
```

### 3.3 是否与Meta Path相关？

**答案：部分相关，但不完全是Meta Path**

#### Meta Path的定义

Meta Path是预定义的类型序列模式，例如：

```
Author -> Paper -> Venue -> Paper -> Author
(作者-论文-期刊-论文-作者)
```

#### Pipeline D的路径查询特点

**相似之处**:

1. ✅ 使用了图中的**关系类型约束**
2. ✅ Step 1-2的`retrieval_query`定义了特定的**关系模式**
   
   ```cypher
   (DataSet)-[:MASTER_mp_supports]->(Claim)
   ```

**不同之处**:

1. ❌ **不是固定的Meta Path模板**
   
   - Meta Path通常是固定的类型序列
   - Pipeline D的路径是**动态查询的最短路径**

2. ❌ **路径长度动态**
   
   ```cypher
   
   shortestPath((seed)-[*1..2]-(v))  # 1-2跳的最短路径
   ```
   
   - Meta Path通常有固定长度
   - 这里根据实际图结构动态决定

3. ❌ **关系类型不限制**
   
   ```cypher
   (seed)-[*1..2]-(v)  # 任意关系类型
   ```
   
   - 不要求特定的关系类型序列
   - 只要能连接seed和v即可

4. ✅ **但初始检索使用了语义模板**
   
   ```cypher
   (DataSet)-[:MASTER_mp_supports]->(Claim)
   ```
   
   - 这部分类似Meta Path的作用
   - 定义了特定的语义关系模式

### 3.4 路径查询的真实含义

```
Pipeline D的路径查询 = 
  预定义语义模板 (初始检索) + 
  动态最短路径查询 (证据路径) + 
  边embedding评分 (路径质量)
```

**实际工作流程**:

```
Step 1-2: 使用语义模板找到候选
    ↓
    (DataSet) -[supports]-> (Claim)
    类似Meta Path的作用

Step 6: 动态查询最短路径
    ↓
    seed -[*1..2]- candidate
    不限制具体关系类型，但限制跳数

Step 7-8: 评估路径质量
    ↓
    使用边的hidden embedding计算语义得分
```

## 四、完整流程示例

### 用户输入与系统响应

**用户输入**:

```
"总汞含量的研究有哪些结果？"
```

**Step-by-Step执行**:

#### Step 1-2: 初始检索

```python
query_text = "总汞含量的研究有哪些结果？"

# 向量检索
query_embedding = embed_model.embed(query_text)
# → 找到相关的"汞含量数据"节点

# 全文检索
# → 精确匹配"总汞含量"关键词的节点

# Cypher扩展
# (DataSet)-[supports]->(Claim)
# → 返回支持关系对
```

#### Step 3: 构造锚点

question： 这里为何要进行mean计算？

```python
# 从Top-20中选择Top-3最相关的节点
# 计算它们的hidden embedding均值作为z_seed
z_seed = mean([z(top1), z(top2), z(top3)])
```

#### Step 4: 构造查询子图

question: 这里实际对edge 是不做限制的，也没有使用edge 的hidden embedding

```cypher
# 以seed为中心，1-3跳范围内的子图
MATCH (seed)-[*1..3]-(v:__Master__)
```

#### Step 5: 结构得分

question: 问题最大在这里，这里得到的是step4 返回的子图关系终点(v) 与锚点z_zeed 的向量相似度，从语义而言有什么意义？开始节点与目标节点相似？那不是成为找到与闭环最相似的终点？ 例如对应z=Data  这个节点，那么找到的是与初始节点v最相似的与之关联的终点v?

```python
# 计算每个候选与z_seed的相似度
s_struct(v) = cos_similarity(z(v), z_seed)
```

#### Step 6: 证据路径

这里也有个问题这里相对于又从新查询了一次路径实际是对step4的重复

```cypher
# 对每个候选v，查询seed→v的最短路径
MATCH p=shortestPath((seed)-[*1..2]-(v))
RETURN relationships(p)
```

#### Step 7-8: 路径语义得分

这里我记得应该是edge.type 对应step6 得到的 relation p 的edge 在整个oseg图中的平均hidden embedding，

那么我理解代码，就是对返回的p路径上的每一个存在的edge，例如 假设有多条(Data)-[support]->(Method)-[use]->(Tool)，中的[support][use]计算其与OSEG 图中平均[support][use] 的edge hidden embedding 相似度，然后求均值，再比较各条实例relation的socre

但是step7-8的意义是什么？为什么要这样计算？

```python
# 对路径上每条边计算得分
for edge in path:
    score = cos_similarity(
        edge.hidden_embedding,        # 边的hidden embedding
        prototype[edge.type]          # 该关系类型的原型
    )
s_path(v) = mean(scores)
```

#### Step 9: Re-ranking

```python
final_score = (
    0.5 * static_score +    # 初始检索得分
    0.3 * s_path +          # 路径语义得分
    0.2 * prior_score +     # 先验置信度
    0.0 * s_struct          # 结构得分（权重和=1）
)
```

#### Step 10: LLM生成答案

```python
# 将Top-5节点的文本送入LLM
context = [node1.text, node2.text, ..., node5.text]
prompt = f"根据以下证据回答：{query_text}\n\n{context}"
answer = llm.generate(prompt)
```

## 五、关键设计特点

### 5.1 与用户输入的多层交互

| 步骤       | 用户输入的作用 | 处理方式                           |
| -------- | ------- | ------------------------------ |
| Step 1-2 | 直接检索    | query_text → embedding + 关键词匹配 |
| Step 3-5 | 间接影响    | 通过初始结果构造锚点和子图                  |
| Step 6-8 | 间接影响    | 评估候选节点与query的关联路径              |
| Step 10  | 直接使用    | query_text作为LLM的问题输入           |

### 5.2 路径查询的设计理念

**不是纯粹的Meta Path，而是**:

1. **语义引导的动态路径查询**
   
   - 初始检索使用语义模板（类似Meta Path）
   - 证据路径使用动态最短路径

2. **质量驱动的路径评估**
   
   - 使用GNN学到的边embedding
   - 评估路径的语义一致性

3. **用户query驱动的整体流程**
   
   - query决定初始候选
   - query影响路径的相关性评估
   - query指导LLM的答案生成

### 5.3 与传统Meta Path的对比

| 特性   | 传统Meta Path | Pipeline D     |
| ---- | ----------- | -------------- |
| 路径模式 | 固定类型序列      | 动态最短路径 + 语义模板  |
| 路径长度 | 固定          | 可变（1-2跳）       |
| 关系约束 | 严格类型序列      | 灵活（初始检索有约束）    |
| 评分方式 | 路径实例计数      | 边embedding语义得分 |
| 用户交互 | 间接（预定义）     | 直接（query驱动）    |

## 六、总结

### Pipeline D的核心思想

```
用户自然语言query
        ↓
[语义引导] 初始检索找到候选节点
        ↓
[结构感知] 基于GNN hidden embeddings构造锚点
        ↓
[证据路径] 动态查询最短路径作为解释证据
        ↓
[质量评估] 使用边embedding评估路径语义一致性
        ↓
[综合排序] 多维度re-ranking
        ↓
[自然语言] LLM生成最终答案
```

### 关键创新点

1. **Hybrid初始检索**: 语义 + 关键词双保险
2. **GNN hidden embeddings**: 结构感知的表示学习
3. **动态证据路径**: 不是固定Meta Path，而是query驱动的动态路径
4. **边embedding评分**: 评估关系的语义质量
5. **多维度re-ranking**: 综合静态、结构、路径、先验得分
6. **End-to-End**: 从自然语言query到自然语言answer

### 与Meta Path的关系

**部分借鉴，但不完全依赖**:

- ✅ 初始检索的`retrieval_query`类似Meta Path模板
- ✅ 定义了特定的语义关系模式
- ❌ 证据路径查询不是固定的Meta Path
- ❌ 更灵活，query驱动，动态适应

Pipeline D是一个**query驱动的、基于GNN表示学习的、动态证据路径查询系统**，而不是传统的基于固定Meta Path的检索系统。
