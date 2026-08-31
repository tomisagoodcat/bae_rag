# Schema P-Plan Migration Report (2026-05-24)

## Summary

Migrated `output/*.json` to P-Plan Step model with `whu_fellow` for plan ordering.

## Files

| File | Change |
|------|--------|
| `entity.json` | 4 Activity classes renamed to `*Step`; p-plan:Step descriptions |
| `relation.json` | +4 relations (`whu_hasContext`, `whu_atLocation`, `p_plan_isStepOfPlan`, `p_plan_hasOutputVar`); fellow/declareUsed revised |
| `potential_schema.json` | 77 triples (was ~100); PROV on steps removed |
| `subgraph_mapping.json` | version 1.1; Master ghosts removed |
| `_backup_20260524/` | Pre-migration backup |

## Validation

```
python utilities/validate_schema.py
# OK: schema validation passed
```

## SchemaLoader

- Entities: 26
- Relations: 28
- Potential schema: 77
- Step labels: `whu_Specimen_CollectionStep`, `whu_Specimen_ProcessingStep`, `whu_BioChemicalStep`, `whu_ComputationalStep`

## Neo4j acceptance (2026-05-22)

Run: `luck2\python.exe utilities/neo4j_acceptance.py`

Connected at `bolt://localhost:7687` (password in notebook / script):

| Metric | Value |
|--------|-------|
| Nodes | 4365 |
| Relationships | 5923 |
| Old Step labels | BioChemicalActivityStep 166, ComputationalActivityStep 38, Collection_Activity 1, Processing_Activity 45 |
| New Step labels | **none yet** |
| New relations | `p_plan_hasInputVar` 2 only |
| Deprecated still in DB | `prov_used` 67, `prov_wasInformedBy` 35, `prov_generated` 28, `whu_hasActivity` 20 |

**Action required:** Run [`1_2_0_2build_kg__neo4j.ipynb`](../1_2_0_2build_kg__neo4j.ipynb) `__main__` cell (`clear_neo4j_database()` + `build_knowledge_graph(schema_base_path=./output)`). Then re-run GDS/MetaPath in [`3_0_2 Retevie.ipynb`](../3_0_2%20Retevie.ipynb).

Post-rebuild check: new Step labels > 0, deprecated relation counts → 0.

## Utilities added

- `utilities/migrate_schema_pplan.py` — one-shot migration (already applied)
- `utilities/validate_schema.py` — consistency checks
- `utilities/patch_notebooks_schema.py` — notebook label/sync patch (already applied)
