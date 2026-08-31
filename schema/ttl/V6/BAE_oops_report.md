# OOPS! Report for BAE

Source: [OOPS! REST](https://oops.linkeddata.es/rest) via OntologyContent (RDF/XML of `schema/ttl/V6/BAE.ttl`)
Evaluated at (UTC): 2026-08-20 00:11:28
Ontology triples (rdflib parse): 720
Total pitfalls reported: **4**
Warnings: **0**; Suggestions: **1**

HTTP status of OOPS! call: **200**

## Minor (4)

### P04 — Creating unconnected ontology elements
- Importance: Minor
- Affected elements: 5
- Description: Ontology elements (classes, object properties and datatype properties) are created isolated, with no relation to the rest of the ontology.
- Elements:
  - obo:BFO_0000031
  - obo:BFO_0000015
  - obo:BFO_0000023
  - obo:ENVO_00002297
  - obo:BFO_0000040

### P13 — Inverse relationships not explicitly declared
- Importance: Minor
- Affected elements: 22
- Description: This pitfall appears when any relationship (except for those that are defined as symmetric properties using owl:SymmetricProperty) does not have an inverse relationship (owl:inverseOf) defined within the ontology.
- MightBeInverse:
  - mp:supports
  - mp:challenges
- NoInverseSuggestion:
  - cito:isCitedBy
  - whu:declaredUsed
  - prov:wasDerivedFrom
  - whu:hasTarget
  - p-plan:correspondsToStep
  - dcterms:hasPart
  - whu:declaredOutput
  - prov:hadMember
  - whu:fellow
  - p-plan:isStepOfPlan
  - whu:declaredInput
  - p-plan:isInputVarOf
  - p-plan:isOutputVarOf
  - obo:BFO_0000051
  - p-plan:isPrecededBy
  - obo:IAO_0000136
  - prov:atLocation
  - whu:hasGoal
  - whu:belongsToModule
  - whu:hasContext

### P20 — Misusing ontology annotations
- Importance: Minor
- Affected elements: 1
- Description: The contents of some annotation properties are swapped or misused. This pitfall might affect annotation properties related to natural language information (for example, annotations for naming such as rdfs:label or for providing descriptions such as rdfs:comment). Other types of annotation could also be affected as temporal, versioning information, among others.
- Elements:
  - prov:wasDerivedFrom

### P22 — Using different naming conventions in the ontology
- Importance: Minor
- Affected elements: 1
- Description: The ontology elements are not named following the same convention (for example CamelCase or use of delimiters as "-" or "_") . Some notions about naming conventions are provided in [2].
- Elements:
  - obo:BFO_0000015
  - whu:EBM

## Suggestions (1)

### SUGGESTION: symmetric or transitive object properties.
- Affected elements: 3
- Description: The domain and range axioms are equal for each of the following object properties. Could they be symmetric or transitive?
- Elements:
  - mp:supports
  - mp:challenges
  - p-plan:isPrecededBy

## Evidence files

| File | Role |
|------|------|
| `schema/ttl/V6/BAE.ttl` | Input Turtle |
| `*.rdf` | RDF/XML submitted as OntologyContent |
| `*_oops_request.xml` | OOPSRequest wrapper |
| `*_oops_report.xml` | Raw OOPS! XML response (authoritative) |
| `*_oops_report.md` | This human-readable rendering |

This report is a human-readable rendering of the OOPS! XML response; no pitfalls were invented offline.
