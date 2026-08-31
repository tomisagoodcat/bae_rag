"""Orchestrate Low hierarchical expand after Mid PASS."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.low_extract_log import LowExtractLogger
from kg_build_pipeline.src.low_parent_context import build_pass1_context
from kg_build_pipeline.src.low_schema_router import (
    activate_local_low_schema,
    mid2low_rel_types,
    primary_parent_label,
    route_low_incident,
    route_mid2low_incident,
    route_schema_for_parent,
)
from kg_build_pipeline.src.schema_loader import load_schema
from kg_build_pipeline.src.stages.build_kg import InsufficientBalanceError
from kg_build_pipeline.src.stages.cross_parent_linker import run_cross_parent_linker
from kg_build_pipeline.src.stages.low_extract import (
    LlmCallBudget,
    extract_for_parent,
    extract_low_entities_for_parent,
    extract_low_low_for_parent,
)
from kg_build_pipeline.src.stages.low_parents import (
    fetch_mid2low_children,
    fetch_mid_parents_for_document,
    list_pass_filenames,
)
from kg_build_pipeline.src.stages.low_quality_gate import run_low_quality_gate_for_parent
from kg_build_pipeline.src.stages.low_validate import validate_low_document_final
from kg_build_pipeline.src.stages.mid_low_linker import link_mid_low_for_parent

EventCallback = Callable[[Dict[str, Any]], None]


def _low_cfg(cfg: PipelineConfig) -> Dict[str, Any]:
    return (cfg.raw or {}).get("low_extraction") or {}


def _routing_mode(low: Dict[str, Any]) -> str:
    routing = low.get("routing") or {}
    mode = str(routing.get("mode") or "incident_two_wave").strip().lower()
    if mode not in {"incident_two_wave", "legacy_closure"}:
        return "incident_two_wave"
    return mode


def _strategy(low: Dict[str, Any]) -> str:
    s = str(low.get("strategy") or "entity_first").strip().lower()
    if s not in {"entity_first", "attach_first"}:
        return "entity_first"
    return s


def _child_pass1_context(
    *,
    child: Dict[str, Any],
    mid_ctx,
    filename: str,
    fp: Dict[str, Any],
):
    """Child original if present; else inherit Mid Pass1 text window."""
    child_orig = str(child.get("original_text") or "").strip()
    child_homes = list(child.get("home_chunks") or [])
    text_fallback = False
    if not child_orig:
        text_fallback = True
        child_orig = str(mid_ctx.parent_original_text or "")
    if not child_homes:
        text_fallback = True
        child_homes = [
            {
                "id": c.chunk_id,
                "index": c.index,
                "filename": c.filename,
                "text": c.text,
            }
            for c in (mid_ctx.home_chunks or [])
        ]
    ctx = build_pass1_context(
        parent_element_id=str(child.get("element_id")),
        parent_name=child.get("name"),
        parent_labels=list(child.get("labels") or []),
        parent_original_text=child_orig,
        filename=filename,
        home_chunks=child_homes,
        use_parent_original_text=bool(fp.get("use_parent_original_text", True)),
        use_current_chunk=bool(fp.get("use_current_chunk", True)),
    )
    return ctx, text_fallback


async def _run_entity_first_parent(
    *,
    cfg: PipelineConfig,
    driver: Driver,
    filename: str,
    parent: Dict[str, Any],
    plabel: str,
    ctx,
    potential_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    embed_model,
    custom_prompt: str,
    ef: Dict[str, Any],
    on_event: Optional[EventCallback],
    m2l_rels: List[str],
    max_children: int,
    mode: str,
) -> Dict[str, Any]:
    hops = int(ef.get("low_expand_hops", 2))
    max_calls = int(ef.get("max_llm_calls_per_parent", 3))
    max_ml_llm = int(ef.get("max_mid_low_llm_calls", 1))
    linker_mode = str(ef.get("mid_low_linker") or "hybrid").strip().lower()
    allow_backfill = bool(ef.get("allow_entity_backfill", True))
    max_entities = int(ef.get("max_entities_per_parent", 40))
    max_per_label = int(ef.get("max_per_label", 0))

    local = activate_local_low_schema(plabel, potential_schema, hops=hops)
    if on_event:
        on_event(
            {
                "type": "low_activate",
                "filename": filename,
                "parent": parent.get("name"),
                "parent_label": plabel,
                **local.to_dict(),
            }
        )

    budget = LlmCallBudget(max_calls)
    entity_info = await extract_low_entities_for_parent(
        ctx=ctx,
        local=local,
        entities=entities,
        llm=llm,
        neo4j_driver=driver,
        cfg=cfg,
        budget=budget,
        on_event=on_event,
        filename=filename,
        max_entities_per_parent=max_entities,
        max_per_label=max_per_label,
    )

    ll_info = await extract_low_low_for_parent(
        ctx=ctx,
        local=local,
        entities=entities,
        relations=relations,
        llm=llm,
        neo4j_driver=driver,
        embed_model=embed_model,
        custom_prompt=custom_prompt,
        cfg=cfg,
        budget=budget,
        on_event=on_event,
        filename=filename,
    )

    missing_labels = set(ll_info.get("missing_labels") or [])
    if allow_backfill and missing_labels and budget.remaining() > 0:
        backfill = await extract_low_entities_for_parent(
            ctx=ctx,
            local=local,
            entities=entities,
            llm=llm,
            neo4j_driver=driver,
            cfg=cfg,
            budget=budget,
            on_event=on_event,
            filename=filename,
            label_subset=missing_labels & set(local.entity_labels),
            max_entities_per_parent=max_entities,
            max_per_label=max_per_label,
        )
        entity_info["backfill"] = backfill
        if budget.remaining() > 0:
            ll_info = await extract_low_low_for_parent(
                ctx=ctx,
                local=local,
                entities=entities,
                relations=relations,
                llm=llm,
                neo4j_driver=driver,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                cfg=cfg,
                budget=budget,
                on_event=on_event,
                filename=filename,
            )

    ml_info = await link_mid_low_for_parent(
        ctx=ctx,
        local=local,
        entities=entities,
        relations=relations,
        llm=llm,
        neo4j_driver=driver,
        embed_model=embed_model,
        custom_prompt=custom_prompt,
        cfg=cfg,
        budget=budget,
        on_event=on_event,
        filename=filename,
        linker_mode=linker_mode,
        max_mid_low_llm_calls=max_ml_llm,
    )

    routed = list(local.mid2low_rows)
    gate_info = await run_low_quality_gate_for_parent(
        cfg=cfg,
        driver=driver,
        filename=filename,
        parent=parent,
        pass1_ctx=ctx,
        parent_label=plabel,
        routed_schema=routed,
        entities=entities,
        relations=relations,
        potential_schema=potential_schema,
        llm=llm,
        embed_model=embed_model,
        custom_prompt=custom_prompt,
        on_event=on_event,
        routing_mode=mode,
        mid2low_rels=m2l_rels,
        max_children=max_children,
    )
    return {
        "parent": parent.get("name"),
        "parent_element_id": parent.get("element_id"),
        "parent_label": plabel,
        "strategy": "entity_first",
        "routing_mode": mode,
        "activation": local.to_dict(),
        "entity": entity_info,
        "low_low": {k: v for k, v in ll_info.items() if k != "missing_triples"},
        "mid_low": ml_info,
        "llm_calls_used": budget.used,
        "extract": {
            "ok": int(entity_info.get("ok") or 0)
            + int(ll_info.get("ok") or 0)
            + int((ml_info.get("llm") or {}).get("ok") or 0),
            "schema_rows": len(local.low_rows) + len(local.mid2low_rows),
            "context": ctx.to_dict(),
        },
        "child_extracts": [],
        "gate": gate_info,
        "status": gate_info.get("status") or "FLAGGED",
    }


async def _run_attach_first_parent(
    *,
    cfg: PipelineConfig,
    driver: Driver,
    filename: str,
    parent: Dict[str, Any],
    plabel: str,
    ctx,
    potential_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    embed_model,
    custom_prompt: str,
    mode: str,
    m2l_rels: List[str],
    max_children: int,
    fp: Dict[str, Any],
    on_event: Optional[EventCallback],
) -> Dict[str, Any]:
    """Legacy attach-first / two-wave path (unchanged behavior)."""
    if mode == "legacy_closure":
        routed = route_schema_for_parent(plabel, potential_schema)
    else:
        routed = route_mid2low_incident(plabel, potential_schema)

    if on_event:
        on_event(
            {
                "type": "low_pass1",
                "filename": filename,
                "parent": parent.get("name"),
                "parent_label": plabel,
                "routing_mode": mode,
                "schema_rows": len(routed),
                "context": ctx.to_dict(),
            }
        )

    extract_info = await extract_for_parent(
        ctx=ctx,
        routed_schema=routed,
        entities=entities,
        relations=relations,
        llm=llm,
        neo4j_driver=driver,
        embed_model=embed_model,
        custom_prompt=custom_prompt,
        cfg=cfg,
        extract_phase="low_pass1",
        on_event=on_event,
        filename=filename,
    )

    child_extracts: List[Dict[str, Any]] = []
    if mode == "incident_two_wave":
        children = fetch_mid2low_children(
            driver,
            cfg.neo4j_database,
            filename,
            str(parent.get("element_id")),
            mid2low_rels=m2l_rels,
            max_children=max_children,
        )
        for child in children:
            clabel = primary_parent_label(child.get("labels") or [])
            if not clabel:
                labs = list(child.get("labels") or [])
                clabel = labs[0] if labs else None
            if not clabel:
                continue
            routed_low = route_low_incident(clabel, potential_schema)
            if not routed_low:
                continue
            child_ctx, text_fallback = _child_pass1_context(
                child=child, mid_ctx=ctx, filename=filename, fp=fp
            )
            if not child_ctx.extraction_text().strip():
                continue
            if on_event:
                on_event(
                    {
                        "type": "low_child_pass1",
                        "filename": filename,
                        "parent": child.get("name"),
                        "mid_parent": parent.get("name"),
                        "parent_label": clabel,
                        "schema_rows": len(routed_low),
                        "text_fallback": text_fallback,
                    }
                )
            suffix = ""
            if text_fallback:
                suffix = (
                    "\n# Child text fallback: using Mid parent original/home "
                    "chunk window because child original_text was empty.\n"
                )
            c_info = await extract_for_parent(
                ctx=child_ctx,
                routed_schema=routed_low,
                entities=entities,
                relations=relations,
                llm=llm,
                neo4j_driver=driver,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                cfg=cfg,
                extract_phase="low_child_pass1",
                prompt_suffix=suffix,
                on_event=on_event,
                filename=filename,
            )
            child_extracts.append(
                {
                    "child": child.get("name"),
                    "child_label": clabel,
                    "extract": c_info,
                    "text_fallback": text_fallback,
                }
            )

    gate_info = await run_low_quality_gate_for_parent(
        cfg=cfg,
        driver=driver,
        filename=filename,
        parent=parent,
        pass1_ctx=ctx,
        parent_label=plabel,
        routed_schema=routed,
        entities=entities,
        relations=relations,
        potential_schema=potential_schema,
        llm=llm,
        embed_model=embed_model,
        custom_prompt=custom_prompt,
        on_event=on_event,
        routing_mode=mode,
        mid2low_rels=m2l_rels,
        max_children=max_children,
    )
    return {
        "parent": parent.get("name"),
        "parent_element_id": parent.get("element_id"),
        "parent_label": plabel,
        "strategy": "attach_first",
        "routing_mode": mode,
        "extract": extract_info,
        "child_extracts": child_extracts,
        "gate": gate_info,
        "status": gate_info.get("status") or "FLAGGED",
    }


async def _run_low_expand_async(
    cfg: PipelineConfig,
    driver: Driver,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    low = _low_cfg(cfg)
    if not bool(low.get("enabled", True)):
        return {"skipped": True, "reason": "low_extraction.enabled=false"}

    def _emit(ev: Dict[str, Any]) -> None:
        if on_event:
            on_event(ev)

    require_pass = bool(low.get("require_mid_pass", True))
    selected = list((cfg.build_kg or {}).get("selected_files") or [])
    if require_pass:
        filenames = list_pass_filenames(
            driver, cfg.neo4j_database, filenames=selected or None
        )
    else:
        filenames = selected
        if not filenames:
            with driver.session(database=cfg.neo4j_database) as session:
                filenames = [
                    r["filename"]
                    for r in session.run(
                        "MATCH (c:Chunk) WHERE c.filename IS NOT NULL "
                        "RETURN DISTINCT c.filename AS filename ORDER BY filename"
                    ).data()
                ]

    strategy = _strategy(low)
    _emit(
        {
            "type": "low_expand_start",
            "pass_docs": filenames,
            "count": len(filenames),
            "strategy": strategy,
        }
    )
    if not filenames:
        return {
            "documents": 0,
            "passed_parents": 0,
            "flagged_parents": 0,
            "results": [],
            "message": "No mid_gate_status=PASS documents found",
            "strategy": strategy,
        }

    entities, relations, potential_schema = load_schema(cfg.schema_dir)
    custom_prompt = cfg.custom_prompt.read_text(encoding="utf-8")
    mode = _routing_mode(low)
    routing = low.get("routing") or {}
    max_children = int(routing.get("max_children_per_mid", 30))
    abort_balance = bool(low.get("abort_on_insufficient_balance", True))
    ef = low.get("entity_first") or {}
    m2l_rels = mid2low_rel_types(potential_schema)

    from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
    from neo4j_graphrag.llm import OpenAILLM

    if not cfg.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY required for low_expand")

    llm = OpenAILLM(
        model_name=cfg.deepseek_model,
        model_params={"max_tokens": 8000, "temperature": 0.1, "top_p": 0.9},
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_base_url,
    )
    embed_model = SentenceTransformerEmbeddings(model=cfg.embedding_model)

    fp = low.get("first_pass") or {}
    logger = LowExtractLogger()
    logger.start_session(filenames)

    doc_results: List[Dict[str, Any]] = []
    passed_parents = 0
    flagged_parents = 0
    aborted_balance = False

    try:
        for filename in filenames:
            if aborted_balance:
                break
            _emit({"type": "low_expand_doc", "filename": filename, "phase": "start"})
            parents = fetch_mid_parents_for_document(driver, cfg.neo4j_database, filename)
            parent_results: List[Dict[str, Any]] = []
            for parent in parents:
                if aborted_balance:
                    break
                plabel = primary_parent_label(parent.get("labels") or [])
                if not plabel:
                    continue

                ctx = build_pass1_context(
                    parent_element_id=str(parent.get("element_id")),
                    parent_name=parent.get("name"),
                    parent_labels=list(parent.get("labels") or []),
                    parent_original_text=str(parent.get("original_text") or ""),
                    filename=filename,
                    home_chunks=list(parent.get("home_chunks") or []),
                    use_parent_original_text=bool(fp.get("use_parent_original_text", True)),
                    use_current_chunk=bool(fp.get("use_current_chunk", True)),
                )
                if not ctx.extraction_text().strip():
                    parent_results.append(
                        {
                            "parent": parent.get("name"),
                            "status": "SKIP",
                            "reason": "empty_context",
                            "strategy": strategy,
                        }
                    )
                    continue

                try:
                    if strategy == "entity_first":
                        entry = await _run_entity_first_parent(
                            cfg=cfg,
                            driver=driver,
                            filename=filename,
                            parent=parent,
                            plabel=plabel,
                            ctx=ctx,
                            potential_schema=potential_schema,
                            entities=entities,
                            relations=relations,
                            llm=llm,
                            embed_model=embed_model,
                            custom_prompt=custom_prompt,
                            ef=ef,
                            on_event=on_event,
                            m2l_rels=m2l_rels,
                            max_children=max_children,
                            mode=mode,
                        )
                    else:
                        entry = await _run_attach_first_parent(
                            cfg=cfg,
                            driver=driver,
                            filename=filename,
                            parent=parent,
                            plabel=plabel,
                            ctx=ctx,
                            potential_schema=potential_schema,
                            entities=entities,
                            relations=relations,
                            llm=llm,
                            embed_model=embed_model,
                            custom_prompt=custom_prompt,
                            mode=mode,
                            m2l_rels=m2l_rels,
                            max_children=max_children,
                            fp=fp,
                            on_event=on_event,
                        )
                except InsufficientBalanceError as e:
                    aborted_balance = True
                    _emit(
                        {
                            "type": "low_abort",
                            "reason": "insufficient_balance",
                            "filename": filename,
                            "parent": parent.get("name"),
                            "message": str(e),
                        }
                    )
                    if abort_balance:
                        raise
                    break

                status = entry.get("status") or "FLAGGED"
                if status == "ACCEPT":
                    passed_parents += 1
                else:
                    flagged_parents += 1
                parent_results.append(entry)
                logger.log_parent(filename, entry)

            if aborted_balance:
                break

            cross_stats = {}
            if bool((low.get("cross_parent_linking") or {}).get("enabled", True)):
                cross_stats = run_cross_parent_linker(driver, cfg.neo4j_database, filename)
                _emit({"type": "low_cross_parent", "filename": filename, **cross_stats})

            final_report = {"hard_count": 0, "warning_count": 0}
            if bool((low.get("validation") or {}).get("shacl_enabled", True)):
                final_report = validate_low_document_final(
                    driver, cfg.neo4j_database, filename
                )
                max_rounds = int((low.get("validation") or {}).get("max_repair_rounds", 2))
                round_i = 0
                while int(final_report.get("hard_count") or 0) > 0 and round_i < max_rounds:
                    round_i += 1
                    _emit(
                        {
                            "type": "low_final_repair",
                            "filename": filename,
                            "round": round_i,
                            "hard_count": final_report.get("hard_count"),
                        }
                    )
                    for pr in parent_results:
                        if pr.get("status") != "ACCEPT":
                            continue
                    final_report = validate_low_document_final(
                        driver, cfg.neo4j_database, filename
                    )
                    break

                _emit(
                    {
                        "type": "low_final_validate",
                        "filename": filename,
                        "hard_count": final_report.get("hard_count", 0),
                        "warning_count": final_report.get("warning_count", 0),
                    }
                )

            doc_results.append(
                {
                    "filename": filename,
                    "parents": parent_results,
                    "cross_parent": cross_stats,
                    "final": {
                        "hard_count": final_report.get("hard_count", 0),
                        "warning_count": final_report.get("warning_count", 0),
                    },
                }
            )
            _emit({"type": "low_expand_doc", "filename": filename, "phase": "done"})
    except InsufficientBalanceError:
        aborted_balance = True
        _emit(
            {
                "type": "low_abort",
                "reason": "insufficient_balance",
                "message": "low_expand stopped: API insufficient balance",
            }
        )

    logger.close()
    return {
        "documents": len(doc_results),
        "passed_parents": passed_parents,
        "flagged_parents": flagged_parents,
        "aborted_insufficient_balance": aborted_balance,
        "routing_mode": mode,
        "strategy": strategy,
        "results": doc_results,
    }


def run_low_expand(
    cfg: PipelineConfig,
    driver: Driver,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    return asyncio.run(_run_low_expand_async(cfg, driver, on_event=on_event))
