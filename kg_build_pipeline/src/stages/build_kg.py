"""KG triple extraction via SimpleKGPipeline (from 1_2_0_2 module3)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

import nest_asyncio
from llama_index.core import Document
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
from neo4j import Driver
from tqdm import tqdm

from kg_build_pipeline.src.argument_cleanup import scrub_cloned_argument_spans
from kg_build_pipeline.src.argument_polarity import (
    filter_nodes_with_challenge_language,
    should_skip_challenges_extract,
)
from kg_build_pipeline.src.chunk_roles import canonical_section, enrich_nodes_with_bae_roles
from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.neo4j_util import (
    build_neo4j_driver,
    clear_neo4j,
    neo4j_is_alive,
    wait_for_neo4j,
)
from kg_build_pipeline.src.schema_loader import load_schema, load_table3_section_bae
from kg_build_pipeline.src.schema_tier import filter_potential_schema, mid_schema_view
from kg_build_pipeline.src.stages.document_loader import (
    SafeSemanticSplitter,
    add_header_paths,
    create_nodes_with_metadata,
    create_section_inferrer,
    load_markdown_with_agent_metadata,
)
from kg_build_pipeline.src.stages.metadata_enhance import enhance_relations, update_metadata_batch

nest_asyncio.apply()

# Re-export for notebooks importing from build_kg
__all__ = [
    "build_neo4j_driver",
    "clear_neo4j",
    "run_build_kg",
    "extract_document_schemas",
    "count_schema_pattern_edges",
    "verify_schema_edge_written",
    "InsufficientBalanceError",
]

_LOW_EXTRACT_PHASES = frozenset(
    {
        "low_pass1",
        "low_pass2",
        "low_repair",
        "low_child_pass1",
        "low_entity",
        "low_ll",
        "low_ml",
    }
)

# low_ml still batches (one LLM call per parent phase) but verify each triple after.
# low_ll uses dedicated JSON+Cypher MERGE (not SimpleKG).
_FORCE_BATCH_LOW_PHASES = frozenset({"low_ml"})

_VERIFY_EDGE_PHASES = frozenset(
    {
        "low_pass1",
        "low_pass2",
        "low_repair",
        "low_child_pass1",
        "low_ll",
        "low_ml",
    }
)


class InsufficientBalanceError(RuntimeError):
    """Raised when the LLM API reports insufficient balance / HTTP 402."""


def _is_insufficient_balance(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "insufficient balance" in msg:
        return True
    if "402" in msg and ("balance" in msg or "invalid_request" in msg or "error code" in msg):
        return True
    return False


def _silence_neo4j_graphrag_warnings() -> None:
    for logger_name in (
        "neo4j_graphrag",
        "neo4j_graphrag.experimental.components.entity_relation_extractor",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)


_silence_neo4j_graphrag_warnings()


def schema_allowed_set(sections: List[str]) -> set:
    if not sections or any(s.lower() == "all" for s in sections):
        return {"__ALL__"}
    return {canonical_section(s) for s in sections}


def join_nodes_text(nodes: List[Any]) -> str:
    return "\n\n".join([n.get_text().strip() for n in nodes if n.get_text().strip()])


def _supplement_chunk_metadata(
    neo4j_driver: Driver,
    database: str,
    filename: str,
    final_nodes: List[Any],
) -> int:
    """Write section_role, bae_roles, header_path onto Neo4j Chunk nodes for this document."""
    updated = 0
    with neo4j_driver.session(database=database) as session:
        for node in final_nodes:
            text_preview = node.get_content()[:50].strip()
            if not text_preview:
                continue
            md = node.metadata or {}
            result = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.text CONTAINS $text_preview
                  AND (c.filename IS NULL OR c.filename = $filename)
                SET c.filename = $filename,
                    c.header_path = $header_path,
                    c.section_role = $section_role,
                    c.bae_roles = $bae_roles,
                    c.from_section = $section_role
                RETURN count(c) AS cnt
                """,
                filename=filename,
                text_preview=text_preview,
                header_path=md.get("header_path", "Unknown"),
                section_role=md.get("section_role", "Other"),
                bae_roles=md.get("bae_roles") or [],
            )
            updated += int(result.single()["cnt"])
    return updated


EventCallback = Callable[[Dict[str, Any]], None]


def count_schema_pattern_edges(
    driver: Driver,
    database: str,
    src_label: str,
    rel_type: str,
    tgt_label: str,
    *,
    parent_element_id: Optional[str] = None,
) -> int:
    """Count Neo4j edges matching a schema triple, optionally scoped to a mid parent."""
    cypher = f"""
    MATCH (s:{src_label})-[r:{rel_type}]->(o:{tgt_label})
    """
    if parent_element_id:
        cypher += """
    WHERE elementId(s) = $pid OR elementId(o) = $pid
       OR s.whu_parent_scope_id = $pid OR o.whu_parent_scope_id = $pid
    """
    cypher += "\nRETURN count(r) AS c"
    params: Dict[str, Any] = {}
    if parent_element_id:
        params["pid"] = parent_element_id
    with driver.session(database=database) as session:
        row = session.run(cypher, **params).single()
    return int(row["c"]) if row else 0


def verify_schema_edge_written(
    driver: Driver,
    database: str,
    triple: List[Any],
    *,
    parent_element_id: Optional[str] = None,
    count_before: Optional[int] = None,
) -> tuple[bool, int, str]:
    """Return (verified, count_after, reason). OK when edge exists after extract."""
    if not triple or len(triple) < 3:
        return False, 0, "invalid triple"
    src, rel, tgt = triple[0], triple[1], triple[2]
    after = count_schema_pattern_edges(
        driver,
        database,
        str(src),
        str(rel),
        str(tgt),
        parent_element_id=parent_element_id,
    )
    if count_before is not None and after > count_before:
        return True, after, ""
    if after >= 1:
        return True, after, "edge_already_present"
    return False, after, "no matching edge in neo4j after extract"


def _verify_edges_enabled(phase: str, extract_cfg: Dict[str, Any]) -> bool:
    if phase not in _VERIFY_EDGE_PHASES:
        return False
    return bool(extract_cfg.get("verify_edges_after_extract", True))


def _emit_verified_schema(
    *,
    prep: Dict[str, Any],
    verified: bool,
    count_after: int,
    reason: str,
    schema_emit: Callable[..., None],
) -> bool:
    triple = prep["triple"]
    if verified:
        schema_emit(
            "ok",
            triple,
            reason,
            allowed_sections=prep["allowed_list"],
            matching_chunk_count=len(prep["selected"]),
        )
        return True
    schema_emit(
        "no_edge",
        triple,
        reason or "no matching edge in neo4j after extract",
        allowed_sections=prep["allowed_list"],
        matching_chunk_count=len(prep["selected"]),
    )
    return False


async def extract_document_schemas(
    *,
    final_nodes: List[Any],
    custom_prompt: str,
    potential_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    neo4j_driver: Driver,
    embed_model,
    cfg: PipelineConfig,
    text_nodes_override: Optional[List[Any]] = None,
    prompt_suffix: str = "",
    on_event: Optional[EventCallback] = None,
    filename: Optional[str] = None,
    emit_schema_events: bool = False,
    extract_phase: str = "build",
    parent_element_id: Optional[str] = None,
) -> int:
    """Run SimpleKGPipeline over schema rows.

    Default text selection: section-filter + join_nodes_text (unchanged).
    When ``text_nodes_override`` is set (targeted re-extract), use those nodes only.
    Returns processed (ok) count only; coverage is emitted via events when enabled.
    """
    from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

    perform_er = bool(cfg.build_kg.get("perform_entity_resolution", False))
    pause_schemas = float(cfg.build_kg.get("pause_between_schemas", 1.0))
    low_ext = (cfg.raw or {}).get("low_extraction") or {}
    extract_cfg = low_ext.get("extract") or {}
    pause_batches = float(
        extract_cfg.get("pause_between_schema_batches", pause_schemas)
    )
    batch_low = bool(extract_cfg.get("batch_schemas_per_call", False))
    abort_balance = bool(low_ext.get("abort_on_insufficient_balance", True))
    prompt = custom_prompt + (prompt_suffix or "")
    phase = (extract_phase or "build").strip().lower()
    known_phases = {"build", "reextract"} | set(_LOW_EXTRACT_PHASES)
    if phase not in known_phases:
        phase = "build"
    verify_edges = _verify_edges_enabled(phase, extract_cfg)
    force_batch = phase in _FORCE_BATCH_LOW_PHASES and text_nodes_override is not None
    use_batch = force_batch or (
        batch_low
        and phase in _LOW_EXTRACT_PHASES
        and text_nodes_override is not None
    )
    attempts: List[Dict[str, Any]] = []

    def _schema_emit(
        status: str,
        triple: List[Any],
        reason: str = "",
        *,
        allowed_sections: Optional[List[str]] = None,
        matching_chunk_count: int = 0,
    ) -> None:
        attempt = {
            "triple": list(triple[:3]) if isinstance(triple, (list, tuple)) else triple,
            "status": status,
            "reason": reason,
            "allowed_sections": list(allowed_sections or []),
            "matching_chunk_count": int(matching_chunk_count),
        }
        attempts.append(attempt)
        if not emit_schema_events or not on_event:
            return
        on_event(
            {
                "type": "schema_extract",
                "phase": phase,
                "filename": filename or "",
                "triple": attempt["triple"],
                "status": status,
                "reason": reason,
                "allowed_sections": attempt["allowed_sections"],
                "matching_chunk_count": attempt["matching_chunk_count"],
            }
        )

    def _prepare_row(schema: Any) -> Optional[Dict[str, Any]]:
        triple = [schema[0], schema[1], schema[2]]
        e1, r, e2 = schema[0], schema[1], schema[2]
        sections = schema[3] if len(schema) > 3 else []
        allowed = schema_allowed_set(sections)
        allowed_list = (
            ["All"]
            if "__ALL__" in allowed
            else sorted(s for s in allowed if s != "__ALL__")
        )
        _entities = [e for e in entities if e.get("label") in (e1, e2)]
        _relations = [rel for rel in relations if rel.get("label") == r]
        if not _entities or not _relations:
            _schema_emit(
                "skip",
                triple,
                "missing entity/relation defs",
                allowed_sections=allowed_list,
            )
            return None
        if text_nodes_override is not None:
            selected = list(text_nodes_override)
        else:
            selected = (
                final_nodes
                if "__ALL__" in allowed
                else [
                    n
                    for n in final_nodes
                    if canonical_section((n.metadata or {}).get("section_role")) in allowed
                ]
            )
        if not selected:
            _schema_emit(
                "skip",
                triple,
                "no matching section chunks",
                allowed_sections=allowed_list,
                matching_chunk_count=0,
            )
            return None
        if str(r).strip() == "mp_challenges":
            challenge_chunks = filter_nodes_with_challenge_language(selected)
            if not challenge_chunks or should_skip_challenges_extract(
                str(r), join_nodes_text(challenge_chunks)
            ):
                _schema_emit(
                    "skip",
                    triple,
                    "no explicit challenge language",
                    allowed_sections=allowed_list,
                    matching_chunk_count=len(selected),
                )
                return None
            selected = challenge_chunks
        text = join_nodes_text(selected)
        if not text.strip():
            _schema_emit(
                "skip",
                triple,
                "empty text",
                allowed_sections=allowed_list,
                matching_chunk_count=len(selected),
            )
            return None
        return {
            "schema": schema,
            "triple": triple,
            "entities": _entities,
            "relations": _relations,
            "text": text,
            "selected": selected,
            "allowed_list": allowed_list,
        }

    processed = 0

    if use_batch:
        runnable: List[Dict[str, Any]] = []
        for schema in potential_schema:
            prep = _prepare_row(schema)
            if prep:
                runnable.append(prep)
        if runnable:
            # Same override text for all low rows in a parent batch.
            text = runnable[0]["text"]
            labels_e = {e.get("label") for p in runnable for e in p["entities"]}
            labels_r = {r.get("label") for p in runnable for r in p["relations"]}
            _entities = [e for e in entities if e.get("label") in labels_e]
            _relations = [rel for rel in relations if rel.get("label") in labels_r]
            # Deduplicate by label
            seen_e: set = set()
            ents_u: List[Dict[str, Any]] = []
            for e in _entities:
                lab = e.get("label")
                if lab in seen_e:
                    continue
                seen_e.add(lab)
                ents_u.append(e)
            seen_r: set = set()
            rels_u: List[Dict[str, Any]] = []
            for rel in _relations:
                lab = rel.get("label")
                if lab in seen_r:
                    continue
                seen_r.add(lab)
                rels_u.append(rel)
            schema_triples = [list(p["schema"][:3]) for p in runnable]
            counts_before: Dict[tuple, int] = {}
            if verify_edges:
                for p in runnable:
                    key = tuple(p["triple"][:3])
                    if key not in counts_before:
                        counts_before[key] = count_schema_pattern_edges(
                            neo4j_driver,
                            cfg.neo4j_database,
                            key[0],
                            key[1],
                            key[2],
                            parent_element_id=parent_element_id,
                        )
            try:
                kg_builder = SimpleKGPipeline(
                    llm=llm,
                    driver=neo4j_driver,
                    embedder=embed_model,
                    entities=ents_u,
                    relations=rels_u,
                    text_splitter=None,
                    potential_schema=schema_triples,
                    from_pdf=False,
                    perform_entity_resolution=perform_er,
                    prompt_template=prompt,
                    neo4j_database=cfg.neo4j_database,
                )
                await kg_builder.run_async(text=text)
                for p in runnable:
                    key = tuple(p["triple"][:3])
                    if verify_edges:
                        verified, _after, reason = verify_schema_edge_written(
                            neo4j_driver,
                            cfg.neo4j_database,
                            p["triple"],
                            parent_element_id=parent_element_id,
                            count_before=counts_before.get(key),
                        )
                        if _emit_verified_schema(
                            prep=p,
                            verified=verified,
                            count_after=_after,
                            reason=reason,
                            schema_emit=_schema_emit,
                        ):
                            processed += 1
                    else:
                        processed += 1
                        _schema_emit(
                            "ok",
                            p["triple"],
                            allowed_sections=p["allowed_list"],
                            matching_chunk_count=len(p["selected"]),
                        )
            except Exception as e:
                if abort_balance and _is_insufficient_balance(e):
                    for p in runnable:
                        _schema_emit(
                            "fail",
                            p["triple"],
                            f"fail: {e}",
                            allowed_sections=p["allowed_list"],
                        )
                    raise InsufficientBalanceError(str(e)) from e
                print(f"Batch schema extract failed ({len(runnable)} rows): {e}")
                for p in runnable:
                    _schema_emit(
                        "fail",
                        p["triple"],
                        f"fail: {e}",
                        allowed_sections=p["allowed_list"],
                    )
            await asyncio.sleep(pause_batches)
    else:
        for schema in potential_schema:
            prep = _prepare_row(schema)
            if not prep:
                continue
            triple = prep["triple"]
            count_before: Optional[int] = None
            if verify_edges:
                count_before = count_schema_pattern_edges(
                    neo4j_driver,
                    cfg.neo4j_database,
                    triple[0],
                    triple[1],
                    triple[2],
                    parent_element_id=parent_element_id,
                )
            try:
                kg_builder = SimpleKGPipeline(
                    llm=llm,
                    driver=neo4j_driver,
                    embedder=embed_model,
                    entities=prep["entities"],
                    relations=prep["relations"],
                    text_splitter=None,
                    potential_schema=[prep["schema"][:3]],
                    from_pdf=False,
                    perform_entity_resolution=perform_er,
                    prompt_template=prompt,
                    neo4j_database=cfg.neo4j_database,
                )
                await kg_builder.run_async(text=prep["text"])
                if verify_edges:
                    verified, _after, reason = verify_schema_edge_written(
                        neo4j_driver,
                        cfg.neo4j_database,
                        triple,
                        parent_element_id=parent_element_id,
                        count_before=count_before,
                    )
                    if _emit_verified_schema(
                        prep=prep,
                        verified=verified,
                        count_after=_after,
                        reason=reason,
                        schema_emit=_schema_emit,
                    ):
                        processed += 1
                else:
                    processed += 1
                    _schema_emit(
                        "ok",
                        triple,
                        allowed_sections=prep["allowed_list"],
                        matching_chunk_count=len(prep["selected"]),
                    )
                sleep_s = pause_batches if phase in _LOW_EXTRACT_PHASES else pause_schemas
                await asyncio.sleep(sleep_s)
            except Exception as e:
                if abort_balance and phase in _LOW_EXTRACT_PHASES and _is_insufficient_balance(e):
                    _schema_emit(
                        "fail",
                        triple,
                        f"fail: {e}",
                        allowed_sections=prep["allowed_list"],
                    )
                    raise InsufficientBalanceError(str(e)) from e
                err_msg = f"Schema {triple} failed: {e}"
                print(err_msg)
                _schema_emit(
                    "fail",
                    triple,
                    f"fail: {e}",
                    allowed_sections=prep["allowed_list"],
                )
                continue

    if emit_schema_events and on_event and phase == "build":
        hist: Dict[str, int] = {}
        for n in final_nodes:
            role = canonical_section((n.metadata or {}).get("section_role", "Other"))
            hist[role] = hist.get(role, 0) + 1
        ok_n = sum(1 for a in attempts if a["status"] == "ok")
        skip_n = sum(1 for a in attempts if a["status"] == "skip")
        fail_n = sum(1 for a in attempts if a["status"] == "fail")
        missing = [a for a in attempts if a["status"] != "ok"]
        on_event(
            {
                "type": "phase_a_coverage",
                "phase": "build",
                "filename": filename or "",
                "expected_total": len(attempts),
                "ok": ok_n,
                "skip": skip_n,
                "fail": fail_n,
                "section_role_histogram": hist,
                "attempts": attempts,
                "missing_triples": missing,
            }
        )

    return processed


async def _process_document_once(
    doc,
    splitter,
    custom_prompt,
    potential_schema,
    entities,
    relations,
    llm,
    neo4j_driver,
    embed_model,
    weight_llm,
    cfg: PipelineConfig,
    table3: Dict[str, Any],
    text_nodes_override: Optional[List[Any]] = None,
    prompt_suffix: str = "",
    skip_postprocess: bool = False,
    on_event: Optional[EventCallback] = None,
    emit_schema_events: bool = False,
) -> int:
    filename = doc.metadata.get("filename", "Unknown")
    dc_metadata = {
        k: v for k, v in doc.metadata.items() if k.startswith("dc_") or k.startswith("dcterms_")
    }

    nodes = create_nodes_with_metadata(doc)
    add_header_paths(nodes, doc.text)
    doc_blocks = [Document(text=n.get_content(), metadata=dict(n.metadata or {})) for n in nodes]
    final_nodes = splitter.get_nodes_from_documents(doc_blocks)
    enrich_nodes_with_bae_roles(final_nodes, table3)

    counts = {"ok": 0, "skip": 0, "fail": 0}

    def _counting_emit(event: Dict[str, Any]) -> None:
        if event.get("type") == "schema_extract" and emit_schema_events:
            st = str(event.get("status", "")).lower()
            if st in counts:
                counts[st] += 1
        if on_event:
            on_event(event)

    processed = await extract_document_schemas(
        final_nodes=final_nodes,
        custom_prompt=custom_prompt,
        potential_schema=potential_schema,
        entities=entities,
        relations=relations,
        llm=llm,
        neo4j_driver=neo4j_driver,
        embed_model=embed_model,
        cfg=cfg,
        text_nodes_override=text_nodes_override,
        prompt_suffix=prompt_suffix,
        on_event=_counting_emit if emit_schema_events else on_event,
        filename=filename,
        emit_schema_events=emit_schema_events,
        extract_phase="build",
    )

    if emit_schema_events and on_event:
        on_event(
            {
                "type": "document_extract_summary",
                "phase": "build",
                "filename": filename,
                "schemas_ok": counts["ok"],
                "schemas_skipped": counts["skip"],
                "schemas_failed": counts["fail"],
            }
        )

    if skip_postprocess:
        return processed

    try:
        n_updated = _supplement_chunk_metadata(
            neo4j_driver, cfg.neo4j_database, filename, final_nodes
        )
        if n_updated:
            print(f"  Chunk metadata backfill: {n_updated} node(s) for {filename}")
    except Exception as e:
        print(f"  Chunk metadata backfill failed for {filename}: {e}")

    if update_metadata_batch(neo4j_driver, filename, dc_metadata):
        enhance_relations(neo4j_driver, filename, dc_metadata, weight_llm)
    scrub_cloned_argument_spans(neo4j_driver, cfg.neo4j_database, filename)
    return processed


async def _process_document_with_retry(
    doc,
    cfg: PipelineConfig,
    on_event: Optional[EventCallback] = None,
    **kwargs,
) -> int:
    neo4j_driver = kwargs["neo4j_driver"]
    filename = doc.metadata.get("filename", "Unknown")
    max_retries = int(cfg.build_kg.get("doc_max_retries", 2))

    def _emit(event: Dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    for attempt in range(1, max_retries + 2):
        try:
            return await _process_document_once(doc=doc, cfg=cfg, **kwargs)
        except (ServiceUnavailable, SessionExpired, TransientError) as e:
            msg = f"[{filename}] Neo4j error attempt {attempt}: {e}"
            print(msg)
            _emit({"type": "log", "message": msg})
            if attempt > max_retries:
                return 0
            if not wait_for_neo4j(neo4j_driver, cfg.neo4j_database, 180):
                return 0
        except Exception as e:
            msg = f"[{filename}] fatal: {e}"
            print(msg)
            _emit({"type": "log", "message": msg})
            return 0
    return 0


async def build_knowledge_graph_async(
    cfg: PipelineConfig,
    driver: Driver | None = None,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    """Schema-guided triple extraction into Neo4j (logic aligned with 1_2_0_2)."""
    own_driver = driver is None
    neo4j_driver = driver or build_neo4j_driver(cfg)
    stats: Dict[str, Any] = {"succeeded_docs": 0, "failed_docs": [], "schemas_processed": 0}

    def _emit(event: Dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    try:
        neo4j_driver.verify_connectivity()
        entities, relations, potential_schema = load_schema(cfg.schema_dir)
        table3 = load_table3_section_bae(cfg.schema_dir)
        if not potential_schema:
            raise RuntimeError("potential_schema is empty")

        tiers = cfg.build_kg.get("schema_tiers")
        emit_schema_events = False
        if tiers:
            if set(t.lower() for t in tiers) == {"mid"}:
                entities, relations, potential_schema = mid_schema_view(
                    entities, relations, potential_schema
                )
                emit_schema_events = True
            else:
                potential_schema = filter_potential_schema(potential_schema, tiers=tiers)
            _emit(
                {
                    "type": "log",
                    "message": (
                        f"build_kg schema_tiers={list(tiers)} → "
                        f"{len(potential_schema)} triples, "
                        f"{len(entities)} entities, {len(relations)} relations"
                    ),
                }
            )
        if not potential_schema:
            raise RuntimeError("potential_schema empty after schema_tiers filter")

        from neo4j_graphrag.llm import OpenAILLM
        from langchain_openai import ChatOpenAI
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.llms.deepseek import DeepSeek
        from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings

        llm_neo4j = OpenAILLM(
            model_name=cfg.deepseek_model,
            model_params={"max_tokens": 8000, "temperature": 0.1, "top_p": 0.9},
            api_key=cfg.deepseek_api_key,
            base_url=cfg.deepseek_base_url,
        )
        llm_langchain = ChatOpenAI(
            model=cfg.deepseek_model,
            api_key=cfg.deepseek_api_key,
            base_url=cfg.deepseek_base_url,
            temperature=0,
            max_tokens=1000,
        )
        weight_llm = DeepSeek(model=cfg.deepseek_model, api_key=cfg.deepseek_api_key)
        embed_model = SentenceTransformerEmbeddings(model=cfg.embedding_model)

        embed_for_split = HuggingFaceEmbedding(model_name=cfg.embedding_model)
        splitter = SafeSemanticSplitter(
            embed_model=embed_for_split,
            section_role_inferrer=create_section_inferrer(llm=llm_langchain),
            similarity_threshold=float(cfg.build_kg.get("similarity_threshold", 0.72)),
            chunk_size=int(cfg.build_kg.get("chunk_size", 300)),
            window_size=2,
        )

        if cfg.custom_prompt.is_file():
            custom_prompt = cfg.custom_prompt.read_text(encoding="utf-8")
        else:
            custom_prompt = "Extract entities and relations from the text."

        documents = load_markdown_with_agent_metadata(str(cfg.markdown_dir))
        selected = cfg.build_kg.get("selected_files")
        if selected:
            allow = set(selected)
            documents = [d for d in documents if d.metadata.get("filename") in allow]
        else:
            max_docs = cfg.build_kg.get("max_docs", "all")
            if isinstance(max_docs, int) and max_docs > 0:
                documents = documents[:max_docs]

        pause_docs = float(cfg.build_kg.get("pause_between_docs", 3.0))
        total_processed = 0
        doc_total = len(documents)
        for idx, doc in enumerate(tqdm(documents, desc="build_kg"), start=1):
            filename = doc.metadata.get("filename", "Unknown")
            _emit(
                {
                    "type": "document_progress",
                    "current": idx,
                    "total": doc_total,
                    "filename": filename,
                }
            )
            if not neo4j_is_alive(neo4j_driver, cfg.neo4j_database):
                if not wait_for_neo4j(neo4j_driver, cfg.neo4j_database, 180):
                    break
            processed = await _process_document_with_retry(
                doc=doc,
                cfg=cfg,
                on_event=on_event,
                splitter=splitter,
                custom_prompt=custom_prompt,
                potential_schema=potential_schema,
                entities=entities,
                relations=relations,
                llm=llm_neo4j,
                neo4j_driver=neo4j_driver,
                embed_model=embed_model,
                weight_llm=weight_llm,
                table3=table3,
                emit_schema_events=emit_schema_events,
            )
            if processed == 0:
                _emit(
                    {
                        "type": "log",
                        "message": (
                            f"[{filename}] extracted 0 schemas — check DeepSeek balance / API errors "
                            "(see server console for Schema ... failed lines)"
                        ),
                    }
                )
            success = processed > 0
            if success:
                total_processed += processed
                stats["succeeded_docs"] += 1
            else:
                stats["failed_docs"].append(filename)
            _emit(
                {
                    "type": "document_done",
                    "filename": filename,
                    "success": success,
                    "current": idx,
                    "total": doc_total,
                }
            )
            if idx < len(documents):
                await asyncio.sleep(pause_docs)

        stats["schemas_processed"] = total_processed
        stats["document_count"] = len(documents)
        with neo4j_driver.session(database=cfg.neo4j_database) as session:
            stats["node_count"] = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            stats["rel_count"] = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        return stats
    finally:
        if own_driver:
            neo4j_driver.close()


def run_build_kg(
    cfg: PipelineConfig,
    driver: Driver | None = None,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    return asyncio.run(build_knowledge_graph_async(cfg, driver=driver, on_event=on_event))
