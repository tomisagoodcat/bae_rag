# BAE.ttl OOPS! revision changelog

- Source: `schema/ttl/BAE_v3_clean.ttl`
- Output: `schema/ttl/V6/BAE.ttl`
- Triples after revision: 712

## Applied fixes

- Renamed ontology IRI to https://bdi.whu.edu.cn/BAE (version 6.0-oops)
- P11: added rdfs:domain for hasName, hasOriginalText, isAboutDimension
- P32: relabeled whu:DataSet to avoid same-label clash with IAO_0000100
- P04: SemanticModule hierarchy + belongsToModule; labels on flagged anchors
- P10: added owl:disjointWith axioms among sibling domain classes
- P08: ensured rdfs:label/rdfs:comment on previously unannotated elements
- Skipped P13 (inverseOf) and symmetric/transitive suggestion by design

## Intentionally not applied

- P13 (`owl:inverseOf`): extraction / Neo4j use single-direction edges.
- Suggestion (symmetric/transitive on supports/challenges/isPrecededBy): semantically incorrect for BAE.
