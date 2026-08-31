# EBM+EEM (MPU=0) Pilot report

- Generated (UTC): `2026-08-14T00:24:02.003750+00:00`
- Script: `utilities/export_ebm_only_pilot.py`
- random_seed: `20260813`
- Filter: `EBM_num > 0 AND EEM_num > 0 AND MPU_num = 0`

## Schema probe

- Chunk keys: `EBM_num`, `EEM_num`, `MPU_num`, `dc_author`, `dc_creator`, `dc_publisher`, `dc_title`, `dcterms_identifier`, `dcterms_issued`, `embedding`, `filename`, `from_section`, `header_path`, `index`, `processed_at`, `section_role`, `source_doc`, `text`
- Required keys present: **yes**

## Counts

- Chunk total: **195**
- EBM_num > 0: **39**
- EBM+EEM (MPU=0) candidates: **18**
- Pilot sample size: **12**
- Distinct documents in sample: **3**

## Among EBM_num > 0 (context)

- EBM only (EEM=0, MPU=0): **0**
- EBM+EEM (MPU=0): **18**
- EBM+MPU (EEM=0): **0**
- EBM+EEM+MPU: **21**

## Candidate EBM_num / EEM_num stats

- EBM_num min/max/mean/median: **1** / **74** / **10.56** / **3.5**
- EEM_num min/max/mean/median: **1** / **83** / **11.39** / **3.5**

| EBM_num | count |
|--------:|------:|
| 1 | 3 |
| 2 | 2 |
| 3 | 4 |
| 4 | 4 |
| 6 | 1 |
| 15 | 1 |
| 23 | 1 |
| 37 | 1 |
| 74 | 1 |

## Sample by document

| document_id | n |
|-------------|--:|
| `doc_02_Characterization of mercury species in brown and white rice` | 5 |
| `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | 4 |
| `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China` | 3 |

## Pilot sample summary

| chunk_id | document_id | section | EBM_num | EEM_num | MPU_num | text_length |
| -------- | ----------- | ------- | ------: | ------: | ------: | ----------: |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:9889` | `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | Methods_Materials | 1 | 1 | 0 | 3999 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:9014` | `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | Other | 23 | 32 | 0 | 3994 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:9890` | `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | Other | 4 | 4 | 0 | 4000 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:9891` | `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market` | Results | 2 | 2 | 0 | 4000 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14118` | `doc_02_Characterization of mercury species in brown and white rice` | Results | 1 | 1 | 0 | 4000 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:13323` | `doc_02_Characterization of mercury species in brown and white rice` | Introduction | 74 | 83 | 0 | 3996 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:13601` | `doc_02_Characterization of mercury species in brown and white rice` | Methods_Materials | 15 | 12 | 0 | 1338 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14122` | `doc_02_Characterization of mercury species in brown and white rice` | Results | 1 | 1 | 0 | 4000 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:14124` | `doc_02_Characterization of mercury species in brown and white rice` | Results | 3 | 3 | 0 | 792 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:16970` | `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China` | Results | 3 | 3 | 0 | 3994 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:16752` | `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China` | Methods_Materials | 37 | 37 | 0 | 2110 |
| `4:a588b8f8-4a1b-4a79-8a1a-924958fc2820:16971` | `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China` | Methods_Materials | 3 | 3 | 0 | 4000 |

## QC

- Duplicate chunk_id in candidates: **0**
- Duplicate chunk_id in sample: **0**
- Empty text in candidates: **0**
- Exact-duplicate texts in candidates (distinct texts with count>1): **0**
- Sample rows violating EBM+EEM (MPU=0) filter: **0**
- CSV sample chunk_ids == LS task chunk_ids: **True**

## Confirmations

1. Neo4j was **not** modified (read-only).
2. All Pilot samples satisfy `EBM_num > 0 AND EEM_num > 0 AND MPU_num = 0` (violations=0).
3. Label Studio tasks contain Chunk attributes only — **no** Entity/Relation/MetaPath pre-annotations.
4. `text` is unchanged from Neo4j `Chunk.text`.
5. Sample CSV and Label Studio JSON use the same ordered `chunk_id` list.
6. Reproducible via `RANDOM_SEED=20260813` in `utilities/export_ebm_only_pilot.py`.

This EBM+EEM (MPU=0) filter is for Pilot / Label Studio process testing only — **not** the final Gold Standard sampling policy.
