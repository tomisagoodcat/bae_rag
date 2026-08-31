# Stage notes (from original notebooks)

## build_kg (1_2_0_2 module3)

- Schema-guided extraction: iterates `potential_schema.json` triples.
- Uses `SimpleKGPipeline` per triple with section filtering via `section_role`.
- Prompt template: `kg_build_pipeline/prompts/custom_prompt.md` (v5 labels; `{schema}` / `{text}` / `{examples}`). Parent-repo `custom_prompt.md` is legacy only.
- After semantic split, `table3_section_bae.json` assigns prior `bae_roles` on memory nodes.
- Post-extract per doc: Chunk backfill (`section_role`, `bae_roles`, `header_path`) then `update_metadata_batch` + `enhance_relations`.
- **Mid pilot:** `build_kg.schema_tiers: [mid]` filters to mid triples only (section-join extract unchanged). Omit or clear `schema_tiers` for full schema.

## mid_quality_gate

- After mid `build_kg`: Cypher validator (SHACL `BAE_mid_shapes` M00–M06/M09/M10/**M13**) → Qwen Mid Reviewer → **pre-reject** orphan nodes → targeted single-chunk DeepSeek re-extract.
- **M13 (HARD):** each `whu_SupportGraph` must have `mp_supports`/`mp_challenges` → `mp_Claim`.
- **Pre-reject:** before each re-extract, nodes named in validator violations (`reject_rules`, default M13+M06) are marked `whu_rejected` or deleted (`reject_mode`). Validation and reviewer graph summary exclude rejected nodes.
- **Repair queue:** reviewer issues ∪ validator violations (`merge_validator_issues`), deduped by `(rule_id, entity)`.
- **Early-stop:** if `hard_count` unchanged vs previous iteration, skip further re-extract loops (`early_stop_on_unchanged_hard`).
- Stop when `hard_violations == 0` and reviewer `overall_score >= pass_score` (config default 0.78; `pass_on_hard_zero: false`), or `max_iterations` (default 3) → FLAG.
- **Persists** `Chunk.mid_gate_status` / `mid_gate_score` (PASS|FLAGGED) for Low expand gating.
- Requires `QWEN_API_KEY` (no silent PASS). Reviewer prompt: `prompts/mid_reviewer.md`.

## low_expand

- After Validated Mid (`mid_gate_status=PASS`): parent-scoped mid2low/low expansion (not section-wide `low_and_all`).
- **Strategy (`low_extraction.strategy`):**
  - `entity_first` (default): per Mid parent — Low Schema Activation (mid2low entries → BFS along `tier=low`) → entity-only extract → Low–Low relations among existing entities → Mid–Low rule/hybrid link → existing Low gate. Caps LLM calls via `entity_first.max_llm_calls_per_parent` (default 3).
  - `attach_first`: previous two-wave / legacy path (rollback).
- **Pass1 context:** parent `WHU_HASORIGINALTEXT` + home `FROM_CHUNK` only (no default ±neighbor).
- **Routing (`low_extraction.routing.mode`)** — used when `strategy=attach_first`:
  - `incident_two_wave`: Mid parent runs only **mid2low rows incident to its label**; then each attached child runs **low rows incident to the child label**.
  - `legacy_closure`: BFS closure over mid2low+low.
- **Extract phases:** `low_entity` / `low_ll` / `low_ml` (entity_first) or `low_pass1|low_child_pass1|low_pass2|low_repair` (attach_first). Optional `extract.batch_schemas_per_call` for schema-triple batches.
- **Abort:** `abort_on_insufficient_balance` stops expand on API 402 / Insufficient Balance.
- **Local SHACL** (Cypher mirror): H01-B (`researchType` ↔ Mid parent; Bio↔Comp cross-link HARD; relation-only edge repair); H04; H09-A/B.
- **Gate:** hard → targeted repair; Warning + reviewer `EXPAND_NEIGHBOR` → Pass2.
- **Then** `cross_parent_linker` → Final SHACL → subgraph / chunk_merge / entity_merge / pagerank / metapath.
- Config: `low_extraction` in `config.yaml`. UI modes: `expand_mid` (Extract Low), `mid_then_low`. Deprecated `low_and_all` remains isolated.

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
- **Acceptance** (`metapath.acceptance`): `mode=lenient` (pipeline default) allows mid without `hasDetailPath` children and zero detail links (warnings in stats); hard-fails only illegal `path_level` / wrong-direction edges / missing mid when required. Set `mode=strict` for notebook-equivalent hard fail on orphans.
