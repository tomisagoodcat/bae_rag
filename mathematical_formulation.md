# OAS-GAT-EM: 数学公式化表述

## 1. 问题定义与输入

给定异质图 $G_{\text{OSEG}} = (V, E)$，其中：

- 每个节点 $v \in V$ 具有类型 $\tau(v) \in \mathcal{T}_V$（如 `mp_ClaimMaster`, `mp_StatementMaster`）
- 每个边 $e = (u, v) \in E$ 具有关系类型 $r(e) \in \mathcal{T}_E$（如 `MASTER_mp_supports`, `MASTER_mp_challenges`）
- 节点静态特征：$\mathbf{n}(v) \in \mathbb{R}^{d_n}$（$d_n = 768$，来自文本embedding）
- 边静态特征：$\mathbf{e}(e) \in \mathbb{R}^{d_e}$（$d_e = 768$，来自关系语义embedding）
- 边权重：$w(e) \in [0,1]$（如 `master_score`）

## 2. Mask机制

### 2.1 Node Mask

对每个节点类型 $\tau \in \mathcal{T}_V$，随机选择比例为 $\rho_n = 0.3$ 的节点进行mask：

$\mathbf{m}_n(v) \sim \text{Bernoulli}(\rho_n)$

被mask的节点特征置零：
$\tilde{\mathbf{n}}(v) = \begin{cases}
\mathbf{0} & \text{if } \mathbf{m}_n(v) = 1 \\
\mathbf{n}(v) & \text{if } \mathbf{m}_n(v) = 0
\end{cases}$

### 2.2 Edge Mask

对每个关系类型 $r \in \mathcal{T}_E$，随机选择比例为 $\rho_e = 0.2$ 的边进行mask：

$\mathbf{m}_e(e) \sim \text{Bernoulli}(\rho_e)$

被mask的边特征置零（**不修改图结构**）：
$\tilde{\mathbf{e}}(e) = \begin{cases}
\mathbf{0} & \text{if } \mathbf{m}_e(e) = 1 \\
\mathbf{e}(e) & \text{if } \mathbf{m}_e(e) = 0
\end{cases}$

注意：边mask是**语义级**的，即只mask `edge_attr`，不删除 `edge_index`。

## 3. Encoder部分

### 3.1 Node Encoder: Heterogeneous Graph Attention Network

#### 3.1.1 第一层：多头异质图注意力

对每个关系类型 $r = (\tau_s, r, \tau_t)$，定义第一层GAT：

对于目标节点 $v$（类型为 $\tau_t$），其邻居集合为：
$\mathcal{N}_r(v) = \{u \in V : (u, v) \in E, \tau(u) = \tau_s, r((u,v)) = r\}$

**注意力系数计算**（融合边特征）：
$\alpha_{uv}^{(r,1,k)} = \frac{\exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(1,k)\top} [\mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u) \| \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(v) \| \mathbf{U}_r^{(1,k)} \tilde{\mathbf{e}}((u,v))]\right)\right)}{\sum_{u' \in \mathcal{N}_r(v)} \exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(1,k)\top} [\mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u') \| \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(v) \| \mathbf{U}_r^{(1,k)} \tilde{\mathbf{e}}((u',v))]\right)\right)}$

其中：

- $k \in \{1, \ldots, H\}$ 是注意力头索引（$H = 4$）
- $\mathbf{W}_r^{(1,k)} \in \mathbb{R}^{d_h \times d_n}$ 是节点特征变换矩阵
- $\mathbf{U}_r^{(1,k)} \in \mathbb{R}^{d_h \times d_e}$ 是边特征变换矩阵
- $\mathbf{a}_r^{(1,k)} \in \mathbb{R}^{3d_h}$ 是注意力参数向量
- $\|$ 表示向量拼接

**消息聚合**（单头）：
$\mathbf{h}_v^{(r,1,k)} = \sum_{u \in \mathcal{N}_r(v)} \alpha_{uv}^{(r,1,k)} \mathbf{W}_r^{(1,k)} \tilde{\mathbf{n}}(u)$

**多头拼接**：
$\mathbf{h}_v^{(r,1)} = \|_{k=1}^{H} \mathbf{h}_v^{(r,1,k)} \in \mathbb{R}^{H \cdot d_h}$

其中 $d_h = 256$，因此 $\mathbf{h}_v^{(r,1)} \in \mathbb{R}^{1024}$。

#### 3.1.2 多关系聚合

对同一目标节点类型 $\tau_t$，所有指向它的关系类型进行聚合：

$\mathbf{h}_v^{(1)} = \text{AGGREGATE}\left(\{\mathbf{h}_v^{(r,1)} : r \in \mathcal{R}_{\text{in}}(v)\}\right)$

其中 $\mathcal{R}_{\text{in}}(v) = \{r : \exists u, (u,v) \in E, r((u,v)) = r\}$，聚合方式为 `sum`：

$\mathbf{h}_v^{(1)} = \sum_{r \in \mathcal{R}_{\text{in}}(v)} \mathbf{h}_v^{(r,1)}$

**激活与正则化**：
$\mathbf{h}_v^{(1)} = \text{Dropout}(\text{ReLU}(\mathbf{h}_v^{(1)}), p=0.3)$

#### 3.1.3 第二层：单头异质图注意力

第二层使用单头注意力（$H=1$），压缩维度：

$\alpha_{uv}^{(r,2)} = \frac{\exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(2)\top} [\mathbf{W}_r^{(2)} \mathbf{h}_u^{(1)} \| \mathbf{W}_r^{(2)} \mathbf{h}_v^{(1)} \| \mathbf{U}_r^{(2)} \tilde{\mathbf{e}}((u,v))]\right)\right)}{\sum_{u' \in \mathcal{N}_r(v)} \exp\left(\text{LeakyReLU}\left(\mathbf{a}_r^{(2)\top} [\mathbf{W}_r^{(2)} \mathbf{h}_{u'}^{(1)} \| \mathbf{W}_r^{(2)} \mathbf{h}_v^{(1)} \| \mathbf{U}_r^{(2)} \tilde{\mathbf{e}}((u',v))]\right)\right)}$

$\mathbf{h}_v^{(r,2)} = \sum_{u \in \mathcal{N}_r(v)} \alpha_{uv}^{(r,2)} \mathbf{W}_r^{(2)} \mathbf{h}_u^{(1)}$

$\mathbf{h}_v^{(2)} = \sum_{r \in \mathcal{R}_{\text{in}}(v)} \mathbf{h}_v^{(r,2)}$

**最终节点hidden embedding**：
$\mathbf{z}(v) = \mathbf{h}_v^{(2)} \in \mathbb{R}^{d_z}$

其中 $d_z = 256$（`node_out_dim`）。

### 3.2 Edge Encoder: MLP-based Feature Fusion

对每条边 $e = (u, v)$，构建边的hidden embedding：

**特征拼接**：
$\mathbf{f}_e = [\mathbf{z}(u) \| \mathbf{z}(v) \| \tilde{\mathbf{e}}(e) \| w(e)] \in \mathbb{R}^{2d_z + d_e + 1}$

**MLP编码**：
$\mathbf{e}_h^{(1)} = \text{ReLU}(\mathbf{W}_e^{(1)} \mathbf{f}_e + \mathbf{b}_e^{(1)})$

$\mathbf{e}_h^{(2)} = \text{Dropout}(\mathbf{e}_h^{(1)}, p=0.3)$

$\mathbf{e}_h(e) = \mathbf{W}_e^{(2)} \mathbf{e}_h^{(2)} + \mathbf{b}_e^{(2)} \in \mathbb{R}^{d_{e_h}}$

其中 $d_{e_h} = 256$（`edge_hidden_dim`）。

**关键点**：Edge encoder **不通过GNN**，而是通过MLP从拼接特征中学习，依赖节点hidden embedding $\mathbf{z}(u)$ 和 $\mathbf{z}(v)$ 提供结构上下文。

## 4. Decoder部分

### 4.1 Node Decoder

对每个节点类型 $\tau \in \mathcal{T}_V$，使用线性解码器：

$\hat{\mathbf{n}}(v) = \mathbf{D}_\tau^{(n)} \mathbf{z}(v) + \mathbf{b}_\tau^{(n)} \in \mathbb{R}^{d_n}$

其中 $\mathbf{D}_\tau^{(n)} \in \mathbb{R}^{d_n \times d_z}$ 是节点类型特定的解码矩阵。

### 4.2 Edge Decoder

对每个关系类型 $r \in \mathcal{T}_E$，使用线性解码器：

$\hat{\mathbf{e}}(e) = \mathbf{D}_r^{(e)} \mathbf{e}_h(e) + \mathbf{b}_r^{(e)} \in \mathbb{R}^{d_e}$

其中 $\mathbf{D}_r^{(e)} \in \mathbb{R}^{d_e \times d_{e_h}}$ 是关系类型特定的解码矩阵。

## 5. Loss函数

### 5.1 Node Reconstruction Loss

仅对被mask的节点计算重建误差：

$\mathcal{L}_n = \frac{1}{|\mathcal{M}_n|} \sum_{v \in \mathcal{M}_n} \|\hat{\mathbf{n}}(v) - \mathbf{n}(v)\|_2^2$

其中 $\mathcal{M}_n = \{v \in V : \mathbf{m}_n(v) = 1\}$ 是被mask的节点集合。

### 5.2 Edge Reconstruction Loss

仅对被mask的边计算重建误差：

$\mathcal{L}_e = \frac{1}{|\mathcal{M}_e|} \sum_{e \in \mathcal{M}_e} \|\hat{\mathbf{e}}(e) - \mathbf{e}(e)\|_2^2$

其中 $\mathcal{M}_e = \{e \in E : \mathbf{m}_e(e) = 1\}$ 是被mask的边集合。

### 5.3 总损失

$\mathcal{L}_{\text{total}} = \mathcal{L}_n + \lambda_e \mathcal{L}_e$

其中 $\lambda_e = 0.5$ 是边损失的权重系数。

## 6. 训练目标

优化目标：
$\theta^* = \arg\min_{\theta} \mathcal{L}_{\text{total}}(\theta)$

其中 $\theta$ 包括：

- Node encoder参数：$\{\mathbf{W}_r^{(l,k)}, \mathbf{U}_r^{(l,k)}, \mathbf{a}_r^{(l,k)} : r \in \mathcal{T}_E, l \in \{1,2\}, k \in \{1,\ldots,H\}\}$
- Edge encoder参数：$\{\mathbf{W}_e^{(1)}, \mathbf{b}_e^{(1)}, \mathbf{W}_e^{(2)}, \mathbf{b}_e^{(2)}\}$
- Node decoder参数：$\{\mathbf{D}_\tau^{(n)}, \mathbf{b}_\tau^{(n)} : \tau \in \mathcal{T}_V\}$
- Edge decoder参数：$\{\mathbf{D}_r^{(e)}, \mathbf{b}_r^{(e)} : r \in \mathcal{T}_E\}$

## 7. 最终输出

训练完成后，每个节点和边映射到结构感知的hidden表示：

- **节点表示**：$\mathbf{h}(v) = \mathbf{z}(v) \in \mathbb{R}^{d_z}$（$d_z = 256$）
- **边表示**：$\mathbf{h}(e) = \mathbf{e}_h(e) \in \mathbb{R}^{d_{e_h}}$（$d_{e_h} = 256$）

这些表示联合编码了：

1. **语义内容**：来自原始文本embedding
2. **本体位置**：通过节点/边类型建模
3. **结构上下文**：通过图消息传递和注意力机制捕获
4. **关系语义**：通过异质关系类型和边特征建模
