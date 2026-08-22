"""section_role normalization and Table 3 prior BAE role lookup."""
from __future__ import annotations

from typing import Any, Dict, List

BAE_ROLE_NAMES = frozenset({"EBM", "EEM", "MPU"})

SECTION_ROLE_ALIASES: Dict[str, str] = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "methods": "Methods_Materials",
    "materials": "Methods_Materials",
    "methods_materials": "Methods_Materials",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "references": "References",
    "bibliography": "References",
    "other": "Other",
}


def canonical_section(name: str) -> str:
    if not name:
        return "Other"
    key = name.strip()
    mapped = SECTION_ROLE_ALIASES.get(key.lower())
    if mapped:
        return mapped
    return key


def bae_roles_for_section(section_role: str, table3: Dict[str, Any]) -> List[str]:
    role = canonical_section(section_role)
    mappings = table3.get("mappings") or {}
    entry = mappings.get(role) or mappings.get("Other") or {}
    prior = entry.get("bae_roles_prior") or []
    return [r for r in prior if r in BAE_ROLE_NAMES]


def enrich_nodes_with_bae_roles(nodes: List[Any], table3: Dict[str, Any]) -> None:
    for node in nodes:
        md = node.metadata or {}
        role = canonical_section(md.get("section_role", "Other"))
        md["section_role"] = role
        md["bae_roles"] = bae_roles_for_section(role, table3)
        node.metadata = md
