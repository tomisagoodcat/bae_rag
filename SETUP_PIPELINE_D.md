# Pipeline D 环境设置和测试说明

## 1. 创建Conda环境

```bash
# 创建新的conda环境
conda create -n pipelineD python=3.10 -y

# 激活环境
conda activate pipelineD

# 安装依赖包
pip install torch>=1.9.0
pip install neo4j>=5.0.0
pip install neo4j-graphrag>=0.1.0
pip install numpy>=1.20.0

# 或者使用requirements文件
pip install -r requirements_pipelineD.txt
```

## 2. 代码结构说明

Pipeline D的实现分为以下步骤（在notebook中的Cell 71-76）：

- **Cell 71 (Step 3)**: 从Top-K中选取Top-M构造z_seed
- **Cell 72 (Step 4)**: 基于z_seed构造查询子图G_q
- **Cell 73 (Step 5)**: 计算结构得分s_struct
- **Cell 74 (Step 6-8)**: 抽取证据路径并计算路径语义得分s_path
- **Cell 75 (Step 9)**: Graph-aware re-ranking
- **Cell 76 (Step 10)**: LLM生成最终答案

## 3. 运行顺序

确保按照以下顺序运行notebook cells：

1. **Cell 77**: 配置常量定义（MASTER_LABEL, TOP_K, TOP_M等）
2. **Cell 69**: 执行步骤1-2，获取初始的elementIDs（uniq_hits）
3. **Cell 71-76**: 依次执行步骤3-10

## 4. 注意事项

- 确保Neo4j数据库连接正常（neo4j_driver）
- 确保LLM配置正确（llm对象）
- 确保__Master__节点有gnn_hiddenEmbdding属性
- 确保关系类型以'MASTER_'开头

## 5. 测试建议

- 首先运行单个cell，检查输出
- 如果出现错误，检查变量是否正确定义
- 逐步调试每个步骤的输出















