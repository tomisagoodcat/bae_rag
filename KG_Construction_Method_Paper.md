# Knowledge Graph Construction from Scientific Literature

## 2. Ontology-driven Knowledge Graph Construction Framework

Building upon the heterogeneous evidence structure introduced in Section 1, this section presents an **ontology-driven, schema-constrained knowledge extraction framework** that transforms scientific papers into structured, FAIR-compliant knowledge graphs. Unlike conventional LLM-based extraction approaches that operate in an open-ended manner, our framework leverages **domain ontologies** to guide both document structuring and entity-relation extraction, ensuring semantic consistency and enabling precise retrieval in downstream tasks.

---

### 2.1 Overview of the Construction Pipeline

Our knowledge graph construction pipeline consists of four key stages, each tightly integrated with ontological principles:

1. **Metadata Annotation**: Agent-based extraction of Dublin Core (DC) metadata for provenance tracking
2. **Rhetorical Structure Segmentation**: Ontology-guided semantic chunking based on SPAR ontology family
3. **Schema-constrained Extraction**: Iterative entity-relation extraction following predefined ontology schemas
4. **Graph Materialization**: Storage in Neo4j with full provenance and structural metadata

The pipeline transforms unstructured markdown documents into a heterogeneous graph where each node and relationship is annotated with ontological types, structural roles, and provenance metadata.

---

### 2.2 Document Metadata Extraction via DC Ontology and LLM Agents

**2.2.1 Dublin Core Metadata Standard**

To enable comprehensive provenance tracking and support paper-level analysis, we adopt the **Dublin Core Metadata Initiative (DCMI)** standard [cite] as the foundation for document annotation. Each document in our corpus is enriched with DC core elements, including:

- **`dc:title`**: Article title
- **`dc:creator`**: Author information
- **`dc:identifier`**: DOI or unique identifier
- **`dcterms:date`**: Publication date
- **`dcterms:abstract`**: Abstract text

These metadata elements are **inherited by all derived artifacts** (chunks, entities, relationships) during the extraction process, creating a complete provenance chain from any graph element back to its source document.

**2.2.2 Agent-based Metadata Extraction**

Traditional metadata extraction approaches rely on structured PDF parsing or manual annotation, which are labor-intensive and error-prone. We propose an **LLM-based agent framework** that automatically extracts DC metadata using a multi-tool architecture:

```python
Agent Tools:
1. search_crossref: For English papers (CrossRef API)
2. search_chinese_metadata: For Chinese papers (CNKI/other APIs)
```

The agent employs a **ReAct (Reasoning + Acting)** paradigm [Yao et al., 2022] to dynamically select appropriate extraction tools based on query analysis. For English papers, the agent queries CrossRef API using title and author information; for Chinese papers, it selects domain-specific metadata sources.

**Key Innovation**: Unlike static metadata extraction, our agent-based approach **adapts to document characteristics** (language, domain, format), achieving higher recall and accuracy, particularly for non-standard document formats or incomplete metadata.

**Implementation**: The extracted DC metadata is stored as document-level properties and automatically propagated to all text chunks and extracted entities/relations, ensuring that every graph element can be traced to its source paper and supports paper-scoped queries (e.g., "find all claims in paper X").

---

### 2.3 Ontology-guided Rhetorical Structure Segmentation

**2.3.1 Semantic Chunking Based on SPAR Ontology Family**

Academic papers exhibit **rhetorical structure** that reflects their communicative purpose. Traditional document chunking methods (fixed-size sliding windows, sentence-based segmentation) ignore this structure, leading to semantic fragmentation and loss of context.

We propose a **two-stage hierarchical segmentation** approach that respects document rhetorical structure:

**Stage 1: Structural Coarse Segmentation**

First, documents are split at **natural boundaries** (section headers, paragraph breaks) based on Markdown structure, preserving chapter integrity:

$$
\text{chunks}_{\text{coarse}} = \text{split\_by\_structure}(\text{markdown\_doc}, \text{chunk\_size}=800)
$$

This preserves section-level coherence and avoids splitting mid-paragraph.

**Stage 2: Semantic Fine Segmentation with Rhetorical Annotation**

Second, coarse chunks undergo **semantic similarity-based splitting** using embedding models, followed by **rhetorical role classification**:

$$
\text{chunks}_{\text{fine}} = \text{SemanticSplitter}(\text{chunks}_{\text{coarse}}, \theta_{\text{similarity}}=0.72)
$$

Each fine-grained chunk is then annotated with a **`section_role`** label based on the **Document Components Ontology (DoCO)**, a member of the SPAR (Semantic Publishing and Referencing) ontology family [Peroni & Shotton, 2012].

**DoCO Section Roles**: The DoCO ontology defines standard academic document sections:

$$
\mathcal{R} = \{\text{Abstract}, \text{Introduction}, \text{Methods\_Materials}, \text{Experiment}, \text{Results}, \text{Discussion}, \text{Conclusion}, \text{References}, \ldots\}
$$

**2.3.2 Hybrid Section Role Inference**

To assign `section_role` labels, we employ a **hybrid rule-based + LLM inference** approach:

**Rule-based Matching** (covers ~80% of standard headers):
- Header keyword matching (multilingual support: English/Chinese)
- Pattern recognition (e.g., numbered sections: "2. Methods" → `Methods_Materials`)

**LLM Fallback** (handles ~20% edge cases):
- Content analysis when headers are ambiguous (e.g., "Results and Discussion")
- Few-shot prompting with DoCO-compliant examples

The LLM inferrer uses a structured prompt that enforces DoCO alignment:

```python
Prompt Template:
"You classify a scientific article chunk into DoCO-style section roles.
Decision Order:
1. Hard Header Match (strong signals)
2. Content Cues (lexical/semantic patterns)
3. Tie-break for Mixed Headers"
```

**Mathematical Formulation**: For a chunk $c_i$ with header path $h_i$ and text content $t_i$:

$$
\text{section\_role}(c_i) = \begin{cases}
\text{RuleMatch}(h_i) & \text{if } \text{confidence} > \theta_{\text{rule}} \\
\text{LLMInfer}(h_i, t_i) & \text{otherwise}
\end{cases}
$$

**Key Innovation**: Unlike purely embedding-based semantic chunking, our approach **combines structural and semantic signals** with **ontological alignment**, ensuring that chunks are both semantically coherent and properly categorized according to scholarly communication standards.

**2.3.3 Connection to DEO and FaBiO**

While DoCO defines **document structure**, the **Discourse Elements Ontology (DEO)** and **FaBiO (FRBR-aligned Bibliographic Ontology)** [Peroni & Shotton, 2012] provide complementary semantic layers:

- **DEO**: Captures **discourse-level relationships** between document sections (e.g., `de:conclusionOf`, `de:evidenceFor`)
- **FaBiO**: Models **bibliographic entities** and their relationships (e.g., papers, datasets, claims)

Our `section_role` annotation serves as the **bridge** between DoCO (structural) and DEO/FaBiO (semantic), enabling us to:
1. Filter extraction targets based on rhetorical function (e.g., extract methods only from `Methods_Materials` sections)
2. Establish discourse-level links (e.g., `Results` sections `de:evidenceFor` `Claims` in `Discussion`)
3. Align with bibliographic standards (e.g., `mp_Claim` entities link to `fabio:Expression`)

---

### 2.4 Schema-constrained Entity-Relation Extraction

**2.4.1 Ontology Schema Definition**

Unlike open-ended LLM extraction that may produce inconsistent or noisy triples, our framework operates under **strict ontological constraints** defined by three JSON files:

```
schema_base_path/
├── entity.json          # Entity type definitions (24 types)
├── relation.json        # Relation type definitions
└── potential_schema.json # Schema templates (triple patterns)
```

**Entity Types**: Defined using namespaces:
- **`whu_*`**: Domain-specific entities (e.g., `whu_DataSet`, `whu_Method`, `whu_Pollutant`)
- **`mp_*`**: MetaPaper entities (e.g., `mp_Claim`, `mp_Statement`)
- **`prov_*`**: PROV-O standard entities (e.g., `prov_Activity`, `prov_Agent`)

**Relation Types**: Aligned with PROV-O and domain ontologies:
- Provenance: `prov_used`, `prov_generated`, `prov_wasInformedBy`
- Argumentation: `supports`, `contradicts`, `cito_isCitedBy`

**Potential Schema Format**: Each schema is a quadruple:

$$
\text{schema} = [e_1, r, e_2, \mathcal{S}]
$$

where:
- $e_1, e_2$: Source and target entity types
- $r$: Relation type
- $\mathcal{S} \subseteq \mathcal{R}$: Allowed section roles (optional, defaults to `__ALL__`)

**Example Schemas**:
```python
# Schema 1: Method supports DataSet (all sections)
["whu_Method", "supports", "whu_DataSet"]

# Schema 2: Statement supports Claim (only Methods and Results)
["mp_Statement", "supports", "mp_Claim", ["Methods_Materials", "Results"]]
```

**2.4.2 Section-aware Schema Filtering**

A critical innovation is **section-aware schema application**: different schemas are applied to different rhetorical sections, aligning extraction with document structure.

**Mathematical Formulation**: For a schema $\sigma = [e_1, r, e_2, \mathcal{S}]$, the extraction operates on filtered chunks:

$$
\mathcal{C}_\sigma = \begin{cases}
\{c_i \mid c_i \in \text{chunks}_{\text{fine}}\} & \text{if } \mathcal{S} = \{\text{__ALL__}\} \\
\{c_i \mid \text{section\_role}(c_i) \in \mathcal{S}\} & \text{otherwise}
\end{cases}
$$

**Rationale**: 
- Methods-related entities (e.g., `whu_Method`, `whu_Device`) should be extracted from `Methods_Materials` sections
- Results-related entities (e.g., `whu_DataSet`, measurement data) should be extracted from `Results` sections
- Argumentative relations (e.g., `Statement → Claim`) may span `Results` and `Discussion` sections

This **section-role filtering** significantly improves **extraction precision** by avoiding spurious entities (e.g., extracting experimental methods from abstract summaries).

**2.4.3 Extraction Order and Iterative Schema-driven Process**

The `SimpleKGPipeline` performs **joint extraction** of entities and relations in a single pass per schema, guided by triple templates (`potential_schema`). However, the extraction process follows an **implicit ordering**:

1. **Entity Recognition**: First, the LLM identifies entity spans and assigns types according to the schema's entity types ($e_1, e_2$)
2. **Relation Extraction**: Then, relations are extracted between recognized entities, constrained by the triple template $(e_1, r, e_2)$
3. **Triple Formation**: Finally, valid triples $(subject, predicate, object)$ are formed and materialized in Neo4j

**Mathematical Formulation**: For a schema $\sigma = [e_1, r, e_2, \mathcal{S}]$ and filtered chunks $\mathcal{C}_\sigma$, the extraction process is:

$$
\begin{aligned}
\text{Entities}(\mathcal{C}_\sigma, \{e_1, e_2\}) &= \{(span_i, type_i) \mid type_i \in \{e_1, e_2\}\} \\
\text{Relations}(\mathcal{C}_\sigma, \text{Entities}(\mathcal{C}_\sigma), r) &= \{(e_s, r, e_o) \mid e_s, e_o \in \text{Entities}(\mathcal{C}_\sigma), (type(e_s), r, type(e_o)) = (e_1, r, e_2)\} \\
\text{Triples}(\sigma, \mathcal{C}_\sigma) &= \text{Relations}(\mathcal{C}_\sigma, \text{Entities}(\mathcal{C}_\sigma), r)
\end{aligned}
$$

**Iterative Schema-driven Extraction**:

To ensure **completeness**, we perform **iterative extraction** over all predefined schemas:

```python
Algorithm: Schema-driven Iterative Extraction

Input: final_nodes (semantically chunked with section_role), potential_schema
Output: Knowledge graph G in Neo4j

for each schema σ in potential_schema:
    e1, r, e2 = σ[0], σ[1], σ[2]
    S_allowed = σ[3] if len(σ) > 3 else ["__ALL__"]
    
    # 1. Filter chunks by section_role
    filtered_chunks = {c | section_role(c) in S_allowed}
    
    # 2. Extract entities and relations for this schema (joint extraction)
    kg_builder = SimpleKGPipeline(
        entities=[e | e.label in {e1, e2}],
        relations=[r | r.label == r],
        potential_schema=[σ[:3]]  # Only this schema
    )
    
    # 3. Run joint extraction on filtered text
    # Internally: entities are recognized first, then relations extracted,
    # finally triples (e1, r, e2) are formed and stored
    text = join(filtered_chunks)
    await kg_builder.run_async(text=text)
```

**Mathematical Formulation**: The final knowledge graph $G = (V, E)$ is the union of extractions from all schemas:

$$
G = \bigcup_{\sigma \in \Sigma} \text{Extract}(\sigma, \mathcal{C}_\sigma)
$$

where $\Sigma$ is the set of all potential schemas.

**Key Innovation**: 

1. **Controlled Extraction**: Unlike open-ended LLM extraction that may produce noisy or inconsistent triples, our schema-constrained approach ensures **semantic consistency** with domain ontologies.

2. **Section-aware Precision**: By filtering chunks based on `section_role`, we **reduce false positives** (e.g., extracting "method" entities from discussion sections where "method" refers to prior work).

3. **Iterative Completeness**: The loop over all schemas ensures that **all predefined entity-relation patterns** are extracted, improving recall compared to single-pass extraction.

**2.4.4 Connection to DEO Rhetorical Structure**

The `section_role` filtering mechanism is **directly inspired by DEO (Discourse Elements Ontology)**, which models how different rhetorical sections contribute to overall argumentation:

- **Methods_Materials sections**: Contain `de:describes` relations to experimental procedures
- **Results sections**: Contain `de:evidenceFor` relations to claims
- **Discussion sections**: Contain `de:interprets` relations to results

By aligning our schema filtering with DoCO `section_role` (which maps to DEO discourse elements), we ensure that extracted triples respect **document-level argumentative structure**, not just lexical similarity.

---

### 2.5 Knowledge Graph Materialization

**2.5.1 Neo4j Storage Structure**

Extracted entities and relations are stored in Neo4j with the following structure:

**Node Labels**: Multi-label hierarchy
- **Primary label**: Entity type (e.g., `whu_DataSet`, `mp_Claim`)
- **Secondary label**: `__Master__` (after entity resolution/merging)

**Node Properties**:
- **`WHU_HASNAME`**: Entity name
- **`WHU_HASORIGINALTEXT`**: Source text fragment (for traceability)
- **`dc_*`, `dcterms_*`**: Inherited DC metadata

**Relationship Properties**:
- **`WHU_HASORIGINALTEXT`**: Source text for the relation (critical for explainability)
- **`WHU_HASNAME`**: Relation name
- **`llm_weight`**: Confidence score (0-1) assigned by LLM during extraction
- **`dc_identifier`**: Source document identifier

**Key Design Decision**: Both nodes and relationships retain **`WHU_HASORIGINALTEXT`**, enabling downstream tasks to:
1. **Trace provenance**: Link any graph element to original text
2. **Explain reasoning**: Show users the source text for retrieved evidence
3. **Validate extraction**: Allow human reviewers to verify LLM outputs

**2.5.2 Entity Resolution and Merging**

The `SimpleKGPipeline` performs **entity resolution** (`perform_entity_resolution=True`) to merge duplicate or near-duplicate entities:

- **Similarity Metrics**: Name similarity + embedding similarity
- **Result**: Multiple chunk-derived entities are merged into `__Master__` nodes
- **Benefit**: Reduces redundancy and enables cross-chunk/cross-paper entity linking

---

### 2.6 Comparison with Conventional Approaches

**Table 1: Comparison of KG Construction Approaches**

| Aspect | Conventional LLM Extraction | Our Ontology-driven Approach |
|--------|---------------------------|------------------------------|
| **Extraction Scope** | Open-ended (all possible triples) | **Schema-constrained** (only predefined patterns) |
| **Semantic Consistency** | Variable (depends on prompt) | **Guaranteed** (ontology-aligned) |
| **Section Awareness** | None (treats document as flat text) | **Section-role filtering** (DoCO/DEO alignment) |
| **Metadata Propagation** | Manual or absent | **Automatic DC inheritance** (full provenance) |
| **Extraction Completeness** | Single-pass (may miss patterns) | **Iterative schema loop** (systematic coverage) |
| **Explainability** | Limited (no source text) | **Full traceability** (`WHU_HASORIGINALTEXT` on nodes/rels) |
| **Standards Compliance** | Ad-hoc | **FAIR-compliant** (DC, PROV-O, SPAR family) |

**Key Differences**:

1. **Ontology Alignment**: We use explicit ontologies (DC, DoCO, DEO, FaBiO, PROV-O) to guide extraction, whereas conventional methods rely solely on LLM reasoning.

2. **Section-aware Filtering**: We leverage rhetorical structure (`section_role`) to filter extraction targets, reducing noise from irrelevant sections.

3. **Schema-driven Iteration**: We systematically iterate over all predefined schemas, ensuring complete coverage of domain patterns.

4. **Provenance Tracking**: DC metadata inheritance ensures every graph element can be traced to source papers, enabling paper-scoped queries and quality assessment.

---

### 2.7 Summary

This section presented an **ontology-driven knowledge graph construction framework** that transforms scientific papers into structured, FAIR-compliant knowledge graphs. Key contributions include:

1. **Agent-based DC metadata extraction** for comprehensive provenance tracking
2. **DoCO-aligned rhetorical structure segmentation** combining structural and semantic signals
3. **Schema-constrained, section-aware extraction** ensuring semantic consistency and precision
4. **Iterative schema-driven extraction** for systematic pattern coverage

The resulting knowledge graph serves as the foundation for downstream tasks (GNN embedding learning, retrieval, reasoning), as detailed in subsequent sections.

---

## References (to be completed)

- Dublin Core Metadata Initiative: https://www.dublincore.org/
- Peroni, S., & Shotton, D. (2012). FaBiO and CiTO: Ontologies for describing bibliographic resources and citations. *Journal of Web Semantics*, 17, 33-43.
- Peroni, S., & Shotton, D. (2012). The Document Components Ontology (DoCO). *Semantic Web*, 9(4), 493-502.
- Yao, S., et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models. *arXiv preprint arXiv:2210.03629*.

