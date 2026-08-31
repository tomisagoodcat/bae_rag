# Pipeline D 可视化流程图

## 图1: 用户Query到最终Answer的完整流程

```mermaid
graph TD
    %% 样式定义
    classDef userStyle fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef retrievalStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef gnnStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef pathStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef rerankStyle fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef llmStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:3px

    %% 用户输入
    USER["👤 用户输入<br/>query_text:<br/>'总汞含量的研究有哪些结果？'"]:::userStyle
    
    %% Step 1-2: 初始检索
    USER --> HYBRID["Step 1-2: HybridCypherRetriever<br/>🔍 双通道检索"]:::retrievalStyle
    
    HYBRID --> VEC["向量通道<br/>query_text → embedding<br/>→ 向量索引"]:::retrievalStyle
    HYBRID --> FULL["全文通道<br/>query_text → 关键词<br/>→ 全文索引"]:::retrievalStyle
    
    VEC --> MERGE["分数融合<br/>归一化 + 加权"]:::retrievalStyle
    FULL --> MERGE
    
    MERGE --> CYPHER["Cypher扩展<br/>(DataSet)-[supports]->(Claim)"]:::retrievalStyle
    
    CYPHER --> TOPK["Top-K 候选节点<br/>(K=20)<br/>elementIDs: [n1, n2, ..., n20]"]:::retrievalStyle
    
    %% Step 3: 构造锚点
    TOPK --> SEED["Step 3: 构造锚点 z_seed<br/>取Top-M (M=3)的<br/>GNN hidden embedding均值"]:::gnnStyle
    
    %% Step 4: 构造子图
    SEED --> SUBG["Step 4: 构造查询子图 G_q<br/>以seed为中心<br/>1-3跳邻域"]:::gnnStyle
    
    %% Step 5: 结构得分
    SUBG --> STRUCT["Step 5: 计算结构得分<br/>s_struct(v) = cos(z(v), z_seed)"]:::gnnStyle
    
    %% Step 6: 证据路径
    STRUCT --> PATH["Step 6: 抽取证据路径<br/>对每个候选v:<br/>shortestPath((seed)-[*1..2]-(v))"]:::pathStyle
    
    %% Step 7-8: 路径得分
    PATH --> PATHSCORE["Step 7-8: 路径语义得分<br/>对路径上每条边e:<br/>score = cos(e_hidden, prototype)<br/>s_path(v) = mean(scores)"]:::pathStyle
    
    %% Step 9: Re-ranking
    PATHSCORE --> RERANK["Step 9: Graph-aware Re-ranking<br/>final_score = 0.5*static + 0.3*path<br/>+ 0.2*prior + 0.0*struct"]:::rerankStyle
    
    RERANK --> TOPN["Top-N 结果<br/>(N=5)<br/>排序后的候选节点"]:::rerankStyle
    
    %% Step 10: LLM生成
    TOPN --> LLM["Step 10: LLM生成答案<br/>Context: Top-N节点文本<br/>Question: query_text"]:::llmStyle
    
    LLM --> ANSWER["📝 自然语言答案<br/>(附带来源标注)"]:::llmStyle
    
    ANSWER --> USEROUT["👤 返回给用户"]:::userStyle
```

## 图2: Step 1-2 HybridCypherRetriever详细流程

```mermaid
graph TD
    %% 样式
    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef vectorStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef fulltextStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef fusionStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef outputStyle fill:#ffebee,stroke:#c62828,stroke-width:2px

    %% 输入
    Q["用户Query<br/>'请给出对HG的相关数据...'"]:::inputStyle
    
    %% 向量通道
    Q --> EMB["Embedding模型<br/>text → vector"]:::vectorStyle
    EMB --> QVEC["query_vector<br/>[0.12, -0.03, ..., 0.45]<br/>768维"]:::vectorStyle
    QVEC --> VIDX["向量索引查询<br/>SEG_static_emb_index<br/>ANN检索"]:::vectorStyle
    VIDX --> VRES["向量结果<br/>[(node1, score1),<br/>(node2, score2), ...]"]:::vectorStyle
    
    %% 全文通道
    Q --> FTEXT["提取关键词<br/>'HG' '相关数据'"]:::fulltextStyle
    FTEXT --> FIDX["全文索引查询<br/>SEG_FULLTEXT_INDEX_CHUNK<br/>BM25检索"]:::fulltextStyle
    FIDX --> FRES["全文结果<br/>[(node3, score3),<br/>(node4, score4), ...]"]:::fulltextStyle
    
    %% 融合
    VRES --> NORM["分数归一化<br/>Min-Max Scaling"]:::fusionStyle
    FRES --> NORM
    NORM --> FUSE["加权融合<br/>α*vector_score +<br/>(1-α)*fulltext_score"]:::fusionStyle
    FUSE --> SORT["合并排序<br/>按融合得分排序"]:::fusionStyle
    
    %% Cypher扩展
    SORT --> TOPK["Top-K节点<br/>(K=20)"]:::fusionStyle
    TOPK --> CYP["执行retrieval_query<br/>MATCH (n)-[:supports]->(m)<br/>RETURN elementId(n), elementId(m)"]:::outputStyle
    
    CYP --> OUT["返回结果<br/>节点对 + 关系信息<br/>[(n_eid, m_eid, texts), ...]"]:::outputStyle
```

## 图3: Step 6 证据路径查询详解

```mermaid
graph LR
    %% 样式
    classDef seedStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    classDef candStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef pathStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef edgeStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    %% 种子节点
    SEED["🎯 Seed Node<br/>(Top-M均值锚点)<br/>z_seed"]:::seedStyle
    
    %% 候选节点
    V1["Candidate v1<br/>'HG浓度结论'"]:::candStyle
    V2["Candidate v2<br/>'HG分析方法'"]:::candStyle
    V3["Candidate v3<br/>'HG健康影响'"]:::candStyle
    
    %% 路径
    SEED -->|"shortestPath<br/>[*1..2]"| P1["Path to v1"]:::pathStyle
    SEED -->|"shortestPath<br/>[*1..2]"| P2["Path to v2"]:::pathStyle
    SEED -->|"shortestPath<br/>[*1..2]"| P3["Path to v3"]:::pathStyle
    
    P1 --> V1
    P2 --> V2
    P3 --> V3
    
    %% 边信息
    P1 -.-> E1["Edge 1<br/>type: supports<br/>e_hidden: [...]"]:::edgeStyle
    P2 -.-> E2["Edge 2<br/>type: hasMethod<br/>e_hidden: [...]"]:::edgeStyle
    P3 -.-> E3["Edge 3<br/>type: causes<br/>e_hidden: [...]"]:::edgeStyle
    
    %% 边评分
    E1 --> S1["cos(e_hidden,<br/>prototype_supports)"]:::edgeStyle
    E2 --> S2["cos(e_hidden,<br/>prototype_hasMethod)"]:::edgeStyle
    E3 --> S3["cos(e_hidden,<br/>prototype_causes)"]:::edgeStyle
```

## 图4: 路径查询与Meta Path的对比

```mermaid
graph TD
    subgraph "传统Meta Path"
        MP1["固定模式<br/>Author→Paper→Venue"]
        MP2["固定长度<br/>必须3跳"]
        MP3["严格类型<br/>每步类型固定"]
        MP4["路径计数<br/>统计路径实例数"]
        
        MP1 --> MP2 --> MP3 --> MP4
    end
    
    subgraph "Pipeline D 路径查询"
        PD1["语义模板 + 动态路径<br/>(DataSet)-[supports]->(Claim)<br/>+ shortestPath"]
        PD2["灵活长度<br/>1-2跳（可变）"]
        PD3["类型灵活<br/>初始检索有约束<br/>证据路径不限"]
        PD4["边embedding评分<br/>语义相似度"]
        
        PD1 --> PD2 --> PD3 --> PD4
    end
    
    MP4 -.->|"vs"| PD4
```

## 图5: Re-ranking多维度得分融合

```mermaid
graph TD
    %% 样式
    classDef scoreStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef weightStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef finalStyle fill:#ffebee,stroke:#c62828,stroke-width:3px

    %% 各维度得分
    S1["Static Score<br/>初始检索得分<br/>(向量+全文融合)"]:::scoreStyle
    S2["Structure Score<br/>s_struct<br/>cos(z(v), z_seed)"]:::scoreStyle
    S3["Path Score<br/>s_path<br/>路径语义得分"]:::scoreStyle
    S4["Prior Score<br/>先验置信度<br/>(master_score)"]:::scoreStyle
    
    %% 权重
    S1 --> W1["α = 0.5"]:::weightStyle
    S2 --> W2["β = 0.0<br/>(结构得分权重小)"]:::weightStyle
    S3 --> W3["γ = 0.3"]:::weightStyle
    S4 --> W4["δ = 0.2"]:::weightStyle
    
    %% 最终得分
    W1 --> FINAL["Final Score<br/>0.5*static + 0.0*struct<br/>+ 0.3*path + 0.2*prior"]:::finalStyle
    W2 --> FINAL
    W3 --> FINAL
    W4 --> FINAL
    
    FINAL --> RANK["按final_score排序<br/>得到Top-N"]:::finalStyle
```

## 图6: 完整的Query-Answer循环

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant HC as HybridCypherRetriever
    participant Neo4j as 📊 Neo4j图数据库
    participant GNN as 🧠 GNN Embeddings
    participant Rerank as 🔄 Re-ranker
    participant LLM as 🤖 LLM
    
    User->>HC: query_text: "总汞含量的研究结果？"
    
    Note over HC: Step 1-2: 初始检索
    HC->>Neo4j: 向量检索 (embedding)
    Neo4j-->>HC: Top-K1 节点
    HC->>Neo4j: 全文检索 (关键词)
    Neo4j-->>HC: Top-K2 节点
    HC->>HC: 融合 + Cypher扩展
    HC-->>User: Top-K 候选 (K=20)
    
    Note over GNN: Step 3-5: GNN处理
    User->>GNN: Top-K elementIDs
    GNN->>Neo4j: 获取 hidden embeddings
    Neo4j-->>GNN: z(v1), z(v2), ...
    GNN->>GNN: 构造 z_seed (Top-M均值)
    GNN->>Neo4j: 构造查询子图 G_q
    Neo4j-->>GNN: 子图节点
    GNN->>GNN: 计算结构得分
    
    Note over Rerank: Step 6-9: 路径与Re-ranking
    GNN->>Neo4j: 查询证据路径 (shortestPath)
    Neo4j-->>Rerank: 路径边 + embeddings
    Rerank->>Rerank: 计算路径语义得分
    Rerank->>Rerank: 综合多维度得分
    Rerank-->>User: Top-N 结果 (N=5)
    
    Note over LLM: Step 10: 生成答案
    User->>Neo4j: 获取Top-N节点文本
    Neo4j-->>User: 节点文本内容
    User->>LLM: Context + query_text
    LLM-->>User: 自然语言答案 + 来源标注
```

## 图7: 数据流与维度变化

```mermaid
graph LR
    %% 样式
    classDef textStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef vecStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef gnnStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef scoreStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px

    %% 用户输入
    Q["query_text<br/>(自然语言)"]:::textStyle
    
    %% 初始检索
    Q --> E["embedding<br/>(768D)"]:::vecStyle
    E --> V["向量检索<br/>Top-K nodes"]:::vecStyle
    Q --> F["关键词<br/>全文检索"]:::textStyle
    F --> T["Top-K nodes"]:::textStyle
    
    V --> M["融合<br/>Top-K=20"]:::vecStyle
    T --> M
    
    %% GNN处理
    M --> Z["获取z(v)<br/>(256D GNN)"]:::gnnStyle
    Z --> S["z_seed<br/>(256D)"]:::gnnStyle
    
    %% 路径查询
    S --> P["查询路径<br/>edges"]:::gnnStyle
    P --> EH["e_hidden<br/>(256D)"]:::gnnStyle
    
    %% 得分
    EH --> PS["path_score<br/>(scalar)"]:::scoreStyle
    Z --> SS["struct_score<br/>(scalar)"]:::scoreStyle
    M --> STS["static_score<br/>(scalar)"]:::scoreStyle
    
    PS --> FS["final_score"]:::scoreStyle
    SS --> FS
    STS --> FS
    
    %% 最终答案
    FS --> TN["Top-N<br/>节点文本"]:::textStyle
    TN --> ANS["LLM Answer<br/>(自然语言)"]:::textStyle
```

## 关键流程总结

### 1. 用户Query的多次使用
- **Step 1-2**: 直接用于检索（embedding + 关键词）
- **Step 10**: 直接用于LLM提示词

### 2. 路径查询的两个层次
- **初始检索**: 使用预定义语义模板（类似Meta Path）
- **证据路径**: 使用动态最短路径查询（不是Meta Path）

### 3. GNN Hidden Embeddings的作用
- **节点embedding**: 用于结构得分
- **边embedding**: 用于路径语义得分

### 4. 多维度融合
- Static (50%): 初始检索相关性
- Path (30%): 证据路径质量
- Prior (20%): 先验置信度
- Struct (0%): 结构相似度（权重可调）

这个Pipeline实现了**从自然语言Query到自然语言Answer的完整闭环**，充分利用了图结构、GNN表示学习和LLM生成能力。

