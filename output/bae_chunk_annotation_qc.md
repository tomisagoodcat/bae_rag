# BAE Chunk Annotation Pool — QC

- Generated (UTC): `2026-08-10T02:25:27.155919+00:00`
- Chunk total: **195**
- Distinct document_id (`source_doc`): **3**
- chunk_id unique: **True** (195/195)
- Empty text: **0**
- text_length min/median/max: **446** / **3998** / **4000**
- Chunks with n_entities_linked=0 (kept in pool): **28**
- source_doc+index collision groups: **36** (reason chunk_id uses elementId)

## Documents

- `doc_01_Dietary intake of minerals and trace elements in rice on the Jamaican market`: 97
- `doc_02_Characterization of mercury species in brown and white rice`: 55
- `doc_03_Rice consumption contributes to low level methylmercury exposure in southern China`: 43

## Section distribution (`from_section`)

- `Discussion`: 80
- `Results`: 38
- `Methods_Materials`: 29
- `Introduction`: 23
- `Other`: 13
- `References`: 10
- `Abstract`: 2

## Notes

- Label Studio tasks contain only: chunk_id, document_id, section, text.
- `mp_subgraphs` / entity counts are diagnostic only; pool was not filtered by them.
- No `bae_role` / start_offset / end_offset properties exist on Chunk in this DB.
