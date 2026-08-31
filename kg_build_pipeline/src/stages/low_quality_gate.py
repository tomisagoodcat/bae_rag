"""Low quality gate: hard targeted repair + warning-triggered neighbor Pass2."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.agents.low_reviewer import review_low_parent
from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.low_parent_context import ParentContext, build_pass1_context, build_pass2_context
from kg_build_pipeline.src.low_schema_router import (
    route_low_incident,
    route_mid2low_incident,
    route_schema_for_parent,
    schema_for_rule_ids,
    schema_for_rule_ids_intersect,
)
from kg_build_pipeline.src.stages.low_extract import extract_for_parent
from kg_build_pipeline.src.stages.low_parents import fetch_mid2low_children, fetch_neighbor_chunks
from kg_build_pipeline.src.stages.low_validate import (
    purge_illegal_has_goal_and_orphan_goals,
    repair_h01b_is_step_of_plan,
    validate_low_parent_local,
)

EventCallback = Callable[[Dict[str, Any]], None]

# Rules whose repair targets low↔low on ResearchStep children (not Mid mid2low).
_CHILD_LOW_RULES = {"H04", "W02"}


def _norm_rule(r: str) -> str:
    return str(r or "").upper().replace("_", "-")


def _has_h01b(rule_ids: List[str]) -> bool:
    return any(_norm_rule(r) == "H01-B" for r in rule_ids)


def _non_h01b_rules(rule_ids: List[str]) -> List[str]:
    return [r for r in rule_ids if _norm_rule(r) != "H01-B"]


async def _repair_research_step_children(
    *,
    cfg: PipelineConfig,
    driver: Driver,
    filename: str,
    parent: Dict[str, Any],
    mid_ctx: ParentContext,
    potential_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    embed_model,
    custom_prompt: str,
    mid2low_rels: List[str],
    max_children: int,
    rule_ids: List[str],
    on_event: Optional[EventCallback],
    extract_phase: str,
) -> int:
    """Targeted low incident extract on ResearchStep children under Mid parent."""
    children = fetch_mid2low_children(
        driver,
        cfg.neo4j_database,
        filename,
        str(parent.get("element_id")),
        mid2low_rels=mid2low_rels,
        max_children=max_children,
    )
    ok_total = 0
    fp = ((cfg.raw or {}).get("low_extraction") or {}).get("first_pass") or {}
    for child in children:
        labs = set(child.get("labels") or [])
        if "whu_ResearchStep" not in labs:
            continue
        routed_low = route_low_incident("whu_ResearchStep", potential_schema)
        # Prefer edges demanded by rules (isPrecededBy / declared*)
        targeted = schema_for_rule_ids(
            routed_low, rule_ids, parent_labels=list(child.get("labels") or [])
        )
        if not targeted:
            targeted = routed_low
        child_orig = str(child.get("original_text") or "").strip()
        homes = list(child.get("home_chunks") or [])
        if not child_orig:
            child_orig = mid_ctx.parent_original_text or ""
        if not homes:
            homes = [
                {
                    "id": c.chunk_id,
                    "index": c.index,
                    "filename": c.filename,
                    "text": c.text,
                }
                for c in (mid_ctx.home_chunks or [])
            ]
        child_ctx = build_pass1_context(
            parent_element_id=str(child.get("element_id")),
            parent_name=child.get("name"),
            parent_labels=list(child.get("labels") or []),
            parent_original_text=child_orig,
            filename=filename,
            home_chunks=homes,
            use_parent_original_text=bool(fp.get("use_parent_original_text", True)),
            use_current_chunk=bool(fp.get("use_current_chunk", True)),
        )
        if not child_ctx.extraction_text().strip() or not targeted:
            continue
        if on_event:
            on_event(
                {
                    "type": "low_child_repair",
                    "filename": filename,
                    "parent": child.get("name"),
                    "mid_parent": parent.get("name"),
                    "rule_ids": rule_ids,
                    "schema_rows": len(targeted),
                    "phase": extract_phase,
                }
            )
        info = await extract_for_parent(
            ctx=child_ctx,
            routed_schema=targeted,
            entities=entities,
            relations=relations,
            llm=llm,
            neo4j_driver=driver,
            embed_model=embed_model,
            custom_prompt=custom_prompt,
            cfg=cfg,
            extract_phase=extract_phase,
            prompt_suffix=f"\n# Child ResearchStep targeted repair\nRules: {rule_ids}\n",
            on_event=on_event,
            filename=filename,
        )
        ok_total += int(info.get("ok") or 0)
    return ok_total


async def run_low_quality_gate_for_parent(
    *,
    cfg: PipelineConfig,
    driver: Driver,
    filename: str,
    parent: Dict[str, Any],
    pass1_ctx: ParentContext,
    parent_label: str,
    routed_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    potential_schema: List[Any],
    llm,
    embed_model,
    custom_prompt: str,
    on_event: Optional[EventCallback] = None,
    routing_mode: str = "incident_two_wave",
    mid2low_rels: Optional[List[str]] = None,
    max_children: int = 30,
) -> Dict[str, Any]:
    """Validate → hard repair loop → optional neighbor Pass2 → re-validate."""
    low_cfg = (cfg.raw or {}).get("low_extraction") or {}
    val_cfg = low_cfg.get("validation") or {}
    sec_cfg = low_cfg.get("second_pass") or {}
    max_rounds = int(val_cfg.get("max_repair_rounds", 2))
    shacl_on = bool(val_cfg.get("shacl_enabled", True))
    second_enabled = bool(sec_cfg.get("enabled", True))
    neighbor_window = int(sec_cfg.get("neighbor_window", 1))
    targeted_only = bool(sec_cfg.get("targeted_only", True))
    incident = routing_mode == "incident_two_wave"
    allow_mid = (
        route_mid2low_incident(parent_label, potential_schema)
        if incident
        else routed_schema
    )
    # For validation allowed child labels: mid2low endpoints ∪ common low children
    allowed = {str(r[0]) for r in allow_mid if isinstance(r, (list, tuple)) and r}
    allowed |= {str(r[2]) for r in allow_mid if isinstance(r, (list, tuple)) and len(r) > 2}
    if incident:
        # Children produced by mid2low may later gain low edges; allow those labels too
        for row in allow_mid:
            if isinstance(row, (list, tuple)) and len(row) >= 3:
                for lab in (row[0], row[2]):
                    if lab != parent_label:
                        allowed.add(str(lab))

    parent_id = str(parent.get("element_id"))
    parent_labs = list(parent.get("labels") or [])
    corpus = pass1_ctx.evidence_corpus()
    rels = list(mid2low_rels or [])

    result: Dict[str, Any] = {
        "parent_element_id": parent_id,
        "parent_name": parent.get("name"),
        "status": "ACCEPT",
        "rounds": [],
        "pass2": None,
        "routing_mode": routing_mode,
    }

    def _emit(ev: Dict[str, Any]) -> None:
        if on_event:
            on_event(ev)

    # Non-Experiment: delete illegal hasGoal / orphan Goals (do not invent repairs).
    purge_stats = purge_illegal_has_goal_and_orphan_goals(
        driver,
        cfg.neo4j_database,
        parent_element_id=parent_id,
        parent_labels=parent_labs,
        filename=filename,
    )
    if purge_stats.get("deleted_has_goal") or purge_stats.get("deleted_orphan_goals"):
        result["purge"] = purge_stats
        _emit(
            {
                "type": "low_purge",
                "filename": filename,
                "parent": parent.get("name"),
                **purge_stats,
            }
        )

    report = (
        validate_low_parent_local(
            driver,
            cfg.neo4j_database,
            filename,
            parent_id,
            parent_corpus=corpus,
            allowed_child_labels=allowed,
        )
        if shacl_on
        else {"hard_violations": [], "warnings": [], "hard_count": 0, "warning_count": 0}
    )
    _emit(
        {
            "type": "low_validate",
            "filename": filename,
            "parent": parent.get("name"),
            "hard_count": report.get("hard_count", 0),
            "warning_count": report.get("warning_count", 0),
            "phase": "local",
        }
    )

    for round_i in range(1, max_rounds + 1):
        hard = int(report.get("hard_count") or 0)
        if hard == 0:
            break
        rule_ids = [
            str(i.get("rule_id"))
            for i in (report.get("hard_violations") or [])
            if i.get("rule_id")
        ]
        rule_upper = {_norm_rule(r) for r in rule_ids}
        need_child = bool(rule_upper & _CHILD_LOW_RULES) and incident and rels

        # H01-B: relation-only fix for wrong isStepOfPlan (no full re-extract).
        if _has_h01b(rule_ids):
            h01b_steps = [
                i.get("entity_id")
                for i in (report.get("hard_violations") or [])
                if _norm_rule(str(i.get("rule_id") or "")) == "H01-B" and i.get("entity_id")
            ]
            _emit(
                {
                    "type": "low_repair",
                    "filename": filename,
                    "parent": parent.get("name"),
                    "round": round_i,
                    "rule_ids": ["H01-B"],
                    "mode": "h01b_isStepOfPlan_edge",
                }
            )
            edge_stats = repair_h01b_is_step_of_plan(
                driver,
                cfg.neo4j_database,
                parent_element_id=parent_id,
                parent_labels=list(parent.get("labels") or []),
                step_ids=h01b_steps or None,
            )
            result.setdefault("h01b_repairs", []).append(
                {"round": round_i, **edge_stats}
            )
            report = validate_low_parent_local(
                driver,
                cfg.neo4j_database,
                filename,
                parent_id,
                parent_corpus=corpus,
                allowed_child_labels=allowed,
            )
            result["rounds"].append(
                {
                    "round": round_i,
                    "hard_count": report.get("hard_count", 0),
                    "warning_count": report.get("warning_count", 0),
                    "h01b_edge_repair": True,
                }
            )
            # Refresh rules after edge-only repair
            rule_ids = [
                str(i.get("rule_id"))
                for i in (report.get("hard_violations") or [])
                if i.get("rule_id")
            ]
            rule_upper = {_norm_rule(r) for r in rule_ids}
            need_child = bool(rule_upper & _CHILD_LOW_RULES) and incident and rels
            if int(report.get("hard_count") or 0) == 0:
                continue
            # Remaining hard are non-H01-B only → fall through to existing LLM path
            if not _non_h01b_rules(rule_ids):
                # Still only H01-B (e.g. unrestorable) — do not full-chunk re-extract
                continue

        other_rules = _non_h01b_rules(rule_ids) or list(rule_ids)
        if need_child:
            _emit(
                {
                    "type": "low_repair",
                    "filename": filename,
                    "parent": parent.get("name"),
                    "round": round_i,
                    "rule_ids": other_rules,
                    "mode": "child_research_step",
                }
            )
            await _repair_research_step_children(
                cfg=cfg,
                driver=driver,
                filename=filename,
                parent=parent,
                mid_ctx=pass1_ctx,
                potential_schema=potential_schema,
                entities=entities,
                relations=relations,
                llm=llm,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                mid2low_rels=rels,
                max_children=max_children,
                rule_ids=other_rules,
                on_event=on_event,
                extract_phase="low_repair",
            )

        if targeted_only:
            repair_schema = (
                schema_for_rule_ids_intersect(
                    routed_schema,
                    other_rules,
                    allow=allow_mid,
                    parent_labels=parent_labs,
                )
                if incident
                else schema_for_rule_ids(
                    routed_schema, other_rules, parent_labels=parent_labs
                )
            )
        else:
            repair_schema = list(allow_mid if incident else routed_schema)

        # Mid-level attach repairs (W01 isStepOfPlan, hasGoal, hadMember, …)
        if repair_schema:
            _emit(
                {
                    "type": "low_repair",
                    "filename": filename,
                    "parent": parent.get("name"),
                    "round": round_i,
                    "rule_ids": other_rules,
                    "schema_rows": len(repair_schema),
                    "mode": "mid_incident",
                }
            )
            await extract_for_parent(
                ctx=pass1_ctx,
                routed_schema=repair_schema,
                entities=entities,
                relations=relations,
                llm=llm,
                neo4j_driver=driver,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                cfg=cfg,
                extract_phase="low_repair",
                prompt_suffix=f"\n# Targeted hard repair round {round_i}\nRules: {other_rules}\n",
                on_event=on_event,
                filename=filename,
            )

        report = validate_low_parent_local(
            driver,
            cfg.neo4j_database,
            filename,
            parent_id,
            parent_corpus=corpus,
            allowed_child_labels=allowed,
        )
        result["rounds"].append(
            {
                "round": round_i,
                "hard_count": report.get("hard_count", 0),
                "warning_count": report.get("warning_count", 0),
            }
        )

    review = review_low_parent(
        cfg=cfg,
        filename=filename,
        parent_name=parent.get("name"),
        parent_labels=list(parent.get("labels") or []),
        shacl_report=report,
        context_summary=pass1_ctx.to_dict(),
    )
    _emit(
        {
            "type": "low_review",
            "filename": filename,
            "parent": parent.get("name"),
            "decision": review.get("decision"),
            "needs_neighbor_pass": review.get("needs_neighbor_pass"),
        }
    )

    warn_n = int(report.get("warning_count") or 0)
    if (
        second_enabled
        and warn_n > 0
        and review.get("needs_neighbor_pass")
        and int(report.get("hard_count") or 0) == 0
    ):
        home_idxs = [
            int(c.index)
            for c in pass1_ctx.home_chunks
            if c.index is not None
        ]
        neighbors = fetch_neighbor_chunks(
            driver,
            cfg.neo4j_database,
            filename,
            home_idxs,
            window=neighbor_window,
        )
        pass2_ctx = build_pass2_context(
            pass1_ctx,
            previous_chunks=neighbors.get("previous") or [],
            next_chunks=neighbors.get("next") or [],
        )
        rule_ids = list(review.get("suggested_rule_ids") or [])
        if not rule_ids:
            rule_ids = [
                str(i.get("rule_id"))
                for i in (report.get("warnings") or [])
                if i.get("rule_id")
            ]
        rule_upper = {str(r).upper() for r in rule_ids}
        if incident and (rule_upper & _CHILD_LOW_RULES) and rels:
            await _repair_research_step_children(
                cfg=cfg,
                driver=driver,
                filename=filename,
                parent=parent,
                mid_ctx=pass1_ctx,
                potential_schema=potential_schema,
                entities=entities,
                relations=relations,
                llm=llm,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                mid2low_rels=rels,
                max_children=max_children,
                rule_ids=rule_ids,
                on_event=on_event,
                extract_phase="low_pass2",
            )

        if targeted_only:
            pass2_schema = (
                schema_for_rule_ids_intersect(
                    routed_schema,
                    rule_ids,
                    allow=allow_mid,
                    parent_labels=parent_labs,
                )
                if incident
                else schema_for_rule_ids(
                    routed_schema, rule_ids, parent_labels=parent_labs
                )
            )
        else:
            pass2_schema = list(allow_mid if incident else routed_schema)
        if not pass2_schema and not incident:
            pass2_schema = route_schema_for_parent(parent_label, potential_schema)
        if not pass2_schema and incident:
            pass2_schema = list(allow_mid)

        _emit(
            {
                "type": "low_pass2",
                "filename": filename,
                "parent": parent.get("name"),
                "schema_rows": len(pass2_schema),
                "prev_chunks": len(neighbors.get("previous") or []),
                "next_chunks": len(neighbors.get("next") or []),
                "rule_ids": rule_ids,
            }
        )
        if pass2_schema:
            await extract_for_parent(
                ctx=pass2_ctx,
                routed_schema=pass2_schema,
                entities=entities,
                relations=relations,
                llm=llm,
                neo4j_driver=driver,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                cfg=cfg,
                extract_phase="low_pass2",
                prompt_suffix="\n# Neighbor Pass2 targeted expansion\n",
                on_event=on_event,
                filename=filename,
            )
        report = validate_low_parent_local(
            driver,
            cfg.neo4j_database,
            filename,
            parent_id,
            parent_corpus=corpus,
            allowed_child_labels=allowed,
        )
        result["pass2"] = {
            "schema_rows": len(pass2_schema),
            "hard_count": report.get("hard_count", 0),
            "warning_count": report.get("warning_count", 0),
            "context": pass2_ctx.to_dict(),
        }

    hard_final = int(report.get("hard_count") or 0)
    result["status"] = "ACCEPT" if hard_final == 0 else "FLAGGED"
    result["final_report"] = {
        "hard_count": hard_final,
        "warning_count": report.get("warning_count", 0),
        "hard_violations": report.get("hard_violations") or [],
        "warnings": report.get("warnings") or [],
    }
    result["review"] = review
    await asyncio.sleep(0)
    return result
