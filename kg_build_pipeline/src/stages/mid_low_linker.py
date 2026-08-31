"""Rule-first Mid–Low linking after Low entities / Low–Low relations exist."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from neo4j import Driver

from kg_build_pipeline.src.low_parent_context import ParentContext, context_to_text_nodes
from kg_build_pipeline.src.low_schema_router import (
    LocalLowSchema,
    PARENT_LABEL_TO_RESEARCH_TYPE,
    RESEARCH_TYPE_TO_PARENT_LABEL,
    _row_triple,
    research_type_for_parent,
)
from kg_build_pipeline.src.schema_tier import schema_closure
from kg_build_pipeline.src.stages.build_kg import extract_document_schemas
from kg_build_pipeline.src.stages.low_extract import LlmCallBudget, RESEARCHTYPE_ISSTEP_CROSSLINK_BAN, parent_scoped_isstep_hint

EventCallback = Callable[[Dict[str, Any]], None]

MID_LOW_PROMPT_SUFFIX = """

# Mid–Low linking (asserted relations only)

Create mid2low relations ONLY when:
1. The mid2low schema allows the triple;
2. Subject/object types and direction are correct;
3. Text or structural evidence supports the link.

Do NOT link a low entity to this mid parent merely because it was extracted in the same text window.
Do NOT create new entities.
ResearchStep may only attach to a parent whose type matches ResearchStep.researchType.
""" + RESEARCHTYPE_ISSTEP_CROSSLINK_BAN


def _source_doc(filename: str) -> str:
    return filename.replace(".md", "") if filename.endswith(".md") else filename


def parent_research_type(parent_labels: List[str]) -> Optional[str]:
    for lab in parent_labels or []:
        rt = research_type_for_parent(str(lab))
        if rt:
            return rt
    return None


def research_type_matches_parent(research_type: Optional[str], parent_labels: List[str]) -> bool:
    """True when researchType is consistent with one of the parent mid labels."""
    if not research_type:
        return False
    expected_parent = RESEARCH_TYPE_TO_PARENT_LABEL.get(str(research_type).strip())
    if not expected_parent:
        return False
    return expected_parent in set(parent_labels or [])


def would_reject_cross_experiment_step(
    research_type: str,
    target_parent_label: str,
) -> bool:
    """T5 guard: BioChemical step must not attach to Computational parent (etc.)."""
    expected = PARENT_LABEL_TO_RESEARCH_TYPE.get(target_parent_label)
    if expected is None:
        return False
    return str(research_type).strip() != expected


def link_mid_low_rules(
    driver: Driver,
    database: str,
    *,
    filename: str,
    parent_element_id: str,
    parent_labels: List[str],
    mid2low_rows: List[Any],
) -> Dict[str, Any]:
    """Deterministic MERGE of mid2low edges for scoped low entities.

    - Parent as object (e.g. ResearchStep -isStepOfPlan-> Parent): require
      researchType match for ResearchStep; require whu_parent_scope_id.
    - Parent as subject (e.g. Parent -hasGoal-> Goal): require scope on object.
    Never auto-links without type-compatible mid2low schema row.
    """
    source_doc = _source_doc(filename)
    parent_rt = parent_research_type(parent_labels)
    created = 0
    skipped_type = 0
    linked_keys: List[Tuple[str, str, str]] = []

    with driver.session(database=database) as session:
        for row in mid2low_rows:
            t = _row_triple(row)
            if not t:
                continue
            s_lab, rel, o_lab = t
            if rel == "whu_hasGoal" and parent_rt is None:
                # Schema: hasGoal only for Bio/Comp Experiment parents.
                skipped_type += 1
                continue
            parent_is_object = o_lab in set(parent_labels) or o_lab == (
                parent_labels[0] if parent_labels else None
            )
            parent_is_subject = s_lab in set(parent_labels)

            # Normalize: treat primary mid label match
            if not parent_is_object and not parent_is_subject:
                # Also accept if row endpoint equals any parent label exactly
                parent_is_object = o_lab in set(parent_labels)
                parent_is_subject = s_lab in set(parent_labels)
            if not parent_is_object and not parent_is_subject:
                continue

            if parent_is_object and not parent_is_subject:
                # (low)-[rel]->(parent)
                if s_lab == "whu_ResearchStep" and parent_rt:
                    cypher = f"""
                    MATCH (p) WHERE elementId(p) = $pid
                    MATCH (s:{s_lab})
                    WHERE coalesce(s.whu_rejected,false)=false
                      AND s.whu_parent_scope_id = $pid
                      AND coalesce(s.WHU_RESEARCHTYPE, $parent_rt) = $parent_rt
                      AND (
                        s.source_doc = $source_doc
                        OR EXISTS {{
                          MATCH (c:Chunk)-[:FROM_CHUNK]-(s) WHERE c.filename = $filename
                        }}
                      )
                      AND NOT EXISTS {{ MATCH (s)-[:{rel}]->(p) }}
                      AND NOT EXISTS {{
                        MATCH (s)-[:p_plan_isStepOfPlan]->(other)
                        WHERE elementId(other) <> $pid
                      }}
                    MERGE (s)-[r:{rel}]->(p)
                    RETURN count(*) AS cnt
                    """
                    r = session.run(
                        cypher,
                        pid=parent_element_id,
                        parent_rt=parent_rt,
                        filename=filename,
                        source_doc=source_doc,
                    ).single()
                else:
                    cypher = f"""
                    MATCH (p) WHERE elementId(p) = $pid
                    MATCH (s:{s_lab})
                    WHERE coalesce(s.whu_rejected,false)=false
                      AND s.whu_parent_scope_id = $pid
                      AND (
                        s.source_doc = $source_doc
                        OR EXISTS {{
                          MATCH (c:Chunk)-[:FROM_CHUNK]-(s) WHERE c.filename = $filename
                        }}
                      )
                      AND NOT EXISTS {{ MATCH (s)-[:{rel}]->(p) }}
                    MERGE (s)-[r:{rel}]->(p)
                    RETURN count(*) AS cnt
                    """
                    r = session.run(
                        cypher,
                        pid=parent_element_id,
                        filename=filename,
                        source_doc=source_doc,
                    ).single()
                n = int(r["cnt"]) if r else 0
                created += n
                if n:
                    linked_keys.append(t)
                else:
                    skipped_type += 1

            elif parent_is_subject and not parent_is_object:
                # (parent)-[rel]->(low)
                cypher = f"""
                MATCH (p) WHERE elementId(p) = $pid
                MATCH (o:{o_lab})
                WHERE coalesce(o.whu_rejected,false)=false
                  AND o.whu_parent_scope_id = $pid
                  AND (
                    o.source_doc = $source_doc
                    OR EXISTS {{
                      MATCH (c:Chunk)-[:FROM_CHUNK]-(o) WHERE c.filename = $filename
                    }}
                  )
                  AND NOT EXISTS {{ MATCH (p)-[:{rel}]->(o) }}
                MERGE (p)-[r:{rel}]->(o)
                RETURN count(*) AS cnt
                """
                r = session.run(
                    cypher,
                    pid=parent_element_id,
                    filename=filename,
                    source_doc=source_doc,
                ).single()
                n = int(r["cnt"]) if r else 0
                created += n
                if n:
                    linked_keys.append(t)
                else:
                    skipped_type += 1

    return {
        "created": created,
        "skipped_empty": skipped_type,
        "linked_triples": linked_keys,
        "mode": "rules",
    }


def unlinked_mid2low_slots(
    driver: Driver,
    database: str,
    *,
    parent_element_id: str,
    parent_labels: List[str],
    mid2low_rows: List[Any],
) -> List[Any]:
    """Return mid2low rows that still have zero edges for this parent."""
    out: List[Any] = []
    with driver.session(database=database) as session:
        for row in mid2low_rows:
            t = _row_triple(row)
            if not t:
                continue
            s_lab, rel, o_lab = t
            parent_is_object = o_lab in set(parent_labels)
            parent_is_subject = s_lab in set(parent_labels)
            if parent_is_object:
                r = session.run(
                    f"""
                    MATCH (p) WHERE elementId(p) = $pid
                    OPTIONAL MATCH (s:{s_lab})-[r:{rel}]->(p)
                    WHERE s.whu_parent_scope_id = $pid
                    RETURN count(r) AS cnt
                    """,
                    pid=parent_element_id,
                ).single()
            elif parent_is_subject:
                r = session.run(
                    f"""
                    MATCH (p) WHERE elementId(p) = $pid
                    OPTIONAL MATCH (p)-[r:{rel}]->(o:{o_lab})
                    WHERE o.whu_parent_scope_id = $pid
                    RETURN count(r) AS cnt
                    """,
                    pid=parent_element_id,
                ).single()
            else:
                continue
            if int(r["cnt"] if r else 0) == 0:
                out.append(row)
    return out


async def link_mid_low_for_parent(
    *,
    ctx: ParentContext,
    local: LocalLowSchema,
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    neo4j_driver: Driver,
    embed_model,
    custom_prompt: str,
    cfg,
    budget: LlmCallBudget,
    on_event: Optional[EventCallback] = None,
    filename: Optional[str] = None,
    linker_mode: str = "hybrid",
    max_mid_low_llm_calls: int = 1,
) -> Dict[str, Any]:
    """Rule-first mid2low linking; optional single LLM fill for remaining slots."""
    from kg_build_pipeline.src.config import PipelineConfig

    assert isinstance(cfg, PipelineConfig)
    fname = filename or ctx.filename
    parent_labels = list(ctx.parent_labels or [])
    rule_stats = link_mid_low_rules(
        neo4j_driver,
        cfg.neo4j_database,
        filename=fname,
        parent_element_id=ctx.parent_element_id,
        parent_labels=parent_labels,
        mid2low_rows=local.mid2low_rows,
    )
    llm_info: Dict[str, Any] = {"ok": 0, "llm_calls": 0, "skipped": None}
    remaining = unlinked_mid2low_slots(
        neo4j_driver,
        cfg.neo4j_database,
        parent_element_id=ctx.parent_element_id,
        parent_labels=parent_labels,
        mid2low_rows=local.mid2low_rows,
    )
    use_llm = (
        linker_mode in {"hybrid", "llm"}
        and remaining
        and max_mid_low_llm_calls > 0
        and budget.remaining() > 0
    )
    if on_event:
        on_event(
            {
                "type": "low_ml",
                "filename": fname,
                "parent": ctx.parent_name,
                "parent_element_id": ctx.parent_element_id,
                "rule_created": rule_stats.get("created"),
                "remaining_slots": len(remaining),
                "budget_used": budget.used,
                "use_llm": use_llm,
            }
        )

    if use_llm and budget.consume(1):
        text_nodes = context_to_text_nodes(ctx)
        ents, rels, _, _ = schema_closure(entities, relations, remaining)
        rt = parent_research_type(parent_labels)
        suffix = MID_LOW_PROMPT_SUFFIX
        if rt:
            suffix += (
                f"\nResearchStep.researchType must be '{rt}' "
                f"and may only isStepOfPlan to this parent.\n"
            )
        if ctx.parent_name:
            suffix += f"\nMid parent name: {ctx.parent_name}\nLabels: {parent_labels}\n"
        suffix += parent_scoped_isstep_hint(parent_labels)
        ok = await extract_document_schemas(
            final_nodes=text_nodes,
            custom_prompt=custom_prompt,
            potential_schema=remaining,
            entities=ents,
            relations=rels,
            llm=llm,
            neo4j_driver=neo4j_driver,
            embed_model=embed_model,
            cfg=cfg,
            text_nodes_override=text_nodes,
            prompt_suffix=suffix,
            on_event=on_event,
            filename=fname,
            emit_schema_events=True,
            extract_phase="low_ml",
            parent_element_id=ctx.parent_element_id,
        )
        llm_info = {
            "ok": int(ok or 0),
            "verified_edges": int(ok or 0),
            "llm_calls": 1,
            "schema_rows": len(remaining),
        }
        # Re-run rules to attach any LLM-created scoped nodes with correct types
        rule_stats2 = link_mid_low_rules(
            neo4j_driver,
            cfg.neo4j_database,
            filename=fname,
            parent_element_id=ctx.parent_element_id,
            parent_labels=parent_labels,
            mid2low_rows=local.mid2low_rows,
        )
        rule_stats["created"] = int(rule_stats.get("created") or 0) + int(
            rule_stats2.get("created") or 0
        )
    elif use_llm:
        llm_info["skipped"] = "llm_budget_exhausted"

    return {
        "rules": rule_stats,
        "llm": llm_info,
        "budget_used": budget.used,
        "context": ctx.to_dict(),
    }
