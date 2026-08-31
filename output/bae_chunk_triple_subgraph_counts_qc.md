# Chunk initial-triple subgraph counts — QC

- Generated (UTC): `2026-08-13T13:37:20.643787+00:00`
- Rule: co-chunk directed domain edges; subgraph via subgraph_mapping (both ends).
- MetaPath excluded from counts.
- Chunks: **195**
- Chunks with triple_total=0: **54**
- Chunks with EBM+EEM+MPU=0: **54**

## Counts (initial triples)

- EBM_num: sum=595 avg=3.05 max=110 median=0
- EEM_num: sum=836 avg=4.29 max=91 median=0
- MPU_num: sum=1434 avg=7.35 max=58 median=2
- triple_total (any domain edge): sum=2171 avg=11.13 max=124 median=3
- unassigned triples (no SG match): **8**

## Contrast: MetaPath-based counts (diagnostic only)

- sum MetaPath EBM/EEM/MPU: **380** / **309** / **1338**
- Chunks with no MetaPath: **54**
- Expect these totals to differ from triple-based E*_num (different unit).

## Top relation types (counted edges)

- `mp_supports`: 743
- `cito_isCitedBy`: 390
- `whu_hasPart`: 252
- `whu_declareUsed`: 172
- `dcterms_hasPart`: 104
- `p_plan_isStepOfPlan`: 79
- `iao_is_about`: 79
- `p_plan_hasOutputVar`: 73
- `prov_wasDerivedFrom`: 64
- `p_plan_isPrecededBy`: 57
- `mp_challenges`: 49
- `p_plan_hasInputVar`: 44
- `whu_fellow`: 26
- `whu_hasContext`: 16
- `whu_hasGoal`: 12
- `whu_atLocation`: 7
- `whu_target`: 4
