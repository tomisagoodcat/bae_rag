"""Low-graph structural validation (BAE_low_shapes → Cypher/Python mirror)."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from neo4j import Driver

from kg_build_pipeline.src.low_parent_context import text_supported_by_corpus
from kg_build_pipeline.src.low_schema_router import (
    PARENT_LABEL_TO_RESEARCH_TYPE,
    RESEARCH_TYPE_TO_PARENT_LABEL,
)
from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS

VALID_RESEARCH_TYPES = set(PARENT_LABEL_TO_RESEARCH_TYPE.values())

SHARED_ENTITY_LABELS = {
    "mp_Method",
    "whu_Device",
    "whu_Reagent",
    "whu_Software",
    "whu_Specimen",
    "whu_ProcessedSpecimen",
    "whu_DataSet",
    "whu_ChemicalEntity",
    "whu_TargetVariable",
}


def _issue(
    rule_id: str,
    severity: str,
    entity_id: Any,
    message: str,
    *,
    entity_name: Any = None,
    labels: Any = None,
    bucket: str = "warnings",
) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "labels": labels,
        "message": message,
        "bucket": bucket,
    }


def check_h01b_research_type(
    steps: List[Dict[str, Any]],
    *,
    parent_labels: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """H01-B: ResearchStep.WHU_RESEARCHTYPE must exist and match isStepOfPlan parent.

    ``steps`` items may include: id, name, labels, research_type, parent_labels (list).
    When ``parent_labels`` is provided (parent-local validate), it is used as fallback
    parent type for steps that omit parent_labels.
    """
    issues: List[Dict[str, Any]] = []
    fallback_parents = set(parent_labels or [])
    for s in steps:
        sid = s.get("id")
        rt = s.get("research_type")
        rt_s = str(rt).strip() if rt is not None else ""
        if not rt_s or rt_s not in VALID_RESEARCH_TYPES:
            issues.append(
                _issue(
                    "H01-B",
                    "Violation",
                    sid,
                    "H01-B: ResearchStep must have exactly one valid researchType "
                    "(SpecimenCollection / SpecimenProcessing / BioChemical / Computational).",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )
            continue
        expected_parent = RESEARCH_TYPE_TO_PARENT_LABEL.get(rt_s)
        p_labs = set(s.get("parent_labels") or []) or fallback_parents
        if expected_parent and p_labs and expected_parent not in p_labs:
            issues.append(
                _issue(
                    "H01-B",
                    "Violation",
                    sid,
                    f"H01-B: ResearchStep researchType={rt_s} inconsistent with "
                    f"isStepOfPlan parent labels {sorted(p_labs)}.",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )
        # Dual-parent Bio+Comp (or any two distinct experiment parents)
        parents = list(s.get("parent_ids") or [])
        if len(parents) > 1:
            issues.append(
                _issue(
                    "H01",
                    "Violation",
                    sid,
                    "H01: ResearchStep must belong to exactly one Mid Parent.",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )
    return issues


def repair_h01b_is_step_of_plan(
    driver: Driver,
    database: str,
    *,
    parent_element_id: str,
    parent_labels: Optional[List[str]] = None,
    step_ids: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Relation-level fix for H01-B: drop mismatched isStepOfPlan; re-link if scoped.

    Does **not** re-extract entities, delete Experiments, or touch other Low edges.
    - Deletes ``(ResearchStep)-[:p_plan_isStepOfPlan]->(parent)`` when
      WHU_RESEARCHTYPE is inconsistent with this parent's mid label.
    - If the step has ``whu_parent_scope_id`` equal to a type-matching mid parent,
      MERGE the correct isStepOfPlan (only when no other isStepOfPlan remains).
    """
    from kg_build_pipeline.src.low_schema_router import research_type_for_parent

    plabels = list(parent_labels or [])
    parent_rt = None
    for lab in plabels:
        parent_rt = research_type_for_parent(str(lab))
        if parent_rt:
            break

    deleted = 0
    relinked = 0
    typed = 0
    with driver.session(database=database) as session:
        # 0) Fill missing researchType from this parent when step is already linked here
        if parent_rt:
            r0 = session.run(
                """
                MATCH (s:whu_ResearchStep)-[:p_plan_isStepOfPlan]->(p)
                WHERE elementId(p) = $pid
                  AND coalesce(s.whu_rejected, false) = false
                  AND (s.WHU_RESEARCHTYPE IS NULL OR trim(toString(s.WHU_RESEARCHTYPE)) = '')
                SET s.WHU_RESEARCHTYPE = $parent_rt
                RETURN count(*) AS cnt
                """,
                pid=parent_element_id,
                parent_rt=parent_rt,
            ).single()
            typed = int(r0["cnt"]) if r0 else 0

        # 1) Delete edges from steps under this parent when researchType mismatches
        if parent_rt:
            params: Dict[str, Any] = {
                "pid": parent_element_id,
                "parent_rt": parent_rt,
            }
            id_filter = ""
            if step_ids:
                id_filter = "AND elementId(s) IN $step_ids"
                params["step_ids"] = list(step_ids)
            r = session.run(
                f"""
                MATCH (s:whu_ResearchStep)-[r:p_plan_isStepOfPlan]->(p)
                WHERE elementId(p) = $pid
                  AND coalesce(s.whu_rejected, false) = false
                  AND s.WHU_RESEARCHTYPE IS NOT NULL
                  AND s.WHU_RESEARCHTYPE <> $parent_rt
                  {id_filter}
                DELETE r
                RETURN count(*) AS cnt
                """,
                **params,
            ).single()
            deleted = int(r["cnt"]) if r else 0

        # 2) For steps scoped to this parent with matching researchType and no plan link, MERGE
        if parent_rt:
            r2 = session.run(
                """
                MATCH (p) WHERE elementId(p) = $pid
                MATCH (s:whu_ResearchStep)
                WHERE coalesce(s.whu_rejected, false) = false
                  AND s.WHU_RESEARCHTYPE = $parent_rt
                  AND s.whu_parent_scope_id = $pid
                  AND NOT EXISTS { MATCH (s)-[:p_plan_isStepOfPlan]->() }
                MERGE (s)-[:p_plan_isStepOfPlan]->(p)
                RETURN count(*) AS cnt
                """,
                pid=parent_element_id,
                parent_rt=parent_rt,
            ).single()
            relinked = int(r2["cnt"]) if r2 else 0

        # 3) Scoped steps: delete Bio↔Comp cross edges to the wrong experiment type
        r3 = session.run(
            """
            MATCH (s:whu_ResearchStep)-[r:p_plan_isStepOfPlan]->(bad)
            WHERE coalesce(s.whu_rejected, false) = false
              AND s.whu_parent_scope_id = $pid
              AND s.WHU_RESEARCHTYPE IS NOT NULL
              AND (
                (s.WHU_RESEARCHTYPE = 'BioChemical'
                 AND 'whu_Computational_Experiment' IN labels(bad))
                OR
                (s.WHU_RESEARCHTYPE = 'Computational'
                 AND 'whu_BioChemical_Experiment' IN labels(bad))
              )
            DELETE r
            RETURN count(*) AS cnt
            """,
            pid=parent_element_id,
        ).single()
        deleted += int(r3["cnt"]) if r3 else 0

    return {
        "deleted_edges": deleted,
        "relinked_edges": relinked,
        "typed_steps": typed,
        "parent_element_id": parent_element_id,
        "parent_research_type": parent_rt,
        "mode": "relation_only",
    }


def check_h04_research_steps(
    steps: List[Dict[str, Any]],
    edges: List[Tuple[Any, Any]],
    *,
    parent_id: Any = None,
) -> List[Dict[str, Any]]:
    """H04: self-loop/cycle/cross-parent/illegal = HARD; missing network = WARNING.

    ``steps`` items: {id, name, labels, parent_id}
    ``edges``: list of (from_id, to_id) for isPrecededBy (from isPrecededBy to).
    """
    issues: List[Dict[str, Any]] = []
    if not steps:
        return issues

    id_set = {s["id"] for s in steps}
    by_id = {s["id"]: s for s in steps}

    # Self-loops
    for a, b in edges:
        if a == b and a in id_set:
            s = by_id[a]
            issues.append(
                _issue(
                    "H04",
                    "Violation",
                    a,
                    "H04-a: ResearchStep isPrecededBy self-loop.",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )

    # Illegal target (edge endpoint not a known ResearchStep in scope)
    for a, b in edges:
        if a in id_set and b not in id_set:
            s = by_id[a]
            issues.append(
                _issue(
                    "H04",
                    "Violation",
                    a,
                    "H04: isPrecededBy target is not a ResearchStep (illegal type/scope).",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )

    # Cross-parent
    for a, b in edges:
        if a not in id_set or b not in id_set:
            continue
        pa = by_id[a].get("parent_id")
        pb = by_id[b].get("parent_id")
        if pa is not None and pb is not None and pa != pb:
            issues.append(
                _issue(
                    "H04",
                    "Violation",
                    a,
                    "H04-e: isPrecededBy crosses Mid Parent boundaries.",
                    entity_name=by_id[a].get("name"),
                    labels=by_id[a].get("labels"),
                    bucket="hard_violations",
                )
            )

    # Directed cycle among steps that share parent_id filter
    if parent_id is not None:
        local = [s for s in steps if s.get("parent_id") == parent_id]
    else:
        local = list(steps)
    local_ids = {s["id"] for s in local}
    adj: Dict[Any, List[Any]] = defaultdict(list)
    undirected: Dict[Any, Set[Any]] = defaultdict(set)
    for a, b in edges:
        if a in local_ids and b in local_ids and a != b:
            adj[a].append(b)
            undirected[a].add(b)
            undirected[b].add(a)

    # Cycle detection (DFS color)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in local_ids}
    cycle_nodes: Set[Any] = set()

    def dfs(u: Any) -> bool:
        color[u] = GRAY
        for v in adj.get(u, []):
            if color[v] == GRAY:
                cycle_nodes.add(u)
                return True
            if color[v] == WHITE and dfs(v):
                cycle_nodes.add(u)
                return True
        color[u] = BLACK
        return False

    for i in local_ids:
        if color[i] == WHITE:
            dfs(i)
    for nid in cycle_nodes:
        s = by_id[nid]
        issues.append(
            _issue(
                "H04",
                "Violation",
                nid,
                "H04-b: ResearchStep isPrecededBy forms a directed cycle.",
                entity_name=s.get("name"),
                labels=s.get("labels"),
                bucket="hard_violations",
            )
        )

    # WARNING: >=2 steps but not fully linked / not weakly connected
    if len(local) >= 2:
        degree: Dict[Any, int] = {s["id"]: 0 for s in local}
        for a, b in edges:
            if a in local_ids and b in local_ids and a != b:
                degree[a] = degree.get(a, 0) + 1
                degree[b] = degree.get(b, 0) + 1
        for s in local:
            if degree.get(s["id"], 0) == 0:
                issues.append(
                    _issue(
                        "H04",
                        "Warning",
                        s["id"],
                        "H04-c: multiple ResearchSteps under parent but this step has no isPrecededBy edge.",
                        entity_name=s.get("name"),
                        labels=s.get("labels"),
                        bucket="warnings",
                    )
                )
        # Weak connectivity
        start = next(iter(local_ids))
        seen: Set[Any] = set()
        q: deque = deque([start])
        while q:
            u = q.popleft()
            if u in seen:
                continue
            seen.add(u)
            for v in undirected.get(u, ()):
                if v not in seen:
                    q.append(v)
        if seen != local_ids:
            for s in local:
                if s["id"] not in seen:
                    issues.append(
                        _issue(
                            "H04",
                            "Warning",
                            s["id"],
                            "H04-d: ResearchSteps under parent are not one weakly connected isPrecededBy component.",
                            entity_name=s.get("name"),
                            labels=s.get("labels"),
                            bucket="warnings",
                        )
                    )

    return issues


def check_h09_evidence(
    *,
    research_steps: List[Dict[str, Any]],
    goals: List[Dict[str, Any]],
    shared_entities: List[Dict[str, Any]],
    parent_corpus: str,
    parent_labels: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """H09-A HARD for ResearchStep/Goal; H09-B WARNING for shared entities.

    Orphan Goal (H09) is only HARD for Bio/Comp Experiment parents. Other parents
    must not invent hasGoal — orphans are cleaned separately, not repaired.
    """
    issues: List[Dict[str, Any]] = []
    labs = {str(x) for x in (parent_labels or [])}
    allow_orphan_goal_hard = bool(
        labs
        & {"whu_BioChemical_Experiment", "whu_Computational_Experiment"}
    )
    for s in research_steps:
        ot = s.get("original_text") or ""
        if ot and not text_supported_by_corpus(ot, parent_corpus):
            issues.append(
                _issue(
                    "H09-A",
                    "Violation",
                    s.get("id"),
                    "H09-A: ResearchStep original_text not supported by parent original ∪ home chunk.",
                    entity_name=s.get("name"),
                    labels=s.get("labels"),
                    bucket="hard_violations",
                )
            )
    for g in goals:
        ot = g.get("original_text") or ""
        if ot and not text_supported_by_corpus(ot, parent_corpus):
            issues.append(
                _issue(
                    "H09-A",
                    "Violation",
                    g.get("id"),
                    "H09-A: Goal original_text not supported by parent original ∪ home chunk.",
                    entity_name=g.get("name"),
                    labels=g.get("labels"),
                    bucket="hard_violations",
                )
            )
        # Orphan Goal (no hasGoal from mid parent) — HARD only for Experiment
        if g.get("orphan") and allow_orphan_goal_hard:
            issues.append(
                _issue(
                    "H09",
                    "Violation",
                    g.get("id"),
                    "H09: Goal is not linked to a Mid Parent via whu_hasGoal (orphan).",
                    entity_name=g.get("name"),
                    labels=g.get("labels"),
                    bucket="hard_violations",
                )
            )
    for e in shared_entities:
        ot = e.get("original_text") or ""
        if ot and not text_supported_by_corpus(ot, parent_corpus):
            # Outside parent original but may be in neighbor — WARNING only
            issues.append(
                _issue(
                    "H09-B",
                    "Warning",
                    e.get("id"),
                    "H09-B: shared entity original_text outside parent∪home; keep edge, review neighbor provenance.",
                    entity_name=e.get("name"),
                    labels=e.get("labels"),
                    bucket="warnings",
                )
            )
    return issues


def purge_illegal_has_goal_and_orphan_goals(
    driver: Driver,
    database: str,
    *,
    parent_element_id: str,
    parent_labels: List[str],
    filename: str,
) -> Dict[str, int]:
    """Delete illegal SE→hasGoal edges and scoped orphan Goals for non-Experiment parents.

    Does not invent replacement edges. Experiment parents are left untouched.
    """
    labs = {str(x) for x in (parent_labels or [])}
    if labs & {"whu_BioChemical_Experiment", "whu_Computational_Experiment"}:
        return {"deleted_has_goal": 0, "deleted_orphan_goals": 0}
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    with driver.session(database=database) as session:
        r1 = session.run(
            """
            MATCH (p) WHERE elementId(p) = $pid
            OPTIONAL MATCH (p)-[r:whu_hasGoal]->(g:whu_Goal)
            DELETE r
            RETURN count(r) AS c
            """,
            pid=parent_element_id,
        ).single()
        deleted_edges = int(r1["c"]) if r1 else 0
        r2 = session.run(
            """
            MATCH (g:whu_Goal)
            WHERE coalesce(g.whu_rejected, false) = false
              AND g.whu_parent_scope_id = $pid
              AND NOT EXISTS { MATCH ()-[:whu_hasGoal]->(g) }
              AND (
                g.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(g) WHERE c.filename = $filename
                }
              )
            DETACH DELETE g
            RETURN count(g) AS c
            """,
            pid=parent_element_id,
            filename=filename,
            source_doc=source_doc,
        ).single()
        deleted_goals = int(r2["c"]) if r2 else 0
    return {"deleted_has_goal": deleted_edges, "deleted_orphan_goals": deleted_goals}


def check_schema_type_violation(
    *,
    parent_labels: List[str],
    child_labels: List[str],
    allowed_child_labels: Set[str],
    entity_id: Any = None,
    entity_name: Any = None,
) -> Optional[Dict[str, Any]]:
    """HARD when extracted child type is not in parent-routed schema (Test10)."""
    child = set(child_labels or [])
    if not child:
        return None
    if child & allowed_child_labels:
        return None
    if child & MID_CORE_ENTITY_LABELS:
        return None
    return _issue(
        "H05",
        "Violation",
        entity_id,
        f"Schema/type violation: child labels {sorted(child)} not allowed for parent {parent_labels}.",
        entity_name=entity_name,
        labels=list(child_labels or []),
        bucket="hard_violations",
    )


def _report_from_issues(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    hard = [i for i in issues if i.get("bucket") == "hard_violations" or i.get("severity") == "Violation"]
    warn = [i for i in issues if i.get("bucket") == "warnings" or i.get("severity") == "Warning"]
    # Avoid double-count if severity Warning but bucket wrong
    hard_ids = {(i.get("rule_id"), i.get("entity_id"), i.get("message")) for i in hard}
    warn = [i for i in warn if (i.get("rule_id"), i.get("entity_id"), i.get("message")) not in hard_ids]
    return {
        "hard_violations": hard,
        "warnings": warn,
        "hard_count": len(hard),
        "warning_count": len(warn),
    }


def validate_low_parent_local(
    driver: Driver,
    database: str,
    filename: str,
    parent_element_id: str,
    *,
    parent_corpus: str = "",
    allowed_child_labels: Optional[Set[str]] = None,
    include_final_rules: bool = False,
) -> Dict[str, Any]:
    """Fetch parent-local low subgraph and run H04/H09 (+ optional Final) checks."""
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    issues: List[Dict[str, Any]] = []
    with driver.session(database=database) as session:
        parent = session.run(
            """
            MATCH (p) WHERE elementId(p) = $pid
            RETURN elementId(p) AS id, labels(p) AS labels,
                   p.WHU_HASNAME AS name,
                   coalesce(p.WHU_HASORIGINALTEXT, '') AS original_text
            """,
            pid=parent_element_id,
        ).single()
        if not parent:
            return _report_from_issues(
                [
                    _issue(
                        "H00",
                        "Violation",
                        parent_element_id,
                        "Parent node not found.",
                        bucket="hard_violations",
                    )
                ]
            )

        steps = session.run(
            """
            MATCH (s:whu_ResearchStep)-[:p_plan_isStepOfPlan]->(p)
            WHERE elementId(p) = $pid
              AND coalesce(s.whu_rejected, false) = false
            OPTIONAL MATCH (s)-[:p_plan_isStepOfPlan]->(op)
            WITH s, p, collect(DISTINCT elementId(op)) AS parent_ids,
                 collect(DISTINCT labels(op)) AS parent_label_lists
            RETURN elementId(s) AS id, s.WHU_HASNAME AS name,
                   labels(s) AS labels,
                   coalesce(s.WHU_HASORIGINALTEXT, '') AS original_text,
                   elementId(p) AS parent_id,
                   s.WHU_RESEARCHTYPE AS research_type,
                   parent_ids,
                   reduce(acc = [], labs IN parent_label_lists | acc + labs) AS parent_labels
            """,
            pid=parent_element_id,
        ).data()

        edges = session.run(
            """
            MATCH (a:whu_ResearchStep)-[:p_plan_isPrecededBy]->(b)
            WHERE coalesce(a.whu_rejected, false) = false
              AND coalesce(b.whu_rejected, false) = false
              AND EXISTS { MATCH (a)-[:p_plan_isStepOfPlan]->(p) WHERE elementId(p) = $pid }
            RETURN elementId(a) AS a, elementId(b) AS b,
                   [(b)-[:p_plan_isStepOfPlan]->(op) | elementId(op)] AS b_parents
            """,
            pid=parent_element_id,
        ).data()

        # Enrich step list with any edge endpoints (for illegal/cross-parent)
        step_map = {s["id"]: s for s in steps}
        edge_tuples: List[Tuple[Any, Any]] = []
        for e in edges:
            a, b = e["a"], e["b"]
            edge_tuples.append((a, b))
            b_parents = e.get("b_parents") or []
            if b not in step_map:
                step_map[b] = {
                    "id": b,
                    "name": None,
                    "labels": ["whu_ResearchStep"],
                    "original_text": "",
                    "parent_id": b_parents[0] if b_parents else None,
                }
        steps_all = list(step_map.values())
        plabels = set(parent.get("labels") or [])
        issues.extend(
            check_h01b_research_type(
                steps,
                parent_labels=list(plabels),
            )
        )
        issues.extend(
            check_h04_research_steps(steps_all, edge_tuples, parent_id=parent_element_id)
        )

        goals = session.run(
            """
            MATCH (g:whu_Goal)
            WHERE coalesce(g.whu_rejected, false) = false
              AND (
                EXISTS { MATCH (p)-[:whu_hasGoal]->(g) WHERE elementId(p) = $pid }
                OR g.source_doc = $source_doc
              )
            OPTIONAL MATCH (p)-[:whu_hasGoal]->(g)
            WHERE elementId(p) = $pid
            RETURN elementId(g) AS id, g.WHU_HASNAME AS name,
                   labels(g) AS labels,
                   coalesce(g.WHU_HASORIGINALTEXT, '') AS original_text,
                   p IS NULL AS orphan
            """,
            pid=parent_element_id,
            source_doc=source_doc,
        ).data()
        # Only goals linked to this parent or orphans in doc scoped carefully
        goals_local = [g for g in goals if not g.get("orphan") or g.get("orphan") is False]
        orphans = session.run(
            """
            MATCH (g:whu_Goal)
            WHERE coalesce(g.whu_rejected, false) = false
              AND (
                g.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(g) WHERE c.filename = $filename
                }
              )
              AND NOT EXISTS { MATCH ()-[:whu_hasGoal]->(g) }
            RETURN elementId(g) AS id, g.WHU_HASNAME AS name,
                   labels(g) AS labels,
                   coalesce(g.WHU_HASORIGINALTEXT, '') AS original_text,
                   true AS orphan
            """,
            filename=filename,
            source_doc=source_doc,
        ).data()

        shared = session.run(
            """
            MATCH (s:whu_ResearchStep)-[:p_plan_isStepOfPlan]->(p)
            WHERE elementId(p) = $pid
            MATCH (s)-[r]->(e)
            WHERE type(r) IN ['whu_declaredUsed','whu_declaredInput','whu_declaredOutput']
              AND coalesce(e.whu_rejected, false) = false
            RETURN DISTINCT elementId(e) AS id, e.WHU_HASNAME AS name,
                   labels(e) AS labels,
                   coalesce(e.WHU_HASORIGINALTEXT, '') AS original_text
            """,
            pid=parent_element_id,
        ).data()

        corpus = parent_corpus or (parent.get("original_text") or "")
        issues.extend(
            check_h09_evidence(
                research_steps=steps,
                goals=list(goals_local) + list(orphans),
                shared_entities=[
                    e
                    for e in shared
                    if set(e.get("labels") or []) & SHARED_ENTITY_LABELS
                ],
                parent_corpus=corpus,
                parent_labels=list(plabels),
            )
        )

        # W01: parent is experiment-like but no ResearchStep
        experimentish = plabels & {
            "whu_BioChemical_Experiment",
            "whu_Computational_Experiment",
            "whu_SpecimenPreprocessing",
            "whu_SpecimenCollection",
        }
        if experimentish and not steps:
            issues.append(
                _issue(
                    "W01",
                    "Warning",
                    parent_element_id,
                    "W01: Experiment/parent has no ResearchStep.",
                    entity_name=parent.get("name"),
                    labels=list(plabels),
                    bucket="warnings",
                )
            )

        if allowed_child_labels is not None:
            for e in shared:
                viol = check_schema_type_violation(
                    parent_labels=list(plabels),
                    child_labels=list(e.get("labels") or []),
                    allowed_child_labels=allowed_child_labels,
                    entity_id=e.get("id"),
                    entity_name=e.get("name"),
                )
                if viol:
                    issues.append(viol)

        if include_final_rules:
            # Final-only H06-ish: SupportGraph must link Claim
            sg_rows = session.run(
                """
                MATCH (sg:whu_SupportGraph)
                WHERE coalesce(sg.whu_rejected, false) = false
                  AND (
                    sg.source_doc = $source_doc
                    OR EXISTS {
                      MATCH (c:Chunk)-[:FROM_CHUNK]-(sg) WHERE c.filename = $filename
                    }
                  )
                OPTIONAL MATCH (sg)-[r:mp_supports|mp_challenges]->(cl:mp_Claim)
                WITH sg, count(cl) AS claim_n
                WHERE claim_n = 0
                RETURN elementId(sg) AS id, sg.WHU_HASNAME AS name, labels(sg) AS labels
                """,
                filename=filename,
                source_doc=source_doc,
            ).data()
            for sg in sg_rows:
                issues.append(
                    _issue(
                        "H06",
                        "Violation",
                        sg.get("id"),
                        "H06: Final SupportGraph missing mp_supports/mp_challenges → Claim.",
                        entity_name=sg.get("name"),
                        labels=sg.get("labels"),
                        bucket="hard_violations",
                    )
                )

    report = _report_from_issues(issues)
    report["parent_element_id"] = parent_element_id
    report["filename"] = filename
    return report


def validate_low_document_final(
    driver: Driver,
    database: str,
    filename: str,
) -> Dict[str, Any]:
    """Document-level Final SHACL (after cross-parent linking)."""
    mid_labels = sorted(MID_CORE_ENTITY_LABELS)
    all_issues: List[Dict[str, Any]] = []
    with driver.session(database=database) as session:
        pids = [
            r["id"]
            for r in session.run(
                """
                MATCH (n)
                WHERE any(l IN labels(n) WHERE l IN $mid_labels)
                  AND coalesce(n.whu_rejected, false) = false
                  AND EXISTS {
                    MATCH (ch:Chunk)-[:FROM_CHUNK]-(n) WHERE ch.filename = $filename
                  }
                RETURN elementId(n) AS id
                """,
                filename=filename,
                mid_labels=mid_labels,
            ).data()
        ]
    for pid in pids:
        rep = validate_low_parent_local(
            driver,
            database,
            filename,
            pid,
            include_final_rules=False,
        )
        all_issues.extend(rep.get("hard_violations") or [])
        all_issues.extend(rep.get("warnings") or [])
    all_issues.extend(_final_only(driver, database, filename).get("hard_violations") or [])
    return _report_from_issues(all_issues)


def _final_only(driver: Driver, database: str, filename: str) -> Dict[str, Any]:
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    issues: List[Dict[str, Any]] = []
    with driver.session(database=database) as session:
        sg_rows = session.run(
            """
            MATCH (sg:whu_SupportGraph)
            WHERE coalesce(sg.whu_rejected, false) = false
              AND (
                sg.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(sg) WHERE c.filename = $filename
                }
              )
            OPTIONAL MATCH (sg)-[:mp_supports|mp_challenges]->(cl:mp_Claim)
            WITH sg, count(cl) AS claim_n
            WHERE claim_n = 0
            RETURN elementId(sg) AS id, sg.WHU_HASNAME AS name, labels(sg) AS labels
            """,
            filename=filename,
            source_doc=source_doc,
        ).data()
        for sg in sg_rows:
            issues.append(
                _issue(
                    "H06",
                    "Violation",
                    sg.get("id"),
                    "H06: Final SupportGraph missing Claim link.",
                    entity_name=sg.get("name"),
                    labels=sg.get("labels"),
                    bucket="hard_violations",
                )
            )
    return _report_from_issues(issues)
