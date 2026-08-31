# Graph-aware Hybrid Retrieval Method：评审与修订

## 总体评估

### ✅ 优点

1. **逻辑完整**：从初始检索 → 图扩展 → 多维度评分 → re-ranking，流程清晰
2. **创新性强**：结合static embedding、hidden embedding、edge embedding和graph metrics
3. **可解释性好**：每个得分都有明确的语义含义
4. **与前文衔接**：明确使用了OSEG和learned embeddings

### ⚠️ 需要改进的问题

1. **步骤3-5的逻辑跳跃**：从"图检索得到锚点" → "返回hidden embedding"，中间过程不清晰
2. **术语混淆**：agentic vs agnentic；node_seed vs node_zeed
3. **公式表述**：需要更严谨的数学符号和定义
4. **与代码实现的差异**：meta-path vs shortest path需要明确权衡

---

## 逐步分析与修订

### **步骤1：Query Understanding & Subgraph Routing**

#### 你的原文（修正拼写）：

> 根据用户的query，通过**agentic**，引导问题导向面向EBM, MPU, EEM语义子图，进行初始检索。agentic根据用户提问，基于react引导载入面向不同语义子图的查询模块。

#### 问题分析：

1. **术语问题**："agentic"应该是"LLM-based agent"或"query router"
2. **EBM/MPU/EEM定义缺失**：需要在前文定义
3. **react机制**：需要说明是ReAct (Reasoning + Acting) framework

#### 📝 修订版本（SCI一区风格）：

### 3.1 Query-driven Subgraph Routing

To enable domain-specific retrieval over heterogeneous OSEG, we employ an 
LLM-based query router that dynamically selects the most relevant semantic 
subgraph for a given user query $q$. Specifically, OSEG is decomposed into 
three domain-specific semantic subgraphs:

1. **Evidence-based Medicine (EBM) Subgraph** ($G_{\text{EBM}}$): 
   Nodes: {DataSet, Method, Claim, Conclusion}
   Key relations: {supports, contradicts, validates}

2. **Methodology and Procedure Unit (MPU) Subgraph** ($G_{\text{MPU}}$): 
   Nodes: {Method, Tool, Protocol, Parameter}
   Key relations: {uses, implements, configures}

3. **Environmental Evidence Model (EEM) Subgraph** ($G_{\text{EEM}}$): 
   Nodes: {Observation, Location, Sample, Measurement}
   Key relations: {observes, samples_from, measures}

The query router $\mathcal{R}$ leverages a ReAct-based agent [Yao et al., 2023] 
to classify $q$ into one or more subgraph categories:

$$
S_q = \mathcal{R}(q; \mathcal{P}_{\text{route}}) \subseteq \{G_{\text{EBM}}, G_{\text{MPU}}, G_{\text{EEM}}\}
$$

where $\mathcal{P}_{\text{route}}$ is a prompt template that guides the LLM to:
(i) analyze query intent, 
(ii) identify relevant evidence types, and 
(iii) select appropriate subgraph(s).

#### 💡 回答你的问题1：EBM/MPU/EEM的定义

**问题**："EBM/MPU/EEM实际类似与meta path，即预定义了大量的路径，但这里路径可能不一定是完全连续的，而更像neo4j中的projected子图，故应该如何定义？"

**答案**：

- **不是meta-path**：meta-path是路径模式序列（如：Author-Paper-Venue-Paper-Author）
- **是projected subgraph**：通过节点类型和关系类型定义的子图投影

**正确定义方式**：

`
Formally, a semantic subgraph $G_s = (V_s, E_s)$ is defined as:

$$
\begin{aligned}
V_s &= \{v \in V_{\text{OSEG}} \mid \tau(v) \in \mathcal{T}_s\} \\
E_s &= \{e = (u, v) \in E_{\text{OSEG}} \mid u, v \in V_s \land \rho(e) \in \mathcal{R}_s\}
\end{aligned}
$$

where:

- $\tau(v)$: node type function (e.g., $\tau(v) = \text{DataSet}$)
- $\mathcal{T}_s$: allowed node types for subgraph $s$
- $\rho(e)$: relation type function (e.g., $\rho(e) = \text{supports}$)
- $\mathcal{R}_s$: allowed relation types for subgraph $s$

This is equivalent to Neo4j's graph projection operation:

```cypher
CALL gds.graph.project(
    'G_EBM',
    ['DataSet', 'Method', 'Claim', 'Conclusion'],
    ['supports', 'contradicts', 'validates']
)
```



**与meta-path的对比**：

| 概念                     | 定义            | 灵活性     | 你的场景              |
| ---------------------- | ------------- | ------- | ----------------- |
| **Projected Subgraph** | 允许的节点类型和边类型集合 | 高（任意路径） | ✅ 适用（EBM/MPU/EEM） |
| **Meta-path**          | 预定义的路径序列      | 低（固定模式） | ❌ 过于限制            |
| **Relation Pattern**   | 单跳或2跳关系模板     | 中等      | 可选（Step 5中使用）     |

---

### **步骤2：Initial Hybrid Retrieval**

#### 你的原文：

> 初始检索基于node的static embedding向量检索，与fulltext全文检索结合的方式，得到top n命中节点，同时返回对应的相似度分数：
> $\text{static}_{\text{score}} = \alpha \times \text{score}_{\text{hiddenembedding}} + (1 - \alpha) \times \text{full\_text}_{\text{score}}$

#### 问题分析：

1. **公式错误**：应该是"static embedding"而非"hidden embedding"
2. **符号不一致**：下标格式需统一
3. **缺少归一化说明**

#### 📝 修订版本：

### 3.2 Initial Hybrid Retrieval

Given query $q$ and selected subgraph $G_s \in S_q$, we perform hybrid retrieval 
combining vector similarity and full-text search over node static embeddings 
$\mathbf{n}(v)$ (learned in Section X) and textual attributes.

**Vector Retrieval**: Retrieve top-$K_v$ nodes by cosine similarity:
$
\mathcal{V}_{\text{vec}} = \text{Top-}K_v \left\{ v \in V_s \mid \cos(\mathbf{q}_{\text{emb}}, \mathbf{n}(v)) \right\}
$

**Full-text Retrieval**: Retrieve top-$K_f$ nodes by BM25 score:
$
\mathcal{V}_{\text{text}} = \text{Top-}K_f \left\{ v \in V_s \mid \text{BM25}(q, \text{text}(v)) \right\}
$

**Score Fusion**: Combine results with normalized scores:
$
s_{\text{static}}(v) = \alpha \cdot \hat{s}_{\text{vec}}(v) + (1 - \alpha) \cdot \hat{s}_{\text{text}}(v)
$

where $\hat{s}(\cdot)$ denotes min-max normalization to $[0, 1]$. 
This yields the initial candidate set $\mathcal{C}_0 = \text{Top-}K(\mathcal{V}_{\text{vec}} \cup \mathcal{V}_{\text{text}})$.

```

**代码实现难度**：⭐⭐☆☆☆ (简单)

- HybridCypherRetriever已实现
- 只需确保索引建立在正确的subgraph上

---

### **步骤3-4：Structural Anchor Construction**

#### 你的原文（整合3和4）：

> 基于n，面向不同EBM, MPU, EEM语义子图，进行图检索，得到锚点$z_{\text{seed}}$
> 
> 返回$\text{node}_{\text{zeed}}$的hidden embedding $z_i = \text{node}_{\text{hidden embedding}}$，并计算加权平均值：
> $z_{\text{seed}} = \text{mean}\left(\sum_i w_i z(z_i)\right)$

#### 问题分析：

1. **步骤3描述不清**："进行图检索得到锚点"是什么意思？
2. **符号混乱**：$z_{\text{seed}}$, $\text{node}_{\text{zeed}}$, $z(z_i)$
3. **权重定义缺失**：$w_i$是什么？

#### 📝 修订版本：

### 3.3 Query Anchor Construction via Structural Embeddings

To robustly represent the query intent in the learned structural embedding space, 
we construct a query anchor $\mathbf{z}_{\text{seed}}$ by aggregating the hidden 
embeddings of top-retrieved nodes.

**Step 1**: Extract hidden embeddings of top-$M$ candidates ($M \ll K$):
$$
\mathcal{Z} = \{\mathbf{z}(v_i) \mid v_i \in \text{Top-}M(\mathcal{C}_0), \mathbf{z}(v_i) \neq \emptyset\}
$$

where $\mathbf{z}(v) \in \mathbb{R}^d$ is the node hidden embedding learned by 
the heterogeneous GNN (Section Y).

**Step 2**: Compute weighted mean as query anchor:
$$
\mathbf{z}_{\text{seed}} = \frac{\sum_{i=1}^{|\mathcal{Z}|} w_i \mathbf{z}(v_i)}{\sum_{i=1}^{|\mathcal{Z}|} w_i}
$$

where $w_i = s_{\text{static}}(v_i)$ is the normalized static score from Step 3.2.

**Rationale**: 

- $\mathbf{z}_{\text{seed}}$ fuses multiple semantic facets of the query
- Weighting by retrieval scores emphasizes more relevant nodes
- This anchor serves as a structural reference for subsequent graph traversal

```

```

**代码实现难度**：⭐☆☆☆☆ (非常简单)

```python
def build_z_seed(node_info: dict, ranked_eids: list, top_m: int):
  """构造查询锚点"""
  seed_nodes = ranked_eids[:top_m]

  zs = []
  weights = []
  for eid in seed_nodes:
      if eid in node_info and node_info[eid]["z"] is not None:
          zs.append(node_info[eid]["z"])
          weights.append(node_info[eid]["static_score"])

  # 加权平均
  weights = np.array(weights)
  weights = weights / weights.sum()  # 归一化

  z_seed = np.average(np.stack(zs), axis=0, weights=weights)
  return z_seed
```

---

### **步骤5：Meta-path-guided Path Extraction**

#### 你的原文：

> 基于$\text{node}_{\text{seed}}$进行在子图中进行查询，在此使用meta path，得到各个子图中有语义含义的查询路径...

#### 💡 回答你的问题2：Meta-path vs Shortest Path

**你的疑问**：

> "与目前代码实现不同，这里使用了meta path而不是单纯的shortestPath，同时node_seed可以位于meta path中任意一个节点位置"

**对比分析**：

| 维度         | Shortest Path (代码实现)               | Meta-path (你的提议)                                         |
| ---------- | ---------------------------------- | -------------------------------------------------------- |
| **定义**     | `shortestPath((seed)-[*1..2]-(v))` | 预定义路径模式，如：`(Method)-[:use]->(Data)-[:supports]->(Claim)` |
| **灵活性**    | 高（任意路径）                            | 低（仅匹配预定义模式）                                              |
| **语义保证**   | 弱（可能返回无意义路径）                       | 强（确保领域语义）                                                |
| **计算成本**   | 低（单次最短路径查询）                        | 中等（需遍历多个meta-path模板）                                     |
| **seed位置** | 必须是起点或终点                           | **可以在路径中间** ✅                                            |
| **适用场景**   | 开放域检索                              | **领域特定检索** ✅ 更适合你的场景                                     |

**推荐方案：结合两者**

### 3.4 Semantic Path Extraction via Meta-path Templates

To ensure domain-relevant evidence paths, we define meta-path templates for each 
semantic subgraph. For example, in $G_{\text{EBM}}$:

$$
\begin{aligned}
\mathcal{M}_1 &: \text{DataSet} \xrightarrow{\text{supports}} \text{Claim} \xrightarrow{\text{contradicts}} \text{Claim} \\
\mathcal{M}_2 &: \text{Method} \xrightarrow{\text{uses}} \text{DataSet} \xrightarrow{\text{supports}} \text{Claim} \\
\mathcal{M}_3 &: \text{Claim} \xrightarrow{\text{cites}} \text{Literature} \xrightarrow{\text{describes}} \text{Method}
\end{aligned}
$$

**Flexible Anchor Matching**: Unlike traditional meta-path approaches that require 
the seed node at path endpoints, we allow $v_{\text{seed}}$ to match **any position** 
in the meta-path:

$$
\mathcal{P}_{v_{\text{seed}}}^{(\mathcal{M})} = \left\{ p \in \text{paths}(\mathcal{M}) \mid \exists i: p[i] = v_{\text{seed}} \right\}
$$

For each candidate node $v \in \mathcal{C}_0$, we extract paths connecting it to 
$v_{\text{seed}}$ via any meta-path template:

$$
\mathcal{P}(v) = \bigcup_{\mathcal{M} \in \mathcal{M}_{G_s}} \left\{ p \mid p \text{ matches } \mathcal{M} \land \{v, v_{\text{seed}}\} \subseteq \text{nodes}(p) \right\}
$$

```

#### 代码实现（Meta-path查询）：

**难度**：⭐⭐⭐☆☆ (中等)

```python
# 定义meta-path模板
META_PATHS = {
    "EBM": [
        # 格式：(节点序列, 关系序列)
        (["DataSet", "Claim"], ["supports"]),
        (["Method", "DataSet", "Claim"], ["uses", "supports"]),
        (["DataSet", "Claim", "Conclusion"], ["supports", "implies"]),
    ],
    "MPU": [
        (["Method", "Tool", "DataSet"], ["uses", "generates"]),
        (["Protocol", "Method", "Result"], ["defines", "produces"]),
    ]
}

def extract_metapath_paths(driver, seed_eid, candidate_eid, subgraph_type, max_paths=5):
    """
    基于meta-path模板提取路径
    允许seed在路径中的任意位置
    """
    paths = []

    for node_seq, rel_seq in META_PATHS[subgraph_type]:
        # 构造Cypher查询
        # 例如：(n1:DataSet)-[r1:supports]->(n2:Claim)
        match_pattern = ""
        for i in range(len(node_seq)):
            match_pattern += f"(n{i}:{node_seq[i]})"
            if i < len(rel_seq):
                match_pattern += f"-[r{i}:{rel_seq[i]}]->"

        # 构造约束：seed或candidate在路径中
        where_clauses = []
        for i in range(len(node_seq)):
            where_clauses.append(f"elementId(n{i}) = $seed_eid OR elementId(n{i}) = $candidate_eid")

        where_condition = " OR ".join(where_clauses)

        cypher = f"""
        MATCH p = {match_pattern}
        WHERE {where_condition}
        AND elementId(n0) != elementId(n{len(node_seq)-1})  // 避免自环
        WITH p, relationships(p) AS rels
        LIMIT $max_paths
        UNWIND rels AS r
        RETURN elementId(r) AS rid, type(r) AS reltype,
               r.gnn_hiddenEmbdding AS e_embedding,
               [n IN nodes(p) | {{
                   eid: elementId(n),
                   z: n.gnn_hiddenEmbdding,
                   text: n.WHU_HASORIGINALTEXT
               }}] AS path_nodes
        """

        with driver.session() as s:
            result = s.run(cypher, seed_eid=seed_eid, candidate_eid=candidate_eid, max_paths=max_paths).data()
            paths.extend(result)

    return paths
```

**优缺点对比**：

| 方面       | Shortest Path           | Meta-path (你的方案)                                 |
| -------- | ----------------------- | ------------------------------------------------ |
| **优点**   | • 简单<br>• 灵活<br>• 快速    | • **语义保证强** ✅<br>• **可解释性高** ✅<br>• **领域适配性好** ✅ |
| **缺点**   | • 可能返回无意义路径<br>• 难以控制语义 | • 需要预定义模板<br>• 灵活性稍低<br>• 实现稍复杂                  |
| **推荐场景** | 开放域、探索性检索               | **特定领域、高质量检索** ✅ **更适合你的论文**                     |

**建议**：在论文中使用**meta-path方案**，因为：

1. 更符合EBM/MPU/EEM的领域特性
2. 可解释性更强（可以明确说明每种路径的语义含义）
3. 是论文的创新点之一（flexible anchor position）

---

### **步骤6：Structural Relevance Scoring**

#### 你的原文：

> 计算$p_1, p_2, \ldots, p_n$中对应的各个node（排除$\text{node}_{\text{seed}}$）hidden embedding与$z_{\text{seed}}$的向量相似度

#### 📝 修订版本：

`

### 3.5 Structural Relevance Scoring

For each extracted path $p \in \mathcal{P}(v)$, we compute the structural relevance 
of intermediate nodes to the query anchor $\mathbf{z}_{\text{seed}}$.

Let $\text{nodes}(p) = \{v_1, v_2, \ldots, v_L\}$ denote the node sequence in path $p$. 
The structural score of path $p$ is defined as:

$$
s_{\text{struct}}(p) = \frac{1}{|\text{nodes}(p) \setminus \{v_{\text{seed}}\}|} 
\sum_{v_i \in \text{nodes}(p), v_i \neq v_{\text{seed}}} \cos(\mathbf{z}(v_i), \mathbf{z}_{\text{seed}})
$$

**Interpretation**: This score measures how well the path nodes align with the 
query's structural semantics in the learned embedding space. High scores indicate 
that the path traverses nodes that are semantically coherent with the query context.

```

**代码实现难度**：⭐☆☆☆☆ (简单)

```python
def compute_struct_score(path_nodes: list, z_seed: np.ndarray, seed_eid: str):
    """计算路径的结构得分"""
    scores = []

    for node in path_nodes:
        if node['eid'] != seed_eid and node['z'] is not None:
            z_node = np.array(node['z'])
            score = cosine_similarity(z_node, z_seed)
            scores.append(score)

    return np.mean(scores) if scores else 0.0
```

---

### **步骤7-8：Path Semantic Coherence Scoring**

#### 💡 回答你的问题3：步骤合并是否合理？

**你的疑问**：

> "按照之前的代码，是先计算struct_score，排序后再提取路径计算edge相似度。我这里合并了，直接根据meta path得到的路径计算。是否正确？优缺点？"

**对比分析**：

| 方案           | 流程                                                                    | 优点                                                 | 缺点                                 |
| ------------ | --------------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------- |
| **原代码（分步）**  | 1. 计算struct_score<br>2. 排序筛选Top-N<br>3. 对Top-N提取路径<br>4. 计算edge score | • 计算效率高（只对Top-N计算路径）<br>• 适合大规模候选集                 | • 可能遗漏edge score高但struct_score低的路径 |
| **你的方案（合并）** | 1. 同时提取路径<br>2. 同时计算struct_score和edge score<br>3. 综合排序                | • **不遗漏高质量路径** ✅<br>• **评分更全面** ✅<br>• **逻辑更简洁** ✅ | • 计算成本稍高（对所有候选计算路径）                |

**推荐**：**使用你的合并方案**，原因：

1. **理论完整性**：struct_score和path_score应该同时考虑，而不是先用一个筛选
2. **适合meta-path**：既然已经用meta-path保证语义，路径数量不会爆炸
3. **论文叙述清晰**：避免"为什么先用struct_score筛选"的解释负担

#### 📝 修订版本：

### 3.6 Path Semantic Coherence via Edge Prototype Matching

Beyond structural alignment, we assess the semantic coherence of each path by 
comparing edge embeddings to relation-type prototypes.

**Relation Type Prototypes**: For each relation type $r \in \mathcal{R}_{G_s}$, 
we compute the prototype as the mean of all edge hidden embeddings of that type:

$$
\boldsymbol{\mu}_r = \frac{1}{|E_r|} \sum_{e \in E_r} \mathbf{h}_e(e)
$$

where $E_r = \{e \in E_s \mid \rho(e) = r\}$ and $\mathbf{h}_e(e) \in \mathbb{R}^{d'}$ 
is the edge hidden embedding learned in Section Y.

**Path Coherence Score**: For path $p$ with edge sequence $\{e_1, e_2, \ldots, e_L\}$:

$$
s_{\text{path}}(p) = \frac{1}{L} \sum_{j=1}^{L} \cos\left(\mathbf{h}_e(e_j), \boldsymbol{\mu}_{\rho(e_j)}\right)
$$

**Interpretation**: This score measures whether each edge in the path is a typical 
instance of its relation type. High scores indicate that the path follows canonical 
semantic patterns in the domain.

```

**代码实现难度**：⭐⭐☆☆☆ (简单-中等)

```python
def fetch_relation_prototypes(driver, subgraph_label="__Master__"):
    """获取关系类型原型"""
    cypher = f"""
    MATCH ()-[r:{subgraph_label}_EDGE]->()
    WHERE r.gnn_hiddenEmbdding IS NOT NULL
    RETURN type(r) AS reltype, 
           collect(r.gnn_hiddenEmbdding) AS embeddings
    """

    with driver.session() as s:
        results = s.run(cypher).data()

    prototypes = {}
    for row in results:
        reltype = row['reltype']
        embeddings = np.array(row['embeddings'])
        prototypes[reltype] = np.mean(embeddings, axis=0)

    return prototypes

def compute_path_score(path_edges: list, prototypes: dict):
    """计算路径语义一致性得分"""
    scores = []

    for edge in path_edges:
        e_emb = np.array(edge['e_embedding'])
        reltype = edge['reltype']

        if reltype in prototypes:
            proto = prototypes[reltype]
            score = cosine_similarity(e_emb, proto)
            scores.append(score)

    return np.mean(scores) if scores else 0.0
```

---

### **步骤9：Multi-dimensional Re-ranking**

#### 你的原文：

> $\text{node}_{\text{score}} = \alpha \cdot \text{static}_{\text{score}} + \beta \cdot \text{struct}_{\text{score}} + \gamma \cdot \text{path}_{\text{score}} + \eta \cdot \text{graph}_{\text{score}}$

#### 💡 回答你的问题4：加入graph_score的合理性

**非常好的想法！** ✅ 这是**重要创新点**

#### 📝 修订版本：

### 3.7 Multi-dimensional Re-ranking with Graph Centrality

We fuse four complementary relevance signals to compute the final node score:

$$
s_{\text{final}}(v) = \alpha \cdot s_{\text{static}}(v) + \beta \cdot s_{\text{struct}}(v) + \gamma \cdot s_{\text{path}}(v) + \eta \cdot s_{\text{graph}}(v)
$$

where $\alpha + \beta + \gamma + \eta = 1$ and:

1. **$s_{\text{static}}(v)$**: Textual similarity (Section 3.2)

2. **$s_{\text{struct}}(v)$**: Structural alignment to query anchor (Section 3.5)
   
   $$
   s_{\text{struct}}(v) = \max_{p \in \mathcal{P}(v)} s_{\text{struct}}(p)
   $$

3. **$s_{\text{path}}(v)$**: Path semantic coherence (Section 3.6)
   
   $$
   s_{\text{path}}(v) = \max_{p \in \mathcal{P}(v)} s_{\text{path}}(p)
   $$

4. **$s_{\text{graph}}(v)$**: **Graph-theoretic centrality** (NEW contribution)
   
   $$
   s_{\text{graph}}(v) = \lambda_1 \cdot \text{PageRank}(v) + \lambda_2 \cdot \text{Degree}(v) + \lambda_3 \cdot \text{Betweenness}(v)
   $$
   
   where scores are normalized to $[0, 1]$ within subgraph $G_s$.

**Rationale for $s_{\text{graph}}$**:

- **PageRank**: Captures global authority (frequently cited/supported nodes)
- **Degree**: Captures local connectivity (hub nodes)
- **Betweenness**: Captures bridging role (nodes connecting communities)

These metrics complement the learned embeddings by encoding **topological importance**, 
which may not be fully captured by GNN neighborhood aggregation alone.

```

**代码实现难度**：⭐⭐⭐☆☆ (中等，需要GDS库)

```python
# 预计算图度量（在subgraph上）
def compute_graph_metrics(driver, subgraph_name="G_EBM"):
    """
    在指定的projected subgraph上计算图度量
    需要先创建GDS projection
    """
    with driver.session() as s:
        # 1. 创建projection（如果不存在）
        s.run(f"""
        CALL gds.graph.project(
            '{subgraph_name}',
            ['__Master__'],  // 或具体的节点类型
            {{
                MASTER_EDGE: {{type: '*', orientation: 'UNDIRECTED'}}
            }}
        )
        """)

        # 2. 计算PageRank
        s.run(f"""
        CALL gds.pageRank.write(
            '{subgraph_name}',
            {{writeProperty: 'pagerank'}}
        )
        """)

        # 3. 计算Degree
        s.run(f"""
        CALL gds.degree.write(
            '{subgraph_name}',
            {{writeProperty: 'degree'}}
        )
        """)

        # 4. 计算Betweenness（可选，计算较慢）
        s.run(f"""
        CALL gds.betweenness.write(
            '{subgraph_name}',
            {{writeProperty: 'betweenness'}}
        )
        """)

def get_graph_score(driver, node_eid, lambda_weights=[0.5, 0.3, 0.2]):
    """获取节点的图度量得分"""
    cypher = """
    MATCH (n) WHERE elementId(n) = $eid
    RETURN n.pagerank AS pr, n.degree AS deg, n.betweenness AS bc
    """

    with driver.session() as s:
        result = s.run(cypher, eid=node_eid).single()

    # 归一化（需要预先计算subgraph的min/max）
    pr_norm = normalize(result['pr'], pr_min, pr_max)
    deg_norm = normalize(result['deg'], deg_min, deg_max)
    bc_norm = normalize(result['bc'], bc_min, bc_max)

    graph_score = (lambda_weights[0] * pr_norm + 
                   lambda_weights[1] * deg_norm + 
                   lambda_weights[2] * bc_norm)

    return graph_score
```

**实现注意事项**：

1. **预计算**：图度量应该在检索前预计算并存储为节点属性
2. **归一化**：需要在subgraph级别归一化（不是全图）
3. **更新策略**：图更新时需要重新计算度量（可以定期批量更新）

---

### **步骤10：Evidence Path Return for LLM**

#### 💡 回答你的问题5：是否应该返回path和edge信息？

**强烈建议返回！** ✅ 这是**可解释性和可靠性的关键**

#### 📝 修订版本：

### 3.8 Structured Evidence Assembly for LLM Generation

Rather than returning only top-ranked nodes, we construct structured evidence 
packages that include both node content and supporting paths.

For each top-$N$ node $v \in \text{Top-}N(\mathcal{C}_{\text{final}})$, we assemble:

**Evidence Package** $\mathcal{E}(v)$:
$
\mathcal{E}(v) = \left\{ 
\begin{aligned}
&\text{node\_text}(v), \\
&\text{node\_properties}(v), \\
&\mathcal{P}_{\text{top}}(v) = \{\text{path}_1, \ldots, \text{path}_k\}
\end{aligned}
\right\}
$

where each $\text{path}_i$ includes:

- **Node sequence**: $\{v_1, \ldots, v_L\}$ with texts $\{\text{text}(v_1), \ldots\}$
- **Edge sequence**: $\{e_1, \ldots, e_{L-1}\}$ with:
  - Relation types: $\{\rho(e_1), \ldots, \rho(e_{L-1})\}$
  - **Edge texts**: $\{\text{edge\_text}(e_1), \ldots\}$ (if available)
  - Coherence scores: $\{s_{\text{edge}}(e_1), \ldots\}$

**LLM Prompt Construction**:

```python
prompt = f"""
Based on the following evidence from the knowledge graph, answer the question:

Question: {query}

Evidence Node {i}: {node_text}
  Properties: {node_properties}

  Supporting Path 1:
    {v1_text} --[{rel1}: {edge1_text}]--> {v2_text} --[{rel2}: {edge2_text}]--> {v3_text}
    (Path coherence score: {path_score})

  Supporting Path 2:
    ...

Please synthesize these evidences and provide a comprehensive answer, 
citing specific nodes and relationships as [Evidence Node {i}, Path {j}].
"""
```

**Benefits**:

1. **Provenance**: Users can trace answers to specific graph paths

2. **Reliability**: LLM can assess evidence quality via coherence scores

3. **Edge text utilization**: Relationship descriptions enrich context

4. **Multi-hop reasoning**: Paths enable transitive inference
   
   ```
   
   ```

**代码实现难度**：⭐⭐☆☆☆ (中等，主要是格式化)

```python
def assemble_evidence_package(driver, node_eid, paths, top_k_paths=3):
    """
    为LLM组装结构化证据包
    """
    # 1. 获取节点信息
    node_info = fetch_node_info(driver, node_eid)

    # 2. 选择top-k条路径（按path_score排序）
    top_paths = sorted(paths, key=lambda p: p['path_score'], reverse=True)[:top_k_paths]

    # 3. 格式化路径
    formatted_paths = []
    for i, path in enumerate(top_paths, 1):
        path_str = format_path_with_edges(path)
        formatted_paths.append({
            'path_id': i,
            'path_str': path_str,
            'score': path['path_score']
        })

    return {
        'node': node_info,
        'paths': formatted_paths
    }

def format_path_with_edges(path):
    """
    格式化路径为可读文本
    例如：Data("汞含量测定") --[supports: "该数据支持"]--> Claim("汞具有毒性")
    """
    nodes = path['path_nodes']
    edges = path['path_edges']

    path_parts = []
    for i, node in enumerate(nodes):
        # 添加节点
        node_text = node['text'][:50] + "..." if len(node['text']) > 50 else node['text']
        path_parts.append(f'{node["type"]}("{node_text}")')

        # 添加边（如果不是最后一个节点）
        if i < len(edges):
            edge = edges[i]
            edge_text = edge.get('text', '')  # 如果有edge text
            if edge_text:
                path_parts.append(f' --[{edge["reltype"]}: "{edge_text[:30]}..."]--> ')
            else:
                path_parts.append(f' --[{edge["reltype"]}]--> ')

    return ''.join(path_parts)

def generate_llm_prompt(query, evidence_packages, top_n=5):
    """生成LLM提示"""
    prompt_parts = [
        f"Question: {query}\n\n",
        "Evidence from Knowledge Graph:\n\n"
    ]

    for i, pkg in enumerate(evidence_packages[:top_n], 1):
        prompt_parts.append(f"[Evidence Node {i}]\n")
        prompt_parts.append(f"Content: {pkg['node']['text']}\n")
        prompt_parts.append(f"Type: {pkg['node']['type']}\n")
        prompt_parts.append(f"Relevance Score: {pkg['node']['final_score']:.3f}\n\n")

        prompt_parts.append("Supporting Paths:\n")
        for path in pkg['paths']:
            prompt_parts.append(f"  Path {path['path_id']} (coherence: {path['score']:.3f}):\n")
            prompt_parts.append(f"    {path['path_str']}\n\n")

    prompt_parts.append("""
Please provide a comprehensive answer based on the above evidence.
Cite specific evidence using the format [Evidence Node X, Path Y].
""")

    return ''.join(prompt_parts)
```

---

## 完整方法论文本（SCI一区风格）

## 3. Graph-aware Hybrid Retrieval and Re-ranking

Building upon the OSEG constructed in Section X and the learned node and edge 
embeddings $\mathbf{z}(v)$ and $\mathbf{h}_e(e)$ from Section Y, we propose a 
multi-stage graph-aware retrieval framework that combines textual similarity, 
structural semantics, and path coherence to enable accurate and explainable 
evidence retrieval for complex domain queries.

### 3.1 Overview

The retrieval pipeline consists of four stages (Figure X):

1. **Query Routing**: Classify query into domain-specific semantic subgraphs 
   (EBM/MPU/EEM) using LLM-based agent
2. **Hybrid Initial Retrieval**: Combine vector and full-text search over 
   static embeddings to obtain candidate nodes
3. **Graph-aware Scoring**: Extract meta-path-guided evidence paths and compute 
   multi-dimensional relevance scores:
   - Structural alignment ($s_{\text{struct}}$)
   - Path semantic coherence ($s_{\text{path}}$)
   - Graph centrality ($s_{\text{graph}}$)
4. **Structured Evidence Assembly**: Package top-ranked nodes with supporting 
   paths for LLM-based answer generation

[继续插入3.1-3.8的修订内容...]

```

---

## 总结与建议

### ✅ 主要改进

1. **术语规范化**：统一符号、修正拼写
2. **公式严谨化**：明确定义、添加约束
3. **逻辑完整化**：补充缺失步骤、澄清概念
4. **创新点突出**：
   - Flexible anchor position in meta-paths ✨
   - Multi-dimensional scoring with graph centrality ✨
   - Structured evidence packages for LLM ✨

### 📊 代码实现难度评估

| 模块                             | 难度    | 工作量（人日）    | 关键技术                        |
| ------------------------------ | ----- | ---------- | --------------------------- |
| Query Routing (3.1)            | ⭐⭐⭐☆☆ | 3-5        | LLM API, Prompt Engineering |
| Hybrid Retrieval (3.2)         | ⭐⭐☆☆☆ | 1-2        | HybridCypherRetriever (已有)  |
| Anchor Construction (3.3)      | ⭐☆☆☆☆ | 0.5-1      | NumPy加权平均                   |
| **Meta-path Extraction (3.4)** | ⭐⭐⭐⭐☆ | **5-7**    | **Cypher动态查询、模板管理**         |
| Struct Scoring (3.5)           | ⭐☆☆☆☆ | 0.5-1      | 余弦相似度                       |
| Path Scoring (3.6)             | ⭐⭐☆☆☆ | 1-2        | 原型计算、相似度                    |
| **Graph Metrics (3.7)**        | ⭐⭐⭐☆☆ | **3-4**    | **Neo4j GDS库**              |
| Evidence Assembly (3.8)        | ⭐⭐☆☆☆ | 2-3        | 文本格式化、模板                    |
| **总计**                         | -     | **16-25天** | -                           |

**最大挑战**：

1. **Meta-path实现**（3.4）：需要设计灵活的模板系统和高效的Cypher查询
2. **Graph Metrics预计算**（3.7）：需要集成Neo4j GDS并设计更新策略

### 🎯 论文撰写建议

1. **标题建议**：

```

   "Graph-aware Hybrid Retrieval with Meta-path-guided Evidence Extraction 
   for Domain-specific Question Answering"

```

2. **贡献点（Contributions）**：

```

1. A domain-specific semantic subgraph framework (EBM/MPU/EEM) that enables 
   targeted retrieval over heterogeneous evidence graphs

2. A flexible meta-path matching mechanism that allows query anchors to 
   appear at arbitrary positions in evidence paths, improving recall

3. A multi-dimensional re-ranking scheme that fuses textual, structural, 
   semantic, and graph-theoretic signals for robust relevance estimation

4. A structured evidence assembly approach that provides explainable 
   graph-based provenance for LLM-generated answers
   
   ```
   
   ```

5. **实验设计**：
   
   - **Ablation study**: 逐个移除$s_{\text{static}}$, $s_{\text{struct}}$, $s_{\text{path}}$, $s_{\text{graph}}$
   - **Meta-path vs Shortest Path**: 比较语义质量和召回率
   - **权重分析**: $\alpha, \beta, \gamma, \eta$的敏感性分析
   - **可解释性评估**: 人工评估返回路径的有效性

6. **与前文衔接**：
   
   ```
   "In Section Y, we learned structure-aware node embeddings z(v) and edge 
   embeddings h_e(e) via masked heterogeneous graph autoencoding. These 
   embeddings capture not only node/edge content, but also their topological 
   roles and relational context within OSEG. In this section, we leverage 
   these learned representations to enable graph-aware retrieval..."
   ```

---

## 直接回答你的5个问题

### Q1: EBM/MPU/EEM如何定义？

**A**: 使用**Projected Subgraph**（子图投影），而非meta-path。定义为允许的节点类型和边类型集合。

### Q2: 使用meta-path还是shortest path？

**A**: **推荐meta-path**，因为语义保证更强，更适合领域特定检索，且是论文创新点。

### Q3: node_seed在路径中的位置？

**A**: **可以在任意位置**（这是你的创新点！），Cypher查询使用OR条件匹配任意节点。

### Q4: 合并struct_score和path_score计算是否合理？

**A**: **非常合理**！避免过早筛选，评分更全面，逻辑更清晰。

### Q5: 是否应该返回edge信息？

**A**: **强烈建议**！提升可解释性和可靠性，充分利用edge hidden embedding和edge text。

---

**总体评价**：你的方法论框架非常完整且创新，经过修订后完全符合SCI一区标准。建议重点突出meta-path和multi-dimensional scoring两个创新点。


