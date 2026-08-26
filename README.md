# KG Build Pipeline — 中文说明

BAE 知识图谱**端到端构建流水线**。将原先分散在多个 Jupyter Notebook 中的建图、子图标注、Chunk 去重、实体消融、PageRank 与 MetaPath 等步骤，整合为可重复执行的 Python 模块与统一入口。

本目录与仓库根目录下的 `output/`、原 Notebook **相互隔离**：Schema 只从 `kg_build_pipeline/schema/` 读取；论文正文仍从 `data/markdown/` 及其子目录（默认 `forTest`）读取。原 Notebook 保留作对照，不被本 Pipeline 修改。

---

## 项目结构

```text
kg_build_pipeline/
├── README.md                 # 本说明（中文）
├── config.yaml               # 路径、Neo4j、阶段开关、LLM 配置
├── run_pipeline.py           # CLI 主入口（推荐）
├── run_pipeline.bat          # Windows 双击一键运行
├── run_ui.bat                # Web UI 启动（浏览器控制台）
│
├── prompts/
│   └── custom_prompt.md      # build_kg 单层抽取 Prompt（v5 schema 对齐）
│
├── ui/                       # FastAPI + Metro 前端
│   ├── app.py
│   ├── stage_manifest.json
│   └── static/
│       ├── index.html
│       ├── metro.css
│       └── app.js
│
├── logs/                     # UI 构建日志（build_*.log）
│
├── schema/                   # 本体 Schema（Pipeline 唯一读取源）
│   ├── entity.json
│   ├── relation.json
│   ├── potential_schema.json
│   ├── subgraph_mapping.json
│   └── metapath_relations.json   # F1 MetaPath 关系模板（自 1_2_1_2 导出）
│
├── src/
│   ├── config.py             # 加载 config.yaml，支持 ${ENV_VAR}
│   ├── paths.py              # REPO_ROOT、SCHEMA_DIR 等路径常量
│   ├── schema_loader.py        # load_schema / validate_schema_dir
│   ├── neo4j_util.py           # Neo4j 驱动（无 torch 依赖，供轻量阶段使用）
│   ├── runner.py               # PipelineRunner 编排器
│   └── stages/                 # 各阶段实现（每阶段一个 run_xxx）
│       ├── document_loader.py    # Markdown 加载、语义切分（1_2_0_2 模块1）
│       ├── metadata_enhance.py   # DC 元数据、关系增强（模块2）
│       ├── build_kg.py           # Schema 约束三元组抽取（模块3）
│       ├── subgraph_annotate.py  # 子图属性标注（模块4）
│       ├── chunk_merge.py        # Chunk 去重（模块5）
│       ├── entity_merge.py       # 实体消融（1_2_1_1 最小集）
│       ├── pagerank.py           # GDS PageRank E 段（1_2_1_2）
│       ├── pagerank_config.py    # 子图 GDS 投影配置
│       └── metapath.py           # MetaPath F1/F4/F2/F3
│
├── notebooks/                # 薄入口 Notebook（调用同一套 Python 逻辑）
│   ├── 00_overview.ipynb
│   ├── 02_build_kg.ipynb
│   ├── 03_subgraph_chunk.ipynb
│   ├── 04_entity_merge.ipynb
│   ├── 05_metapath.ipynb
│   └── 99_run_all.ipynb        # 等价于 run_pipeline.py --all
│
└── docs/
    └── STAGE_NOTES.md          # 各阶段逻辑说明（摘自原 Notebook）
```

---

## 流水线阶段与顺序

默认执行顺序（可在 `config.yaml` 的 `stages` 中开关）：

| 阶段 | 说明 | 对应原 Notebook | 入口函数 |
|------|------|-----------------|----------|
| `clear_neo4j` | 清空当前库（**默认关闭**） | 1_2_0_2 | `neo4j_util.clear_neo4j` |
| `build_kg` | 按 `potential_schema` 逐条 LLM 抽取三元组 | 1_2_0_2 模块3 | `stages.build_kg.run_build_kg` |
| `subgraph_annotate` | 写入 `subgraph` / `subgraphs` | 1_2_0_2 模块4 | `stages.subgraph_annotate.run_subgraph_annotate` |
| `chunk_merge` | 同 filename 内 Chunk 去重 | 1_2_0_2 模块5 | `stages.chunk_merge.run_chunk_merge` |
| `entity_merge` | 精确匹配 + WCC Master（**默认关闭**） | 1_2_1_1 | `stages.entity_merge.run_entity_merge` |
| `pagerank` | MPU/EEM/EBM 子图 PageRank | 1_2_1_2 E 段 | `stages.pagerank.run_pagerank` |
| `metapath` | F1 low → F4 mid/层级边 → F2/F3 | 1_2_1_2 | `stages.metapath.run_metapath` |

**总编排入口**：`src/runner.py` 中的 `PipelineRunner.run()`。

---

## 如何运行

### 前置条件

1. **Neo4j** 已启动（默认 `bolt://localhost:7687`）。
2. 设置环境变量（或在父目录 `cursorParperExtarct/.env` 中配置，见 `kg_build_pipeline/.env.example`）：
   - `NEO4J_PASSWORD` — 必需
   - `DEEPSEEK_API_KEY` — `build_kg` 阶段必需
   - `QWEN_API_KEY` — MetaPath F2/F3 可选；未设置且 `metapath.skip_f2_without_qwen: true` 时会跳过 F2/F3
3. 本地 Embedding 模型路径与 `config.yaml` 中 `paths.embedding_model` 一致（默认 `C:/model/bce-embedding-base_v1`）。
4. 论文 Markdown 位于 `data/markdown/forTest/`（或修改 `paths.markdown_dir`）。

### 方式一：双击运行（Windows）

在资源管理器中双击：

```text
kg_build_pipeline/run_pipeline.bat
```

脚本会：切换到仓库根目录 → 激活 `pipelineD_env` → 执行 `run_pipeline.py --all`。

### 方式二：命令行（推荐）

在**仓库根目录**执行：

```bash
# 全流程（按 config.yaml 中 stages 开关）
python kg_build_pipeline/run_pipeline.py --config kg_build_pipeline/config.yaml --all

# 跳过实体消融
python kg_build_pipeline/run_pipeline.py --all --skip entity_merge

# 只跑指定阶段
python kg_build_pipeline/run_pipeline.py --stage build_kg,subgraph_annotate,chunk_merge

# 启动前校验 Schema
python utilities/validate_schema.py --dir kg_build_pipeline/schema
```

### 方式四：Web UI（可视化控制台）

在**仓库根目录**启动 Metro 风格浏览器界面，支持 stage 勾选、实时日志、论文进度、成功/失败弹窗提示，以及本地日志文件：

```text
# Windows 双击
kg_build_pipeline/run_ui.bat

# 或命令行
python -m kg_build_pipeline.ui.app
```

浏览器访问：**http://127.0.0.1:8765**

- 论文数目：页面加载时显示待抽取数量（受 `build_kg.max_docs` 限制）
- 构建日志：同时写入 `kg_build_pipeline/logs/build_YYYYMMDD_HHMMSS.log`
- 依赖：`pip install -r kg_build_pipeline/requirements.txt`（FastAPI + Uvicorn）

### 方式三：Jupyter Notebook

| Notebook | 用途 |
|----------|------|
| `notebooks/99_run_all.ipynb` | 调用 `run_pipeline.py --all`，与 `.bat` 等价 |
| `notebooks/02_build_kg.ipynb` | 仅建图抽取 |
| `notebooks/03_subgraph_chunk.ipynb` | 子图标注 + Chunk 去重 |
| `notebooks/04_entity_merge.ipynb` | 实体消融（可选） |
| `notebooks/05_metapath.ipynb` | PageRank + MetaPath |

Notebook 仅作入口，**业务逻辑均在 `src/stages/`**，避免重复维护。

---

## 入口函数一览

| 层级 | 文件 | 函数 / 类 | 作用 |
|------|------|-----------|------|
| CLI | `run_pipeline.py` | `main()` | 解析参数，创建 `PipelineRunner` |
| 编排 | `src/runner.py` | `PipelineRunner.run()` | 按顺序调用各阶段，输出 summary |
| 配置 | `src/config.py` | `PipelineConfig.load()` | 读取 `config.yaml` |
| Schema | `src/schema_loader.py` | `load_schema()` | 加载 entity/relation/potential |
| Neo4j | `src/neo4j_util.py` | `build_neo4j_driver()` | 创建驱动（轻量阶段不 import torch） |
| 建图 | `src/stages/build_kg.py` | `run_build_kg(cfg, driver=None)` | 异步三元组抽取主流程 |
| 子图 | `src/stages/subgraph_annotate.py` | `run_subgraph_annotate(cfg, driver)` | 子图属性写入与验收 |
| Chunk | `src/stages/chunk_merge.py` | `run_chunk_merge(driver)` | Chunk 去重 |
| 消融 | `src/stages/entity_merge.py` | `run_entity_merge(cfg, driver)` | 精确匹配 + WCC |
| PageRank | `src/stages/pagerank.py` | `run_pagerank(cfg, driver)` | GDS 中心性 |
| MetaPath | `src/stages/metapath.py` | `run_metapath(cfg, driver)` | 复用 `utilities/metapath_path_level.py` |

在 Python 中单独调用示例：

```python
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]  # 仓库根目录
sys.path.insert(0, str(REPO))

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.runner import PipelineRunner

cfg = PipelineConfig.load(REPO / "kg_build_pipeline" / "config.yaml")
results = PipelineRunner(cfg).run()
print(results.get("summary"))
```

---

## 配置说明（`config.yaml`）

| 配置块 | 主要项 | 说明 |
|--------|--------|------|
| `paths.schema_dir` | `kg_build_pipeline/schema` | 本体 JSON 目录 |
| `paths.markdown_dir` | `data/markdown/forTest` | 论文 Markdown 目录 |
| `paths.custom_prompt` | `kg_build_pipeline/prompts/custom_prompt.md` | build_kg 抽取 Prompt（仓内 v5） |
| `neo4j.*` | uri / user / password / database | Neo4j 连接 |
| `stages.*` | 各阶段 true/false | 是否参与 `--all` |
| `build_kg.max_docs` | `all` 或整数 | 处理文档数量上限 |
| `build_kg.perform_entity_resolution` | false | 与原版 Notebook 一致，抽取阶段不做实体消解 |
| `entity_merge` | 默认 false | 第一版建议手动开启或 `--stage entity_merge` |

密码与 API Key 优先从环境变量读取（`${NEO4J_PASSWORD}` 等占位符）。

---

## 与原 Notebook 的关系

| 原文件 | 状态 |
|--------|------|
| `1_2_0_2build_kg__neo4j.ipynb` | 保留；逻辑已抽到 `stages/build_kg.py` 等 |
| `1_2_1_1merging_entity_relation.ipynb` | 保留；最小消融在 `entity_merge.py` |
| `1_2_1_2pagerankMetapath.ipynb` | 保留；PageRank/MetaPath 在 `pagerank.py`、`metapath.py` |
| `output/*.json` | 不再作为 Pipeline 默认 Schema 源；已拷贝至 `schema/` |

MetaPath 核心 Cypher **不重复实现**，直接调用仓库内 `utilities/metapath_path_level.py`。

---

## Metapath 故障排查

`metapath` 阶段依赖前置阶段写回的图谱与 pagerank 属性，执行顺序必须为：`build_kg` → `subgraph_annotate` → `chunk_merge` → `pagerank` → `metapath`。

### 仅重跑 metapath

图数据已存在时，无需重跑前面阶段：

```powershell
python kg_build_pipeline/run_pipeline.py --config kg_build_pipeline/config.yaml --stage metapath
```

或在 Web UI 中只勾选 **metapath** 后 Build。

### 常见错误

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `F1 预检失败：无任何匹配实例` | `schema/metapath_relations.json` 与当前 KG 标签/关系不一致，或 `build_kg` 未完成 | 检查 build_kg 日志；对照 `entity.json` / `relation.json` |
| `F1 未创建任何 low MetaPath` | 实体缺少 `__Entity__` 标签，或模板全部无实例 | 确认 neo4j_graphrag 抽取成功；F1 使用 `:__Entity__` 过滤（与 Notebook 验收一致） |
| `未找到任何 {mpu,eem,ebm}_pagerank` | 未执行 `pagerank` 阶段 | 先跑 `--stage pagerank` 或全链路中包含 pagerank |
| `link_mid_to_low: F1 未创建任何 low` | F1 产出为 0，误进入 F4 | 先修复 F1；错误信息会明确指向 F1 而非 FROM_CHUNK |
| `link_mid_to_low: 未创建任何 hasDetailPath`（low>0） | mid 锚点与 low 实体未共享 `FROM_CHUNK` 的 Chunk | 检查实体 `FROM_CHUNK` 溯源；属 F4 层级边策略（Chunk 共现） |
| F1 单条模板 `缺少 ebm_pagerank` | 跨子图节点（如 EBM 模板中的 Experiment）仅有 `eem_pagerank` | 已用 COALESCE 回退；若仍失败，确认 pagerank 阶段成功 |

### 预期规模（2 篇 forTest 论文，仅供参考）

- low MetaPath：约 800+
- mid MetaPath：约 100+（Plan + Container）
- `hasDetailPath` 边：> 0（通常数千条）

---

## 设计原则

1. **一个阶段一个 `run_xxx()`**，返回 stats 字典，失败即中断后续阶段。
2. **Notebook 只做薄包装**，不在 Notebook 内堆业务代码。
3. **Schema 与数据路径可配置**，默认与 Pilot 实验目录 `forTest` 对齐。
4. **`clear_neo4j` 默认关闭**，防止误删生产图数据。

更细的各阶段算法说明见 [`docs/STAGE_NOTES.md`](docs/STAGE_NOTES.md)。
