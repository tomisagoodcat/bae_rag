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

from kg_build_pipeline.src.chunk_roles import canonical_section, enrich_nodes_with_bae_roles
from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.neo4j_util import (
    build_neo4j_driver,
    clear_neo4j,
    neo4j_is_alive,
    wait_for_neo4j,
)
from kg_build_pipeline.src.schema_loader import load_schema, load_table3_section_bae
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
__all__ = ["build_neo4j_driver", "clear_neo4j", "run_build_kg"]


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
) -> int:
    from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

    filename = doc.metadata.get("filename", "Unknown")
    dc_metadata = {
        k: v for k, v in doc.metadata.items() if k.startswith("dc_") or k.startswith("dcterms_")
    }
    perform_er = bool(cfg.build_kg.get("perform_entity_resolution", False))
    pause_schemas = float(cfg.build_kg.get("pause_between_schemas", 1.0))

    nodes = create_nodes_with_metadata(doc)
    add_header_paths(nodes, doc.text)
    doc_blocks = [Document(text=n.get_content(), metadata=dict(n.metadata or {})) for n in nodes]
    final_nodes = splitter.get_nodes_from_documents(doc_blocks)
    enrich_nodes_with_bae_roles(final_nodes, table3)

    processed = 0
    for schema in potential_schema:
        try:
            e1, r, e2 = schema[0], schema[1], schema[2]
            sections = schema[3] if len(schema) > 3 else []
            allowed = schema_allowed_set(sections)
            _entities = [e for e in entities if e.get("label") in (e1, e2)]
            _relations = [rel for rel in relations if rel.get("label") == r]
            if not _entities or not _relations:
                continue
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
                continue
            text = join_nodes_text(selected)
            if not text.strip():
                continue

            kg_builder = SimpleKGPipeline(
                llm=llm,
                driver=neo4j_driver,
                embedder=embed_model,
                entities=_entities,
                relations=_relations,
                text_splitter=None,
                potential_schema=[schema[:3]],
                from_pdf=False,
                perform_entity_resolution=perform_er,
                prompt_template=custom_prompt,
                neo4j_database=cfg.neo4j_database,
            )
            await kg_builder.run_async(text=text)
            processed += 1
            await asyncio.sleep(pause_schemas)
        except Exception as e:
            err_msg = f"Schema {schema[:3]} failed: {e}"
            print(err_msg)
            continue

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
    return processed


async def _process_document_with_retry(doc, cfg: PipelineConfig, on_event: Optional[EventCallback] = None, **kwargs) -> int:
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


EventCallback = Callable[[Dict[str, Any]], None]


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
