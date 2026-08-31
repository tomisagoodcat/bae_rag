# schema/oops_revise — OOPS!-driven BAE ontology revision (standalone)

This folder is **independent** of `kg_build_pipeline/` and Neo4j runtime code.
It only reads/writes under `schema/`.

## Scripts

| Script | Purpose |
|--------|---------|
| `apply_oops_fixes.py` | Load `schema/ttl/BAE_v3_clean.ttl`, apply OOPS!-mapped fixes, write `schema/ttl/V6/BAE.ttl` |
| `run_oops_eval.py` | Convert TTL → RDF/XML, POST to [OOPS! REST](https://oops.linkeddata.es/rest), write reports |

## Typical workflow

```bash
# from repo root, env with rdflib + requests
python schema/oops_revise/apply_oops_fixes.py
python schema/oops_revise/run_oops_eval.py --ttl schema/ttl/V6/BAE.ttl --out-dir schema/ttl/V6
```

## Fix policy (aligned with BAE_v3_clean OOPS! report)

| Pitfall | Action |
|---------|--------|
| P11 Important | Add `rdfs:domain` for `hasName`, `hasOriginalText`, `isAboutDimension` |
| P10 Important | Add sibling `owl:disjointWith` axioms |
| P04 Minor | `SemanticModule` + `belongsToModule`; labels on flagged anchors |
| P08 Minor | Ensure `rdfs:label` / `rdfs:comment` |
| P32 Minor | Relabel `whu:DataSet` |
| P13 / Suggestion | **Skipped** (would distort extraction semantics) |

## Outputs

See `schema/ttl/V6/` (`BAE.ttl`, OOPS reports, changelog).
