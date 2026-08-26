# Stage notes (from original notebooks)

## build_kg (1_2_0_2 module3)

- Schema-guided extraction: iterates `potential_schema.json` triples.
- Uses `SimpleKGPipeline` per triple with section filtering via `section_role`.
- Prompt template: `kg_build_pipeline/prompts/custom_prompt.md` (v5 labels; `{schema}` / `{text}` / `{examples}`). Parent-repo `custom_prompt.md` is legacy only.
- After semantic split, `table3_section_bae.json` assigns prior `bae_roles` on memory nodes.
- Post-extract per doc: Chunk backfill (`section_role`, `bae_roles`, `header_path`) then `update_metadata_batch` + `enhance_relations`.

## subgraph_annotate (module4)

- Reads `subgraph_mapping.json`; writes `subgraphs` / `subgraph` on entity nodes.
- Strict validation: all ontology labels must appear in mapping.

## chunk_merge (module5)

- Merges duplicate `Chunk` nodes **within the same filename** only.

## entity_merge (1_2_1_1 minimal)

- Exact match on `WHU_HASNAME` via neo4j_graphrag resolver.
- Optional WCC + `AttributionMaster` / `HAS_REFERENCE` for `mp_Attribution`.
- Embedding-based merge **not** included in v1.

## pagerank (1_2_1_2 E segment)

- GDS projections per MPU/EEM/EBM subgraph.
- Writes `{mpu,eem,ebm}_pagerank` used by MetaPath `maxPageRank`.

## metapath (1_2_1_2 F1–F4 + F2/F3)

- F1: low MetaPath from `schema/metapath_relations.json`.
- F4: mid MetaPath + `hasDetailPath` / `detailOf`.
- F2/F3: LLM query + embedding indexes (requires `QWEN_API_KEY` unless skipped).
