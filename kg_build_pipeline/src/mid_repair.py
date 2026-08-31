"""Rule-targeted schema filtering and chunk resolution for mid quality gate."""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from neo4j import Driver

from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS

# rule_id -> allowed (subject, relation, object) triples for targeted re-extract.
RULE_TO_TRIPLES: Dict[str, List[Tuple[str, str, str]]] = {
    "M01": [("whu_SpecimenCollection", "whu_hasContext", "whu_EnvironmentFeature")],
    "M02": [("whu_SpecimenPreprocessing", "whu_fellow", "whu_SpecimenCollection")],
    "M03": [
        ("whu_BioChemical_Experiment", "whu_fellow", "whu_SpecimenPreprocessing"),
        ("whu_BioChemical_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
    ],
    "M04": [
        ("whu_Computational_Experiment", "whu_fellow", "whu_BioChemical_Experiment"),
        ("whu_Computational_Experiment", "whu_fellow", "whu_Computational_Experiment"),
    ],
    "M05": [
        ("whu_ScienceEvidence", "prov_wasDerivedFrom", "whu_Computational_Experiment"),
    ],
    "M06": [
        ("whu_ScienceEvidence", "mp_supports", "whu_SupportGraph"),
        ("whu_ScienceEvidence", "mp_challenges", "whu_SupportGraph"),
    ],
    "M13": [
        ("whu_SupportGraph", "mp_supports", "mp_Claim"),
        ("whu_SupportGraph", "mp_challenges", "mp_Claim"),
    ],
}

_M09_TRIPLE_RE = re.compile(
    r"illegal mid triple\s+(\[[^\]]*\])\s*-\[([^\]]+)\]\s*->\s*(\[[^\]]*\])",
    re.IGNORECASE,
)

_PREFERRED_SECTIONS = ("Methods_Materials", "Results", "Discussion", "Experiment")

# Lower = higher priority in repair queue.
_RULE_PRIORITY: Dict[str, int] = {
    "M13": 0,
    "M09": 1,
    "M06": 2,
    "M05": 3,
    "M04": 4,
    "M03": 5,
    "M02": 6,
    "M01": 7,
}

_DEFAULT_REJECT_RULES = ("M13", "M06")
_DEFAULT_MERGE_RULES = ("M13", "M06", "M01", "M02", "M03", "M04", "M05", "M09")


def _row_triple(row: Sequence[Any]) -> Optional[Tuple[str, str, str]]:
    if not isinstance(row, (list, tuple)) or len(row) < 3:
        return None
    return (str(row[0]), str(row[1]), str(row[2]))


def _filter_by_triples(
    potential_schema: List[Any],
    triples: List[Tuple[str, str, str]],
) -> List[Any]:
    allowed = set(triples)
    out: List[Any] = []
    for row in potential_schema:
        t = _row_triple(row)
        if t and t in allowed:
            out.append(row)
    return out


def _parse_m09_triple_from_reason(reason: str) -> Optional[Tuple[str, str, str]]:
    if not reason:
        return None
    m = _M09_TRIPLE_RE.search(reason)
    if not m:
        return None
    try:
        a_labels = ast.literal_eval(m.group(1))
        rel = m.group(2).strip()
        b_labels = ast.literal_eval(m.group(3))
    except (SyntaxError, ValueError):
        return None
    if not a_labels or not b_labels:
        return None
    return (str(a_labels[0]), rel, str(b_labels[0]))


def filter_potential_schema_by_rule(
    issue: Dict[str, Any],
    potential_schema: List[Any],
) -> List[Any]:
    """Return schema rows relevant to an issue's rule_id; fallback to full list if empty."""
    rule_id = str(issue.get("rule_id") or "").upper()
    if not rule_id:
        return list(potential_schema)

    if rule_id == "M09":
        triple = _parse_m09_triple_from_reason(str(issue.get("reason") or ""))
        if triple:
            filtered = _filter_by_triples(potential_schema, [triple])
            if filtered:
                return filtered
        return list(potential_schema)

    triples = RULE_TO_TRIPLES.get(rule_id)
    if not triples:
        return list(potential_schema)

    filtered = _filter_by_triples(potential_schema, triples)
    return filtered if filtered else list(potential_schema)


def lookup_chunk_from_neo4j(
    driver: Driver,
    database: str,
    filename: str,
    entity_name: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Read-only: find Chunk linked to entity via FROM_CHUNK."""
    if not entity_name:
        return None
    with driver.session(database=database) as session:
        rec = session.run(
            """
            MATCH (n {WHU_HASNAME: $name})-[:FROM_CHUNK]-(c:Chunk)
            WHERE c.filename = $filename
            RETURN c.index AS chunk_index, c.id AS chunk_id,
                   left(coalesce(c.text, ''), 80) AS text_head
            LIMIT 1
            """,
            name=entity_name,
            filename=filename,
        ).single()
    if rec is None:
        return None
    return dict(rec)


def _match_nodes_by_text_head(
    final_nodes: List[Any],
    text_head: str,
) -> Optional[List[Any]]:
    head = (text_head or "").strip()
    if not head:
        return None
    preview = head[:50]
    for n in final_nodes:
        text = (n.get_text() or "").strip()
        if preview and preview in text:
            return [n]
        if head and head in text:
            return [n]
    return None


def _match_nodes_by_chunk_key(
    final_nodes: List[Any],
    source_chunk: str,
) -> Optional[List[Any]]:
    key = str(source_chunk)
    for n in final_nodes:
        md = n.metadata or {}
        if str(md.get("chunk_id") or "") == key:
            return [n]
        if str(md.get("id") or "") == key:
            return [n]
    for n in final_nodes:
        if key in (n.get_text() or "")[:80]:
            return [n]
    return None


def _match_nodes_by_entity_hint(
    final_nodes: List[Any],
    entity_hint: Optional[str],
) -> Optional[List[Any]]:
    if not entity_hint:
        return None
    hint = str(entity_hint).lower()
    for n in final_nodes:
        text = (n.get_text() or "").lower()
        if hint and hint in text:
            return [n]
    return None


def _fallback_preferred_nodes(final_nodes: List[Any]) -> Tuple[List[Any], str]:
    preferred = []
    for n in final_nodes:
        role = (n.metadata or {}).get("section_role", "")
        if role in _PREFERRED_SECTIONS:
            preferred.append(n)
    if preferred:
        return preferred[:1], "section_fallback"
    if final_nodes:
        return final_nodes[:1], "first_chunk_fallback"
    return [], "no_nodes"


def _issue_entity_name(violation: Dict[str, Any]) -> Optional[str]:
    name = violation.get("entity_name") or violation.get("entity")
    if name is None:
        return None
    text = str(name).strip()
    return text or None


def _issue_key(issue: Dict[str, Any]) -> Optional[tuple[str, str]]:
    rule_id = str(issue.get("rule_id") or "").upper()
    entity = _issue_entity_name(issue)
    if not rule_id or not entity:
        return None
    return rule_id, entity.casefold()


def _sort_priority(issue: Dict[str, Any]) -> tuple[int, str]:
    rule_id = str(issue.get("rule_id") or "").upper()
    entity = _issue_entity_name(issue) or ""
    return (_RULE_PRIORITY.get(rule_id, 99), entity)


def _violation_to_issue(violation: Dict[str, Any]) -> Dict[str, Any]:
    entity = _issue_entity_name(violation) or ""
    rule_id = str(violation.get("rule_id") or "").upper()
    return {
        "rule_id": rule_id,
        "entity": entity,
        "entity_name": entity,
        "suggested_action": "REEXTRACT",
        "type": "VALIDATOR",
        "source": "validator",
        "reason": violation.get("message") or violation.get("reason") or "",
    }


def violations_for_reject(
    validation_report: Dict[str, Any],
    reject_rules: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Collect validator violations whose rule_id is listed in reject_rules."""
    rules = {str(r).upper() for r in (reject_rules or _DEFAULT_REJECT_RULES)}
    out: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for bucket, default_rules in (
        ("hard_violations", rules),
        ("warnings", rules),
    ):
        for item in validation_report.get(bucket) or []:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("rule_id") or "").upper()
            if rule_id not in default_rules:
                continue
            key = _issue_key(item)
            if key is None or key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def merge_repair_issues(
    review_issues: Optional[List[Dict[str, Any]]],
    validation_report: Dict[str, Any],
    *,
    merge_rules: Optional[Sequence[str]] = None,
    max_issues: int = 15,
) -> List[Dict[str, Any]]:
    """Merge reviewer issues with validator violations; reviewer wins on duplicate keys."""
    rules = {str(r).upper() for r in (merge_rules or _DEFAULT_MERGE_RULES)}
    merged: Dict[tuple[str, str], Dict[str, Any]] = {}

    for item in validation_report.get("hard_violations") or []:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("rule_id") or "").upper()
        if rule_id not in rules:
            continue
        key = _issue_key(item)
        if key is None:
            continue
        merged[key] = _violation_to_issue(item)

    for item in validation_report.get("warnings") or []:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("rule_id") or "").upper()
        if rule_id not in rules:
            continue
        key = _issue_key(item)
        if key is None or key in merged:
            continue
        merged[key] = _violation_to_issue(item)

    for item in review_issues or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("suggested_action", "")).upper()
        if action not in {"REEXTRACT", "EXPAND_SPAN", "RETYPE"}:
            continue
        key = _issue_key(item)
        if key is None:
            continue
        copy = dict(item)
        copy.setdefault("source", "reviewer")
        merged[key] = copy

    ordered = sorted(merged.values(), key=_sort_priority)
    if max_issues > 0:
        ordered = ordered[:max_issues]
    return ordered


def mark_entity_rejected(
    driver: Driver,
    database: str,
    filename: str,
    entity_name: Optional[str],
) -> int:
    """Mark document-scoped nodes by WHU_HASNAME as whu_rejected."""
    if not entity_name:
        return 0
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    with driver.session(database=database) as session:
        result = session.run(
            """
            MATCH (n)
            WHERE n.WHU_HASNAME = $name
              AND NOT n:Chunk AND NOT n:MetaPath
              AND coalesce(n.whu_rejected, false) = false
              AND (
                n.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
                  WHERE c.filename = $filename
                }
              )
            SET n.whu_rejected = true
            RETURN count(n) AS c
            """,
            name=entity_name,
            filename=filename,
            source_doc=source_doc,
        )
        return int(result.single()["c"])


def reject_violation_nodes(
    driver: Driver,
    database: str,
    filename: str,
    violations: List[Dict[str, Any]],
    mode: str = "mark",
) -> Dict[str, Any]:
    """Mark or delete nodes referenced by validator violations (by WHU_HASNAME)."""
    names: List[str] = []
    seen: set[str] = set()
    for v in violations:
        name = _issue_entity_name(v)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)

    if not names:
        return {"mode": mode, "count": 0, "names": []}

    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    mid_labels = sorted(MID_CORE_ENTITY_LABELS)

    if mode == "delete":
        with driver.session(database=database) as session:
            result = session.run(
                """
                MATCH (n)
                WHERE n.WHU_HASNAME IN $names
                  AND NOT n:Chunk AND NOT n:MetaPath
                  AND any(l IN labels(n) WHERE l IN $mid_labels)
                  AND (
                    n.source_doc = $source_doc
                    OR EXISTS {
                      MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
                      WHERE c.filename = $filename
                    }
                  )
                WITH collect(n) AS nodes
                WITH nodes, size(nodes) AS c
                FOREACH (x IN nodes | DETACH DELETE x)
                RETURN c
                """,
                names=names,
                filename=filename,
                source_doc=source_doc,
                mid_labels=mid_labels,
            )
            count = int(result.single()["c"])
        return {"mode": "delete", "count": count, "names": names}

    count = 0
    for name in names:
        count += mark_entity_rejected(driver, database, filename, name)
    return {"mode": "mark", "count": count, "names": names}


def resolve_chunk_nodes(
    driver: Driver,
    database: str,
    filename: str,
    final_nodes: List[Any],
    issue: Dict[str, Any],
) -> Tuple[Optional[List[Any]], str]:
    """Resolve memory chunk nodes for a repair issue; returns (nodes, method)."""
    if not final_nodes:
        return None, "no_nodes"

    entity = issue.get("entity")
    source_chunk = issue.get("source_chunk")

    chunk_info = lookup_chunk_from_neo4j(driver, database, filename, entity)
    if chunk_info:
        text_head = chunk_info.get("text_head") or ""
        nodes = _match_nodes_by_text_head(final_nodes, text_head)
        if nodes:
            return nodes, "neo4j_from_chunk"
        chunk_index = chunk_info.get("chunk_index")
        if chunk_index is not None:
            for n in final_nodes:
                md = n.metadata or {}
                if str(md.get("chunk_id") or "") == str(chunk_index):
                    return [n], "neo4j_chunk_index"

    if source_chunk:
        nodes = _match_nodes_by_chunk_key(final_nodes, str(source_chunk))
        if nodes:
            return nodes, "reviewer_source_chunk"

    nodes = _match_nodes_by_entity_hint(final_nodes, entity)
    if nodes:
        return nodes, "entity_text_match"

    fallback, method = _fallback_preferred_nodes(final_nodes)
    return (fallback if fallback else None), method
