"""Text normalization for merge keys and conservative ontology lookup."""
from __future__ import annotations

import re

# Strip leading concentration / grade qualifiers before Reagent ontology lookup.
_REAGENT_PREFIX_RE = re.compile(
    r"^(\s*(?:\d+(?:\.\d+)?\s*%|suprapure|analytical\s+grade|"
    r"reagent\s+grade|ACS\s+grade|HPLC\s+grade|trace\s+metal\s+grade)\s*[-,]?\s*)+",
    re.IGNORECASE,
)


def normalize_original_text(value: str | None) -> str:
    """Trim only; preserve case (chemical symbols are case-sensitive)."""
    return (value or "").strip()


def hard_merge_key(label: str, source_doc: str, original_text: str | None) -> tuple[str, str, str] | None:
    """Return merge key or None when original text is empty after trim."""
    ot = normalize_original_text(original_text)
    if not ot:
        return None
    sd = (source_doc or "").strip()
    if not sd:
        return None
    return (label, sd, ot)


def ontology_lookup_query(label: str, original_text: str | None) -> str | None:
    """Conservative lookup string for exact index match (no inference)."""
    ot = normalize_original_text(original_text)
    if not ot:
        return None
    if label == "whu_Reagent":
        ot = normalize_reagent_for_lookup(ot)
        if not ot:
            return None
    return ot


def normalize_reagent_for_lookup(text: str) -> str:
    """Remove concentration/grade prefixes; keep substance name verbatim otherwise."""
    cleaned = _REAGENT_PREFIX_RE.sub("", text).strip()
    return cleaned or text.strip()


_SPLIT_RE = re.compile(r"[\s,;:|/（）()\[\]{}·•\-]+")
# Latin element/formula fragments: Hg, As, Cd, HNO3, MeHg, Cd2+
_FORMULA_RE = re.compile(r"(?:MeHg|THg|iAs|[A-Z][a-z]?(?:\d+[+-]?|[+-])?|(?:[A-Z][a-z]?\d*){1,8})")


def extract_lookup_keys(text: str | None, *, min_length: int = 2) -> list[str]:
    """Conservative extra exact-lookup keys (tokens/symbols), no translation."""
    raw = normalize_original_text(text)
    keys: list[str] = []
    seen: set[str] = set()

    def add(item: str) -> None:
        item = (item or "").strip()
        if len(item) < min_length or item in seen:
            return
        seen.add(item)
        keys.append(item)

    add(raw)
    add(normalize_reagent_for_lookup(raw))
    for tok in _SPLIT_RE.split(raw):
        add(tok)
    for match in _FORMULA_RE.finditer(raw):
        add(match.group(0))
    return keys
