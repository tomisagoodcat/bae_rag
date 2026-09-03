"""Label whitelists for entity normalization (hard merge vs external concept)."""
from __future__ import annotations

# Same source_doc + WHU_HASORIGINALTEXT exact → physical merge
HARD_MERGE_LABELS: frozenset[str] = frozenset(
    {
        "whu_ChemicalEntity",
        "envo_EnvironmentMaterial",
        "whu_Reagent",
    }
)

# ExternalConcept lookup only (no hard merge)
EXTERNAL_CONCEPT_ONLY_LABELS: frozenset[str] = frozenset(
    {
        "whu_Specimen",
        "whu_ProcessedSpecimen",
        "obi_organism",
    }
)

# Skip normalization entirely
EXCLUDED_LABELS: frozenset[str] = frozenset(
    {
        "whu_EnvironmentFeature",
        "whu_Device",
    }
)

# Labels that receive ExternalConcept linking (hard-merge labels + external-only)
EXTERNAL_CONCEPT_LABELS: frozenset[str] = HARD_MERGE_LABELS | EXTERNAL_CONCEPT_ONLY_LABELS

# BAE label → ontology index basename (under resources/ontologies/_index/)
LABEL_ONTOLOGY_MAP: dict[str, str] = {
    "whu_ChemicalEntity": "chebi",
    "whu_Reagent": "chebi",
    "envo_EnvironmentMaterial": "envo",
    "obi_organism": "ncbitaxon",
}

# Specimen types: no direct ontology class mapping (provenance-only policy).
SPECIMEN_NO_DIRECT_ONTOLOGY: frozenset[str] = frozenset(
    {
        "whu_Specimen",
        "whu_ProcessedSpecimen",
    }
)

REL_NORMALIZED_TO = "whu_normalizedTo"
LABEL_EXTERNAL_CONCEPT = "whu_ExternalConcept"

# First-phase LLM alignment (CheBI only)
LLM_ALIGN_LABELS: frozenset[str] = frozenset(
    {
        "whu_ChemicalEntity",
        "whu_Reagent",
    }
)
