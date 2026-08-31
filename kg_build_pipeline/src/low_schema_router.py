"""Route mid2low/low potential_schema rows to a mid parent label."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS, filter_potential_schema, triple_tier

# Mid parent Neo4j label → ResearchStep.WHU_RESEARCHTYPE (H01-B).
PARENT_LABEL_TO_RESEARCH_TYPE: Dict[str, str] = {
    "whu_SpecimenCollection": "SpecimenCollection",
    "whu_SpecimenPreprocessing": "SpecimenProcessing",
    "whu_BioChemical_Experiment": "BioChemical",
    "whu_Computational_Experiment": "Computational",
}

RESEARCH_TYPE_TO_PARENT_LABEL: Dict[str, str] = {
    v: k for k, v in PARENT_LABEL_TO_RESEARCH_TYPE.items()
}

# Relations that hang low/mid2low nodes onto a mid parent (or vice versa).
PARENT_ATTACH_RELS: Set[str] = {
    "p_plan_isStepOfPlan",
    "whu_hasGoal",
    "prov_hadMember",
    "whu_hasContext",
    "mp_supports",
    "mp_challenges",
    "prov_wasDerivedFrom",
}

LOW_TO_LOW_RELS: Set[str] = {
    "p_plan_isPrecededBy",
    "whu_declaredUsed",
    "whu_declaredInput",
    "whu_declaredOutput",
    "p_plan_isInputVarOf",
    "p_plan_isOutputVarOf",
    "bfo_has_part",
    "whu_fellow",
}

# Labels commonly produced under parents during low expand.
LOW_ENTITY_LABELS: Set[str] = {
    "whu_ResearchStep",
    "whu_Goal",
    "whu_TargetVariable",
    "mp_Method",
    "whu_Device",
    "whu_Reagent",
    "whu_Software",
    "whu_Specimen",
    "whu_ProcessedSpecimen",
    "whu_DataSet",
    "whu_ChemicalEntity",
    "mp_Statement",
    "mp_Attribution",
    "mp_Reference",
}


def _row_triple(row: Sequence[Any]) -> Optional[Tuple[str, str, str]]:
    if not isinstance(row, (list, tuple)) or len(row) < 3:
        return None
    return (str(row[0]), str(row[1]), str(row[2]))


def primary_parent_label(labels: Iterable[str]) -> Optional[str]:
    """Prefer a mid-core label when multiple labels are present."""
    labs = [str(l) for l in labels if l]
    for lab in labs:
        if lab in MID_CORE_ENTITY_LABELS:
            return lab
    return labs[0] if labs else None


def expand_reachable_labels(
    parent_label: str,
    potential_schema: List[Any],
    *,
    tiers: Optional[Iterable[str]] = None,
) -> Set[str]:
    """BFS entity labels reachable from parent via mid2low/low triples."""
    rows = filter_potential_schema(potential_schema, tiers=tiers or {"mid2low", "low"})
    seed: Set[str] = {parent_label}
    changed = True
    while changed:
        changed = False
        for row in rows:
            t = _row_triple(row)
            if not t:
                continue
            s, rel, o = t
            if s in seed and o not in seed:
                seed.add(o)
                changed = True
            # Reverse: subject hangs onto known object via attach / parent object
            if o in seed and s not in seed and (
                rel in PARENT_ATTACH_RELS or o == parent_label
            ):
                seed.add(s)
                changed = True
    return seed


def route_schema_for_parent(
    parent_label: str,
    potential_schema: List[Any],
    *,
    tiers: Optional[Iterable[str]] = None,
) -> List[Any]:
    """Return mid2low|low rows whose endpoints are in the parent-reachable set."""
    if not parent_label:
        return []
    allowed_tiers = {t.lower() for t in (tiers or {"mid2low", "low"})}
    rows = filter_potential_schema(potential_schema, tiers=allowed_tiers)
    reachable = expand_reachable_labels(parent_label, potential_schema, tiers=allowed_tiers)
    out: List[Any] = []
    for row in rows:
        t = _row_triple(row)
        if not t:
            continue
        s, _rel, o = t
        # Both endpoints must be in the parent-reachable closure (avoids
        # pulling unrelated triples that only share a common leaf type).
        if s in reachable and o in reachable:
            out.append(row)
    return out


def route_mid2low_incident(
    parent_label: str,
    potential_schema: List[Any],
) -> List[Any]:
    """mid2low rows where subject or object equals parent_label (no BFS closure)."""
    if not parent_label:
        return []
    out: List[Any] = []
    for row in filter_potential_schema(potential_schema, tiers={"mid2low"}):
        t = _row_triple(row)
        if not t:
            continue
        s, _rel, o = t
        if s == parent_label or o == parent_label:
            out.append(row)
    return out


@dataclass
class LocalLowSchema:
    """Parent-specific low schema: mid2low entries expanded along tier=low only."""

    parent_label: str
    entry_labels: Set[str] = field(default_factory=set)
    entity_labels: Set[str] = field(default_factory=set)
    mid2low_rows: List[Any] = field(default_factory=list)
    low_rows: List[Any] = field(default_factory=list)
    hops: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_label": self.parent_label,
            "entry_labels": sorted(self.entry_labels),
            "entity_labels": sorted(self.entity_labels),
            "mid2low_rows": len(self.mid2low_rows),
            "low_rows": len(self.low_rows),
            "hops": self.hops,
        }


def research_type_for_parent(parent_label: str) -> Optional[str]:
    """Map mid parent Neo4j label to ResearchStep WHU_RESEARCHTYPE."""
    if not parent_label:
        return None
    return PARENT_LABEL_TO_RESEARCH_TYPE.get(str(parent_label))


def mid2low_entry_labels(parent_label: str, mid2low_rows: List[Any]) -> Set[str]:
    """Low/other endpoint labels from mid2low incident rows (exclude parent)."""
    entries: Set[str] = set()
    for row in mid2low_rows:
        t = _row_triple(row)
        if not t:
            continue
        s, _rel, o = t
        if s != parent_label:
            entries.add(s)
        if o != parent_label:
            entries.add(o)
    return entries


# Evidence / argumentation parents: do not BFS into Experiment-level Goal/Step.
_NARROW_ACTIVATION_PARENTS = frozenset(
    {
        "whu_ScienceEvidence",
        "whu_SupportGraph",
        "mp_Claim",
    }
)


def activate_local_low_schema(
    parent_label: str,
    potential_schema: List[Any],
    *,
    hops: int = 2,
) -> LocalLowSchema:
    """mid2low entries → BFS along tier=low only → parent-local schema.

    Does **not** dump the full low schema. Expansion starts from mid2low entry
    labels (not from the mid parent itself via mid2low edges).

    ScienceEvidence / SupportGraph / Claim use hops=0 (entry labels only) so
    Goal/ResearchStep are not invented under evidence parents.
    """
    if not parent_label:
        return LocalLowSchema(parent_label="")
    mid2low_rows = route_mid2low_incident(parent_label, potential_schema)
    entries = mid2low_entry_labels(parent_label, mid2low_rows)
    low_all = filter_potential_schema(potential_schema, tiers={"low"})
    hop_n = max(0, int(hops))
    if parent_label in _NARROW_ACTIVATION_PARENTS:
        hop_n = 0
    frontier: Set[str] = set(entries)
    entity_labels: Set[str] = set(entries)
    selected_keys: Set[Tuple[str, str, str]] = set()
    low_rows: List[Any] = []

    for _ in range(hop_n):
        if not frontier:
            break
        nxt: Set[str] = set()
        for row in low_all:
            t = _row_triple(row)
            if not t:
                continue
            s, _rel, o = t
            if s not in frontier and o not in frontier:
                continue
            if t not in selected_keys:
                selected_keys.add(t)
                low_rows.append(row)
            if s not in entity_labels:
                entity_labels.add(s)
                nxt.add(s)
            if o not in entity_labels:
                entity_labels.add(o)
                nxt.add(o)
        frontier = nxt

    return LocalLowSchema(
        parent_label=parent_label,
        entry_labels=set(entries),
        entity_labels=entity_labels,
        mid2low_rows=list(mid2low_rows),
        low_rows=low_rows,
        hops=hop_n,
    )


def filter_low_rows_for_present_types(
    low_rows: List[Any],
    present_labels: Set[str],
) -> Tuple[List[Any], List[Tuple[str, str, str]]]:
    """Keep low rows whose both endpoints exist; return missing triples separately."""
    ok: List[Any] = []
    missing: List[Tuple[str, str, str]] = []
    for row in low_rows:
        t = _row_triple(row)
        if not t:
            continue
        s, rel, o = t
        if s in present_labels and o in present_labels:
            ok.append(row)
        else:
            missing.append(t)
    return ok, missing


def route_low_incident(
    child_label: str,
    potential_schema: List[Any],
) -> List[Any]:
    """low rows where subject or object equals child_label (no BFS closure)."""
    if not child_label:
        return []
    out: List[Any] = []
    for row in filter_potential_schema(potential_schema, tiers={"low"}):
        t = _row_triple(row)
        if not t:
            continue
        s, _rel, o = t
        if s == child_label or o == child_label:
            out.append(row)
    return out


def intersect_schema_rows(rows: List[Any], allow: List[Any]) -> List[Any]:
    """Keep rows whose (s,rel,o) appear in allow (order of rows preserved)."""
    allow_keys: Set[Tuple[str, str, str]] = set()
    for row in allow:
        t = _row_triple(row)
        if t:
            allow_keys.add(t)
    if not allow_keys:
        return []
    out: List[Any] = []
    for row in rows:
        t = _row_triple(row)
        if t and t in allow_keys:
            out.append(row)
    return out


def mid2low_rel_types(potential_schema: List[Any]) -> List[str]:
    """Distinct relation labels from mid2low schema rows (for Cypher)."""
    seen: Set[str] = set()
    ordered: List[str] = []
    for row in filter_potential_schema(potential_schema, tiers={"mid2low"}):
        t = _row_triple(row)
        if not t:
            continue
        rel = t[1]
        if rel not in seen:
            seen.add(rel)
            ordered.append(rel)
    return ordered


def partition_schema_batches(routed: List[Any]) -> List[Tuple[str, List[Any]]]:
    """Three-step extract order: entities/attach → mid→low residual → low→low."""
    mid2low: List[Any] = []
    low_other: List[Any] = []
    low_ll: List[Any] = []
    for row in routed:
        tier = (triple_tier(row) or "").lower()
        t = _row_triple(row)
        if not t:
            continue
        _s, rel, _o = t
        if tier == "mid2low":
            mid2low.append(row)
        elif rel in LOW_TO_LOW_RELS:
            low_ll.append(row)
        else:
            low_other.append(row)
    batches: List[Tuple[str, List[Any]]] = []
    if mid2low:
        batches.append(("entities_attach", mid2low))
    if low_other:
        batches.append(("low_entities", low_other))
    if low_ll:
        batches.append(("low_low_links", low_ll))
    if not batches and routed:
        batches.append(("all", list(routed)))
    return batches


_HASGOAL_ALLOWED_PARENTS = frozenset(
    {"whu_BioChemical_Experiment", "whu_Computational_Experiment"}
)


def schema_for_rule_ids(
    routed: List[Any],
    rule_ids: Iterable[str],
    *,
    parent_labels: Optional[Iterable[str]] = None,
) -> List[Any]:
    """Targeted Pass2 schema subset bound to Warning rule_ids.

    When parent is not Bio/Comp Experiment, never inject whu_hasGoal / Goal
    (avoids inventing Experiment structure under ScienceEvidence).
    """
    rules = {str(r).upper() for r in rule_ids}
    parent_labs = {str(x) for x in (parent_labels or [])}
    allow_has_goal = bool(parent_labs & _HASGOAL_ALLOWED_PARENTS)
    # W01 → need ResearchStep attach; W02 → ProcessedSpecimen output; Goal/TV etc.
    want_rels: Set[str] = set()
    want_labels: Set[str] = set()
    if "W01" in rules or "H04" in rules:
        want_rels |= {"p_plan_isStepOfPlan", "p_plan_isPrecededBy"}
        want_labels |= {"whu_ResearchStep"}
    if "H01-B" in rules or "H01B" in rules or any(r.replace("_", "-") == "H01-B" for r in rules):
        want_rels |= {"p_plan_isStepOfPlan"}
        want_labels |= {"whu_ResearchStep"}
    if "W02" in rules:
        want_rels |= {"whu_declaredOutput", "p_plan_isStepOfPlan"}
        want_labels |= {"whu_ProcessedSpecimen", "whu_ResearchStep"}
    if "W03" in rules or "GOAL" in "".join(rules):
        if allow_has_goal:
            want_rels |= {"whu_hasGoal", "p_plan_isOutputVarOf", "p_plan_isInputVarOf"}
            want_labels |= {"whu_Goal", "whu_TargetVariable"}
    if "W04" in rules:
        want_rels |= {"prov_hadMember"}
        want_labels |= {"whu_DataSet", "mp_Method"}
    if "W05" in rules:
        want_rels |= {"prov_hadMember", "mp_supports", "mp_challenges"}
        want_labels |= {"mp_Statement", "mp_Attribution", "mp_Reference"}
    if "H09" in rules or any(r.startswith("H09") for r in rules):
        want_rels |= {"p_plan_isStepOfPlan"}
        want_labels |= {"whu_ResearchStep"}
        if allow_has_goal:
            want_rels |= {"whu_hasGoal"}
            want_labels |= {"whu_Goal"}

    if not want_rels and not want_labels:
        return list(routed)

    out: List[Any] = []
    for row in routed:
        t = _row_triple(row)
        if not t:
            continue
        s, rel, o = t
        if not allow_has_goal and (rel == "whu_hasGoal" or s == "whu_Goal" or o == "whu_Goal"):
            continue
        if rel in want_rels or s in want_labels or o in want_labels:
            out.append(row)
    return out or list(routed)


def schema_for_rule_ids_intersect(
    routed: List[Any],
    rule_ids: Iterable[str],
    *,
    allow: Optional[List[Any]] = None,
    parent_labels: Optional[Iterable[str]] = None,
) -> List[Any]:
    """schema_for_rule_ids then intersect with allow set (incident mode)."""
    targeted = schema_for_rule_ids(routed, rule_ids, parent_labels=parent_labels)
    if allow is None:
        return targeted
    clipped = intersect_schema_rows(targeted, allow)
    return clipped if clipped else intersect_schema_rows(routed, allow)
