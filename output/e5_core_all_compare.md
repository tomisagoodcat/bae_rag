# Legacy10 同集 OLAP 跨版本对比

数据源: `C:\Users\tom\OneDrive\LUCK\luck grpahrag\code\cursorParperExtarct\output\eval_log.md`

说明: **legacy10** 对比应使用 ``--test-set legacy10``（按 name 筛选 q01–q10）。
旧版 ``--max-scenarios 10`` 仅取 JSON 前 10 条，在 66 条文件中与 legacy10 等价；
扩展后应用 ``legacy10`` 而非 ``first``。

## Turn2 Core Δ（Stateful − Stateless）

| version | recall Δ | precision Δ | anchor Δ | faithfulness Δ | answer_rel Δ | ctx_prec Δ |
|---------|----------|-------------|----------|----------------|--------------|------------|
| v3-stateless-baseline | -0.294 | +0.040 | -0.070 | +0.030 | +0.160 | +0.070 |
| v5-recall-wide-legacy10 | +0.002 | +0.120 | -0.010 | +0.100 | -0.025 | +0.010 |
| v6-e5-core-all | +0.004 | +0.025 | +0.041 | +0.031 | +0.145 | +0.016 |

## Turn2 绝对值（Stateful / Stateless）

### v3-stateless-baseline
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.469 | 0.764 | -0.294 |
| precision_at_10 | 0.51 | 0.47 | 0.04 |
| anchor_overlap | 0.08 | 0.15 | -0.07 |
| faithfulness | 0.03 | 0.0 | 0.03 |
| answer_relevance | 0.83 | 0.67 | 0.16 |
| context_precision | 0.21 | 0.14 | 0.07 |

- Stateful: scenarios 10/10, turns 30/30
- Stateless: scenarios 10/10, turns 30/30

### v5-recall-wide-legacy10
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.219 | 0.217 | 0.002 |
| precision_at_10 | 0.19 | 0.07 | 0.12 |
| anchor_overlap | 0.09 | 0.1 | -0.01 |
| faithfulness | 0.7 | 0.6 | 0.1 |
| answer_relevance | 0.285 | 0.31 | -0.025 |
| context_precision | 0.02 | 0.01 | 0.01 |

- Stateful: scenarios 7/10, turns 27/30
- Stateless: scenarios 10/10, turns 30/30

### v6-e5-core-all
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.258 | 0.254 | 0.004 |
| precision_at_10 | 0.138 | 0.113 | 0.025 |
| anchor_overlap | 0.509 | 0.469 | 0.041 |
| faithfulness | 0.219 | 0.188 | 0.031 |
| answer_relevance | 0.48 | 0.334 | 0.145 |
| context_precision | 0.053 | 0.038 | 0.016 |

- Stateful: scenarios 32/32, turns 86/86
- Stateless: scenarios 32/32, turns 86/86

## Turn1 Sanity Δ

| version | recall Δ | precision Δ | answer_rel Δ |
|---------|----------|-------------|--------------|
| v3-stateless-baseline | +0.100 | -0.030 | +0.135 |
| v5-recall-wide-legacy10 | +0.300 | +0.100 | +0.030 |
| v6-e5-core-all | +0.188 | +0.066 | -0.025 |
