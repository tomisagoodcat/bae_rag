"""Compute frozen KG judgement metrics from a snapshot (no LLM)."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from kg_build_pipeline.judgement.constants import (
    EVIDENCE_LABELS,
    ORPHAN_ELIGIBLE_LABELS,
    ORPHAN_RULES,
    SAMPLE_LIMIT,
)
from kg_build_pipeline.judgement.graph_read import EdgeRec, GraphSnapshot, NodeRec, node_docs
from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS

Triple = Tuple[str, str, str]


def _nodes_for_doc(nodes: Sequence[NodeRec], filename: str) -> List[NodeRec]:
    return [n for n in nodes if filename in node_docs(n)]


def _edges_among(edges: Sequence[EdgeRec], ids: Set[str]) -> List[EdgeRec]:
    return [e for e in edges if e.src in ids and e.tgt in ids]


def class_population(nodes: Sequence[NodeRec], instantiable: Sequence[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {lab: 0 for lab in instantiable}
    for n in nodes:
        if n.bae_label in counts:
            counts[n.bae_label] += 1
    return counts


def class_richness(pop: Dict[str, int]) -> Dict[str, Any]:
    denom = len(pop)
    if denom == 0:
        return {"value": None, "status": "NOT_COMPUTABLE", "reason": "no instantiable classes"}
    populated = sum(1 for v in pop.values() if v > 0)
    return {
        "value": round(populated / denom, 6),
        "status": "OK",
        "populated_classes": populated,
        "instantiable_classes": denom,
    }


def average_population(pop: Dict[str, int]) -> Dict[str, Any]:
    denom = len(pop)
    if denom == 0:
        return {"value": None, "status": "NOT_COMPUTABLE", "reason": "no instantiable classes"}
    return {
        "value": round(sum(pop.values()) / denom, 6),
        "status": "OK",
        "instance_total": sum(pop.values()),
        "instantiable_classes": denom,
    }


def relation_schema_conformance(
    edges: Sequence[EdgeRec],
    legal: Set[Triple],
) -> Dict[str, Any]:
    eval_edges = [e for e in edges if e.src_label and e.tgt_label]
    denom = len(eval_edges)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no BAE–BAE relations to evaluate",
            "legal": 0,
            "total": 0,
            "illegal_samples": [],
        }
    legal_n = 0
    illegal_samples: List[Dict[str, Any]] = []
    for e in eval_edges:
        trip = (e.src_label, e.rel_type, e.tgt_label)
        if trip in legal:
            legal_n += 1
        elif len(illegal_samples) < SAMPLE_LIMIT:
            illegal_samples.append(
                {
                    "src": e.src,
                    "tgt": e.tgt,
                    "rel": e.rel_type,
                    "triple": list(trip),
                }
            )
    return {
        "value": round(legal_n / denom, 6),
        "status": "OK",
        "legal": legal_n,
        "total": denom,
        "illegal_samples": illegal_samples,
    }


def relation_conflict_rate(
    edges: Sequence[EdgeRec],
    legal: Set[Triple],
) -> Dict[str, Any]:
    eval_edges = [e for e in edges if e.src_label and e.tgt_label]
    denom = len(eval_edges)
    mutex = {
        "value": None,
        "status": "NOT_COMPUTABLE",
        "reason": "potential_schema has no mutex table; same-pair distinct relation types are not errors",
    }
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no BAE–BAE relations to evaluate",
            "duplicate_extra": 0,
            "illegal_direction": 0,
            "self_loop": 0,
            "mutex": mutex,
            "samples": [],
        }
    key_counts: Counter[Tuple[str, str, str]] = Counter()
    for e in eval_edges:
        key_counts[(e.src, e.rel_type, e.tgt)] += 1
    duplicate_extra = sum(c - 1 for c in key_counts.values() if c > 1)
    illegal_direction = 0
    self_loop = 0
    samples: List[Dict[str, Any]] = []
    for e in eval_edges:
        kinds: List[str] = []
        if e.src == e.tgt:
            self_loop += 1
            kinds.append("self_loop")
        trip = (e.src_label or "", e.rel_type, e.tgt_label or "")
        if trip not in legal:
            illegal_direction += 1
            kinds.append("illegal_direction")
        if kinds and len(samples) < SAMPLE_LIMIT:
            samples.append(
                {
                    "src": e.src,
                    "tgt": e.tgt,
                    "rel": e.rel_type,
                    "kinds": kinds,
                    "triple": list(trip),
                }
            )
    # duplicate extras counted separately (not per-edge unique to avoid double-count in numerator)
    conflict_n = duplicate_extra + illegal_direction + self_loop
    return {
        "value": round(conflict_n / denom, 6),
        "status": "OK",
        "duplicate_extra": duplicate_extra,
        "illegal_direction": illegal_direction,
        "self_loop": self_loop,
        "conflict_count": conflict_n,
        "total": denom,
        "mutex": mutex,
        "samples": samples,
        "note": "same-pair mp_supports+mp_challenges is not an RCR error",
    }


def provenance_coverage(nodes: Sequence[NodeRec]) -> Dict[str, Any]:
    denom = len(nodes)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no BAE instances",
            "covered": 0,
            "total": 0,
        }
    covered = 0
    for n in nodes:
        has_ot = bool((n.original_text or "").strip())
        has_doc = bool((n.source_doc or "").strip()) or bool(n.filenames)
        if has_ot and has_doc:
            covered += 1
    return {
        "value": round(covered / denom, 6),
        "status": "OK",
        "covered": covered,
        "total": denom,
    }


def _wcc_largest(ids: Sequence[str], edges: Sequence[EdgeRec]) -> int:
    if not ids:
        return 0
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    idset = set(ids)
    for e in edges:
        if e.src in idset and e.tgt in idset:
            union(e.src, e.tgt)
    sizes: Counter[str] = Counter(find(i) for i in ids)
    return max(sizes.values()) if sizes else 0


def connectivity_ratio(
    nodes: Sequence[NodeRec],
    edges: Sequence[EdgeRec],
    labels: Set[str],
) -> Dict[str, Any]:
    selected = [n for n in nodes if n.bae_label in labels]
    denom = len(selected)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no nodes in the frozen label set",
            "largest": 0,
            "total": 0,
        }
    ids = [n.eid for n in selected]
    largest = _wcc_largest(ids, _edges_among(edges, set(ids)))
    return {
        "value": round(largest / denom, 6),
        "status": "OK",
        "largest": largest,
        "total": denom,
    }


def has_legal_path_at_least(
    nodes: Sequence[NodeRec],
    edges: Sequence[EdgeRec],
    legal: Set[Triple],
    min_hops: int = 3,
) -> bool:
    """True if a schema-legal directed path with >= min_hops relationships exists."""
    adj: Dict[str, List[str]] = defaultdict(list)
    for e in edges:
        if not e.src_label or not e.tgt_label:
            continue
        if (e.src_label, e.rel_type, e.tgt_label) not in legal:
            continue
        adj[e.src].append(e.tgt)
    idset = {n.eid for n in nodes}
    for start in idset:
        stack = [(start, 0, {start})]
        while stack:
            cur, hops, seen = stack.pop()
            if hops >= min_hops:
                return True
            for nxt in adj.get(cur, []):
                if nxt not in idset or nxt in seen:
                    continue
                stack.append((nxt, hops + 1, seen | {nxt}))
    return False


def per_document_metrics(
    snap: GraphSnapshot,
    legal: Set[Triple],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for fn in snap.filenames:
        nodes = _nodes_for_doc(snap.nodes, fn)
        ids = {n.eid for n in nodes}
        edges = _edges_among(snap.edges, ids)
        dc = connectivity_ratio(nodes, edges, set(EVIDENCE_LABELS))
        mc = connectivity_ratio(nodes, edges, set(MID_CORE_ENTITY_LABELS))
        evidence_nodes = [n for n in nodes if n.bae_label in EVIDENCE_LABELS]
        mpc_ok = has_legal_path_at_least(evidence_nodes, edges, legal, 3)
        rows.append(
            {
                "filename": fn,
                "bae_nodes": len(nodes),
                "dc": dc,
                "mc": mc,
                "mpc_has_ge3": mpc_ok,
                "mpc_status": "OK",
            }
        )
    return rows


def multi_hop_path_coverage(doc_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    evaluable = [r for r in doc_rows if int(r.get("bae_nodes") or 0) > 0]
    denom = len(evaluable)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no papers with BAE nodes",
            "covered": 0,
            "total": 0,
        }
    covered = sum(1 for r in evaluable if r.get("mpc_has_ge3"))
    return {
        "value": round(covered / denom, 6),
        "status": "OK",
        "covered": covered,
        "total": denom,
    }


def duplicate_entity_rate() -> Dict[str, Any]:
    return {
        "value": None,
        "status": "NOT_COMPUTABLE",
        "reason": (
            "no high-confidence duplicate scorer: identical WHU_HASORIGINALTEXT is not a "
            "duplicate; WHU_HASNAME is an LLM title and must not be a duplicate-identity key"
        ),
    }


def duplicate_candidates(nodes: Sequence[NodeRec], limit: int = SAMPLE_LIMIT) -> List[Dict[str, Any]]:
    """Same document + same type + same FROM_CHUNK set. Not a duplicate judgement."""
    groups: Dict[Tuple[str, str, Tuple[str, ...]], List[NodeRec]] = defaultdict(list)
    for n in nodes:
        chunks = tuple(sorted(n.filenames))
        if not chunks or not n.bae_label:
            continue
        for fn in node_docs(n):
            groups[(fn, n.bae_label, chunks)].append(n)
    out: List[Dict[str, Any]] = []
    for (fn, lab, chunks), members in groups.items():
        uniq = {m.eid: m for m in members}
        if len(uniq) < 2:
            continue
        out.append(
            {
                "filename": fn,
                "label": lab,
                "chunk_filenames": list(chunks),
                "size": len(uniq),
                "names": [m.name for m in uniq.values()][:10],
                "note": "co-chunk same-type group only; not classified as duplicates",
            }
        )
        if len(out) >= limit:
            break
    return out


def resolve_issue_node_id(iss: Dict[str, Any], nodes: Sequence[NodeRec]) -> Optional[str]:
    """Map a validator issue onto a snapshot node (elementId or name+label)."""
    by_eid = {n.eid: n for n in nodes}
    raw = iss.get("entity_id") if iss.get("entity_id") is not None else iss.get("element_id")
    if raw is not None and str(raw) in by_eid:
        return str(raw)
    name = str(iss.get("entity_name") or "").strip()
    if not name and raw is not None:
        name = str(raw).strip()
    if not name:
        return None
    labels = {str(x) for x in (iss.get("labels") or []) if x}
    matches = [n for n in nodes if n.name == name]
    if labels:
        labeled = [
            n
            for n in matches
            if n.bae_label in labels or labels.intersection(n.labels)
        ]
        if labeled:
            matches = labeled
    if not matches:
        return None
    return matches[0].eid


def bind_issues_to_nodes(
    issues: Sequence[Dict[str, Any]],
    nodes: Sequence[NodeRec],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for iss in issues:
        row = dict(iss)
        eid = resolve_issue_node_id(row, nodes)
        if eid:
            row["entity_id"] = eid
        out.append(row)
    return out


def _issue_rule(issue: Dict[str, Any]) -> str:
    return str(issue.get("rule_id") or "").strip()


def _normalize_rule(rule_id: str) -> str:
    return rule_id.replace("_", "-").upper()


def shacl_conformance(
    inspected_ids: Sequence[str],
    hard_issues: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    inspected = {str(i) for i in inspected_ids if i is not None}
    denom = len(inspected)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no inspected BAE nodes",
            "hard_nodes": 0,
            "total": 0,
            "rule_counts": {},
        }
    hard_nodes: Set[str] = set()
    rule_counts: Counter[str] = Counter()
    for iss in hard_issues:
        if str(iss.get("bucket") or "") not in ("hard_violations", "") and str(
            iss.get("severity") or ""
        ) not in ("Violation", "HARD", ""):
            if str(iss.get("bucket")) == "warnings":
                continue
        if str(iss.get("bucket")) == "warnings" or str(iss.get("severity")) == "Warning":
            continue
        rule_counts[_issue_rule(iss)] += 1
        eid = iss.get("entity_id") or iss.get("element_id")
        if eid is not None:
            hard_nodes.add(str(eid))
    ok_n = sum(1 for i in inspected if i not in hard_nodes)
    return {
        "value": round(ok_n / denom, 6),
        "status": "OK",
        "hard_nodes": len(hard_nodes & inspected),
        "total": denom,
        "rule_counts": dict(rule_counts),
    }


def _is_orphan_issue(iss: Dict[str, Any]) -> bool:
    if str(iss.get("bucket")) == "isolated_nodes":
        return False
    rule = _issue_rule(iss)
    allowed = {_normalize_rule(r) for r in ORPHAN_RULES}
    return _normalize_rule(rule) in allowed or rule in ORPHAN_RULES


def orphan_rate(
    nodes: Sequence[NodeRec],
    issues: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    eligible = [n for n in nodes if n.bae_label in ORPHAN_ELIGIBLE_LABELS]
    denom = len(eligible)
    if denom == 0:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": "no orphan-eligible node types present",
            "orphan_nodes": 0,
            "total": 0,
            "rule_counts": {},
        }
    eligible_ids = {n.eid for n in eligible}
    orphan_ids: Set[str] = set()
    rule_counts: Counter[str] = Counter()
    for iss in issues:
        if not _is_orphan_issue(iss):
            continue
        eid = str(iss.get("entity_id") or iss.get("element_id") or "")
        if eid and eid in eligible_ids:
            orphan_ids.add(eid)
            rule_counts[_issue_rule(iss)] += 1
    return {
        "value": round(len(orphan_ids) / denom, 6),
        "status": "OK",
        "orphan_nodes": len(orphan_ids),
        "total": denom,
        "rule_counts": dict(rule_counts),
    }


def mean_ratio(doc_rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, Any]:
    vals = []
    for r in doc_rows:
        cell = r.get(key) or {}
        if cell.get("status") == "OK" and cell.get("value") is not None:
            vals.append(float(cell["value"]))
    if not vals:
        return {
            "value": None,
            "status": "NOT_COMPUTABLE",
            "reason": f"no per-document {key} values",
        }
    return {"value": round(sum(vals) / len(vals), 6), "status": "OK", "documents": len(vals)}
