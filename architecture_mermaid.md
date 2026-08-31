# OAS-GAT-EM 架构图 (Mermaid格式)

## 可以直接在GitHub、Jupyter、或支持Mermaid的Markdown查看器中渲染

### 图1: 整体架构流程图

```mermaid
graph TD
    %% 定义样式
    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef encoderStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef decoderStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef lossStyle fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    classDef outputStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    %% 输入层
    G[("G_OSEG<br/>Heterogeneous Graph")]:::inputStyle
    N["Node Features<br/>n(v) ∈ ℝ^768"]:::inputStyle
    E["Edge Features<br/>e(e) ∈ ℝ^768"]:::inputStyle
    
    G --> N
    G --> E
    
    %% Mask层
    N --> NM["Node Mask<br/>ρ_n = 0.3<br/>ñ(v) ∈ ℝ^768"]:::inputStyle
    E --> EM["Edge Mask<br/>ρ_e = 0.2<br/>ẽ(e) ∈ ℝ^768"]:::inputStyle
    
    %% Node Encoder
    NM --> NE["Node Encoder<br/>HeteroGAT<br/>2-layer, 4-head"]:::encoderStyle
    EM -.->|"For Attention"| NE
    NE --> Z["Node Hidden<br/>z(v) ∈ ℝ^256"]:::encoderStyle
    
    %% Edge Encoder
    Z --> EE["Edge Encoder<br/>MLP<br/>2-layer"]:::encoderStyle
    EM --> EE
    EE --> EH["Edge Hidden<br/>e_h(e) ∈ ℝ^256"]:::encoderStyle
    
    %% Decoders
    Z --> ND["Node Decoder<br/>Linear"]:::decoderStyle
    EH --> ED["Edge Decoder<br/>Linear"]:::decoderStyle
    
    ND --> NR["Reconstructed<br/>n̂(v) ∈ ℝ^768"]:::decoderStyle
    ED --> ER["Reconstructed<br/>ê(e) ∈ ℝ^768"]:::decoderStyle
    
    %% Loss
    NR --> LN["L_n = MSE<br/>(masked only)"]:::lossStyle
    N -.->|"Original"| LN
    
    ER --> LE["L_e = MSE<br/>(masked only)"]:::lossStyle
    E -.->|"Original"| LE
    
    LN --> LT["L_total = L_n + λ_e·L_e<br/>λ_e = 0.5"]:::lossStyle
    LE --> LT
    
    %% Optimization
    LT --> OPT["Backpropagation<br/>Adam Optimizer"]:::lossStyle
    
    %% Output
    Z --> OUT1["Node Embeddings<br/>h(v) = z(v)"]:::outputStyle
    EH --> OUT2["Edge Embeddings<br/>h(e) = e_h(e)"]:::outputStyle
```

### 图2: Node Encoder详细结构

```mermaid
graph TB
    %% 样式
    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef layerStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef outputStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    %% 输入
    IN["Masked Input<br/>ñ(v) ∈ ℝ^768<br/>ẽ(e) ∈ ℝ^768"]:::inputStyle
    
    %% Layer 1
    IN --> L1["Layer 1: Multi-Head GAT<br/>H=4 heads, d_h=256"]:::layerStyle
    L1 --> L1D["Details:<br/>α_uv^k = Attn([W·ñ(u) ∥ W·ñ(v) ∥ U·ẽ])<br/>h_v^r = Concat(heads)<br/>∈ ℝ^1024"]:::layerStyle
    L1D --> L1A["Multi-Relation Aggregation:<br/>h_v^(1) = Σ_r h_v^r"]:::layerStyle
    L1A --> ACT1["ReLU + Dropout(0.3)"]:::layerStyle
    
    %% Layer 2
    ACT1 --> L2["Layer 2: Single-Head GAT<br/>H=1, d_z=256"]:::layerStyle
    L2 --> L2D["Details:<br/>α_uv = Attn([W·h_u^(1) ∥ W·h_v^(1) ∥ U·ẽ])<br/>z(v) = Σ_r Σ_u α_uv·W·h_u^(1)"]:::layerStyle
    
    %% Output
    L2D --> OUT["Node Hidden Embedding<br/>z(v) ∈ ℝ^256"]:::outputStyle
```

### 图3: Edge Encoder详细结构

```mermaid
graph TB
    %% 样式
    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef layerStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef outputStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    %% 输入
    ZU["z(u) ∈ ℝ^256<br/>(Source Node)"]:::inputStyle
    ZV["z(v) ∈ ℝ^256<br/>(Target Node)"]:::inputStyle
    EE["ẽ(e) ∈ ℝ^768<br/>(Masked Edge)"]:::inputStyle
    W["w(e) ∈ ℝ<br/>(Weight)"]:::inputStyle
    
    %% Concatenation
    ZU --> CONCAT["Concatenate<br/>f_e = [z(u) ∥ z(v) ∥ ẽ(e) ∥ w(e)]<br/>∈ ℝ^1281"]:::layerStyle
    ZV --> CONCAT
    EE --> CONCAT
    W --> CONCAT
    
    %% MLP Layer 1
    CONCAT --> MLP1["MLP Layer 1<br/>h_e^(1) = ReLU(W·f_e + b)<br/>∈ ℝ^256"]:::layerStyle
    MLP1 --> DROP["Dropout(0.3)"]:::layerStyle
    
    %% MLP Layer 2
    DROP --> MLP2["MLP Layer 2<br/>e_h(e) = W·h_e^(1) + b<br/>∈ ℝ^256"]:::layerStyle
    
    %% Output
    MLP2 --> OUT["Edge Hidden Embedding<br/>e_h(e) ∈ ℝ^256"]:::outputStyle
```

### 图4: 注意力机制详细结构

```mermaid
graph LR
    %% 样式
    classDef nodeStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef attnStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef outputStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    %% 节点特征
    U["Source u<br/>ñ(u)"]:::nodeStyle
    V["Target v<br/>ñ(v)"]:::nodeStyle
    EUV["Edge<br/>ẽ(u,v)"]:::nodeStyle
    
    %% 变换
    U --> WU["W_r·ñ(u)"]:::attnStyle
    V --> WV["W_r·ñ(v)"]:::attnStyle
    EUV --> UE["U_r·ẽ(u,v)"]:::attnStyle
    
    %% 拼接
    WU --> CAT["[· ∥ · ∥ ·]"]:::attnStyle
    WV --> CAT
    UE --> CAT
    
    %% 注意力计算
    CAT --> A["a_r^⊤ · [concat]"]:::attnStyle
    A --> LR["LeakyReLU"]:::attnStyle
    LR --> SOFT["Softmax"]:::attnStyle
    SOFT --> ALPHA["α_uv"]:::outputStyle
    
    %% 消息
    ALPHA --> MSG["α_uv · W_r·ñ(u)"]:::outputStyle
    WU -.-> MSG
```

### 图5: Masking策略对比

```mermaid
graph TD
    %% 样式
    classDef normalStyle fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    classDef maskStyle fill:#ffcdd2,stroke:#d32f2f,stroke-width:2px
    classDef preserveStyle fill:#fff9c4,stroke:#f57c00,stroke-width:2px

    subgraph "Semantic-level Masking (Our Method)"
        N1["Node u"]:::normalStyle
        N2["Node v"]:::normalStyle
        E1["Edge e<br/>Features: MASKED ✗<br/>Structure: PRESERVED ✓"]:::preserveStyle
        N1 -->|"e, ẽ(e)=[0,0,...]"| N2
    end
    
    subgraph "Topology-level Masking (NOT Used)"
        N3["Node u"]:::normalStyle
        N4["Node v"]:::normalStyle
        E2["Edge REMOVED<br/>Both features and structure"]:::maskStyle
        N3 -.->|"✗ Deleted"| N4
    end
```

### 图6: 训练流程

```mermaid
sequenceDiagram
    participant Data as Input Data
    participant Mask as Masking
    participant Enc as Encoders
    participant Dec as Decoders
    participant Loss as Loss Function
    participant Opt as Optimizer
    
    Data->>Mask: Original features
    Note over Mask: 30% nodes<br/>20% edges
    Mask->>Enc: Masked features
    Note over Enc: HeteroGAT + MLP
    Enc->>Dec: Hidden embeddings
    Note over Dec: Linear layers
    Dec->>Loss: Reconstructions
    Data->>Loss: Original features
    Note over Loss: MSE on masked only
    Loss->>Opt: Gradients
    Opt->>Enc: Update parameters
    Opt->>Dec: Update parameters
    
    loop Training Epochs (20)
        Mask->>Enc: New masks per epoch
    end
```

### 图7: 数据流与维度变化

```mermaid
graph LR
    %% 样式
    classDef d768 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef d1024 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef d256 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px

    %% Node流
    N1["n(v)<br/>768"]:::d768
    N2["ñ(v)<br/>768"]:::d768
    N3["h^(1)<br/>1024"]:::d1024
    N4["z(v)<br/>256"]:::d256
    N5["n̂(v)<br/>768"]:::d768
    
    N1 -->|"Mask 30%"| N2
    N2 -->|"GAT L1<br/>4-head"| N3
    N3 -->|"GAT L2<br/>1-head"| N4
    N4 -->|"Linear<br/>Decode"| N5
    
    %% Edge流
    E1["e(e)<br/>768"]:::d768
    E2["ẽ(e)<br/>768"]:::d768
    E3["f_e<br/>1281"]:::d1024
    E4["e_h(e)<br/>256"]:::d256
    E5["ê(e)<br/>768"]:::d768
    
    E1 -->|"Mask 20%"| E2
    E2 -->|"Concat with<br/>z(u),z(v),w"| E3
    E3 -->|"MLP<br/>2-layer"| E4
    E4 -->|"Linear<br/>Decode"| E5
    
    N4 -.->|"For Edge"| E3
```

## 使用说明

1. **GitHub/GitLab**: 这些Mermaid图会自动渲染
2. **Jupyter Notebook**: 需要安装 `jupyter-mermaid` 扩展
3. **Markdown编辑器**: 使用支持Mermaid的编辑器（如Typora, VS Code）
4. **在线工具**: 可以在 https://mermaid.live 查看和编辑

## 导出为论文图片

可以使用以下工具将Mermaid图导出为高质量图片：

1. **Mermaid CLI**: `mmdc -i input.mmd -o output.png -w 2000 -H 1500`
2. **在线编辑器**: https://mermaid.live （可导出PNG/SVG）
3. **VS Code**: 安装 Markdown Preview Mermaid Support 扩展
4. **Draw.io**: 支持导入Mermaid代码

## 推荐论文使用方案

1. **主架构图**: 使用图1（整体架构流程图）
2. **技术细节图**: 使用图2（Node Encoder）和图3（Edge Encoder）
3. **Attention机制**: 使用图4
4. **补充材料**: 使用图5-7作为附录或补充说明




