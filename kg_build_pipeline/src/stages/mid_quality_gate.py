"""Mid quality gate: validate → Qwen review → targeted single-chunk re-extract."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

from llama_index.core import Document
from neo4j import Driver

from kg_build_pipeline.src.agents.mid_reviewer import review_mid_document
from kg_build_pipeline.src.chunk_roles import enrich_nodes_with_bae_roles
from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.schema_loader import load_schema, load_table3_section_bae
from kg_build_pipeline.src.schema_tier import mid_schema_view
from kg_build_pipeline.src.stages.build_kg import extract_document_schemas, join_nodes_text
from kg_build_pipeline.src.stages.document_loader import (
    SafeSemanticSplitter,
    add_header_paths,
    create_nodes_with_metadata,
    create_section_inferrer,
    load_markdown_with_agent_metadata,
)
from kg_build_pipeline.src.mid_repair import (
    filter_potential_schema_by_rule,
    mark_entity_rejected,
    merge_repair_issues,
    reject_violation_nodes,
    resolve_chunk_nodes,
    violations_for_reject,
)
from kg_build_pipeline.src.stages.mid_validate import validate_mid_document
from kg_build_pipeline.src.stages.metadata_enhance import enhance_relations, update_metadata_batch

EventCallback = Callable[[Dict[str, Any]], None]

REEXTRACT_ACTIONS = {"REEXTRACT", "EXPAND_SPAN", "RETYPE"}


def persist_mid_gate_status(
    driver: Driver,
    database: str,
    filename: str,
    *,
    status: str,
    score: Optional[float] = None,
) -> int:
    """Write mid_gate_status onto Chunk nodes for this document (Low expand gate)."""
    status_norm = str(status or "").strip().upper() or "FLAGGED"
    with driver.session(database=database) as session:
        result = session.run(
            """
            MATCH (c:Chunk)
            WHERE c.filename = $filename
            SET c.mid_gate_status = $status,
                c.mid_gate_score = $score
            RETURN count(c) AS cnt
            """,
            filename=filename,
            status=status_norm,
            score=score,
        )
        rec = result.single()
        return int(rec["cnt"]) if rec else 0


REEXTRACT_PROMPT_SUFFIX = """

# Mid targeted re-extraction (quality gate)

You are re-extracting **mid-level** schema patterns only for this text span.

Constraints:
- Ground every entity and relation in the provided text. Do **not** invent nodes solely because a reviewer suggested them.
- Use reviewer/validator notes only as hypotheses to check against the text.
- Focal `mp_Claim` may be co-created with `whu_SupportGraph` when the text supports a focal proposition; link SupportGraph → Claim via `mp_supports`/`mp_challenges` (not `prov_hadMember`).
- `whu_ScienceEvidence` links to `whu_SupportGraph` only via `mp_supports`/`mp_challenges` (never directly to `mp_Claim`).
- If the text does not support a fix, omit the relation rather than fabricating it.

Reviewer / validator context:
{repair_context}
"""


def _format_repair_context_for_prompt(repair: Dict[str, Any]) -> str:
    """Serialize repair notes safely for neo4j_graphrag prompt templates.

    SimpleKGPipeline later calls ``prompt_template.format(text=..., schema=...,
    examples=...)`` on the full prompt string. Any literal ``{`` / ``}`` in the
    embedded repair JSON must be doubled so they are not treated as placeholders.
    """
    text = json.dumps(repair, ensure_ascii=False)
    return text.replace("{", "{{").replace("}", "}}")


def _build_reextract_suffix(repair: Dict[str, Any]) -> str:
    return REEXTRACT_PROMPT_SUFFIX.replace(
        "{repair_context}",
        _format_repair_context_for_prompt(repair),
    )


def _gate_cfg(cfg: PipelineConfig) -> Dict[str, Any]:
    return cfg.raw.get("mid_quality_gate") or {}


def _list_doc_filenames(cfg: PipelineConfig, driver: Driver):
    selected = cfg.build_kg.get("selected_files")
    docs = load_markdown_with_agent_metadata(str(cfg.markdown_dir))
    if selected:
        allow = set(selected)
        docs = [d for d in docs if d.metadata.get("filename") in allow]
    else:
        max_docs = cfg.build_kg.get("max_docs", "all")
        if isinstance(max_docs, int) and max_docs > 0:
            docs = docs[:max_docs]
    return [d.metadata.get("filename", "Unknown") for d in docs], docs


async def _targeted_reextract(
    *,
    doc,
    filename: str,
    final_nodes: List[Any],
    issues: List[Dict[str, Any]],
    entities,
    relations,
    potential_schema,
    llm,
    neo4j_driver,
    embed_model,
    custom_prompt: str,
    cfg: PipelineConfig,
    use_rule_targeted_schemas: bool = True,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    processed = 0
    seen_texts = set()
    schemas_per_issue: List[int] = []
    chunk_methods: Dict[str, int] = {}
    for issue in issues:
        action = str(issue.get("suggested_action", "")).upper()
        if action not in REEXTRACT_ACTIONS:
            continue
        nodes, resolution_method = resolve_chunk_nodes(
            neo4j_driver,
            cfg.neo4j_database,
            filename,
            final_nodes,
            issue,
        )
        chunk_methods[resolution_method] = chunk_methods.get(resolution_method, 0) + 1
        if not nodes:
            continue
        text_key = join_nodes_text(nodes)[:200]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        schemas = (
            filter_potential_schema_by_rule(issue, potential_schema)
            if use_rule_targeted_schemas
            else potential_schema
        )
        schemas_per_issue.append(len(schemas))
        repair = {
            "rule_id": issue.get("rule_id"),
            "type": issue.get("type"),
            "entity": issue.get("entity"),
            "reason": issue.get("reason"),
            "suggested_action": action,
            "source": issue.get("source"),
        }
        suffix = _build_reextract_suffix(repair)
        processed += await extract_document_schemas(
            final_nodes=final_nodes,
            custom_prompt=custom_prompt,
            potential_schema=schemas,
            entities=entities,
            relations=relations,
            llm=llm,
            neo4j_driver=neo4j_driver,
            embed_model=embed_model,
            cfg=cfg,
            text_nodes_override=nodes,
            prompt_suffix=suffix,
            on_event=on_event,
            filename=filename,
            emit_schema_events=bool(on_event),
            extract_phase="reextract",
        )
    return {
        "reextract_schemas": processed,
        "schemas_per_issue": schemas_per_issue,
        "chunk_resolution": chunk_methods,
    }


async def _prepare_doc_nodes(doc, splitter, table3):
    nodes = create_nodes_with_metadata(doc)
    add_header_paths(nodes, doc.text)
    doc_blocks = [Document(text=n.get_content(), metadata=dict(n.metadata or {})) for n in nodes]
    final_nodes = splitter.get_nodes_from_documents(doc_blocks)
    enrich_nodes_with_bae_roles(final_nodes, table3)
    return final_nodes


async def run_mid_quality_gate_async(
    cfg: PipelineConfig,
    driver: Driver,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    def _emit(event: Dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    gate = _gate_cfg(cfg)
    max_iter = int(gate.get("max_iterations", 3))
    pass_score = float(gate.get("pass_score", 0.78))
    use_rule_targeted_schemas = bool(gate.get("use_rule_targeted_schemas", True))
    pass_on_hard_zero = bool(gate.get("pass_on_hard_zero", True))

    entities_all, relations_all, ps_all = load_schema(cfg.schema_dir)
    entities, relations, potential_schema = mid_schema_view(
        entities_all, relations_all, ps_all
    )
    mid_schema_summary = {
        "triples": [[t[0], t[1], t[2], t[4] if len(t) > 4 else None] for t in potential_schema],
        "note": (
            "SE → SupportGraph via mp_supports/mp_challenges only; "
            "SupportGraph → Claim via mp_supports/mp_challenges (not hadMember)."
        ),
    }
    table3 = load_table3_section_bae(cfg.schema_dir)

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

    filenames, documents = _list_doc_filenames(cfg, driver)
    doc_by_name = {d.metadata.get("filename"): d for d in documents}

    results: List[Dict[str, Any]] = []
    for filename in filenames:
        doc = doc_by_name.get(filename)
        if doc is None:
            continue
        _emit({"type": "log", "message": f"[mid_quality_gate] {filename}"})
        final_nodes = await _prepare_doc_nodes(doc, splitter, table3)
        doc_result: Dict[str, Any] = {
            "filename": filename,
            "iterations": [],
            "status": "FLAGGED",
        }
        prev_hard: Optional[int] = None

        for iteration in range(1, max_iter + 1):
            _emit(
                {
                    "type": "mid_gate_phase",
                    "phase": "validate",
                    "filename": filename,
                    "iteration": iteration,
                }
            )
            report = validate_mid_document(driver, cfg.neo4j_database, filename)
            _emit(
                {
                    "type": "mid_gate_validate",
                    "filename": filename,
                    "iteration": iteration,
                    "hard_count": report.get("hard_count", 0),
                    "warning_count": report.get("warning_count", 0),
                    "hard_violations": report.get("hard_violations", []),
                    "warnings": report.get("warnings", []),
                }
            )
            _emit(
                {
                    "type": "mid_gate_phase",
                    "phase": "review",
                    "filename": filename,
                    "iteration": iteration,
                }
            )
            review = review_mid_document(
                cfg, driver, filename, report, mid_schema_summary=mid_schema_summary
            )
            hard = int(report.get("hard_count", 0))
            score = float(review.get("overall_score", 0.0))
            iter_info = {
                "iteration": iteration,
                "hard_count": hard,
                "overall_score": score,
                "decision": review.get("decision"),
                "issue_count": len(review.get("issues") or []),
            }
            doc_result["iterations"].append(iter_info)
            _emit(
                {
                    "type": "mid_gate_review",
                    "filename": filename,
                    "iteration": iteration,
                    "scores": {
                        "type_score": review.get("type_score"),
                        "relation_score": review.get("relation_score"),
                        "coverage_score": review.get("coverage_score"),
                        "overall_score": score,
                    },
                    "overall_score": score,
                    "decision": review.get("decision"),
                    "issue_count": len(review.get("issues") or []),
                }
            )
            _emit(
                {
                    "type": "log",
                    "message": (
                        f"  iter {iteration}: hard={hard} score={score} "
                        f"decision={review.get('decision')}"
                    ),
                }
            )

            if hard == 0 and (pass_on_hard_zero or score >= pass_score):
                doc_result["status"] = "PASS"
                doc_result["final_score"] = score
                break

            if iteration >= max_iter:
                doc_result["status"] = "FLAGGED"
                doc_result["final_score"] = score
                break

            # Apply DELETE marks from reviewer
            for issue in review.get("issues") or []:
                if str(issue.get("suggested_action", "")).upper() == "DELETE":
                    mark_entity_rejected(
                        driver, cfg.neo4j_database, filename, issue.get("entity")
                    )

            if bool(gate.get("early_stop_on_unchanged_hard", True)) and (
                prev_hard is not None and prev_hard == hard
            ):
                iter_info["early_stop"] = True
                iter_info["early_stop_reason"] = "hard_count_unchanged"
                _emit(
                    {
                        "type": "mid_gate_early_stop",
                        "filename": filename,
                        "iteration": iteration,
                        "hard_count": hard,
                        "reason": "hard_count_unchanged",
                    }
                )
                doc_result["status"] = "FLAGGED"
                doc_result["final_score"] = score
                break

            reject_stats: Dict[str, Any] = {"mode": "skip", "count": 0, "names": []}
            if bool(gate.get("reject_before_reextract", True)):
                to_reject = violations_for_reject(
                    report, gate.get("reject_rules", ["M13", "M06"])
                )
                reject_mode = str(gate.get("reject_mode", "mark")).lower()
                if reject_mode not in ("mark", "delete"):
                    reject_mode = "mark"
                reject_stats = reject_violation_nodes(
                    driver,
                    cfg.neo4j_database,
                    filename,
                    to_reject,
                    mode=reject_mode,
                )
                _emit(
                    {
                        "type": "mid_gate_reject",
                        "filename": filename,
                        "iteration": iteration,
                        "mode": reject_stats.get("mode"),
                        "count": reject_stats.get("count", 0),
                        "names": reject_stats.get("names", []),
                    }
                )
            iter_info["reject"] = reject_stats

            if bool(gate.get("merge_validator_issues", True)):
                merged_issues = merge_repair_issues(
                    review.get("issues") or [],
                    report,
                    merge_rules=gate.get("merge_rules", ["M13", "M06", "M01", "M02", "M03", "M04", "M05", "M09"]),
                    max_issues=int(gate.get("max_reextract_issues_per_iter", 15)),
                )
            else:
                merged_issues = [
                    i
                    for i in (review.get("issues") or [])
                    if str(i.get("suggested_action", "")).upper() in REEXTRACT_ACTIONS
                ]
            iter_info["merged_issue_count"] = len(merged_issues)

            _emit(
                {
                    "type": "mid_gate_phase",
                    "phase": "reextract",
                    "filename": filename,
                    "iteration": iteration,
                }
            )
            reextract_info = await _targeted_reextract(
                doc=doc,
                filename=filename,
                final_nodes=final_nodes,
                issues=merged_issues,
                entities=entities,
                relations=relations,
                potential_schema=potential_schema,
                llm=llm_neo4j,
                neo4j_driver=driver,
                embed_model=embed_model,
                custom_prompt=custom_prompt,
                cfg=cfg,
                use_rule_targeted_schemas=use_rule_targeted_schemas,
                on_event=on_event,
            )
            iter_info["reextract_schemas"] = reextract_info.get("reextract_schemas", 0)
            iter_info["schemas_per_issue"] = reextract_info.get("schemas_per_issue", [])
            iter_info["chunk_resolution"] = reextract_info.get("chunk_resolution", {})
            _emit(
                {
                    "type": "mid_gate_reextract",
                    "filename": filename,
                    "iteration": iteration,
                    "reextract_schemas": reextract_info.get("reextract_schemas", 0),
                    "schemas_per_issue": reextract_info.get("schemas_per_issue", []),
                    "chunk_resolution": reextract_info.get("chunk_resolution", {}),
                    "merged_issue_count": len(merged_issues),
                }
            )

            dc_metadata = {
                k: v
                for k, v in doc.metadata.items()
                if k.startswith("dc_") or k.startswith("dcterms_")
            }
            update_metadata_batch(driver, filename, dc_metadata)
            enhance_relations(driver, filename, dc_metadata, weight_llm)
            prev_hard = hard

        _emit(
            {
                "type": "mid_gate_phase",
                "phase": "done",
                "filename": filename,
                "iteration": doc_result["iterations"][-1]["iteration"]
                if doc_result["iterations"]
                else 0,
                "status": doc_result.get("status"),
                "final_score": doc_result.get("final_score"),
            }
        )
        persist_mid_gate_status(
            driver,
            cfg.neo4j_database,
            filename,
            status=str(doc_result.get("status") or "FLAGGED"),
            score=doc_result.get("final_score"),
        )
        results.append(doc_result)

    passed = sum(1 for r in results if r.get("status") == "PASS")
    flagged = sum(1 for r in results if r.get("status") == "FLAGGED")
    return {
        "documents": len(results),
        "passed": passed,
        "flagged": flagged,
        "results": results,
        "pass_score": pass_score,
        "pass_on_hard_zero": pass_on_hard_zero,
        "use_rule_targeted_schemas": use_rule_targeted_schemas,
        "max_iterations": max_iter,
    }


def run_mid_quality_gate(
    cfg: PipelineConfig,
    driver: Driver | None = None,
    on_event: Optional[EventCallback] = None,
) -> Dict[str, Any]:
    from kg_build_pipeline.src.neo4j_util import build_neo4j_driver

    own = driver is None
    d = driver or build_neo4j_driver(cfg)
    try:
        return asyncio.run(run_mid_quality_gate_async(cfg, d, on_event=on_event))
    finally:
        if own:
            d.close()
