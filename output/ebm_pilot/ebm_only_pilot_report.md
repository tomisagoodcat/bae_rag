# EBM-only Pilot report

- Generated (UTC): `2026-08-13T15:03:32.410558+00:00`
- Script: `utilities/export_ebm_only_pilot.py`
- random_seed: `20260813`
- Filter: `EBM_num > 0 AND EEM_num = 0 AND MPU_num = 0`

## Schema probe

- Chunk keys: `EBM_num`, `EEM_num`, `MPU_num`, `dc_author`, `dc_creator`, `dc_publisher`, `dc_title`, `dcterms_identifier`, `dcterms_issued`, `embedding`, `filename`, `from_section`, `header_path`, `index`, `processed_at`, `section_role`, `source_doc`, `text`
- Required keys present: **yes**

## Counts

- Chunk total: **195**
- EBM_num > 0: **39**
- EBM-only candidates: **0**
- Pilot sample size: **0** (all candidates; fewer than 12)
- Distinct documents in sample: **0**

## Why EBM-only may be empty

Among chunks with `EBM_num > 0`, co-occurrence with EEM/MPU:

- EBM only (EEM=0, MPU=0): **0**
- EBM+EEM (MPU=0): **18**
- EBM+MPU (EEM=0): **0**
- EBM+EEM+MPU: **21**

If EBM-only count is 0, Label Studio cannot be piloted with this strict filter until the count definition or filter policy is relaxed (out of scope for this export).

## Candidate EBM_num stats

- (no candidates)

## Sample by document

| document_id | n |
|-------------|--:|

## Pilot sample summary

| chunk_id | document_id | section | EBM_num | EEM_num | MPU_num | text_length |
| -------- | ----------- | ------- | ------: | ------: | ------: | ----------: |

## QC

- Duplicate chunk_id in candidates: **0**
- Duplicate chunk_id in sample: **0**
- Empty text in candidates: **0**
- Exact-duplicate texts in candidates (distinct texts with count>1): **0**
- Sample rows violating EBM-only filter: **0**
- CSV sample chunk_ids == LS task chunk_ids: **True**

## Confirmations

1. Neo4j was **not** modified (read-only).
2. All Pilot samples satisfy `EBM_num>0 AND EEM_num=0 AND MPU_num=0` (violations=0).
3. Label Studio tasks contain Chunk attributes only — **no** Entity/Relation/MetaPath pre-annotations.
4. `text` is unchanged from Neo4j `Chunk.text`.
5. Sample CSV and Label Studio JSON use the same ordered `chunk_id` list.
6. Reproducible via `RANDOM_SEED=20260813` in `utilities/export_ebm_only_pilot.py`.

This EBM-only filter is for Pilot / Label Studio process testing only — **not** the final Gold Standard sampling policy.
