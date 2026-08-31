# EBM Pilot — EBM_num distribution

- Generated (UTC): `2026-08-13T13:53:31.983356+00:00`
- Method: Chunk.EBM_num (initial co-chunk triples with both ends in subgraph_mapping.EBM)
- Entity/relation inventories use label∈mappings.EBM (NOT n.subgraph property)
- Nodes with property `subgraph` (by label): [{'label': '__KGBuilder__', 'n': 4987}, {'label': '__Entity__', 'n': 4987}, {'label': 'MetaPath', 'n': 2007}, {'label': 'mp_References', 'n': 1850}, {'label': 'mp_Statement', 'n': 1436}, {'label': 'mp_Claim', 'n': 850}, {'label': 'mp_Attribution', 'n': 595}, {'label': 'whu_Computational_Experiment', 'n': 74}, {'label': 'whu_EnvironmentFeature', 'n': 66}, {'label': 'whu_Bio_chemical_Experiment', 'n': 40}, {'label': 'whu_Target_analyte', 'n': 36}, {'label': 'whu_SpecimenPreprocessing', 'n': 21}, {'label': 'whu_SpecimenCollection', 'n': 19}]
- Chunk keys include EBM_num: True
- Chunks total / EBM_num>0: 195 / 39

## Exact EBM_num histogram

| EBM_num | chunk_count |
|--------:|------------:|
| 0 | 156 |
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

## Buckets (no sampling decision)

| bucket | chunk_count |
|--------|------------:|
| 0 | 156 |
| 1-2 | 8 |
| 3-10 | 22 |
| 11-30 | 3 |
| >30 | 6 |
| null/-1 | 0 |

## Relation filter diagnostics

- Edges with **both** ends EBM-mapped: **595**
- Edges with **exactly one** end EBM-mapped (bridge, not in inventory): **498**

## Outputs

- `ebm_entity_inventory.csv`: 15 entity types
- `ebm_relation_inventory.csv`: 33 (rel_type, src, tgt) rows
- `ebm_pilot_chunk_candidates.csv`: 39 pilot candidate chunks
- `ebm_pilot_chunk_tasks.json`: Label Studio tasks (no E*_num)

No Gold rules / legal ER→Rel→ER combinations generated.
Neo4j was not modified.
