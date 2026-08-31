# OLAP 评估 v2 运行结果

**日期**: 2026-05-28  
**版本**: v2.0-olap-metrics  
**Neo4j**: 2024 MetaPath，索引正常  
**耗时**: OLAP ~38 min + Ablation ~30 min（合计 ~68 min）

---

## 1. OLAP 对比（Stateful vs Stateless，10 scenarios）

### Turn1 Sanity（应 ≈ 0）

| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall@10 | 0.593 | 0.593 | **0.000** |
| precision@10 | 0.260 | 0.260 | **0.000** |
| faithfulness | 0.200 | 0.100 | 0.100 |
| answer_relevance | 0.880 | 0.865 | 0.015 |
| context_precision | 0.188 | 0.188 | **0.000** |

Turn1 检索指标完全一致，符合 sanity 预期。

### Turn2 Core Δ（Stateful − Stateless，主结论）

| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall@10 (LLM proxy) | 0.171 | 0.674 | **-0.503** |
| precision@10 | 0.612 | 0.363 | **+0.250** |
| anchor_overlap | 0.000 | 0.319 | **-0.319** |
| faithfulness | 0.125 | 0.000 | +0.125 |
| answer_relevance | 0.731 | 0.787 | -0.056 |
| context_precision | 0.287 | 0.153 | **+0.134** |

**解读（谨慎）**：
- Stateful 在 Turn2 **Precision@10、Context Precision 更高**，但 **Recall proxy、Anchor Overlap 更低**
- drill_down 后 Top-10 与 Turn1 P* 几乎无重叠（anchor≈0），符合 low-level 重排行为，但也说明 OLAP 锚定叙事需与指标对齐
- 全部指标均为 **LLM judge**（无人工 qrels），Recall 为 proxy

### 失败场景（Stateful）

| Scenario | 错误 |
|----------|------|
| q02_measurement_qc | Turn2: `sibling_nav G_sub 为空` |
| q09_study_area_background | Turn2: `sibling_nav G_sub 为空` |

Stateful 8/10 完成；Stateless 10/10 完成。

---

## 2. 多维 Ablation（full vs no_hierarchy，Stateful Turn2+）

| metric | full | no_hierarchy | Δ |
|--------|------|--------------|---|
| Turn2 recall@10 | 0.171 | 0.562 | -0.392 |
| Turn2 precision@10 | 0.612 | 0.340 | **+0.272** |
| Turn2 anchor_overlap | 0.000 | 0.305 | -0.305 |
| Turn2 faithfulness | 0.125 | 0.100 | +0.025 |
| Turn2 answer_relevance | 0.712 | 0.740 | -0.028 |
| Turn2 context_precision | 0.175 | 0.189 | -0.014 |
| turns failed | **2** | 0 | 2 |

**解读**：full 在 Turn2 **Precision 更高**，但 **Recall proxy 更低** 且有 2 次 G_sub 空失败；no_hierarchy 更稳（0 失败）但失去 drill 语义。

---

## 3. 输出文件

- 完整 log：[`output/eval_log.md`](eval_log.md)（检索 `v2.0-olap-metrics`）
- 运行 stdout：[`output/v2_full_eval.log`](v2_full_eval.log)

---

## 4. 建议后续

1. 修复 q02/q09 Turn2 的 `sibling_nav G_sub 为空`（图算子或测试用例 expected_kappa）
2. 补充 Turn2 人工 `relevant_mp_ids` 以替换 LLM Recall proxy
3. 分析 anchor_overlap=0 是否与 Top-20 锚点 / low-level rerank 设计一致
