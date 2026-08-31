# OOPS! Report for BAE_v3_clean

Source: [OOPS! REST](https://oops.linkeddata.es/rest) via OntologyContent (RDF/XML of BAE_v3_clean.ttl)
Evaluated at (UTC): 2026-08-19 23:53:44
Ontology triples (rdflib parse of BAE_v3_clean.ttl): 545
Total pitfalls reported: **7**
Warnings: **0**; Suggestions: **1**

HTTP status of OOPS! call: **200** (response saved to BAE_v3_clean_oops_report.xml)

## Important (2)

### P10 — Missing disjointness
- Importance: Important
- Affected elements: 
- Description: The ontology lacks disjoint axioms between classes or between properties that should be defined as disjoint. This pitfall is related with the guidelines provided in [6], [2] and [7].

### P11 — Missing domain or range in properties
- Importance: Important
- Affected elements: 3
- Description: Object and/or datatype properties without domain or range (or none of them) are included in the ontology.
- Elements:
  - whu:isAboutDimension
  - whu:hasOriginalText
  - whu:hasName

## Minor (5)

### P04 — Creating unconnected ontology elements
- Importance: Minor
- Affected elements: 10
- Description: Ontology elements (classes, object properties and datatype properties) are created isolated, with no relation to the rest of the ontology.
- Elements:
  - whu:EBM
  - whu:MPU
  - obo:BFO_0000031
  - whu:EEM
  - obo:BFO_0000015
  - obo:BFO_0000023
  - obo:ENVO_00002297
  - p-plan:Step
  - prov:Location
  - obo:BFO_0000040

### P08 — Missing annotations
- Importance: Minor
- Affected elements: 54
- Description: This pitfall consists in creating an ontology element and failing to provide human readable annotations attached to it. Consequently, ontology elements lack annotation properties that label them (e.g. rdfs:label, lemon:LexicalEntry, skos:prefLabel or skos:altLabel) or that define them (e.g. rdfs:comment or dc:description). This pitfall is related to the guidelines provided in [5].
- Elements:
  - mp:Statement
  - prov:Activity
  - prov:Location
  - mp:Representation
  - mp:Attribution
  - mp:Reference
  - prov:Plan
  - mp:Data
  - mp:Claim
  - mp:Method
  - p-plan:Step
  - prov:Collection
  - p-plan:Plan
  - prov:Entity
  - obo:BFO_0000015
  - obo:IAO_0000109
  - obo:BFO_0000040
  - obo:ENVO_00002297
  - obo:IAO_0000100
  - obo:BFO_0000031
  - obo:IAO_0000027
  - obo:IAO_0000032
  - obo:ENVO_00010483
  - obo:IAO_0000030
  - obo:BFO_0000023
  - obo:OBI_0100026
  - cito:isCitedBy
  - prov:wasDerivedFrom
  - whu:hasTarget
  - mp:supports
  - dcterms:hasPart
  - whu:declaredOutput
  - prov:hadMember
  - p-plan:isStepOfPlan
  - whu:declaredInput
  - mp:challenges
  - obo:BFO_0000051
  - obo:IAO_0000136
  - prov:atLocation
  - whu:hasGoal
  - geo:lat
  - whu:hasName
  - obo:IAO_0000004
  - whu:researchType
  - gn:population
  - schema:model
  - schema:brand
  - geo:long
  - schema:softwareVersion
  - whu:softwareBrand
  - whu:hasOriginalText
  - geo:alt
  - schema:serialNumber
  - whu:hasComparator

### P13 — Inverse relationships not explicitly declared
- Importance: Minor
- Affected elements: 21
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
  - whu:hasContext

### P22 — Using different naming conventions in the ontology
- Importance: Minor
- Affected elements: 1
- Description: The ontology elements are not named following the same convention (for example CamelCase or use of delimiters as "-" or "_") . Some notions about naming conventions are provided in [2].
- Elements:
  - obo:BFO_0000015
  - whu:EBM

### P32 — Several classes with the same label
- Importance: Minor
- Affected elements: 1
- Description: Two or more classes have the same content for natural language annotations for naming, for example the rdfs:label annotation. This pitfall might involve lack of accuracy when defining terms.
- HaveSameLabel:
  - whu:DataSet
  - obo:IAO_0000100

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
| schema/ttl/BAE_v3_clean.ttl | Input Turtle |
| schema/ttl/BAE_v3_clean.rdf | RDF/XML submitted as OntologyContent |
| schema/ttl/BAE_v3_clean_oops_request.xml | OOPSRequest wrapper |
| schema/ttl/BAE_v3_clean_oops_report.xml | Raw OOPS! XML response (authoritative) |
| schema/ttl/BAE_v3_clean_oops_report.md | This human-readable rendering |

This report is a human-readable rendering of BAE_v3_clean_oops_report.xml returned by OOPS!; no pitfalls were invented offline.
