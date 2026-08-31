# OAS-GAT-EM 架构图文件说明

已创建多个版本的架构图，适用于不同场景。请根据需要选择使用。

## 文件列表与推荐使用场景

### 1. `model_architecture_diagram.md` ⭐ 推荐用于技术文档

**内容**：
- 最详细的文本ASCII架构图
- 包含所有技术细节和维度标注
- 三张独立的详细图：整体架构、Node Encoder、Edge Encoder
- 完整的参数配置表

**适用场景**：
- 技术报告和详细文档
- 代码库的README
- 技术交流和讨论
- 内部培训材料

**优点**：
- 无需特殊工具即可查看
- 包含完整的技术细节
- 易于在文本编辑器中修改

### 2. `paper_figure_architecture.md` ⭐⭐ 强烈推荐用于论文

**内容**：
- 简化的论文标准架构图
- 清晰的模块划分和数据流
- 详细的图注（Caption）
- 包含注意力机制详图和Masking策略对比图
- 紧凑版架构（适合空间受限的论文）

**适用场景**：
- 学术论文的Figure
- 会议演讲Slides
- 学位论文
- 期刊投稿

**优点**：
- 符合科学论文的视觉规范
- 包含完整的Caption和说明
- 提供多个视角的图示
- 包含使用颜色的建议

**推荐使用**：
- **主图（Figure X）**: 简化版整体架构
- **技术细节（Figure X+1）**: 注意力机制详图
- **对比图（Figure X+2）**: Masking策略说明

### 3. `architecture_mermaid.md` ⭐⭐⭐ 推荐用于可视化渲染

**内容**：
- 7个Mermaid格式的流程图
- 可直接在GitHub/GitLab等平台渲染
- 包含数据流和维度变化图
- 训练流程序列图

**适用场景**：
- GitHub/GitLab项目README
- 在线文档（支持Mermaid的平台）
- 需要可交互查看的场景
- 需要导出为SVG/PNG的场景

**优点**：
- 自动渲染，无需手动绘图
- 易于维护和更新
- 可导出为高质量图片
- 支持交互式查看

**推荐图表**：
- **图1**: 整体架构流程图（最常用）
- **图2-3**: Encoder详细结构（技术细节）
- **图4**: 注意力机制（核心创新）
- **图7**: 数据流与维度变化（易于理解）

### 4. `formulation_summary.md`

**内容**：
- 代码与数学公式的对应关系
- 关键设计特性说明
- 维度说明表

**适用场景**：
- 代码实现参考
- 数学公式与代码的对照
- 论文的补充材料

## 使用建议

### 场景1: 撰写学术论文

推荐组合：
1. **主图**: `paper_figure_architecture.md` 中的简化版整体架构
2. **详图**: 注意力机制详图（Figure X+1(a)）
3. **对比图**: Masking策略对比（Figure X+2）
4. **Caption**: 直接使用提供的Caption模板

### 场景2: 项目文档（GitHub README）

推荐组合：
1. **架构图**: `architecture_mermaid.md` 中的图1（会自动渲染）
2. **详细说明**: 链接到 `model_architecture_diagram.md`
3. **参数配置**: 使用 `model_architecture_diagram.md` 中的表1

### 场景3: 技术报告

推荐组合：
1. **整体架构**: `model_architecture_diagram.md` 中的完整ASCII图
2. **公式说明**: 结合 `formulation_summary.md`
3. **代码对应**: 使用 `formulation_summary.md` 中的对应表

### 场景4: 演讲Slides

推荐组合：
1. **导出Mermaid图**: 从 `architecture_mermaid.md` 导出PNG
2. **简化流程**: 使用 `paper_figure_architecture.md` 中的紧凑版
3. **关键点**: 使用"Key Visual Elements"中的高亮建议

## 如何导出高质量论文图片

### 方法1: 使用Mermaid在线编辑器（推荐）

1. 访问 https://mermaid.live
2. 复制 `architecture_mermaid.md` 中的Mermaid代码
3. 调整主题和样式
4. 导出为PNG（高分辨率）或SVG（矢量图）

### 方法2: 使用Draw.io

1. 打开 https://app.diagrams.net
2. File → Import from → Text
3. 粘贴Mermaid代码或根据ASCII图手动绘制
4. 导出为PNG/PDF（推荐用于论文）

### 方法3: 使用专业绘图工具

根据提供的架构图，在以下工具中重新绘制：
- **Adobe Illustrator**: 矢量图，最高质量
- **Microsoft Visio**: 适合技术图表
- **Inkscape**: 免费的矢量图工具
- **PowerPoint**: 简单快捷，适合Slides

### 推荐规格（论文投稿）

- **格式**: PDF或EPS（矢量）优先，PNG次之
- **分辨率**: 至少300 DPI（如果使用位图）
- **尺寸**: 单栏图宽度约8.5cm，双栏图宽度约17.5cm
- **字体**: 10-12pt，Sans Serif（如Arial或Helvetica）
- **配色**: 建议使用色盲友好的配色方案

## 配色建议（适用于所有图）

基于论文标准的配色方案：

```
Input Layer:    Light Blue   (#e3f2fd / RGB: 227, 242, 253)
Encoder:        Light Green  (#e8f5e9 / RGB: 232, 245, 233)
Decoder:        Light Orange (#fff3e0 / RGB: 255, 243, 224)
Loss:           Light Red    (#ffebee / RGB: 255, 235, 238)
Output:         Light Purple (#f3e5f5 / RGB: 243, 229, 245)
```

边框颜色使用对应的深色版本。

## 修改建议

如需根据具体论文要求修改图表：

### 简化版本（空间受限）
- 使用 `paper_figure_architecture.md` 中的"紧凑版"
- 移除详细的维度标注
- 合并相似的模块

### 详细版本（技术报告）
- 使用 `model_architecture_diagram.md` 中的完整版
- 添加更多的中间步骤说明
- 包含所有的数学公式

### 强调特定部分
- 注意力机制 → 使用图4（Mermaid）或Figure X+1(a)
- Masking策略 → 使用图5（Mermaid）或Figure X+2
- 数据流 → 使用图7（Mermaid）

## 常见问题

### Q1: 哪个图最适合放在论文的Method部分？
**A**: 推荐使用 `paper_figure_architecture.md` 中的简化版整体架构（Figure X）。它清晰展示了双分支结构、关键组件和数据流，同时不过于复杂。

### Q2: 如何在LaTeX中引用这些图？
**A**: 导出图片后，使用标准的figure环境：
```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{architecture.pdf}
  \caption{Architecture of OAS-GAT-EM...}
  \label{fig:architecture}
\end{figure}
```

### Q3: Mermaid图在GitHub上不显示怎么办？
**A**: 
1. 确保文件扩展名是 `.md`
2. Mermaid代码块正确使用 ` ```mermaid `
3. GitHub有时需要刷新才能看到渲染结果
4. 可以在本地用支持Mermaid的编辑器预览

### Q4: 如何调整图的尺寸以适配论文要求？
**A**: 
1. 如果使用矢量图（SVG/PDF），直接在LaTeX中用width参数调整
2. 如果使用位图（PNG），在导出时设置合适的分辨率
3. 推荐使用矢量图，缩放不失真

## 技术支持

如需进一步定制或有问题，可以：
1. 修改对应的Markdown文件
2. 使用在线Mermaid编辑器调整
3. 参考 `formulation_summary.md` 了解技术细节

## 版权说明

这些架构图基于实验2（OAS-GAT-EM）的实现创建，适用于学术和研究用途。在论文中使用时，请确保：
1. 引用相关的理论基础（GAT、HeteroGNN等）
2. 说明这是你的实现架构
3. 如果投稿期刊要求，说明图表的创作工具




