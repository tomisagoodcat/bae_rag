"""Constrained CheBI alignment: LLM may only emit lookup keys or pick an index ID."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from kg_build_pipeline.src.entity_normalize.ontology_lookup import OntologyHit, OntologyIndex
from kg_build_pipeline.src.entity_normalize.text_keys import extract_lookup_keys

CompleteJson = Callable[[str], Any]

_ID_RE = re.compile(r"^(CHEBI|ENVO|NCBITAXON):\S+$", re.I)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


@dataclass(frozen=True)
class AlignmentResult:
    hit: OntologyHit
    match_type: str  # exact | llm
    method: str
    confidence: float
    query_text: str


class LlmAligner:
    """JSON-only DeepSeek (or injectable complete_json) for key rewrite and candidate pick."""

    def __init__(
        self,
        *,
        llm: Any = None,
        complete_json: Optional[CompleteJson] = None,
        max_keys: int = 6,
    ):
        self._llm = llm
        self._complete_json = complete_json
        self.max_keys = max(1, int(max_keys))

    def rewrite_lookup_keys(self, original_text: str, label: str) -> list[str]:
        prompt = (
            "You map a scientific entity mention to CheBI lookup strings.\n"
            "Return JSON only: {\"keys\": [\"...\"]}.\n"
            "keys must be English names, formulas, or element symbols that might appear "
            "in CheBI labels (e.g. Hg, mercury, nitric acid, HNO3).\n"
            "Do NOT output ontology IDs (no CHEBI:).\n"
            "If unsure, return {\"keys\": []}.\n"
            f"entity_label: {label}\n"
            f"original_text: {original_text}\n"
        )
        payload = self._invoke_json(prompt)
        raw_keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(raw_keys, list):
            return []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw_keys:
            key = str(item or "").strip()
            if not key or _ID_RE.match(key) or key in seen:
                continue
            seen.add(key)
            out.append(key)
            if len(out) >= self.max_keys:
                break
        return out

    def pick_candidate(
        self,
        original_text: str,
        label: str,
        candidates: Sequence[OntologyHit],
    ) -> Optional[str]:
        allowed = {c.external_id for c in candidates}
        if not allowed:
            return None
        listing = "\n".join(
            f"- {c.external_id} | pref={c.pref_label} | matched={c.matched_label}"
            for c in candidates
        )
        prompt = (
            "Select the single CheBI term that best matches the mention, "
            "or abstain.\n"
            "Return JSON only: {\"external_id\": \"CHEBI:...\"} or {\"external_id\": null}.\n"
            "You MUST copy external_id from the candidate list. Do not invent IDs.\n"
            f"entity_label: {label}\n"
            f"original_text: {original_text}\n"
            f"candidates:\n{listing}\n"
        )
        payload = self._invoke_json(prompt)
        if not isinstance(payload, dict):
            return None
        chosen = payload.get("external_id")
        if chosen is None:
            return None
        eid = str(chosen).strip()
        if eid not in allowed:
            return None
        return eid

    def _invoke_json(self, prompt: str) -> dict[str, Any]:
        try:
            if self._complete_json is not None:
                raw = self._complete_json(prompt)
            elif self._llm is not None:
                resp = self._llm.invoke(prompt)
                content = getattr(resp, "content", resp)
                raw = _parse_json_object(str(content or ""))
            else:
                return {}
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _FENCE_RE.sub("", (text or "").strip()).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return {}
    data = json.loads(cleaned[start : end + 1])
    return data if isinstance(data, dict) else {}


def resolve_external_hit(
    index: OntologyIndex,
    *,
    label: str,
    original_text: str,
    query: str,
    aligner: Optional[LlmAligner],
    llm_labels: set[str],
    max_candidates: int = 8,
    confidence_llm: float = 0.6,
) -> Optional[AlignmentResult]:
    """Exact lookup first; optional constrained LLM only for configured labels."""
    exact = index.exact_lookup(query)
    if exact is not None:
        return AlignmentResult(
            hit=exact,
            match_type="exact",
            method="lexical",
            confidence=1.0,
            query_text=query,
        )
    if aligner is None or label not in llm_labels:
        return None
    keys = extract_lookup_keys(original_text)
    keys.extend(aligner.rewrite_lookup_keys(original_text, label))
    candidates = index.harvest_candidates(keys, max_candidates=max_candidates)
    if not candidates:
        return None
    chosen_id = aligner.pick_candidate(original_text, label, candidates)
    if not chosen_id:
        return None
    allowed = {c.external_id for c in candidates}
    if chosen_id not in allowed:
        return None
    verified = index.lookup_by_id(chosen_id)
    if verified is None:
        return None
    matched = verified.matched_label
    for cand in candidates:
        if cand.external_id == chosen_id:
            matched = cand.matched_label
            verified = OntologyHit(
                external_id=verified.external_id,
                external_uri=verified.external_uri,
                pref_label=verified.pref_label,
                source_ontology=verified.source_ontology,
                matched_label=matched,
            )
            break
    return AlignmentResult(
        hit=verified,
        match_type="llm",
        method="llm",
        confidence=float(confidence_llm),
        query_text=original_text,
    )


def build_llm_aligner(cfg) -> Optional[LlmAligner]:
    """None when llm_align is off or DeepSeek key is missing."""
    opts = (getattr(cfg, "entity_normalize", None) or {}).get("external_concept") or {}
    if not bool(opts.get("llm_align", False)):
        return None
    api_key = getattr(cfg, "deepseek_api_key", "") or ""
    if not api_key:
        return None
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=getattr(cfg, "deepseek_model", "deepseek-chat"),
        api_key=api_key,
        base_url=getattr(cfg, "deepseek_base_url", "https://api.deepseek.com/v1"),
        temperature=0,
        max_tokens=400,
    )
    return LlmAligner(llm=llm)