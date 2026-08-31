# OAS-GAT-EM 架构图（论文插图版）

## Figure X: Overall Architecture of OAS-GAT-EM

### 简化版架构图（推荐用于论文主图）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Heterogeneous Graph G_OSEG                        │
│                                                                           │
│    Nodes: n(v) ∈ ℝ^768           Edges: e(e) ∈ ℝ^768                    │
│    Types: τ ∈ T_V                Types: r ∈ T_E                         │
└─────────────────┬────────────────────────────┬───────────────────────────┘
                  │                            │
                  │ Masking (30%)              │ Masking (20%)
                  ▼                            ▼
          ┌───────────────┐            ┌───────────────┐
          │  ñ(v) ∈ ℝ^768 │            │  ẽ(e) ∈ ℝ^768 │
          └───────┬───────┘            └───────┬───────┘
                  │                            │
                  │                            │ (For attention)
                  │                            │
┏━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┓
┃                          ENCODER MODULE                                ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                         ┃
┃  ┌──────────────────────────────────────────────────────────────┐     ┃
┃  │              Node Encoder (HeteroGAT)                         │     ┃
┃  │                                                                │     ┃
┃  │  ┌────────────────────────────────────────────────────────┐  │     ┃
┃  │  │ Layer 1: Multi-Head Attention (H=4, d_h=256)          │  │     ┃
┃  │  │                                                         │  │     ┃
┃  │  │ α_uv^k = Attn([W·ñ(u) ∥ W·ñ(v) ∥ U·ẽ(u,v)])         │  │     ┃
┃  │  │ h_v^(1) = Σ_r Σ_u α_uv · W·ñ(u)                      │  │     ┃
┃  │  │          ∈ ℝ^1024                                      │  │     ┃
┃  │  └────────────────────────────────────────────────────────┘  │     ┃
┃  │                            ↓ ReLU + Dropout                   │     ┃
┃  │  ┌────────────────────────────────────────────────────────┐  │     ┃
┃  │  │ Layer 2: Single-Head Attention (H=1, d_z=256)         │  │     ┃
┃  │  │                                                         │  │     ┃
┃  │  │ z(v) = Σ_r Σ_u α_uv · W·h_u^(1)                       │  │     ┃
┃  │  │       ∈ ℝ^256                                          │  │     ┃
┃  │  └────────────────────────────────────────────────────────┘  │     ┃
┃  └─────────────────────────┬────────────────────────────────────┘     ┃
┃                            │                                           ┃
┃                            ▼                                           ┃
┃                  ┌─────────────────┐                                   ┃
┃                  │  z(v) ∈ ℝ^256   │ (Node Hidden Emb)                ┃
┃                  └────────┬────────┘                                   ┃
┃                           │                                            ┃
┃                           └────────────────┐                           ┃
┃                                            │                           ┃
┃  ┌─────────────────────────────────────────┼────────────────────────┐ ┃
┃  │           Edge Encoder (MLP)            ▼                        │ ┃
┃  │                                                                   │ ┃
┃  │  f_e = [z(u) ∥ z(v) ∥ ẽ(e) ∥ w(e)] ∈ ℝ^1281                     │ ┃
┃  │                        ↓                                          │ ┃
┃  │  e_h(e) = MLP(f_e) ∈ ℝ^256                                       │ ┃
┃  │                                                                   │ ┃
┃  └─────────────────────────┬───────────────────────────────────────┘ ┃
┃                            │                                           ┃
┃                            ▼                                           ┃
┃                  ┌─────────────────┐                                   ┃
┃                  │ e_h(e) ∈ ℝ^256  │ (Edge Hidden Emb)                ┃
┃                  └─────────────────┘                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                            │
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         DECODER MODULE                                 ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                         ┃
┃         ┌──────────────────┐              ┌──────────────────┐         ┃
┃         │  Node Decoder    │              │  Edge Decoder    │         ┃
┃         │  (Linear)        │              │  (Linear)        │         ┃
┃         │                  │              │                  │         ┃
┃         │ n̂(v) = D_τ·z(v)  │              │ ê(e) = D_r·e_h   │         ┃
┃         │      ∈ ℝ^768     │              │      ∈ ℝ^768     │         ┃
┃         └────────┬─────────┘              └────────┬─────────┘         ┃
┃                  │                                 │                    ┃
┗━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┛
                   │                                 │
┏━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┓
┃                          LOSS MODULE                                   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                         ┃
┃      L_n = 1/|M_n| Σ ∥n̂(v)-n(v)∥²    L_e = 1/|M_e| Σ ∥ê(e)-e(e)∥²   ┃
┃            v∈M_n                              e∈M_e                    ┃
┃                                                                         ┃
┃                    L_total = L_n + λ_e · L_e                           ┃
┃                                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │  Backpropagation & Adam  │
                    └──────────────────────────┘
                                  │
                                  ▼
          ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          ┃              OUTPUT EMBEDDINGS               ┃
          ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
          ┃                                              ┃
          ┃  h(v) = z(v) ∈ ℝ^256    h(e) = e_h(e) ∈ ℝ^256┃
          ┃                                              ┃
          ┃  • Structure-aware     • Relation semantics ┃
          ┃  • Type-specific       • Context-dependent  ┃
          ┃  • Self-supervised     • Path quality       ┃
          ┃                                              ┃
          ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Figure X+1: Attention Mechanism Details

### (a) Heterogeneous Graph Attention with Edge Features

```
For each relation type r = (τ_s, r, τ_t):

Source Node u (τ_s)         Target Node v (τ_t)
     ñ(u)                        ñ(v)
      │                           │
      ├──────────┐                │
      │          │                │
      ▼          ▼                ▼
   W_r·ñ(u)   U_r·ẽ(u,v)     W_r·ñ(v)
      │          │                │
      └─────┬────┴────────────────┘
            │
            ▼
      [W_r·ñ(u) ∥ W_r·ñ(v) ∥ U_r·ẽ(u,v)]
            │
            ▼
    a_r^⊤ · [concatenated features]
            │
            ▼
      LeakyReLU(·)
            │
            ▼
        exp(·)
            │
            ▼
    Normalize (Softmax over N_r(v))
            │
            ▼
         α_uv  (Attention Weight)
            │
            ▼
    α_uv · W_r·ñ(u)  (Weighted Message)
```

### (b) Multi-Relation Aggregation

```
Target Node v receives messages from multiple relation types:

Relation r1: ─────┐
Relation r2: ─────┤
Relation r3: ─────┼──► Σ_r (messages) ──► h_v
    ...           │
Relation rk: ─────┘

Final: h_v = Σ_{r∈R_in(v)} Σ_{u∈N_r(v)} α_uv^r · W_r·ñ(u)
```

## Figure X+2: Masking Strategy

### Semantic-level Edge Masking (Topology Preserved)

```
Before Masking:
    (u) ──[e, e(e)=[0.1,0.2,...]]──► (v)
         Graph structure + Edge features

After Masking (20%):
    (u) ──[e, ẽ(e)=[0,0,...]]──► (v)
         Graph structure PRESERVED + Edge features MASKED

Compare to Topology-level Masking (NOT used):
    (u)  ╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳  (v)
         Graph structure CHANGED + Edge removed
```

## Table: Model Specifications (for Caption)

**Table X**: Hyperparameter settings of OAS-GAT-EM. The model uses a dual-branch encoder-decoder architecture with heterogeneous graph attention for nodes and MLP-based encoding for edges. All experiments use Adam optimizer with learning rate 1e-3 for 20 epochs.

| Component | Configuration |
|-----------|---------------|
| Node Encoder | 2-layer HeteroGAT, 4 heads (Layer 1), hidden dim 256 |
| Edge Encoder | 2-layer MLP, hidden dim 256 |
| Decoder | Type-specific linear layers |
| Masking | 30% nodes, 20% edges (semantic-level) |
| Loss | MSE, λ_e = 0.5 |
| Training | Adam, lr=1e-3, epochs=20, dropout=0.3 |

## Caption for Main Architecture Figure

**Figure X**: Architecture of the Ontology-Aware Self-supervised Graph Attention Embedding Module (OAS-GAT-EM). The model employs a dual-branch encoder-decoder framework: (i) the **node branch** uses a two-layer heterogeneous graph attention network (HeteroGAT) to process masked node features, explicitly incorporating edge features into attention computation; (ii) the **edge branch** uses a two-layer MLP to encode edge hidden embeddings by fusing node hidden representations with masked edge static features. Both branches are jointly optimized via masked reconstruction losses ($L_n$ and $L_e$) computed only on masked entities. The final outputs are structure-aware hidden embeddings for both nodes ($h(v) \in \mathbb{R}^{256}$) and edges ($h(e) \in \mathbb{R}^{256}$), which jointly encode semantic content, ontological types, and relational context.

## Key Visual Elements for Paper Figure

1. **Use different colors**:
   - Blue: Input layer
   - Green: Encoder module
   - Orange: Decoder module
   - Red: Loss module
   - Purple: Output embeddings

2. **Highlight key innovations**:
   - ⭐ Dual-branch architecture
   - ⭐ Edge features in attention
   - ⭐ Semantic-level edge masking
   - ⭐ Type-specific parameters

3. **Dimension annotations**:
   - Clearly mark tensor dimensions at each step
   - Show dimension transformations

4. **Flow indicators**:
   - Use solid arrows for forward pass
   - Use dashed arrows for dependencies
   - Use thick arrows for main data flow

## Alternative Compact Version (for space-constrained papers)

```
Input: G_OSEG with masked features (30% nodes, 20% edges)
   │
   ├─► Node Branch: HeteroGAT (2 layers) → z(v) ∈ ℝ^256
   │      • Multi-head attention with edge features
   │      • Multi-relation aggregation
   │
   └─► Edge Branch: MLP (2 layers) → e_h(e) ∈ ℝ^256
          • Fuses [z(u), z(v), ẽ(e), w(e)]
   │
   ├─► Decoders: Linear reconstruction
   │      • n̂(v) = D_τ·z(v) ∈ ℝ^768
   │      • ê(e) = D_r·e_h(e) ∈ ℝ^768
   │
   └─► Loss: L = L_n + λ_e·L_e (masked only)
   
Output: Structure-aware embeddings h(v), h(e)
```




