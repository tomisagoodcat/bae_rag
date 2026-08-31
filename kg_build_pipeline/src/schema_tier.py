"""Filter potential_schema / entity / relation views by tier (mid|low|mid2low)."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Mid structural containers + scheme A focal Claim via supports/challenges.
MID_CORE_ENTITY_LABELS: Set[str] = {
    "whu_EnvironmentFeature",
    "whu_SpecimenCollection",
    "whu_SpecimenPreprocessing",
    "whu_BioChemical_Experiment",
    "whu_Computational_Experiment",
    "whu_ScienceEvidence",
    "whu_SupportGraph",
    "mp_Claim",
}

# Mid–mid structural whitelist used by M09 (Neo4j underscore labels).
MID_MID_ALLOWED_TRIPLES: Set[Tuple[str, str, str]] = {
    ("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection"),
    ("whu_BioChemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
    ("whu_BioChemical_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
    ("whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment"),
    ("whu_ScienceEvidence", "prov_wasDerivedFrom", "whu_Computational_Experiment"),
    ("whu_ScienceEvidence", "mp_supports", "whu_SupportGraph"),
    ("whu_ScienceEvidence", "mp_challenges", "whu_SupportGraph"),
    ("whu_SpecimenCollection", "whu_hasContext", "whu_EnvironmentFeature"),
    # Focal Claim linked via SupportGraph argumentative edges, not hadMember; SE never → Claim
    ("whu_SupportGraph", "mp_supports", "mp_Claim"),
    ("whu_SupportGraph", "mp_challenges", "mp_Claim"),
}


def triple_tier(schema_row: Sequence[Any]) -> Optional[str]:
    if len(schema_row) >= 5 and isinstance(schema_row[4], str):
        return schema_row[4]
    return None


def filter_potential_schema(
    potential_schema: List[Any],
    tiers: Optional[Iterable[str]] = None,
) -> List[Any]:
    """Return rows whose 5th element is in ``tiers``. None/empty tiers → unchanged."""
    if not tiers:
        return list(potential_schema)
    allowed = {t.lower() for t in tiers}
    out: List[Any] = []
    for row in potential_schema:
        t = triple_tier(row)
        if t is not None and t.lower() in allowed:
            out.append(row)
    return out


def schema_closure(
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    filtered_ps: List[Any],
    *,
    extra_entity_labels: Optional[Set[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Set[str], Set[str]]:
    """Entity/relation defs limited to labels appearing in filtered potential_schema."""
    ent_labels: Set[str] = set(extra_entity_labels or ())
    rel_labels: Set[str] = set()
    for row in filtered_ps:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        ent_labels.add(row[0])
        ent_labels.add(row[2])
        rel_labels.add(row[1])
    ents = [e for e in entities if e.get("label") in ent_labels]
    rels = [r for r in relations if r.get("label") in rel_labels]
    return ents, rels, ent_labels, rel_labels


def mid_schema_view(
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    potential_schema: List[Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Any]]:
    """Mid extraction view: tier=mid triples + closure including scheme-A Claim."""
    filtered = filter_potential_schema(potential_schema, tiers={"mid"})
    ents, rels, _, _ = schema_closure(
        entities,
        relations,
        filtered,
        extra_entity_labels=MID_CORE_ENTITY_LABELS,
    )
    return ents, rels, filtered
