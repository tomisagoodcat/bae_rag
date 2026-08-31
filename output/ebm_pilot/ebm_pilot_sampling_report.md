# EBM Pilot sampling report

- Generated (UTC): `2026-08-13T14:41:17.602963+00:00`
- Script: `utilities/export_ebm_pilot_sample.py`
- random_seed: `20260813`

## Schema probe

- Chunk property keys: `EBM_num`, `EEM_num`, `MPU_num`, `dc_author`, `dc_creator`, `dc_publisher`, `dc_title`, `dcterms_identifier`, `dcterms_issued`, `embedding`, `filename`, `from_section`, `header_path`, `index`, `processed_at`, `section_role`, `source_doc`, `text`
- Required keys present: **yes**

## Pool sizes

- Original Chunk total: **195**
- EBM_num > 0: **39**
- Excluded non-body Chunks: **0**
- Final candidates: **39**
- Pilot sample size: **12**
- Distinct documents in sample: **3**

### Exclusion reasons

- (none)

## Candidate EBM_num distribution

| EBM_num | count |
|--------:|------:|
| 1 | 4 |
| 2 | 4 |
| 3 | 5 |
| 4 | 6 |
| 5 | 1 |
| 6 | 5 |
| 7 | 2 |
| 8 | 1 |
| 9 | 1 |
| 10 | 1 |
| 14 | 1 |
| 15 | 1 |
| 23 | 1 |
| 37 | 1 |
| 39 | 1 |
| 65 | 1 |
| 74 | 1 |
| 91 | 1 |
| 110 | 1 |

## Stratified quotas vs selected

| bucket | quota | available | selected | shortfall |
|--------|------:|----------:|---------:|----------:|
| 1-2 | 3 | 8 | 3 | 0 |
| 3-10 | 6 | 22 | 6 | 0 |
| 11-30 | 2 | 3 | 2 | 0 |
| >30 | 1 | 6 | 1 | 0 |

## Sample by document

| document_id | n_selected |
|-------------|-----------:|
| `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | 4 |
| `doc_02_Characterization of mercury species in brown and white rice` | 4 |
| `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China` | 4 |

## Sample rows (ids)

- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:9889` | EBM=1 | `Methods_Materials` | `doc_01_Dietary intake of minerals and trace elements in rice`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14121` | EBM=2 | `Results` | `doc_02_Characterization of mercury species in brown and whit`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:17155` | EBM=1 | `Introduction` | `doc_03_Rice consumption contributes to low level methylmercu`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:10188` | EBM=3 | `Discussion` | `doc_01_Dietary intake of minerals and trace elements in rice`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:10191` | EBM=6 | `Discussion` | `doc_01_Dietary intake of minerals and trace elements in rice`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14120` | EBM=3 | `Introduction` | `doc_02_Characterization of mercury species in brown and whit`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14378` | EBM=6 | `Discussion` | `doc_02_Characterization of mercury species in brown and whit`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:17154` | EBM=6 | `Results` | `doc_03_Rice consumption contributes to low level methylmercu`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:17160` | EBM=4 | `Discussion` | `doc_03_Rice consumption contributes to low level methylmercu`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:10192` | EBM=14 | `Discussion` | `doc_01_Dietary intake of minerals and trace elements in rice`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:13601` | EBM=15 | `Methods_Materials` | `doc_02_Characterization of mercury species in brown and whit`
- `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:16752` | EBM=37 | `Methods_Materials` | `doc_03_Rice consumption contributes to low level methylmercu`

## QC

- Duplicate chunk_id in candidates: **0**
- Duplicate chunk_id in sample: **0**
- Empty text in candidates: **0**
- Texts with exact duplicates (count of texts appearing >1): **0**

## Confirmations

1. Neo4j was **not** modified (read-only queries only).
2. Label Studio tasks contain only `chunk_id`, `document_id`, `section`, `text` (no E*_num, entities, relations, MetaPath, or pre-annotations).
3. `text` is copied unchanged from Neo4j `Chunk.text` (no rewrite/summary/clean).
4. Sampling is fully reproducible via `RANDOM_SEED=20260813` in `utilities/export_ebm_pilot_sample.py`.
