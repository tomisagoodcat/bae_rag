# 论文扩展：OAS-GAT-EM模块的完整描述

Building upon the OSEG defined in Section X, we further introduce a graph representation learning module to derive structured hidden embeddings that jointly encode semantic roles, ontological constraints, and relational context.

Unlike representations based solely on textual similarity, the learned embeddings explicitly incorporate both local graph topology and typed relational semantics, enabling downstream inference, semantic retrieval, and Graph-RAG re-ranking to exploit higher-order structural dependencies.

Formally, OSEG is modeled as a heterogeneous graph $G_{\text{OSEG}} = (V, E)$, where each node $v \in V$ is associated with a static feature vector $\mathbf{n}(v) \in \mathbb{R}^{d_n}$ (typically $d_n = 768$ from pre-trained text embeddings), and each edge $e = (u, v) \in E$ is associated with a static feature vector $\mathbf{e}(e) \in \mathbb{R}^{d_e}$ (typically $d_e = 768$ from relation semantic embeddings) and an optional weight $w(e) \in [0,1]$ (e.g., confidence scores from LLM extraction). Each node has a semantic type $\tau(v) \in \mathcal{T}_V$ (e.g., `mp_ClaimMaster`, `mp_StatementMaster`), and each edge has a relation type $r(e) \in \mathcal{T}_E$ (e.g., `MASTER_mp_supports`, `MASTER_mp_challenges`).

To learn unified representations over OSEG, we propose an **Ontology-Aware Self-supervised Graph Attention Embedding Module (OAS-GAT-EM)**. As illustrated in Fig. X, the model adopts a **dual-branch encoder-decoder architecture** jointly optimized under a multi-task objective:
(i) a **node branch** that employs a heterogeneous graph attention encoder to reconstruct masked node attributes; and
(ii) an **edge branch** that uses an MLP-based encoder to reconstruct masked edge attributes.

## Masked Self-Supervised Learning

During training, we apply random masking to both node and edge features to enable self-supervised learning without manual annotation. Specifically, for each node type $\tau \in \mathcal{T}_V$, we randomly mask $30\%$ of nodes by setting their feature vectors to zero:

$\tilde{\mathbf{n}}(v) = \begin{cases}
\mathbf{0} & \text{if } \mathbf{m}_n(v) = 1 \\
\mathbf{n}(v) & \text{if } \mathbf{m}_n(v) = 0
\end{cases}$

where $\mathbf{m}_n(v) \sim \text{Bernoulli}(0.3)$ is a binary mask indicator. Similarly, for each relation type $r \in \mathcal{T}_E$, we randomly mask $20\%$ of edge attributes (semantic-level masking that preserves graph topology):

$\tilde{\mathbf{e}}(e) = \begin{cases}
\mathbf{0} & \text{if } \mathbf{m}_e(e) = 1 \\
\mathbf{e}(e) & \text{if } \mathbf{m}_e(e) = 0
\end{cases}$

where $\mathbf{m}_e(e) \sim \text{Bernoulli}(0.2)$. Note that edge masking only affects edge feature vectors $\mathbf{e}(e)$ and does not modify the graph structure (i.e., `edge_index` remains unchanged), enabling the model to learn relation semantic reconstruction rather than link prediction.

## Node Encoder: Heterogeneous Graph Attention Network

The node encoder employs a two-layer heterogeneous graph attention network (HeteroGAT) that explicitly models different semantic roles and relation types through multi-head attention mechanisms.

### First Layer: Multi-Head Heterogeneous Attention

For each relation type $r = (\tau_s, r, \tau_t)$ and each attention head $k \in \{1, \ldots, H\}$ (where $H = 4$), the attention coefficient between source node $u$ (type $\tau_s$) and target node $v$ (type $\tau_t$) is computed as:

$\alpha_{uv}^{(r,1,k)} = \frac{\exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(1,k)\top} [\mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u) \| \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(v) \| \mathbf{U}_r^{(1,k)} \tilde{\mathbf{e}}((u,v))]\right)\right)}{\sum_{u' \in \mathcal{N}_r(v)} \exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(1,k)\top} [\mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u') \| \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(v) \| \mathbf{U}_r^{(1,k)} \tilde{\mathbf{e}}((u',v))]\right)\right)}$

where $\mathcal{N}_r(v) = \{u \in V : (u, v) \in E, \tau(u) = \tau_s, r((u,v)) = r\}$ denotes the set of neighbors of $v$ connected via relation type $r$, $\mathbf{W}_r^{(1,k)} \in \mathbb{R}^{d_h \times d_n}$ and $\mathbf{U}_r^{(1,k)} \in \mathbb{R}^{d_h \times d_e}$ are learnable transformation matrices, $\mathbf{a}_r^{(1,k)} \in \mathbb{R}^{3d_h}$ is the attention parameter vector, and $\|$ denotes vector concatenation. The attention mechanism explicitly incorporates edge features $\tilde{\mathbf{e}}((u,v))$ into the computation, enabling the model to weight neighbor contributions based on both node semantics and relation semantics.

The aggregated message from head $k$ is:

$\mathbf{h}_v^{(r,1,k)} = \sum_{u \in \mathcal{N}_r(v)} \alpha_{uv}^{(r,1,k)} \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u)$

Multi-head outputs are concatenated:

$\mathbf{h}_v^{(r,1)} = \|_{k=1}^{H} \mathbf{h}_v^{(r,1,k)} \in \mathbb{R}^{H \cdot d_h}$

where $d_h = 256$, resulting in $\mathbf{h}_v^{(r,1)} \in \mathbb{R}^{1024}$.

### Multi-Relation Aggregation

For each target node $v$, messages from all incoming relation types are aggregated:

$\mathbf{h}_v^{(1)} = \sum_{r \in \mathcal{R}_{\text{in}}(v)} \mathbf{h}_v^{(r,1)}$

where $\mathcal{R}_{\text{in}}(v) = \{r : \exists u, (u,v) \in E, r((u,v)) = r\}$ denotes the set of relation types pointing to $v$. This aggregation allows the model to capture diverse semantic relationships simultaneously.

After applying ReLU activation and dropout ($p = 0.3$):

$\mathbf{h}_v^{(1)} = \text{Dropout}(\text{ReLU}(\mathbf{h}_v^{(1)}), p=0.3)$

### Second Layer: Single-Head Attention with Dimension Compression

The second layer uses single-head attention ($H=1$) to compress the representation:

$\alpha_{uv}^{(r,2)} = \frac{\exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(2)\top} [\mathbf{W}_r^{(2)} \mathbf{h}_u^{(1)} \| \mathbf{W}_r^{(2)} \mathbf{h}_v^{(1)} \| \mathbf{U}_r^{(2)} \tilde{\mathbf{e}}((u,v))]\right)\right)}{\sum_{u' \in \mathcal{N}_r(v)} \exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(2)\top} [\mathbf{W}_r^{(2)} \mathbf{h}_{u'}^{(1)} \| \mathbf{W}_r^{(2)} \mathbf{h}_v^{(1)} \| \mathbf{U}_r^{(2)} \tilde{\mathbf{e}}((u',v))]\right)\right)}$

$\mathbf{h}_v^{(r,2)} = \sum_{u \in \mathcal{N}_r(v)} \alpha_{uv}^{(r,2)} \mathbf{W}_r^{(2)} \mathbf{h}_u^{(1)}$

$\mathbf{h}_v^{(2)} = \sum_{r \in \mathcal{R}_{\text{in}}(v)} \mathbf{h}_v^{(r,2)}$

The final node hidden embedding is:

$\mathbf{z}(v) = \mathbf{h}_v^{(2)} \in \mathbb{R}^{d_z}$

where $d_z = 256$ (`node_out_dim`).

## Edge Encoder: MLP-based Feature Fusion

Unlike the node encoder that uses graph neural networks, the edge encoder employs a multi-layer perceptron (MLP) to construct edge hidden embeddings by fusing node hidden representations with edge static features. This design choice enables the model to learn relation semantics that are contextually aware of the connected nodes' structural positions.

For each edge $e = (u, v)$, the edge encoder first concatenates the hidden embeddings of the source and target nodes, the masked edge static feature, and optionally the edge weight:

$\mathbf{f}_e = [\mathbf{z}(u) \| \mathbf{z}(v) \| \tilde{\mathbf{e}}(e) \| w(e)] \in \mathbb{R}^{2d_z + d_e + 1}$

The concatenated features are then processed through a two-layer MLP:

$\mathbf{e}_h^{(1)} = \text{ReLU}(\mathbf{W}_e^{(1)} \mathbf{f}_e + \mathbf{b}_e^{(1)})$

$\mathbf{e}_h(e) = \mathbf{W}_e^{(2)} \text{Dropout}(\mathbf{e}_h^{(1)}, p=0.3) + \mathbf{b}_e^{(2)} \in \mathbb{R}^{d_{e_h}}$

where $d_{e_h} = 256$ (`edge_hidden_dim`). The edge encoder explicitly depends on the node hidden embeddings $\mathbf{z}(u)$ and $\mathbf{z}(v)$, which provide rich structural context learned through the graph attention mechanism, enabling the edge representation to capture both relation semantics and structural dependencies.

## Decoder: Linear Reconstruction

The decoder components map the hidden embeddings back to the original feature space for reconstruction.

### Node Decoder

For each node type $\tau \in \mathcal{T}_V$, a type-specific linear decoder reconstructs the original node features:

$\hat{\mathbf{n}}(v) = \mathbf{D}_\tau^{(n)} \mathbf{z}(v) + \mathbf{b}_\tau^{(n)} \in \mathbb{R}^{d_n}$

where $\mathbf{D}_\tau^{(n)} \in \mathbb{R}^{d_n \times d_z}$ and $\mathbf{b}_\tau^{(n)} \in \mathbb{R}^{d_n}$ are learnable parameters.

### Edge Decoder

For each relation type $r \in \mathcal{T}_E$, a type-specific linear decoder reconstructs the original edge features:

$\hat{\mathbf{e}}(e) = \mathbf{D}_r^{(e)} \mathbf{e}_h(e) + \mathbf{b}_r^{(e)} \in \mathbb{R}^{d_e}$

where $\mathbf{D}_r^{(e)} \in \mathbb{R}^{d_e \times d_{e_h}}$ and $\mathbf{b}_r^{(e)} \in \mathbb{R}^{d_e}$ are learnable parameters.

## Loss Function

The training objective combines node and edge reconstruction losses, computed only on masked entities to enforce the model to learn from structural context:

### Node Reconstruction Loss

$\mathcal{L}_n = \frac{1}{|\mathcal{M}_n|} \sum_{v \in \mathcal{M}_n} \|\hat{\mathbf{n}}(v) - \mathbf{n}(v)\|_2^2$

where $\mathcal{M}_n = \{v \in V : \mathbf{m}_n(v) = 1\}$ is the set of masked nodes.

### Edge Reconstruction Loss

$\mathcal{L}_e = \frac{1}{|\mathcal{M}_e|} \sum_{e \in \mathcal{M}_e} \|\hat{\mathbf{e}}(e) - \mathbf{e}(e)\|_2^2$

where $\mathcal{M}_e = \{e \in E : \mathbf{m}_e(e) = 1\}$ is the set of masked edges.

### Total Loss

The total loss is a weighted combination:

$\mathcal{L}_{\text{total}} = \mathcal{L}_n + \lambda_e \mathcal{L}_e$

where $\lambda_e = 0.5$ is the edge loss weight. The model parameters are optimized via backpropagation:

$\theta^* = \arg\min_{\theta} \mathcal{L}_{\text{total}}(\theta)$

where $\theta$ includes all encoder and decoder parameters.

## Final Representations

After training, each node $v$ and edge $e$ are mapped to structure-aware hidden representations:

- **Node representation**: $\mathbf{h}(v) = \mathbf{z}(v) \in \mathbb{R}^{d_z}$ ($d_z = 256$)
- **Edge representation**: $\mathbf{h}(e) = \mathbf{e}_h(e) \in \mathbb{R}^{d_{e_h}}$ ($d_{e_h} = 256$)

These representations jointly encode:

1. **Semantic content**: Preserved from original text embeddings through reconstruction
2. **Ontological position**: Explicitly modeled through node/edge type-specific parameters
3. **Structural context**: Captured via multi-hop neighborhood aggregation and attention-weighted message passing
4. **Relational semantics**: Modeled through heterogeneous relation types and edge feature integration

The learned embeddings enable downstream tasks such as semantic retrieval, argumentative relation prediction, evidence chain quality assessment, and Graph-RAG re-ranking to exploit both textual semantics and higher-order structural dependencies within the argumentative evidence graph.
