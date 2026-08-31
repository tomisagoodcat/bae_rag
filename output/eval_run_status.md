# Retrieval Evaluation Run Status

Date: 2026-05-24

## Completed

### Test module updates
- `utilities/test_evaluation.py`: shared loader, **single invoke per case**, route hit_any/hit_all
- CSV path: `data/questions.csv` via `resolve_questions_csv()` (no PaperExtract hardcode)
- `data/dialogue_test_cases.json`: multi-turn scenarios
- Notebook: Faithfulness / Relevancy / Precision / 综合测试 updated
- Relevancy fixed: uses `make_initial_state()` via `run_single_case()`

### Neo4j smoke (passed)
```
python utilities/run_neo4j_gsub_smoke.py
anchor mid: MPU_MID_00001
drill_down N_l: 11 low paths
G_sub drill_down: 11 ids
questions.csv: 10 cases
```

## Blocked: full Pipeline + LLM eval

`utilities/run_retrieval_eval.py` failed at Cell 11 (SentenceTransformer / PyTorch):

```
OSError: WinError 1114 loading torch c10.dll
```

Cause: `pipelineD_env` on OneDrive path; tomLuck2 conda not available in CLI.

## Run in Notebook (tomluck2 kernel)

1. G Cell 0 → G Cell 7 (Pipeline)
2. G Cell 8 多轮对话测试 (optional)
3. 综合测试 → **详细测试** or **简短测试**

Or with working Python env:

```bash
python utilities/run_retrieval_eval.py
```

Neo4j-only:

```bash
python utilities/run_retrieval_eval.py --neo4j-only
```
