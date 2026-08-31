# OOPS! Report for BAE_v2

Source: [OOPS! REST](https://oops.linkeddata.es/rest) via OntologyContent (RDF/XML of BAE_v2.ttl)
Total pitfalls reported: **9**
Warnings: **0**; Suggestions: **1**

## Critical (1)

### P19 — Defining multiple domains or ranges in properties
- Importance: Critical
- Affected elements: 6
- Description: The domain or range (or both) of a property (relationships and attributes) is defined by stating more than one rdfs:domain or rdfs:range statements. In OWL multiple rdfs:domain or rdfs:range axioms are allowed, but they are interpreted as conjunction, being, therefore, equivalent to the construct owl:intersectionOf. This pitfall is related to the common error that appears when defining domains and ranges described in [7].
- Elements:
  - p-plan:isPrecededBy
  - mp:challenges
  - whu:hasGoal
  - mp:supports
  - prov:wasDerivedFrom
  - iao:is_about

## Important (3)

### P10 — Missing disjointness
- Importance: Important
- Affected elements: 
- Description: The ontology lacks disjoint axioms between classes or between properties that should be defined as disjoint. This pitfall is related with the guidelines provided in [6], [2] and [7].

### P34 — Untyped class
- Importance: Important
- Affected elements: 2
- Description: An ontology element is used as a class without having been explicitly declared as such using the primitives owl:Class or rdfs:Class. This pitfall is related with the common problems listed in [8].
- Elements:
  - dcat:Dataset
  - dcat:DataService

### P35 — Untyped property
- Importance: Important
- Affected elements: 1
- Description: An ontology element is used as a property without having been explicitly declared as such using the primitives rdf:Property, owl:ObjectProperty or owl:DatatypeProperty. This pitfall is related with the common problems listed in [8].
- Elements:
  - prov:used

## Minor (5)

### P04 — Creating unconnected ontology elements
- Importance: Minor
- Affected elements: 7
- Description: Ontology elements (classes, object properties and datatype properties) are created isolated, with no relation to the rest of the ontology.
- Elements:
  - fabio:Table
  - whu:EBM
  - whu:EEM
  - fabio:Figure
  - iao:0000030
  - prov:Entity
  - whu:MPU

### P08 — Missing annotations
- Importance: Minor
- Affected elements: 34
- Description: This pitfall consists in creating an ontology element and failing to provide human readable annotations attached to it. Consequently, ontology elements lack annotation properties that label them (e.g. rdfs:label, lemon:LexicalEntry, skos:prefLabel or skos:altLabel) or that define them (e.g. rdfs:comment or dc:description). This pitfall is related to the guidelines provided in [5].
- Elements:
  - dcat:DataService
  - dcat:Dataset
  - iao:is_about
  - prov:wasDerivedFrom
  - iao:hasMeasurementValue
  - iao:hasMeasurementUnit
  - whu:hasComparator
  - prov:Activity
  - mp:Representation
  - fabio:Figure
  - fabio:Table
  - qudt:QuantityValue
  - iao:0000100
  - iao:0000027
  - p-plan:Step
  - iao:0000030
  - prov:Collection
  - p-plan:Plan
  - prov:Entity
  - mp:Sentence
  - mp:supports
  - whu:hasGoal
  - dct:hasPart
  - whu:hasTemperature
  - prov:hadMember
  - whu:hasHumidity
  - whu:hasDuration
  - mp:challenges
  - whu:hasTarget
  - p-plan:hasInputVar
  - p-plan:isPrecededBy
  - p-plan:hasOutputVar
  - whu:hasExecutionEnvironment
  - mp:statement

### P13 — Inverse relationships not explicitly declared
- Importance: Minor
- Affected elements: 19
- Description: This pitfall appears when any relationship (except for those that are defined as symmetric properties using owl:SymmetricProperty) does not have an inverse relationship (owl:inverseOf) defined within the ontology.
- Elements:
  - iao:is_about
  - prov:wasDerivedFrom
  - mp:supports
  - p-plan:correspondsToStep
  - whu:hasGoal
  - dct:hasPart
  - whu:hasTemperature
  - prov:hadMember
  - p-plan:isStepOfPlan
  - whu:declaredUsed
  - whu:hasHumidity
  - whu:hasDuration
  - mp:challenges
  - whu:hasTarget
  - p-plan:hasInputVar
  - p-plan:isPrecededBy
  - p-plan:hasOutputVar
  - whu:hasContext
  - whu:hasExecutionEnvironment

### P22 — Using different naming conventions in the ontology
- Importance: Minor
- Affected elements: 1
- Description: The ontology elements are not named following the same convention (for example CamelCase or use of delimiters as "-" or "_") . Some notions about naming conventions are provided in [2].
- Elements:
  - iao:0000100
  - qudt:QuantityValue

### P32 — Several classes with the same label
- Importance: Minor
- Affected elements: 2
- Description: Two or more classes have the same content for natural language annotations for naming, for example the rdfs:label annotation. This pitfall might involve lack of accuracy when defining terms.
- Elements:
  - whu:DataItem
  - iao:0000027
  - whu:DataSet
  - iao:0000100

## Suggestions
### SUGGESTION: symmetric or transitive object properties.
The domain and range axioms are equal for each of the following object properties. Could they be symmetric or transitive?
- p-plan:isPrecededBy
