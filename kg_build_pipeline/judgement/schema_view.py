"""Read-only schema view for judgement."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from kg_build_pipeline.src.schema_loader import load_schema

from kg_build_pipeline.judgement.constants import INFRA_LABELS


def instantiable_classes(entities: Sequence[Dict]) -> List[str]:
    labels: List[str] = []
    seen: Set[str] = set()
    for ent in entities:
        lab = str(ent.get("label") or "").strip()
        if not lab or lab in INFRA_LABELS or lab in seen:
            continue
        seen.add(lab)
        labels.append(lab)
    return labels


def legal_triples(potential_schema: Sequence) -> Set[Tuple[str, str, str]]:
    out: Set[Tuple[str, str, str]] = set()
    for row in potential_schema:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        s, p, o = str(row[0]), str(row[1]), str(row[2])
        if s and p and o:
            out.add((s, p, o))
    return out


def load_judgement_schema(schema_dir=None) -> Tuple[List[str], Set[Tuple[str, str, str]]]:
    entities, _relations, potential_schema = load_schema(schema_dir)
    return instantiable_classes(entities), legal_triples(potential_schema)


def primary_bae_label(labels: Optional[Sequence[str]], instantiable: Sequence[str]) -> Optional[str]:
    labs = set(labels or [])
    for lab in instantiable:
        if lab in labs:
            return lab
    return None
