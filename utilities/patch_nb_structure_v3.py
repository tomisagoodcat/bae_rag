"""Reorganize 3_0_2 Retevie.ipynb docs (Plan A) and remove Neo4jSchemaManager."""
from __future__ import annotations

import json
import re
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"
RUN_EVAL = Path(__file__).resolve().parents[1] / "utilities" / "run_retrieval_eval.py"


def _md(text: str) -> list:
    if not text.endswith("\n"):
        text += "\n"
    return text.splitlines(keepends=True)


# ── Part 0 ──────────────────────────────────────────────────────────
MD_0_INTRO = """# 3_0_2 对话检索（G 段）

**前置 Notebook**

| 步骤 | Notebook | 内容 |
|------|----------|------|
| KG 构建 | `1_2_0_2build_kg__neo4j.ipynb` | 知识图谱 |
| 索引与 MetaPath | `1_2_1_2pagerankMetapath.ipynb` | PageRank、embedding/fulltext、mid/low |

**本 Notebook**：多轮 **LangGraph** 检索 + 答案生成（论文 §5.1 / §5.4）。不包含 Neo4jSchemaManager（v3 已移除，检索不依赖 LLM 动态 Cypher）。
"""

MD_0_ARCH = """## Part 0 · 架构导读

### LangGraph 六节点（与 `build_graph_rag_pipeline` 一致）

```
改写(N1) → 路由(N2) → 候选池(N3) → 召回(N4) → 重排(N5) → 答案(N6)
```

| LangGraph 节点 | 论文章节 | 中文职责 |
|----------------|----------|----------|
| `query_rewriter` | — | 问题改写成英文检索短语 |
| `route` | §5.1 | 选主题模块 r、路径层级 l、多轮操作 κ |
| `gsub_builder` | §5.1 | 构造 OLAP 软先验池 `gsub_mp_ids` |
| `recall` | §5.2 | Hybrid 广召回 Top-50 |
| `rerank` | §5.2 | 融合检索分/图分/OLAP 先验 → Top-10 |
| `answer_generator` | §5.4 | 路径级 Context + 答案 + 写回状态 |

### 准备层 / 评估层（非 LangGraph 节点）

| 编号 | 内容 |
|------|------|
| **P0–P3** | 依赖、状态、Neo4j/LLM 连接 |
| **Prep** | 图算子 import、Recall 用 Cypher 模板 |
| **E1–E5** | 指标说明、评估脚本、OLAP 对比 |
"""

MD_0_GLOSSARY = """## 术语表（读代码与评估前先看）

| 中文 | 字段 / 符号 | 说明 |
|------|-------------|------|
| 主题模块 | `target_subgraphs` (r) | MPU / EEM / EBM，不是 mid/low |
| 路径层级 | `path_level` (l) | mid 概览，low 细节；首轮由 Route/LLM 选择 |
| 多轮操作 | `kappa` (κ) | first_turn / drill_down / roll_up / sibling_nav / drill_across |
| 上一轮短名单 | `candidate_mp_ids` (C) | 上轮 P*，约 10 条 |
| OLAP 先验池 | `gsub_mp_ids` | Turn2+ 图算子展开；**不**限制 Recall 范围 |
| 广召回池 | `recall_candidates` | Recall 输出，最多 50 条 |
| 本轮短名单 | `retrieval_mp_ids` (P*) | Rerank 后 Top-10 |
"""

MD_0_FLOW = """## 数据流与流程图

```mermaid
flowchart LR
    Q[用户问题] --> N1[改写]
    N1 --> N2[路由 r,l,κ]
    N2 --> N3[建池 G_sub]
    N3 --> N4[Recall Top-50]
    N4 --> N5[Rerank Top-10]
    N5 --> N6[答案]
    N6 --> M[写回 M_t]
```

**实验开关**：`PIPELINE_VARIANT = "full" | "no_hierarchy"`（见 P2 Code Cell）。
"""

MD_PART2_RERANK = """## Part 2 · 检索与重排（Recall + Rerank）

### 重排公式（Node 5）

$$s_{\mathrm{final}} = \alpha s_{\mathrm{search}} + \eta s_{\mathrm{pr}} + \gamma s_{\mathrm{olap}}$$

| 符号 | 代码 | 默认值 | 含义 |
|------|------|--------|------|
| \(s_{\mathrm{search}}\) | hybrid `score` 或 embedding | 归一化 | 与问题的语义相关性 |
| \(s_{\mathrm{pr}}\) | `graph_score` = `maxPageRank` | 归一化 | 图分析分；缺失则 **raise** |
| \(s_{\mathrm{olap}}\) | `gsub_mp_ids` 内 1.0 / 外 0.3 | 归一化 | OLAP 软先验，**非**硬过滤 |
| α, η, γ | `RerankWeights` | 0.5, 0.35, 0.15 | γ=0 当 κ=first_turn |

实现：`utilities/retrieval_rerank.py` → `rerank_metapath_candidates()`。

### Stateful vs Stateless（OLAP 评估对照）

| 维度 | Stateful | Stateless |
|------|----------|-----------|
| 状态 | 保留 C、r、l、κ、`dialogue_turn` | 每轮 `make_initial_state`，无记忆 |
| Turn2+ Route | 可走 drill_down / roll_up 等 | 常被判为 `first_turn` |
| `gsub_mp_ids` | 图算子展开（可空，不中断） | 几乎总为空 |
| Recall | 各轮 hybrid，按当轮 r+l | **相同机制** |
| Rerank γ | Turn2+ 为 0.15（κ≠first_turn） | **恒为 0** |

**评估含义**：Recall 相同；Stateful 的差异主要在 **路由 + G_sub 软先验** 是否把池内路径推入 Top-10。见 **E5 OLAP 对比** Code Cell。
"""

# ── Part 1 markdown ─────────────────────────────────────────────────
MD_P0 = """### P0 环境与依赖导入

**在整体中的位置**：Notebook 最前；为 P2–P3 与全部 Node 提供路径与 `dotenv`。

**本 Code Cell 做什么**

- 加载 `PaperExtract/output` 等路径（历史字段，v3 检索不读动态 Schema 文件）
- 导入 `langgraph`、`neo4j_graphrag` 等包

**关键输出**：无 graph state；仅副作用导入。
"""

MD_P2 = """### P2 对话状态 M_t 与实验开关

**在整体中的位置**：Pipeline 运行前定义；`make_initial_state()` 供首轮与评估调用。

**本 Code Cell 做什么**

- 定义 `SimplifiedGraphRAGState`（TypedDict）
- 设置 `PIPELINE_VARIANT`：`full` | `no_hierarchy`

**关键字段**

| 字段 | 含义 |
|------|------|
| `target_subgraphs` | 主题模块 r |
| `path_level` | l = mid / low |
| `kappa` | 多轮操作 κ |
| `candidate_mp_ids` | 上一轮 P* |
| `gsub_mp_ids` | OLAP 先验池（Node 3 写入） |
| `recall_candidates` | Recall Top-50（Node 4 写入） |
| `retrieval_mp_ids` | 本轮 P* Top-10（Node 5 写入） |

**`no_hierarchy`**：Turn≥2 强制 `κ=first_turn, l=mid`（消融 Stateful 导航，见 `pipeline_config.py`）。
"""

MD_P3 = """### P3 模型与 Neo4j 连接

**在整体中的位置**：所有 Node 之前执行；提供全局 `llm`、`neo4j_embed_model`、`neo4j_driver`。

**本 Code Cell 做什么**

- `SentenceTransformerEmbeddings`（本地向量模型）
- `OpenAILLM`（改写 / 路由 / 答案 / 评估 judge）
- `GraphDatabase.driver` 连接 Neo4j

**关键环境变量**：`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、`QWEN_API_KEY`、`LOCAL_MODEL_PATH_BCE` 等（见 `.env`）。

**运行注意**：必须先本 Cell 再跑 Pipeline；否则 `neo4j_driver` / `llm` 未定义。
"""

# ── Part 2 node markdown ────────────────────────────────────────────
MD_N1 = """### N1 查询改写（Query Rewriter）

**在整体中的位置**：LangGraph 入口 → 输出 `rewritten_query` → Node 2 Route。

**本 Code Cell 做什么**

- 中文：关键词表 + LLM 英译改写
- 英文：LLM 压缩为 ≤20 词检索短语
- 改写失败或过短：**raise**（无固定 fallback 短语）

**关键参数**：改写长度上限约 120 字符；**不使用** Neo4j Schema。

**输入 / 输出**

| 方向 | 字段 |
|------|------|
| 入 | `original_query` |
| 出 | `rewritten_query`，`keywords_*`（`schema_info` 保留字段但恒为空） |
"""

MD_N2 = """### N2 多轮路由（Route: r, l, κ）

**在整体中的位置**：读 `M_{t-1}`（`candidate_mp_ids`、`dialogue_turn` 等）→ 决定本轮检索范围。

**本 Code Cell 做什么**

- 首轮或无 C：LLM 选 **r + l**，`κ=first_turn`（**不写死 l=mid**）
- 多轮：LLM 选 κ、l、r；`drill_down`/`roll_up` 保持 r

**关键依赖**：`utilities/dialogue_routing.route_dialogue`；`PIPELINE_VARIANT` 可覆盖路由结果。

**输入 / 输出**

| 出 | 字段 |
|----|------|
| | `target_subgraphs`, `path_level`, `kappa` |
"""

MD_PREP_IMPORT = """### Prep 图算子与重排函数导入

**在整体中的位置**：Node 3/4/5 之前执行一次；仅 import，无 state 更新。

**本 Code Cell 做什么**

- `N_l`, `WF`, `DA`, `build_gsub_mp_ids`（`dialogue_routing.py`）
- `RECALL_TOP_K=50`, `OUTPUT_TOP_K=10`, `rerank_metapath_candidates`

**关键常量**：广召回 50 条，最终 P* 10 条。
"""

MD_N3 = """### N3 候选路径池 G_sub（OLAP 软先验）

**在整体中的位置**：Route 之后、Recall 之前；写入 `gsub_mp_ids`。

**本 Code Cell 做什么**

- `κ=first_turn`：池为空，Recall 仍按 r+l 全库 hybrid
- 其他 κ：从上一轮 P* 用图算子展开 mid/low 邻接路径
- **池为空仅 warn**，不中断（软先验在 Rerank 中体现为全体 0.3）

**输入 / 输出**

| 入 | `kappa`, `path_level`, `candidate_mp_ids` |
| 出 | `gsub_mp_ids`, `gsub_size` |
"""

MD_N5_CYPHER = """### Prep Recall 用 Cypher 模板

**在整体中的位置**：Node 4 Recall 调用 `_build_cypher_for_subgraph(sg, l)`。

**本 Code Cell 做什么**

- 定义 hybrid 检索后的 Cypher 投影（Chunk 文本、`maxPageRank` 等）
- `graph_score = node.maxPageRank`（**无 COALESCE**）

**关键参数**：`subgraph` ∈ MPU/EEM/EBM；`path_level` ∈ mid/low。
"""

MD_N4 = """### N4 广召回 Recall（Hybrid Top-50）

**在整体中的位置**：按 Route 的 r、l 在各模块做 hybrid；**与 κ 无关**（每轮均广召回）。

**本 Code Cell 做什么**

- `HybridCypherRetriever` + `HYBRID_SCAN_TOP_K`（mid 300 / low 60）
- 合并去重 → 最多 **50** 条 → `recall_candidates`

**输入 / 输出**

| 入 | `rewritten_query`, `target_subgraphs`, `path_level` |
| 出 | `recall_candidates`, `recall_count` |
"""

MD_N5 = """### N5 重排序 Rerank（Top-10）

**在整体中的位置**：读 `recall_candidates` + `gsub_mp_ids` → 输出 P*。

**本 Code Cell 做什么**

- 调用 `rerank_metapath_candidates`（见 Part 2 公式说明）
- `κ=first_turn` → **γ=0**；否则 γ=0.15

**输入 / 输出**

| 出 | `retrieval_mp_ids`, `candidate_mp_ids`（10 条） |
"""

MD_N6 = """### N6 证据上下文与答案（§5.4）

**在整体中的位置**：Pipeline 出口；写回多轮状态。

**本 Code Cell 做什么**

- 对 P* 前 10 条构建 `Context(p)`（路径结构 + 有序 Chunk）
- LLM 生成带引用答案
- 写回 `candidate_mp_ids`、`dialogue_turn+1` 等

**输入 / 输出**

| 入 | `original_query`, `retrieval_mp_ids` |
| 出 | `final_answer`，更新后的 M_t |
"""

MD_G7 = """### 组装 LangGraph Pipeline

**在整体中的位置**：定义 `graph_app`；评估与多轮测试均 `graph_app.invoke(state)`。

**本 Code Cell 做什么**

- `build_graph_rag_pipeline()` 注册六节点与边
- 可选 `test_multiturn_dialogue()` 冒烟

**运行顺序（手动）**：P0 → P2 → P3 → Prep import → N1–N6 定义 → 本 Cell → 评估 Cell。
"""

# ── Part 4 eval ─────────────────────────────────────────────────────
MD_E1 = """## Part 4 · 评估

### E1 评估指标说明

| 指标 | 含义 | 备注 |
|------|------|------|
| Recall@10 | 相关路径被召回到 Top-10 的比例 | 无 qrels 时用 LLM judge（proxy） |
| Precision@10 | Top-10 中相关路径占比 | 同上 |
| anchor_overlap | Turn2 的 P* 与 Turn1 P* 的 mp_id 交集 | 衡量多轮锚定 |
| faithfulness | 答案是否可由 Context 支持 | LLM judge |
| answer_relevance | 答案与问题相关性 | LLM judge |
| context_precision | 检索上下文相关性 | LLM judge |

数据：`data/dialogue_test_cases.json`（多轮）；`data/questions.csv`（单轮 legacy）。
"""

MD_E2 = """### E2 评估模块导入

**本 Code Cell**：导入 `utilities/test_evaluation`（`evaluate_dialogue_scenarios`、`evaluate_olap_comparison` 等）。

**输出日志**：`output/eval_log.md`（追加写入）。
"""

MD_E3 = """### E3 Stateful 多轮对话测试

对 `dialogue_test_cases.json` 跑 **Stateful** 全流程并打核心指标（默认 `PIPELINE_VARIANT=full`）。
"""

MD_E4 = """### E4 单轮 / 综合测试（可选）

`questions.csv` 单轮路由与 legacy 指标；按需运行，非 OLAP 主实验。
"""

MD_E5 = """### E5 OLAP 对比（Stateful vs Stateless）

**成对运行**同一批 scenario：

1. **Stateful**：状态在轮次间传递  
2. **Stateless**：每轮 `make_initial_state`  

输出 Turn1 sanity（Δ≈0）与 Turn2 core Δ；结果写入 `eval_log.md`。

CLI 等价：`python utilities/run_retrieval_eval.py --olap-compare --skip-smoke`
"""

QUERY_REWRITER_CODE = r'''# ══════════════════════════════════════════════════════════════
# N1: Query Rewriter
# ══════════════════════════════════════════════════════════════

from typing import Dict, List


def extract_and_translate_keywords(query: str) -> dict:
    """中文领域关键词 → 英文（词典映射，无 LLM）。"""
    keyword_map = {
        "汞": ["mercury", "Hg", "HgT", "MeHg"],
        "铅": ["lead", "Pb"],
        "镉": ["cadmium", "Cd"],
        "砷": ["arsenic", "As"],
        "铬": ["chromium", "Cr"],
        "重金属": ["heavy metal", "heavy metals"],
        "水稻": ["rice", "paddy rice", "Oryza"],
        "大米": ["rice", "rice grain"],
        "籽粒": ["grain", "seed"],
        "样本": ["sample", "specimen"],
        "标本": ["specimen"],
        "检测": ["detection", "determination", "measurement"],
        "分析": ["analysis", "assay"],
        "方法": ["method", "approach", "technique"],
        "实验": ["experiment", "test"],
        "测定": ["determination", "measurement"],
        "消解": ["digestion", "dissolution"],
        "数据": ["data"],
        "数据集": ["dataset", "data set"],
        "结果": ["result", "outcome"],
        "结论": ["conclusion", "finding"],
        "污染": ["contamination", "pollution"],
        "浓度": ["concentration", "level"],
        "含量": ["content", "amount"],
        "采集": ["collection", "sampling"],
        "保存": ["preservation", "storage"],
    }
    chinese_kws = []
    english_kws = []
    for cn_word, en_words in keyword_map.items():
        if cn_word in query:
            chinese_kws.append(cn_word)
            english_kws.extend(en_words)
    english_kws = list(dict.fromkeys(english_kws))
    both = []
    for cn_word in chinese_kws:
        en_words = keyword_map.get(cn_word, [])
        if en_words:
            both.append(cn_word + "|" + "|".join(en_words[:2]))
    return {
        "chinese_keywords": chinese_kws,
        "english_keywords": english_kws,
        "both": both,
        "has_keywords": len(chinese_kws) > 0,
    }


def query_rewriter_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\n" + "=" * 60)
    print("Node 1: Query Rewriter")
    print("=" * 60)

    original = state["original_query"]
    if not original or not original.strip():
        raise ValueError("original_query 为空")

    print(f"原问题: {original}")
    keywords = extract_and_translate_keywords(original)
    if keywords["has_keywords"]:
        print(f"  [关键词] 中文: {keywords['chinese_keywords']}")
        print(f"  [关键词] 英文: {keywords['english_keywords'][:5]}")

    is_chinese = _is_chinese_query(original)
    print(f"  [语言] {'中文' if is_chinese else '英文'}")

    if is_chinese:
        prompt = _build_translate_and_rewrite_prompt(original, keywords)
    else:
        prompt = _build_english_rewrite_prompt(original)

    print("  [改写] 调用 LLM...")
    rewritten = llm.invoke(prompt).content.strip()
    rewritten = _clean_rewritten_query(rewritten)

    if not rewritten or len(rewritten) < 3:
        raise ValueError(
            f"改写结果过短或为空: {rewritten!r}; keywords={keywords['english_keywords'][:5]}"
        )

    if len(rewritten) > 120:
        print(f"  ⚠ 改写过长({len(rewritten)}字符)，词边界截断")
        rewritten = rewritten[:120].rsplit(" ", 1)[0]

    print(f"改写后(英文): {rewritten}")

    return {
        "rewritten_query": rewritten,
        "schema_info": "",
        "keywords_zh": keywords["chinese_keywords"],
        "keywords_en": keywords["english_keywords"],
        "keywords_both": keywords["both"],
    }


def _is_chinese_query(query: str) -> bool:
    chinese_chars = sum(1 for c in query if "\u4e00" <= c <= "\u9fff")
    return chinese_chars / max(len(query.strip()), 1) > 0.3


def _build_translate_and_rewrite_prompt(query: str, keywords: Dict) -> str:
    keyword_hint = ""
    if keywords["english_keywords"]:
        en_kws = keywords["english_keywords"][:5]
        keyword_hint = f"Key terms: {', '.join(en_kws)}\n"
    return f"""You are a scientific literature search expert. Translate the Chinese query to a concise English search phrase.

Chinese query: {query}
{keyword_hint}
Instructions:
- Output English ONLY, maximum 20 words
- Preserve the EXACT semantic intent, do NOT expand or add context
- Output a noun phrase or short declarative sentence
- NEVER use: whu_, mp_, iao_, prov_ prefixes

Output (20 words max):"""


def _build_english_rewrite_prompt(query: str) -> str:
    return f"""You are a scientific literature search expert. Rewrite the query as a concise search phrase.

Query: {query}

Instructions:
- Output English ONLY, maximum 20 words
- Preserve the EXACT semantic intent, do NOT expand or add new concepts
- Output a noun phrase or short declarative sentence
- NEVER use: whu_, mp_, iao_, prov_ prefixes

Output (20 words max):"""


def _clean_rewritten_query(query: str) -> str:
    prefixes = [
        "Rewritten query:", "Query:", "English:",
        "Translated:", "Output:", "Result:",
        "改写后", "翻译", "查询",
    ]
    for prefix in prefixes:
        if query.lower().startswith(prefix.lower()):
            query = query[len(prefix) :].strip()
            break
    query = query.strip("\"'\"\"''")
    return query.rstrip(".").strip()


print("✅ N1 query_rewriter_node 定义完成")
'''


DROP_CELL_IDS = frozenset({
    "3c60fb9c",
    "7ebd1501",
    "4a0d3ffb",
    "034adf08",
    "d6b4b4d4",
})


def _is_schema_cell(src: str) -> bool:
    return "class Neo4jSchemaManager" in src or "def test_schema_manager" in src


def _code_marker(src: str) -> str:
    if "def build_graph_rag_pipeline" in src:
        return "g7_pipeline"
    if "def make_initial_state" in src or "class SimplifiedGraphRAGState" in src:
        return "p2_state"
    if "Cell 1: 导入依赖" in src or "# Cell 1: 导入依赖" in src:
        return "p0_import"
    if "环境与模型初始化" in src or "neo4j_embed_model" in src and "GraphDatabase.driver" in src:
        return "p3_connect"
    if "def query_rewriter_node" in src or "Node 1 - Query Rewriter" in src:
        return "n1_rewriter"
    if "def route_node" in src:
        return "n2_route"
    if "G_sub 算子" in src and "import" in src and "build_gsub_mp_ids" in src:
        return "prep_import"
    if "def gsub_builder_node" in src:
        return "n3_gsub"
    if "def recall_node" in src:
        return "n4_recall"
    if "def _build_cypher_for_subgraph" in src:
        return "prep_cypher"
    if "def rerank_node" in src:
        return "n5_rerank"
    if "def answer_generator_node" in src:
        return "n6_answer"
    if "report_stateful = evaluate_dialogue_scenarios" in src:
        return "e5_olap"
    if "CORE_METRIC_KEYS" in src and "from utilities.test_evaluation import" in src:
        return "e2_eval_import"
    if "evaluate_dialogue_scenarios" in src and "dialogue_report" in src:
        return "e3_dialogue"
    if "evaluate_olap_comparison" not in src and "evaluate_dialogue_scenarios" in src:
        return "e3_dialogue"
    if "Faithfulness" in src and "def " in src:
        return "eval_legacy"
    if "综合测试" in src and "run_single_case" in src:
        return "e4_comprehensive"
    if "综合测试 - 精简" in src:
        return "e4_short"
    return ""


MD_BEFORE_CODE = {
    "p0_import": MD_P0,
    "p2_state": MD_P2,
    "p3_connect": MD_P3,
    "n1_rewriter": MD_N1,
    "n2_route": MD_N2,
    "prep_import": MD_PREP_IMPORT,
    "n3_gsub": MD_N3,
    "prep_cypher": MD_N5_CYPHER,
    "n4_recall": MD_N4,
    "n5_rerank": MD_N5,
    "n6_answer": MD_N6,
    "g7_pipeline": MD_G7,
    "e2_eval_import": MD_E2,
    "e3_dialogue": MD_E3,
    "e4_comprehensive": MD_E4,
    "e5_olap": MD_E5,
}


def _should_drop_cell(cell: dict) -> bool:
    cid = cell.get("id") or ""
    if cid in DROP_CELL_IDS:
        return True
    src = "".join(cell.get("source", []))
    if cell["cell_type"] == "code" and _is_schema_cell(src):
        return True
    if cell["cell_type"] == "markdown" and "Neo4jSchemaManager" in src:
        return True
    if cell["cell_type"] == "markdown" and src.strip().startswith("# ══") and "import" in src:
        return True
    if cell["cell_type"] == "markdown" and "def _build_cypher_for_subgraph" in src:
        return True
    # legacy metric fragment cells -> drop, merged into E1
    if cell["cell_type"] == "markdown" and src.strip().startswith("######"):
        return True
    if cell["cell_type"] == "code" and ("Faithfulness" in src or "Answer Relevancy" in src or "Context Precision" in src):
        return True
    if cell["cell_type"] == "markdown" and src.strip() in ("###### 详细测试", "###### 简短测试"):
        return True
    if cell["cell_type"] == "markdown" and src.strip().startswith("##### "):
        return True
    if cell["cell_type"] == "markdown" and src.strip().startswith("## 术语表（读代码 / 评估"):
        return True
    if cell["cell_type"] == "markdown" and src.strip().startswith("# 流程（论文"):
        return True
    if cell["cell_type"] == "code" and "综合测试 - 精简" in src:
        return True
    return False


def rebuild_notebook() -> list[dict]:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    kept: list[dict] = []
    for cell in nb["cells"]:
        if _should_drop_cell(cell):
            continue
        if cell["cell_type"] == "code":
            src = "".join(cell.get("source", []))
            marker = _code_marker(src)
            if marker == "n1_rewriter":
                cell = {**cell, "source": _md(QUERY_REWRITER_CODE)}
            kept.append(cell)
        else:
            kept.append(cell)

    # Rebuild front matter: keep cell 0, replace 1-4 with new Part 0
    out: list[dict] = []
    part0_md = [
        _md(MD_0_INTRO),
        _md(MD_0_ARCH),
        _md(MD_0_GLOSSARY),
        _md(MD_0_FLOW),
    ]
    inserted_part0 = False
    inserted_part2_rerank = False
    part0_done = False

    for i, cell in enumerate(kept):
        if not part0_done and cell["cell_type"] == "markdown" and "3_0_2" in "".join(cell.get("source", []))[:30]:
            out.append({"cell_type": "markdown", "metadata": {}, "id": "7378ae1d", "source": part0_md[0]})
            for j, block in enumerate(part0_md[1:], 1):
                out.append({"cell_type": "markdown", "metadata": {}, "id": f"part0_{j}", "source": block})
            part0_done = True
            continue
        if cell["cell_type"] == "markdown" and not inserted_part0 and "G 子图" in "".join(cell.get("source", [])):
            # skip duplicate old intro
            continue

        if cell["cell_type"] == "code":
            marker = _code_marker("".join(cell.get("source", [])))
            if marker == "prep_import" and not inserted_part2_rerank:
                out.append({"cell_type": "markdown", "metadata": {}, "id": "part2_rerank_doc", "source": _md(MD_PART2_RERANK)})
                inserted_part2_rerank = True
            if marker in MD_BEFORE_CODE:
                out.append({"cell_type": "markdown", "metadata": {}, "id": f"md_{marker}", "source": MD_BEFORE_CODE[marker]})
            if marker == "e2_eval_import":
                out.append({"cell_type": "markdown", "metadata": {}, "id": "e1_metrics", "source": _md(MD_E1)})
        out.append(cell)

    return out


def find_pipeline_indices(cells: list[dict]) -> list[int]:
    markers = [
        "p0_import",
        "p2_state",
        "p3_connect",
        "n1_rewriter",
        "n2_route",
        "prep_import",
        "n3_gsub",
        "prep_cypher",
        "n4_recall",
        "n5_rerank",
        "n6_answer",
        "g7_pipeline",
    ]
    idx_map = {}
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        m = _code_marker("".join(c.get("source", [])))
        if m:
            idx_map[m] = i
    return [idx_map[m] for m in markers if m in idx_map]


def find_eval_indices(cells: list[dict]) -> tuple[int | None, int | None]:
    e2 = e5 = None
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        src = "".join(c.get("source", []))
        if "CORE_METRIC_KEYS" in src:
            e2 = i
        if "evaluate_olap_comparison" in src:
            e5 = i
    return e2, e5


def patch_run_retrieval_eval(indices: list[int], e2: int | None, e5: int | None) -> None:
    text = RUN_EVAL.read_text(encoding="utf-8")
    text = re.sub(
        r"PIPELINE_CELL_INDICES = \[.*?\]",
        f"PIPELINE_CELL_INDICES = {indices}",
        text,
        count=1,
    )
    if e2 is not None:
        text = re.sub(r"EVAL_IMPORT_CELL = \d+", f"EVAL_IMPORT_CELL = {e2}", text, count=1)
    if e5 is not None:
        text = re.sub(r"OLAP_COMPARE_CELL = \d+", f"OLAP_COMPARE_CELL = {e5}", text, count=1)
    RUN_EVAL.write_text(text, encoding="utf-8")


def main() -> None:
    cells = rebuild_notebook()
    nb = json.loads(NB.read_text(encoding="utf-8"))
    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    pipeline_idx = find_pipeline_indices(cells)
    e2, e5 = find_eval_indices(cells)
    patch_run_retrieval_eval(pipeline_idx, e2, e5)

    print(f"✅ {NB} → {len(cells)} cells")
    print(f"   PIPELINE_CELL_INDICES = {pipeline_idx}")
    print(f"   EVAL_IMPORT_CELL = {e2}, OLAP_COMPARE_CELL = {e5}")


if __name__ == "__main__":
    main()
