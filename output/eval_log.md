# Retrieval Pipeline Evaluation Log

本文件由 `utilities/run_retrieval_eval.py` 自动追加。格式说明见 [eval_log_template.md](./eval_log_template.md)。

---

<!-- APPEND_BELOW -->

## Run 2026-05-31 23:02:01 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v6-e5-core-all |
| dialogue_test_set | all |
| olap_modes | drill_down,first_turn,roll_up |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: all
- scenarios completed: 32/32
- turns OK: 86/86 (failed: 0)
- κ hit rate (mechanism): 87.2%
- l hit rate (mechanism): 73.3%
- avg relevancy (legacy): 0.661
- qrels scored turns: 3
- LLM-judge scored turns: 83

#### Turn1 核心指标
- recall_at_10: 0.656
- precision_at_10: 0.275
- faithfulness: 0.244
- answer_relevance: 0.589
- context_precision: 0.106

#### Turn2 核心指标
- recall_at_10: 0.258
- precision_at_10: 0.138
- anchor_overlap: 0.509
- faithfulness: 0.219
- answer_relevance: 0.480
- context_precision: 0.053

---
## Run 2026-05-31 23:02:01 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v6-e5-core-all |
| dialogue_test_set | all |
| olap_modes | — |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: all
- scenarios completed: 32/32
- turns OK: 86/86 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.662
- qrels scored turns: 3
- LLM-judge scored turns: 83

#### Turn1 核心指标
- recall_at_10: 0.469
- precision_at_10: 0.209
- faithfulness: 0.250
- answer_relevance: 0.614
- context_precision: 0.087

#### Turn2 核心指标
- recall_at_10: 0.254
- precision_at_10: 0.113
- anchor_overlap: 0.469
- faithfulness: 0.188
- answer_relevance: 0.334
- context_precision: 0.038

---
## Run 2026-05-31 23:02:01 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v6-e5-core-all |
| dialogue_test_set | all |
| olap_modes | — |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 4874.0 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.656 | 0.469 | 0.188 |
| precision_at_10 | 0.275 | 0.209 | 0.066 |
| faithfulness | 0.244 | 0.250 | -0.006 |
| answer_relevance | 0.589 | 0.614 | -0.025 |
| context_precision | 0.106 | 0.087 | 0.019 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.258 | 0.254 | 0.004 |
| precision_at_10 | 0.138 | 0.113 | 0.025 |
| anchor_overlap | 0.509 | 0.469 | 0.041 |
| faithfulness | 0.219 | 0.188 | 0.031 |
| answer_relevance | 0.480 | 0.334 | 0.145 |
| context_precision | 0.053 | 0.038 | 0.016 |

---


## Run 2026-05-31 12:33:54 UTC

| 项 | 值 |
|----|-----|
| version | v6-e3-core-legacy10 |
| dialogue_test_set | — |
| olap_modes | drill_down,first_turn,roll_up |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 995.9 |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 76.7%
- l hit rate (mechanism): 56.7%
- avg relevancy (legacy): 0.698
- qrels scored turns: 3
- LLM-judge scored turns: 27

#### Turn1 核心指标
- recall_at_10: 0.900
- precision_at_10: 0.380
- faithfulness: 0.200
- answer_relevance: 0.650
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.215
- precision_at_10: 0.160
- anchor_overlap: 0.080
- faithfulness: 0.300
- answer_relevance: 0.395
- context_precision: 0.020

---


## Run 2026-05-31 10:20:49 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 7/10
- turns OK: 27/30 (failed: 3)
- κ hit rate (mechanism): 77.8%
- l hit rate (mechanism): 55.6%
- avg relevancy (legacy): 0.685
- qrels scored turns: 2
- LLM-judge scored turns: 25

#### Turn1 核心指标
- recall_at_10: 0.900
- precision_at_10: 0.360
- faithfulness: 0.200
- answer_relevance: 0.755
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.219
- precision_at_10: 0.190
- anchor_overlap: 0.090
- faithfulness: 0.700
- answer_relevance: 0.285
- context_precision: 0.020

---
## Run 2026-05-31 10:20:49 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.704
- qrels scored turns: 3
- LLM-judge scored turns: 27

#### Turn1 核心指标
- recall_at_10: 0.600
- precision_at_10: 0.260
- faithfulness: 0.300
- answer_relevance: 0.725
- context_precision: 0.100

#### Turn2 核心指标
- recall_at_10: 0.217
- precision_at_10: 0.070
- anchor_overlap: 0.100
- faithfulness: 0.600
- answer_relevance: 0.310
- context_precision: 0.010

---
## Run 2026-05-31 10:20:49 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1662.3 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.900 | 0.600 | 0.300 |
| precision_at_10 | 0.360 | 0.260 | 0.100 |
| faithfulness | 0.200 | 0.300 | -0.100 |
| answer_relevance | 0.755 | 0.725 | 0.030 |
| context_precision | 0.120 | 0.100 | 0.020 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.219 | 0.217 | 0.002 |
| precision_at_10 | 0.190 | 0.070 | 0.120 |
| anchor_overlap | 0.090 | 0.100 | -0.010 |
| faithfulness | 0.700 | 0.600 | 0.100 |
| answer_relevance | 0.285 | 0.310 | -0.025 |
| context_precision | 0.020 | 0.010 | 0.010 |

---


## Run 2026-05-31 10:18:47 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 7/10
- turns OK: 27/30 (failed: 3)
- κ hit rate (mechanism): 77.8%
- l hit rate (mechanism): 55.6%
- avg relevancy (legacy): 0.685
- qrels scored turns: 2
- LLM-judge scored turns: 25

#### Turn1 核心指标
- recall_at_10: 0.900
- precision_at_10: 0.370
- faithfulness: 0.200
- answer_relevance: 0.695
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.253
- precision_at_10: 0.170
- anchor_overlap: 0.100
- faithfulness: 0.700
- answer_relevance: 0.225
- context_precision: 0.010

---
## Run 2026-05-31 10:18:47 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.699
- qrels scored turns: 3
- LLM-judge scored turns: 27

#### Turn1 核心指标
- recall_at_10: 0.600
- precision_at_10: 0.220
- faithfulness: 0.300
- answer_relevance: 0.620
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.117
- precision_at_10: 0.060
- anchor_overlap: 0.110
- faithfulness: 0.600
- answer_relevance: 0.210
- context_precision: 0.010

---
## Run 2026-05-31 10:18:47 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1686.7 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.900 | 0.600 | 0.300 |
| precision_at_10 | 0.370 | 0.220 | 0.150 |
| faithfulness | 0.200 | 0.300 | -0.100 |
| answer_relevance | 0.695 | 0.620 | 0.075 |
| context_precision | 0.120 | 0.120 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.253 | 0.117 | 0.137 |
| precision_at_10 | 0.170 | 0.060 | 0.110 |
| anchor_overlap | 0.100 | 0.110 | -0.010 |
| faithfulness | 0.700 | 0.600 | 0.100 |
| answer_relevance | 0.225 | 0.210 | 0.015 |
| context_precision | 0.010 | 0.010 | 0.000 |

---


## Run 2026-05-31 10:18:24 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 7/10
- turns OK: 27/30 (failed: 3)
- κ hit rate (mechanism): 77.8%
- l hit rate (mechanism): 55.6%
- avg relevancy (legacy): 0.695
- qrels scored turns: 2
- LLM-judge scored turns: 25

#### Turn1 核心指标
- recall_at_10: 0.900
- precision_at_10: 0.360
- faithfulness: 0.200
- answer_relevance: 0.690
- context_precision: 0.140

#### Turn2 核心指标
- recall_at_10: 0.203
- precision_at_10: 0.160
- anchor_overlap: 0.100
- faithfulness: 0.700
- answer_relevance: 0.360
- context_precision: 0.020

---
## Run 2026-05-31 10:18:24 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- test_set: legacy10
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.705
- qrels scored turns: 3
- LLM-judge scored turns: 27

#### Turn1 核心指标
- recall_at_10: 0.600
- precision_at_10: 0.260
- faithfulness: 0.300
- answer_relevance: 0.570
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.133
- precision_at_10: 0.070
- anchor_overlap: 0.110
- faithfulness: 0.300
- answer_relevance: 0.210
- context_precision: 0.020

---
## Run 2026-05-31 10:18:24 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v5-recall-wide-legacy10 |
| dialogue_test_set | legacy10 |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1649.9 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.900 | 0.600 | 0.300 |
| precision_at_10 | 0.360 | 0.260 | 0.100 |
| faithfulness | 0.200 | 0.300 | -0.100 |
| answer_relevance | 0.690 | 0.570 | 0.120 |
| context_precision | 0.140 | 0.120 | 0.020 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.203 | 0.133 | 0.070 |
| precision_at_10 | 0.160 | 0.070 | 0.090 |
| anchor_overlap | 0.100 | 0.110 | -0.010 |
| faithfulness | 0.700 | 0.300 | 0.400 |
| answer_relevance | 0.360 | 0.210 | 0.150 |
| context_precision | 0.020 | 0.020 | 0.000 |

---


## Run 2026-05-31 07:08:25 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 55/66
- turns OK: 177/188 (failed: 11)
- κ hit rate (mechanism): 67.8%
- l hit rate (mechanism): 65.5%
- avg relevancy (legacy): 0.663
- qrels scored turns: 2
- LLM-judge scored turns: 175

#### Turn1 核心指标
- recall_at_10: 0.576
- precision_at_10: 0.242
- faithfulness: 0.227
- answer_relevance: 0.680
- context_precision: 0.098

#### Turn2 核心指标
- recall_at_10: 0.395
- precision_at_10: 0.247
- anchor_overlap: 0.584
- faithfulness: 0.250
- answer_relevance: 0.658
- context_precision: 0.091

---
## Run 2026-05-31 07:08:25 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 66/66
- turns OK: 196/196 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.658
- qrels scored turns: 3
- LLM-judge scored turns: 193

#### Turn1 核心指标
- recall_at_10: 0.439
- precision_at_10: 0.194
- faithfulness: 0.273
- answer_relevance: 0.614
- context_precision: 0.091

#### Turn2 核心指标
- recall_at_10: 0.319
- precision_at_10: 0.182
- anchor_overlap: 0.468
- faithfulness: 0.242
- answer_relevance: 0.627
- context_precision: 0.053

---
## Run 2026-05-31 07:08:25 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 10539.9 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.576 | 0.439 | 0.136 |
| precision_at_10 | 0.242 | 0.194 | 0.048 |
| faithfulness | 0.227 | 0.273 | -0.045 |
| answer_relevance | 0.680 | 0.614 | 0.067 |
| context_precision | 0.098 | 0.091 | 0.008 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.395 | 0.318 | 0.078 |
| precision_at_10 | 0.247 | 0.178 | 0.069 |
| anchor_overlap | 0.584 | 0.481 | 0.103 |
| faithfulness | 0.250 | 0.234 | 0.016 |
| answer_relevance | 0.658 | 0.632 | 0.026 |
| context_precision | 0.091 | 0.045 | 0.045 |

---


## Run 2026-05-31 04:39:24 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 56/66
- turns OK: 179/189 (failed: 10)
- κ hit rate (mechanism): 68.7%
- l hit rate (mechanism): 67.0%
- avg relevancy (legacy): 0.661
- qrels scored turns: 2
- LLM-judge scored turns: 177

#### Turn1 核心指标
- recall_at_10: 0.576
- precision_at_10: 0.245
- faithfulness: 0.227
- answer_relevance: 0.620
- context_precision: 0.115

#### Turn2 核心指标
- recall_at_10: 0.362
- precision_at_10: 0.238
- anchor_overlap: 0.583
- faithfulness: 0.262
- answer_relevance: 0.639
- context_precision: 0.089

---
## Run 2026-05-31 04:39:24 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 66/66
- turns OK: 196/196 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.661
- qrels scored turns: 3
- LLM-judge scored turns: 193

#### Turn1 核心指标
- recall_at_10: 0.455
- precision_at_10: 0.212
- faithfulness: 0.273
- answer_relevance: 0.577
- context_precision: 0.100

#### Turn2 核心指标
- recall_at_10: 0.303
- precision_at_10: 0.180
- anchor_overlap: 0.456
- faithfulness: 0.273
- answer_relevance: 0.573
- context_precision: 0.048

---
## Run 2026-05-31 04:39:24 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-full |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 10334.1 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.576 | 0.455 | 0.121 |
| precision_at_10 | 0.245 | 0.212 | 0.033 |
| faithfulness | 0.227 | 0.273 | -0.045 |
| answer_relevance | 0.620 | 0.577 | 0.042 |
| context_precision | 0.115 | 0.100 | 0.015 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.362 | 0.308 | 0.055 |
| precision_at_10 | 0.238 | 0.183 | 0.055 |
| anchor_overlap | 0.583 | 0.457 | 0.126 |
| faithfulness | 0.262 | 0.277 | -0.015 |
| answer_relevance | 0.639 | 0.582 | 0.058 |
| context_precision | 0.089 | 0.049 | 0.040 |

---


## Run 2026-05-31 04:30:20 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 55/66
- turns OK: 177/188 (failed: 11)
- κ hit rate (mechanism): 68.9%
- l hit rate (mechanism): 66.1%
- avg relevancy (legacy): 0.659
- qrels scored turns: 2
- LLM-judge scored turns: 175

#### Turn1 核心指标
- recall_at_10: 0.561
- precision_at_10: 0.252
- faithfulness: 0.212
- answer_relevance: 0.665
- context_precision: 0.097

#### Turn2 核心指标
- recall_at_10: 0.364
- precision_at_10: 0.237
- anchor_overlap: 0.589
- faithfulness: 0.234
- answer_relevance: 0.676
- context_precision: 0.091

---
## Run 2026-05-31 04:30:20 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 66/66
- turns OK: 196/196 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.659
- qrels scored turns: 3
- LLM-judge scored turns: 193

#### Turn1 核心指标
- recall_at_10: 0.455
- precision_at_10: 0.209
- faithfulness: 0.273
- answer_relevance: 0.616
- context_precision: 0.097

#### Turn2 核心指标
- recall_at_10: 0.294
- precision_at_10: 0.183
- anchor_overlap: 0.474
- faithfulness: 0.182
- answer_relevance: 0.589
- context_precision: 0.053

---
## Run 2026-05-31 04:30:20 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 10315.9 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.561 | 0.455 | 0.106 |
| precision_at_10 | 0.252 | 0.209 | 0.042 |
| faithfulness | 0.212 | 0.273 | -0.061 |
| answer_relevance | 0.665 | 0.616 | 0.049 |
| context_precision | 0.097 | 0.097 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.364 | 0.293 | 0.071 |
| precision_at_10 | 0.237 | 0.183 | 0.055 |
| anchor_overlap | 0.589 | 0.483 | 0.106 |
| faithfulness | 0.234 | 0.188 | 0.047 |
| answer_relevance | 0.676 | 0.592 | 0.084 |
| context_precision | 0.091 | 0.053 | 0.037 |

---


## Run 2026-05-31 06:40:17 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 7/10
- turns OK: 27/30 (failed: 3)
- κ hit rate (mechanism): 77.8%
- l hit rate (mechanism): 55.6%
- avg relevancy (legacy): 0.692
- qrels scored turns: 2
- LLM-judge scored turns: 25

#### Turn1 核心指标
- recall_at_10: 0.900
- precision_at_10: 0.370
- faithfulness: 0.300
- answer_relevance: 0.695
- context_precision: 0.120

#### Turn2 核心指标
- recall_at_10: 0.203
- precision_at_10: 0.130
- anchor_overlap: 0.100
- faithfulness: 0.400
- answer_relevance: 0.385
- context_precision: 0.010

---
## Run 2026-05-31 06:40:17 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-10 |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.711
- qrels scored turns: 3
- LLM-judge scored turns: 27

#### Turn1 核心指标
- recall_at_10: 0.600
- precision_at_10: 0.220
- faithfulness: 0.300
- answer_relevance: 0.710
- context_precision: 0.100

#### Turn2 核心指标
- recall_at_10: 0.133
- precision_at_10: 0.070
- anchor_overlap: 0.110
- faithfulness: 0.500
- answer_relevance: 0.260
- context_precision: 0.010

---
## Run 2026-05-31 06:40:17 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-10 |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1665.4 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.900 | 0.600 | 0.300 |
| precision_at_10 | 0.370 | 0.220 | 0.150 |
| faithfulness | 0.300 | 0.300 | 0.000 |
| answer_relevance | 0.695 | 0.710 | -0.015 |
| context_precision | 0.120 | 0.100 | 0.020 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.203 | 0.133 | 0.070 |
| precision_at_10 | 0.130 | 0.070 | 0.060 |
| anchor_overlap | 0.100 | 0.110 | -0.010 |
| faithfulness | 0.400 | 0.500 | -0.100 |
| answer_relevance | 0.385 | 0.260 | 0.125 |
| context_precision | 0.010 | 0.010 | 0.000 |

---


## Run 2026-05-31 04:19:23 UTC

| 项 | 值 |
|----|-----|
| version | v4-recall-wide-smoke |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 2576.2 |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 7/66
- turns OK: 83/142 (failed: 59)
- κ hit rate (mechanism): 94.0%
- l hit rate (mechanism): 78.3%
- avg relevancy (legacy): 0.666
- qrels scored turns: 1
- LLM-judge scored turns: 82

#### Turn1 核心指标
- recall_at_10: 0.561
- precision_at_10: 0.239
- faithfulness: 0.197
- answer_relevance: 0.634
- context_precision: 0.103

#### Turn2 核心指标
- recall_at_10: 0.185
- precision_at_10: 0.257
- anchor_overlap: 0.364
- faithfulness: 0.214
- answer_relevance: 0.686
- context_precision: 0.136

---


## Run 2026-05-31 04:31:20 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 1/3
- turns OK: 7/9 (failed: 2)
- κ hit rate (mechanism): 85.7%
- l hit rate (mechanism): 71.4%
- avg relevancy (legacy): 0.717
- qrels scored turns: 2
- LLM-judge scored turns: 5

#### Turn1 核心指标
- recall_at_10: 0.667
- precision_at_10: 0.433
- faithfulness: 0.000
- answer_relevance: 0.600
- context_precision: 0.133

#### Turn2 核心指标
- recall_at_10: 0.111
- precision_at_10: 0.133
- anchor_overlap: 0.167
- faithfulness: 0.667
- answer_relevance: 0.100
- context_precision: 0.000

---
## Run 2026-05-31 04:31:20 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 3/3
- turns OK: 9/9 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.735
- qrels scored turns: 3
- LLM-judge scored turns: 6

#### Turn1 核心指标
- recall_at_10: 0.667
- precision_at_10: 0.267
- faithfulness: 0.000
- answer_relevance: 0.933
- context_precision: 0.100

#### Turn2 核心指标
- recall_at_10: 0.222
- precision_at_10: 0.167
- anchor_overlap: 0.167
- faithfulness: 1.000
- answer_relevance: 0.000
- context_precision: 0.033

---
## Run 2026-05-31 04:31:20 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v4-recall-wide |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Route_r + Recall(flat) + Route_olap + G_sub + Rerank(α·search+η·PR+γ·OLAP); Stateless: Route_r + Recall(flat) + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_rank_bias | ✅ |
| recall_module_flat | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 460.9 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.667 | 0.667 | 0.000 |
| precision_at_10 | 0.433 | 0.267 | 0.167 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.600 | 0.933 | -0.333 |
| context_precision | 0.133 | 0.100 | 0.033 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.111 | 0.222 | -0.111 |
| precision_at_10 | 0.133 | 0.167 | -0.033 |
| anchor_overlap | 0.167 | 0.167 | 0.000 |
| faithfulness | 0.667 | 1.000 | -0.333 |
| answer_relevance | 0.100 | 0.000 | 0.100 |
| context_precision | 0.000 | 0.033 | -0.033 |

---


## Run 2026-05-31 00:44:41 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 93.3%
- l hit rate (mechanism): 83.3%
- avg relevancy (legacy): 0.555
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.600
- precision_at_10: 0.210
- faithfulness: 0.180
- answer_relevance: 0.790
- context_precision: 0.165

#### Turn2 核心指标
- recall_at_10: 0.469
- precision_at_10: 0.510
- anchor_overlap: 0.080
- faithfulness: 0.030
- answer_relevance: 0.830
- context_precision: 0.210

---
## Run 2026-05-31 00:44:41 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.536
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.500
- precision_at_10: 0.240
- faithfulness: 0.200
- answer_relevance: 0.655
- context_precision: 0.140

#### Turn2 核心指标
- recall_at_10: 0.764
- precision_at_10: 0.470
- anchor_overlap: 0.150
- faithfulness: 0.000
- answer_relevance: 0.670
- context_precision: 0.140

---
## Run 2026-05-31 00:44:41 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Recall@l + Rerank(α·search+η·PR+γ·OLAP); Stateless: flat Recall + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1699.3 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.600 | 0.500 | 0.100 |
| precision_at_10 | 0.210 | 0.240 | -0.030 |
| faithfulness | 0.180 | 0.200 | -0.020 |
| answer_relevance | 0.790 | 0.655 | 0.135 |
| context_precision | 0.165 | 0.140 | 0.025 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.469 | 0.764 | -0.294 |
| precision_at_10 | 0.510 | 0.470 | 0.040 |
| anchor_overlap | 0.080 | 0.150 | -0.070 |
| faithfulness | 0.030 | 0.000 | 0.030 |
| answer_relevance | 0.830 | 0.670 | 0.160 |
| context_precision | 0.210 | 0.140 | 0.070 |

---


## Run 2026-05-31 00:38:36 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 2/2
- turns OK: 6/6 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 83.3%
- avg relevancy (legacy): 0.567
- qrels scored turns: 0
- LLM-judge scored turns: 6

#### Turn1 核心指标
- recall_at_10: 0.500
- precision_at_10: 0.100
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.125

#### Turn2 核心指标
- recall_at_10: 0.488
- precision_at_10: 0.700
- anchor_overlap: 0.000
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.150

---
## Run 2026-05-31 00:38:36 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 2/2
- turns OK: 6/6 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.565
- qrels scored turns: 0
- LLM-judge scored turns: 6

#### Turn1 核心指标
- recall_at_10: 0.500
- precision_at_10: 0.100
- faithfulness: 0.000
- answer_relevance: 0.500
- context_precision: 0.100

#### Turn2 核心指标
- recall_at_10: 0.597
- precision_at_10: 0.350
- anchor_overlap: 0.100
- faithfulness: 0.450
- answer_relevance: 0.925
- context_precision: 0.150

---
## Run 2026-05-31 00:38:36 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v3-stateless-baseline |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Stateful: Recall@l + Rerank(α·search+η·PR+γ·OLAP); Stateless: flat Recall + Rerank(η·PR only) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 347.7 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.500 | 0.500 | 0.000 |
| precision_at_10 | 0.100 | 0.100 | 0.000 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.950 | 0.500 | 0.450 |
| context_precision | 0.125 | 0.100 | 0.025 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.488 | 0.597 | -0.109 |
| precision_at_10 | 0.700 | 0.350 | 0.350 |
| anchor_overlap | 0.000 | 0.100 | -0.100 |
| faithfulness | 0.000 | 0.450 | -0.450 |
| answer_relevance | 0.950 | 0.925 | 0.025 |
| context_precision | 0.150 | 0.150 | 0.000 |

---


## Run 2026-05-30 13:48:12 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 90.0%
- l hit rate (mechanism): 83.3%
- avg relevancy (legacy): 0.550
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.700
- precision_at_10: 0.250
- faithfulness: 0.100
- answer_relevance: 0.840
- context_precision: 0.170

#### Turn2 核心指标
- recall_at_10: 0.474
- precision_at_10: 0.420
- anchor_overlap: 0.020
- faithfulness: 0.100
- answer_relevance: 0.800
- context_precision: 0.220

---
## Run 2026-05-30 13:48:12 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap-full |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 33.3%
- l hit rate (mechanism): 86.7%
- avg relevancy (legacy): 0.561
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.700
- precision_at_10: 0.250
- faithfulness: 0.100
- answer_relevance: 0.845
- context_precision: 0.170

#### Turn2 核心指标
- recall_at_10: 0.602
- precision_at_10: 0.620
- anchor_overlap: 0.000
- faithfulness: 0.115
- answer_relevance: 0.785
- context_precision: 0.227

---
## Run 2026-05-30 13:48:12 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap-full |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Recall50→Rerank10; α·search+η·PR+γ·OLAP; qrels/LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1677.9 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.700 | 0.700 | 0.000 |
| precision_at_10 | 0.250 | 0.250 | 0.000 |
| faithfulness | 0.100 | 0.100 | 0.000 |
| answer_relevance | 0.840 | 0.845 | -0.005 |
| context_precision | 0.170 | 0.170 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.474 | 0.602 | -0.128 |
| precision_at_10 | 0.420 | 0.620 | -0.200 |
| anchor_overlap | 0.020 | 0.000 | 0.020 |
| faithfulness | 0.100 | 0.115 | -0.015 |
| answer_relevance | 0.800 | 0.785 | 0.015 |
| context_precision | 0.220 | 0.227 | -0.007 |

---


## Run 2026-05-30 13:42:16 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 2/2
- turns OK: 6/6 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 83.3%
- avg relevancy (legacy): 0.536
- qrels scored turns: 0
- LLM-judge scored turns: 6

#### Turn1 核心指标
- recall_at_10: 0.500
- precision_at_10: 0.100
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.125

#### Turn2 核心指标
- recall_at_10: 0.478
- precision_at_10: 0.650
- anchor_overlap: 0.000
- faithfulness: 0.000
- answer_relevance: 0.900
- context_precision: 0.100

---
## Run 2026-05-30 13:42:16 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 2/2
- turns OK: 6/6 (failed: 0)
- κ hit rate (mechanism): 33.3%
- l hit rate (mechanism): 83.3%
- avg relevancy (legacy): 0.550
- qrels scored turns: 0
- LLM-judge scored turns: 6

#### Turn1 核心指标
- recall_at_10: 0.500
- precision_at_10: 0.100
- faithfulness: 0.000
- answer_relevance: 0.925
- context_precision: 0.125

#### Turn2 核心指标
- recall_at_10: 0.563
- precision_at_10: 0.650
- anchor_overlap: 0.000
- faithfulness: 0.000
- answer_relevance: 0.875
- context_precision: 0.100

---
## Run 2026-05-30 13:42:16 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v3-recall-rerank-olap |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | Recall50→Rerank10; α·search+η·PR+γ·OLAP; qrels/LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 344.3 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.500 | 0.500 | 0.000 |
| precision_at_10 | 0.100 | 0.100 | 0.000 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.950 | 0.925 | 0.025 |
| context_precision | 0.125 | 0.125 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.478 | 0.563 | -0.085 |
| precision_at_10 | 0.650 | 0.650 | 0.000 |
| anchor_overlap | 0.000 | 0.000 | 0.000 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.900 | 0.875 | 0.025 |
| context_precision | 0.100 | 0.100 | 0.000 |

---


## Run 2026-05-28 13:35:35 UTC [full arm]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-ablation |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 8/10
- turns OK: 26/28 (failed: 2)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.561
- qrels scored turns: 0
- LLM-judge scored turns: 26

#### Turn1 核心指标
- recall_at_10: 0.493
- precision_at_10: 0.220
- faithfulness: 0.200
- answer_relevance: 0.895
- context_precision: 0.198

#### Turn2 核心指标
- recall_at_10: 0.171
- precision_at_10: 0.612
- anchor_overlap: 0.000
- faithfulness: 0.125
- answer_relevance: 0.712
- context_precision: 0.175

---
## Run 2026-05-28 13:35:35 UTC [no_hierarchy arm]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-ablation |
| PIPELINE_VARIANT | `no_hierarchy` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ❌ |
| kappa_routing | ❌ |
| gsub_constraint | ❌ |
| path_level_navigation | ❌ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.563
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.593
- precision_at_10: 0.240
- faithfulness: 0.280
- answer_relevance: 0.870
- context_precision: 0.188

#### Turn2 核心指标
- recall_at_10: 0.562
- precision_at_10: 0.340
- anchor_overlap: 0.305
- faithfulness: 0.100
- answer_relevance: 0.740
- context_precision: 0.189

---
## Run 2026-05-28 13:35:35 UTC

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-ablation |
| PIPELINE_VARIANT | `ablation (full vs no_hierarchy)` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1783.5 |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 8/10
- turns OK: 26/28 (failed: 2)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.561
- qrels scored turns: 0
- LLM-judge scored turns: 26

#### Turn1 核心指标
- recall_at_10: 0.493
- precision_at_10: 0.220
- faithfulness: 0.200
- answer_relevance: 0.895
- context_precision: 0.198

#### Turn2 核心指标
- recall_at_10: 0.171
- precision_at_10: 0.612
- anchor_overlap: 0.000
- faithfulness: 0.125
- answer_relevance: 0.712
- context_precision: 0.175

### Multidim Ablation (full vs no_hierarchy, Stateful Turn2+)
| metric | full | no_hierarchy | Δ |
|--------|------|--------------|---|
| Turn2 recall@10 | 0.171 | 0.562 | -0.392 |
| Turn2 precision@10 | 0.612 | 0.340 | +0.272 |
| Turn2 anchor_overlap | 0.000 | 0.305 | -0.305 |
| Turn2 faithfulness | 0.125 | 0.100 | +0.025 |
| Turn2 answer_relevance | 0.712 | 0.740 | -0.028 |
| Turn2 context_precision | 0.175 | 0.189 | -0.014 |
| Turn2+ recall@10 | 0.346 | 0.465 | -0.119 |
| Turn2+ precision@10 | 0.519 | 0.320 | +0.199 |
| κ hit rate (mechanism) | 1.000 | 1.000 | +0.0% |
| l hit rate (mechanism) | 1.000 | 1.000 | +0.0% |
| avg relevancy (legacy) | 0.561 | 0.563 | -0.002 |
| turns failed | 2 | 0 | 2 |

---


## Run 2026-05-28 12:57:22 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-olap |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 8/10
- turns OK: 26/28 (failed: 2)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.560
- qrels scored turns: 0
- LLM-judge scored turns: 26

#### Turn1 核心指标
- recall_at_10: 0.593
- precision_at_10: 0.260
- faithfulness: 0.200
- answer_relevance: 0.880
- context_precision: 0.188

#### Turn2 核心指标
- recall_at_10: 0.171
- precision_at_10: 0.612
- anchor_overlap: 0.000
- faithfulness: 0.125
- answer_relevance: 0.731
- context_precision: 0.287

---
## Run 2026-05-28 12:57:22 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-olap |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate (mechanism): 33.3%
- l hit rate (mechanism): 66.7%
- avg relevancy (legacy): 0.566
- qrels scored turns: 0
- LLM-judge scored turns: 30

#### Turn1 核心指标
- recall_at_10: 0.593
- precision_at_10: 0.260
- faithfulness: 0.100
- answer_relevance: 0.865
- context_precision: 0.188

#### Turn2 核心指标
- recall_at_10: 0.614
- precision_at_10: 0.320
- anchor_overlap: 0.280
- faithfulness: 0.100
- answer_relevance: 0.820
- context_precision: 0.156

---
## Run 2026-05-28 12:57:22 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-olap |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | qrels优先 / 无则 LLM judge (recall=proxy) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 2292.4 |
| exit | failed |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.593 | 0.593 | 0.000 |
| precision_at_10 | 0.260 | 0.260 | 0.000 |
| faithfulness | 0.200 | 0.100 | 0.100 |
| answer_relevance | 0.880 | 0.865 | 0.015 |
| context_precision | 0.188 | 0.188 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.171 | 0.674 | -0.503 |
| precision_at_10 | 0.612 | 0.363 | 0.250 |
| anchor_overlap | 0.000 | 0.319 | -0.319 |
| faithfulness | 0.125 | 0.000 | 0.125 |
| answer_relevance | 0.731 | 0.787 | -0.056 |
| context_precision | 0.287 | 0.153 | 0.134 |

---


## Run 2026-05-28 12:53:25 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-1sc |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 1/1
- turns OK: 3/3 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.599
- qrels scored turns: 0
- LLM-judge scored turns: 3

#### Turn1 核心指标
- recall_at_10: 0.000
- precision_at_10: 0.000
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.000

#### Turn2 核心指标
- recall_at_10: 0.163
- precision_at_10: 0.700
- anchor_overlap: 0.000
- faithfulness: 0.000
- answer_relevance: 0.850
- context_precision: 0.000

---
## Run 2026-05-28 12:53:25 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-1sc |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 1/1
- turns OK: 3/3 (failed: 0)
- κ hit rate (mechanism): 33.3%
- l hit rate (mechanism): 66.7%
- avg relevancy (legacy): 0.581
- qrels scored turns: 0
- LLM-judge scored turns: 3

#### Turn1 核心指标
- recall_at_10: 0.000
- precision_at_10: 0.000
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.000

#### Turn2 核心指标
- recall_at_10: 0.091
- precision_at_10: 0.200
- anchor_overlap: 0.050
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.000

---
## Run 2026-05-28 12:53:25 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-1sc |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | qrels优先 / 无则 LLM judge (recall=proxy) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 222.6 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.000 | 0.000 | 0.000 |
| precision_at_10 | 0.000 | 0.000 | 0.000 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.950 | 0.950 | 0.000 |
| context_precision | 0.000 | 0.000 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.163 | 0.091 | 0.072 |
| precision_at_10 | 0.700 | 0.200 | 0.500 |
| anchor_overlap | 0.000 | 0.050 | -0.050 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.850 | 0.950 | -0.100 |
| context_precision | 0.000 | 0.000 | 0.000 |

---


## Run 2026-05-28 12:49:52 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-smoke |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 1/1
- turns OK: 3/3 (failed: 0)
- κ hit rate (mechanism): 100.0%
- l hit rate (mechanism): 100.0%
- avg relevancy (legacy): 0.623
- qrels scored turns: 0
- LLM-judge scored turns: 3

#### Turn1 核心指标
- recall_at_10: 0.000
- precision_at_10: 0.000
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.000

#### Turn2 核心指标
- recall_at_10: 0.163
- precision_at_10: 0.700
- anchor_overlap: 0.000
- faithfulness: 0.000
- answer_relevance: 0.900
- context_precision: 0.000

---
## Run 2026-05-28 12:49:52 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-smoke |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 1/1
- turns OK: 3/3 (failed: 0)
- κ hit rate (mechanism): 33.3%
- l hit rate (mechanism): 66.7%
- avg relevancy (legacy): 0.574
- qrels scored turns: 0
- LLM-judge scored turns: 3

#### Turn1 核心指标
- recall_at_10: 0.000
- precision_at_10: 0.000
- faithfulness: 0.000
- answer_relevance: 0.900
- context_precision: 0.000

#### Turn2 核心指标
- recall_at_10: 0.091
- precision_at_10: 0.200
- anchor_overlap: 0.050
- faithfulness: 0.000
- answer_relevance: 0.950
- context_precision: 0.000

---
## Run 2026-05-28 12:49:52 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-metrics-smoke |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | qrels优先 / 无则 LLM judge (recall=proxy) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 252.7 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.000 | 0.000 | 0.000 |
| precision_at_10 | 0.000 | 0.000 | 0.000 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.950 | 0.900 | 0.050 |
| context_precision | 0.000 | 0.000 | 0.000 |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | 0.163 | 0.091 | 0.072 |
| precision_at_10 | 0.700 | 0.200 | 0.500 |
| anchor_overlap | 0.000 | 0.050 | -0.050 |
| faithfulness | 0.000 | 0.000 | 0.000 |
| answer_relevance | 0.900 | 0.950 | -0.050 |
| context_precision | 0.000 | 0.000 | 0.000 |

---


## Run 2026-05-28 12:38:28 UTC [preflight failed]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-preflight |
| exit | failed |

### 错误

```
评估前置检查失败:
  - Neo4j 数据库为空（0 节点）。请先导入 KG 并运行 MetaPath 构建 pipeline。
  - MetaPath 数量不足: 0 < 1。请运行 1_2_1_2pagerankMetapath.ipynb 或 utilities/run_metapath_pipeline.py。
  - 带 embedding 的 MetaPath 不足: 0。请运行 F3 embedding + 索引创建。
  - 缺少向量索引 metapath_embedding_index。HybridRetriever 无法运行。
  - 缺少全文索引 metapath_fulltext_index。HybridRetriever 无法运行。
```

---


## Run 2026-05-28 12:34:11 UTC [stateful]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-smoke-1scenario |
| PIPELINE_VARIANT | `full` |
| session_mode | stateful |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 0/1
- turns OK: 0/1 (failed: 1)
- κ hit rate (mechanism): 0.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.000
- qrels scored turns: 0
- LLM-judge scored turns: 0

#### Turn1 核心指标
- (无)

#### Turn2 核心指标
- (无)

---
## Run 2026-05-28 12:34:11 UTC [stateless]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-smoke-1scenario |
| PIPELINE_VARIANT | `full` |
| session_mode | stateless |
| retrieval_scoring | qrels优先 / 无则 LLM judge |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 0/1
- turns OK: 0/1 (failed: 1)
- κ hit rate (mechanism): 0.0%
- l hit rate (mechanism): 0.0%
- avg relevancy (legacy): 0.000
- qrels scored turns: 0
- LLM-judge scored turns: 0

#### Turn1 核心指标
- (无)

#### Turn2 核心指标
- (无)

---
## Run 2026-05-28 12:34:11 UTC [olap compare]

| 项 | 值 |
|----|-----|
| version | v2.0-olap-smoke-1scenario |
| PIPELINE_VARIANT | `full (Stateful vs Stateless)` |
| session_mode | paired |
| retrieval_scoring | qrels优先 / 无则 LLM judge (recall=proxy) |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 41.4 |
| exit | success |

### Turn1 Sanity (Stateful − Stateless, 应 ≈ 0)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | — | — | — |
| precision_at_10 | — | — | — |
| faithfulness | — | — | — |
| answer_relevance | — | — | — |
| context_precision | — | — | — |

### Turn2 Core Δ (Stateful − Stateless, 主结论)
| metric | Stateful | Stateless | Δ |
|--------|----------|-----------|---|
| recall_at_10 | — | — | — |
| precision_at_10 | — | — | — |
| anchor_overlap | — | — | — |
| faithfulness | — | — | — |
| answer_relevance | — | — | — |
| context_precision | — | — | — |

---


## Run 2026-05-27 03:13:31 UTC [full arm]

| 项 | 值 |
|----|-----|
| version | v1.0-ablation-dialogue |
| PIPELINE_VARIANT | `full` |
| multi_dim_retrieval | ✅ |
| kappa_routing | ✅ |
| gsub_constraint | ✅ |
| path_level_navigation | ✅ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate: 100.0%
- l hit rate: 100.0%
- avg relevancy (all turns): 0.557
- avg relevancy (turn≥2): 0.525

---
## Run 2026-05-27 03:13:31 UTC [no_hierarchy arm]

| 项 | 值 |
|----|-----|
| version | v1.0-ablation-dialogue |
| PIPELINE_VARIANT | `no_hierarchy` |
| multi_dim_retrieval | ❌ |
| kappa_routing | ❌ |
| gsub_constraint | ❌ |
| path_level_navigation | ❌ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | — |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate: 100.0%
- l hit rate: 100.0%
- avg relevancy (all turns): 0.561
- avg relevancy (turn≥2): 0.528

---
## Run 2026-05-27 03:13:31 UTC

| 项 | 值 |
|----|-----|
| version | v1.0-ablation-dialogue |
| PIPELINE_VARIANT | `ablation` |
| multi_dim_retrieval | ❌ |
| kappa_routing | ❌ |
| gsub_constraint | ❌ |
| path_level_navigation | ❌ |
| python | C:\Users\tom\.conda\envs\tomluck2\python.exe |
| duration_sec | 1317.8 |
| exit | success |

### 多轮对话 (dialogue_test_cases.json)
- scenarios completed: 10/10
- turns OK: 30/30 (failed: 0)
- κ hit rate: 100.0%
- l hit rate: 100.0%
- avg relevancy (all turns): 0.557
- avg relevancy (turn≥2): 0.525

### Ablation 对比 (full vs no_hierarchy)
| metric | full | no_hierarchy | Δ |
|--------|------|--------------|---|
| κ hit rate | 100.0% | 100.0% | +0.0% |
| l hit rate | 100.0% | 100.0% | +0.0% |
| avg relevancy (all) | 0.557 | 0.561 | -0.004 |
| avg relevancy (turn≥2) | 0.525 | 0.528 | -0.003 |
| turns failed | 0 | 0 | 0 |

---

