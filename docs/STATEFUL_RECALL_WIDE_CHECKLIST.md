# Stateful「双 Route + Recall flat」改动清单

对照 notebook：`3_0_2 Retevie.ipynb`  
原则：**Search Wide, Rank Narrow**；**不兜底、不静默降级**（空 G_sub、缺 graph_score、缺候选等均 `raise`）。

---

## 图拓扑（改后）

```text
Stateless（不变）:
  N1 Rewriter → N2 Route(r) → N4 Recall(flat) → N5 Rerank(PR-only) → N6 Answer

Stateful（新）:
  N1 Rewriter → N2a Route_r(r) → N4 Recall(flat) → N2b Route_olap(κ,l) → N3 G_sub → N5 Rerank(α,η,γ) → N6 Answer
```

| 旧边 | 新边 |
|------|------|
| `route → gsub → recall → rerank` | `route_r → recall → route_olap → gsub → rerank` |

---

## 逐节点改动

### 文档 · Part 0 / Part 2 / E5 Markdown

| 项 | 改动 |
|----|------|
| Pipeline 总览表 | 节点拆为 `route_r` / `route_olap`；Recall 写明 **Stateful flat** |
| Part 2 公式表 | `s_olap` 改为 **1.0 / 0.0**（G_sub 内/外）；Recall 行改为「模块级 flat，不按 l 过滤」 |
| E5 对照表 | Stateful：Route 拆两阶段；Recall 与 Stateless 同宽 |

### Prep · `SimplifiedGraphRAGState` + `make_initial_state`

| 字段 | 改动 |
|------|------|
| `previous_query` | **新增**：上一轮用户原问句，供 `Route_olap(q_{n-1}, q_n)` |
| 重复注释 | 删除重复的 `# G_sub 构造结果` 行 |
| `make_initial_state` | 初始化 `previous_query: ""` |

### N1 · `query_rewriter_node`

| 项 | 改动 |
|----|------|
| 逻辑 | **不变** |
| 约束 | 仍要求非空 `rewritten_query`，失败即抛错 |

### N2a · `route_r_node`（新，替代 Stateful 下原 `route_node`）

| 项 | 改动 |
|----|------|
| 职责 | **仅选 r**（`target_subgraphs`） |
| 实现 | `route_modules_recall(llm, query)` → `utilities.dialogue_routing.route_modules_only` |
| 写出 | 只更新 `target_subgraphs`；**不写** `kappa` / `path_level`（留给 Route_olap） |
| Stateless | 保持原 `route_node` 行为：`route_modules_only` + `kappa=first_turn`, `l=flat` |

### N4 · `recall_node`

| 项 | 改动 |
|----|------|
| Stateful | **一律** `_search_single_subgraph_flat`（与 Stateless 相同宽召回） |
| 删除 | Stateful 分支里 `_search_single_subgraph(..., path_level)` |
| 日志 | 打印 `Recall=flat (module-wide, no l filter)` |
| 仍用 | `state["target_subgraphs"]`（来自 Route_r） |
| 禁止 | 读取 `gsub_mp_ids` / `kappa` 过滤候选 |

### N2b · `route_olap_node`（新）

| 项 | 改动 |
|----|------|
| 时机 | **Recall 之后** |
| 输入 | `rewritten_query`（当前）、`previous_query`（Turn≥2 **必填**）、`M_{t-1}`（`candidate_mp_ids`, `target_subgraphs`） |
| 实现 | `route_olap_dialogue(llm, query_curr, query_prev, state)` |
| 写出 | 仅 `kappa`, `path_level`；**不修改** `target_subgraphs` |
| Turn1 | `kappa=first_turn`，`path_level` 由 LLM（`route_first_turn` 的 l 部分） |
| Turn≥2 | 必须提供 `previous_query`，否则 `ValueError` |
| `no_hierarchy` | `apply_olap_route_override`：Turn≥2 强制 `κ=first_turn`（Recall 仍 flat） |

### N3 · `gsub_builder_node`

| 项 | 改动 |
|----|------|
| 输入 | Recall **之后** 的 `kappa`, `path_level`, `candidate_mp_ids`（仍为上轮 P*） |
| `first_turn` | `G_sub=∅`（合法） |
| Turn≥2 且 `κ≠first_turn` | `build_gsub_mp_ids` 后若 **空集 → `RuntimeError`**（删除 `warnings.warn` 继续跑） |
| Stateless | 仍返回空 G_sub |

### N5 · `rerank_node`

| 项 | 改动 |
|----|------|
| `s_olap` | 池内 **1.0**，池外 **0.0**（`retrieval_rerank.olap_prior_score`） |
| `γ>0` | 要求 **非空** `gsub_mp_ids`，否则 `ValueError` |
| Turn1 | `kappa==first_turn` → `γ=0`（不变） |
| Stateless | `rerank_page_rank_only`（不变） |

### N6 · `answer_generator_node`

| 项 | 改动 |
|----|------|
| 逻辑 | **不变** |
| 写回 | 仍更新 `candidate_mp_ids`, `dialogue_turn+1` |

### Graph · `build_graph_rag_pipeline`

| 项 | 改动 |
|----|------|
| 节点 | 注册 `route_r`, `route_olap`；Stateful 不再用单节点 `route` 串 gsub |
| 边 | 见上文拓扑 |
| 打印 | `Rewriter → Route_r → Recall → Route_olap → G_sub → Rerank → Answer` |

### 多轮调用 · `test_multiturn_dialogue` / `test_evaluation.run_dialogue_scenario`

| 项 | 改动 |
|----|------|
| Turn≥2 | 调用前设置 `state["previous_query"]` 为上一轮 `turn["query"]` |
| 评估 | Route 命中率仍对比 `state["kappa"]` / `state["path_level"]`（来自 Route_olap） |

---

## `utilities/` 代码清单

| 文件 | 改动 |
|------|------|
| `dialogue_routing.py` | 新增 `route_olap_dialogue`；导出 `route_modules_recall`（别名 `route_modules_only`） |
| `retrieval_rerank.py` | `OLAP_NOT_IN_POOL=0.0`；`rerank_metapath_candidates` 在 `γ>0` 且空 G_sub 时 `raise` |
| `pipeline_config.py` | 新增 `apply_olap_route_override`；`feature_flags` 增加 `recall_module_flat` |
| `test_retrieval_rerank.py` | 更新 olap 先验期望值；空 G_sub + γ>0 用例 |
| `test_evaluation.py` | `run_dialogue_scenario` 写入 `previous_query` |

---

## 明确不做（满足约束）

- 不删除 `route_dialogue` / `build_gsub_mp_ids` / `N_l` / `WF` / `DA`
- 不改 MetaPath 生成、embedding、向量索引 API
- 不用 G_sub 过滤 Recall
- 不用 0.3 软惩罚掩盖空 G_sub

---

## 验证建议

1. `python -m utilities.test_retrieval_rerank`
2. `python -m utilities.test_olap_metrics_unit`
3. Notebook：跑 `test_multiturn_dialogue()`，Turn2 `sibling_nav` 若 WF 为空应 **失败** 而非静默
4. E5：`run_retrieval_eval.py --olap-compare` 对比 Recall@10 是否收敛
