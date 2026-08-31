# 数学公式化总结：实验一+实验二对应关系

## 文件说明

1. **mathematical_formulation.md**: 完整的数学公式化表述，包括所有技术细节
2. **paper_extension.md**: 扩展的论文段落，可直接用于论文写作

## 关键对应关系

### 1. Mask机制（对应代码中的mask函数）

| 代码模块 | 数学表示 | 说明 |
|---------|---------|------|
| `mask_hetero_x` | $\tilde{\mathbf{n}}(v)$, $\mathbf{m}_n(v) \sim \text{Bernoulli}(0.3)$ | Node mask，30%比例 |
| `mask_edge_attr_dict` | $\tilde{\mathbf{e}}(e)$, $\mathbf{m}_e(e) \sim \text{Bernoulli}(0.2)$ | Edge mask，20%比例，语义级 |

### 2. Encoder部分

#### Node Encoder (实验一核心)

| 代码模块 | 数学表示 | 说明 |
|---------|---------|------|
| `HeteroEdgeGATEncoder.conv1` | $\alpha_{uv}^{(r,1,k)}$, $\mathbf{h}_v^{(r,1,k)}$ | 第一层多头注意力 |
| `HeteroConv` (聚合) | $\mathbf{h}_v^{(1)} = \sum_{r \in \mathcal{R}_{\text{in}}(v)} \mathbf{h}_v^{(r,1)}$ | 多关系聚合 |
| `HeteroEdgeGATEncoder.conv2` | $\alpha_{uv}^{(r,2)}$, $\mathbf{z}(v)$ | 第二层单头注意力，输出hidden embedding |

**关键点**：
- 注意力机制融合了边特征：$[\mathbf{W}_r \tilde{\mathbf{n}}(u) \| \mathbf{W}_r \tilde{\mathbf{n}}(v) \| \mathbf{U}_r \tilde{\mathbf{e}}((u,v))]$
- 这是EdgeGAT的核心，区别于标准GAT

#### Edge Encoder (实验二新增)

| 代码模块 | 数学表示 | 说明 |
|---------|---------|------|
| `EdgeHiddenBuilder.forward` | $\mathbf{f}_e = [\mathbf{z}(u) \| \mathbf{z}(v) \| \tilde{\mathbf{e}}(e) \| w(e)]$ | 特征拼接 |
| `EdgeHiddenBuilder.mlp` | $\mathbf{e}_h(e) = \text{MLP}(\mathbf{f}_e)$ | MLP编码，**非GNN** |

**关键点**：
- Edge encoder **不通过GNN**，而是MLP
- 依赖节点hidden embedding $\mathbf{z}(u)$, $\mathbf{z}(v)$ 提供结构上下文

### 3. Decoder部分

| 代码模块 | 数学表示 | 说明 |
|---------|---------|------|
| `NodeDecoders` | $\hat{\mathbf{n}}(v) = \mathbf{D}_\tau^{(n)} \mathbf{z}(v) + \mathbf{b}_\tau^{(n)}$ | 线性解码器，按节点类型 |
| `EdgeDecoders` | $\hat{\mathbf{e}}(e) = \mathbf{D}_r^{(e)} \mathbf{e}_h(e) + \mathbf{b}_r^{(e)}$ | 线性解码器，按关系类型 |

**关键点**：
- Decoder是简单的线性变换，将hidden embedding映射回原始维度
- 每个节点/边类型有独立的decoder参数

### 4. Loss函数

| 代码模块 | 数学表示 | 说明 |
|---------|---------|------|
| `masked_recon_loss` | $\mathcal{L}_n = \frac{1}{|\mathcal{M}_n|} \sum_{v \in \mathcal{M}_n} \|\hat{\mathbf{n}}(v) - \mathbf{n}(v)\|_2^2$ | 节点重建损失，仅masked节点 |
| `masked_edge_recon_loss` | $\mathcal{L}_e = \frac{1}{|\mathcal{M}_e|} \sum_{e \in \mathcal{M}_e} \|\hat{\mathbf{e}}(e) - \mathbf{e}(e)\|_2^2$ | 边重建损失，仅masked边 |
| `total_loss` | $\mathcal{L}_{\text{total}} = \mathcal{L}_n + \lambda_e \mathcal{L}_e$ | 总损失，$\lambda_e = 0.5$ |

**关键点**：
- Loss只计算被mask的部分（类似BERT的MLM）
- 多任务学习：同时优化节点和边重建

## 数学公式的关键特性

### 1. 体现Node Mask和Edge Mask
- Node mask: $\tilde{\mathbf{n}}(v)$ 在encoder输入中使用
- Edge mask: $\tilde{\mathbf{e}}(e)$ 在attention计算和edge encoder中使用
- Loss中只计算masked部分：$\mathcal{M}_n$, $\mathcal{M}_e$

### 2. 体现GAT如何学习Attention
- **注意力系数计算**：$\alpha_{uv}^{(r,1,k)}$ 通过LeakyReLU和softmax学习
- **融合边特征**：注意力计算中包含 $\mathbf{U}_r \tilde{\mathbf{e}}((u,v))$
- **多头机制**：$k \in \{1, \ldots, H\}$，$H=4$
- **消息传递**：$\mathbf{h}_v^{(r,1,k)} = \sum_{u \in \mathcal{N}_r(v)} \alpha_{uv}^{(r,1,k)} \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u)$

### 3. Decoder原理
- **线性变换**：简单的矩阵乘法，无非线性激活
- **类型特定**：每个节点类型/关系类型有独立参数
- **维度映射**：$d_z \to d_n$ (节点), $d_{e_h} \to d_e$ (边)

### 4. Loss计算
- **MSE损失**：$\|\hat{\mathbf{n}}(v) - \mathbf{n}(v)\|_2^2$
- **仅masked部分**：$\sum_{v \in \mathcal{M}_n}$ 而非 $\sum_{v \in V}$
- **多任务加权**：$\lambda_e = 0.5$ 平衡节点和边损失

## 维度说明

| 变量 | 维度 | 代码对应 |
|------|------|---------|
| $\mathbf{n}(v)$ | $\mathbb{R}^{768}$ | `in_dim=768` |
| $\mathbf{e}(e)$ | $\mathbb{R}^{768}$ | `edge_attr_dim=768` |
| $\mathbf{z}(v)$ | $\mathbb{R}^{256}$ | `node_out_dim=256` |
| $\mathbf{e}_h(e)$ | $\mathbb{R}^{256}$ | `edge_hidden_dim=256` |
| $\mathbf{h}_v^{(r,1)}$ | $\mathbb{R}^{1024}$ | `hidden_dim * heads = 256 * 4` |

## 论文使用建议

1. **Introduction/Method部分**：使用 `paper_extension.md` 中的扩展段落
2. **Technical Details部分**：使用 `mathematical_formulation.md` 中的完整公式
3. **Figure Caption**：可引用公式编号说明架构

## 注意事项

1. **Edge Mask是语义级**：只mask `edge_attr`，不删除边（`edge_index`保持不变）
2. **Edge Encoder非GNN**：使用MLP而非图消息传递
3. **异质图建模**：每个关系类型 $r$ 有独立的参数集合
4. **自监督学习**：无需人工标注，通过masked reconstruction学习

