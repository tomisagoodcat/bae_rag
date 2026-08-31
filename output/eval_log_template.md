# Retrieval Pipeline Evaluation Log

本文件由 `utilities/run_retrieval_eval.py` 自动追加；也可在 Notebook 综合测试 cell 调用 `append_eval_log()` 写入。

---

## 记录格式说明

每次运行追加一节，包含：

| 字段 | 含义 |
|------|------|
| `timestamp` | 测试开始时间 (ISO 8601) |
| `version` | 人工版本标签，如 `v2.0-olap-metrics` |
| `dialogue_test_set` | `legacy10`（q01–q10）/ `all`（66）/ `first`（前 N 条）；见 `utilities/dialogue_test_set.py` |
| `PIPELINE_VARIANT` | `full` 或 `no_hierarchy` |
| `session_mode` | `stateful` / `stateless` / `paired` |
| `retrieval_scoring` | `qrels`（若 turn 含 `relevant_mp_ids`）或 `llm_judge`（recall 为 proxy） |
| `feature_flags` | 各功能开关状态 |

### 核心指标（Turn2 主结论）

| 指标 | 定义 |
|------|------|
| recall@10 | qrels: \|qrels∩Top10\|/\|qrels\|；无 qrels: LLM 扩池 proxy |
| precision@10 | \|relevant∩Top10\| / 10 |
| anchor_overlap | \|Top10 ∩ Turn1 P*\| / \|Turn1 P*\| |
| faithfulness | LLM：答案是否被 context 支撑 |
| answer_relevance | LLM：答案是否回应当前 turn query |
| context_precision | LLM：有序 context 精确度 |

### qrels 扩展（可选）

在 `dialogue_test_cases.json` 的 turn 对象添加：

```json
"relevant_mp_ids": ["mp_xxx", "mp_yyy"]
```

非空时检索指标用经典 Recall/Precision；缺失或空数组则 fallback LLM judge。

### 测试集切换

```bash
# 默认 legacy10（q01–q10 按 name，约 28min）
python utilities/run_retrieval_eval.py --olap-compare --test-set legacy10 --version my-run

# 全量 66 条
python utilities/run_retrieval_eval.py --olap-compare --test-set all --version my-run-full

# 跨版本对比报告
python utilities/compare_eval_logs.py --versions v3-stateless-baseline v5-recall-wide-legacy10
```

---

## Run Template (示例 — 勿删，供复制)

```markdown
## Run YYYY-MM-DD HH:MM:SS

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics |
| PIPELINE_VARIANT | full |
| session_mode | paired |
| retrieval_scoring | qrels优先 / 无则 LLM judge |

### Turn1 Sanity (Stateful − Stateless)
| metric | Stateful | Stateless | Δ |

### Turn2 Core Δ (Stateful − Stateless)
| metric | Stateful | Stateless | Δ |

### Multidim Ablation (full vs no_hierarchy, Stateful Turn2+)
| metric | full | no_hierarchy | Δ |
```

---

<!-- APPEND_BELOW -->
