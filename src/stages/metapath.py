"""MetaPath F1/F4/F2/F3 pipeline (wraps utilities/metapath_path_level)."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.paths import ensure_repo_on_syspath
from kg_build_pipeline.src.schema_loader import load_metapath_relations


def run_metapath(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Clean old MetaPath nodes, build low/mid paths, optional F2/F3."""
    ensure_repo_on_syspath()
    from utilities.metapath_path_level import (
        build_all_metapaths,
        build_mid_metapaths_for_containers,
        build_mid_metapaths_for_plans,
        link_mid_to_low,
        refresh_and_verify_metapath_max_pagerank,
        verify_metapath_path_level,
    )

    subgraph_relations, pagerank_prop = load_metapath_relations(cfg.schema_dir)
    stats: Dict[str, Any] = {}

    with driver.session(database=cfg.neo4j_database) as session:
        n_before = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
        session.run("MATCH (mp:MetaPath) DETACH DELETE mp")
        stats["deleted_metapaths"] = n_before

    try:
        from neo4j_graphrag.indexes import drop_index_if_exists

        drop_index_if_exists(driver, "metapath_embedding_index")
        drop_index_if_exists(driver, "metapath_fulltext_index")
    except Exception as e:
        stats["index_drop_warning"] = str(e)

    stats["f1"] = build_all_metapaths(driver, subgraph_relations, pagerank_prop)
    verify_metapath_path_level(driver, require_mid=False)

    mid_counters = {"MPU": 1, "EBM": 1, "EEM": 1}
    mid_counters = build_mid_metapaths_for_plans(driver, mid_counters)
    mid_counters = build_mid_metapaths_for_containers(driver, mid_counters)
    stats["link"] = link_mid_to_low(driver)
    verify_metapath_path_level(driver, require_mid=True)
    stats["pagerank"] = refresh_and_verify_metapath_max_pagerank(
        driver, pagerank_prop=pagerank_prop
    )

    skip_f2 = bool(cfg.metapath.get("skip_f2_without_qwen", True))
    api_key = os.environ.get("QWEN_API_KEY")
    if skip_f2 and not api_key:
        stats["f2"] = {"skipped": True, "reason": "QWEN_API_KEY not set"}
        stats["f3"] = {"skipped": True, "reason": "F2 skipped"}
    else:
        stats["f2"] = _run_f2(cfg, driver)
        stats["f3"] = _run_f3(cfg, driver)

    with driver.session(database=cfg.neo4j_database) as session:
        stats["metapath_low"] = session.run(
            "MATCH (mp:MetaPath {path_level:'low'}) RETURN count(mp) AS c"
        ).single()["c"]
        stats["metapath_mid"] = session.run(
            "MATCH (mp:MetaPath {path_level:'mid'}) RETURN count(mp) AS c"
        ).single()["c"]
        stats["hasDetailPath"] = session.run(
            "MATCH (:MetaPath {path_level:'mid'})-[h:hasDetailPath]->(:MetaPath {path_level:'low'}) RETURN count(h) AS c"
        ).single()["c"]
    return stats


def _run_f2(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    from neo4j_graphrag.llm import OpenAILLM

    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise EnvironmentError("QWEN_API_KEY required for F2")

    llm = OpenAILLM(
        model_name="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key,
        model_params={"temperature": 0.1, "max_tokens": 200},
    )
    prompt_tpl = (
        "Rewrite this knowledge path into ONE English sentence (20-60 words) for search:\n\n"
        "{metapath_text}\n\nOutput:"
    )
    with driver.session(database=cfg.neo4j_database) as session:
        pending = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.metaPathQuery IS NULL AND mp.metaPathText IS NOT NULL
            RETURN mp.mp_id AS mp_id, mp.metaPathText AS text
            """
        ).data()

    failed = 0
    t0 = time.time()
    with driver.session(database=cfg.neo4j_database) as session:
        for idx, row in enumerate(pending, 1):
            query = None
            for _ in range(3):
                try:
                    resp = llm.invoke(prompt_tpl.format(metapath_text=row["text"]))
                    query = resp.content.strip().strip("\"'")
                    if len(query) >= 20:
                        break
                except Exception:
                    time.sleep(2)
            if not query:
                failed += 1
                continue
            session.run(
                "MATCH (mp:MetaPath {mp_id: $mp_id}) SET mp.metaPathQuery = $q",
                mp_id=row["mp_id"],
                q=query,
            )
    return {"total": len(pending), "failed": failed, "seconds": time.time() - t0}


def _run_f3(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    import numpy as np
    from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
    from neo4j_graphrag.indexes import create_fulltext_index, create_vector_index, drop_index_if_exists

    model_path = cfg.metapath.get("embedding_model", cfg.embedding_model)
    embedder = SentenceTransformerEmbeddings(model=model_path)

    with driver.session(database=cfg.neo4j_database) as session:
        rows = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.metaPathQuery IS NOT NULL AND mp.embedding IS NULL
            RETURN mp.mp_id AS mp_id, mp.metaPathQuery AS text
            """
        ).data()

    written = 0
    with driver.session(database=cfg.neo4j_database) as session:
        for row in rows:
            vec = embedder.embed_query(row["text"])
            session.run(
                "MATCH (mp:MetaPath {mp_id: $id}) SET mp.embedding = $emb",
                id=row["mp_id"],
                emb=[float(x) for x in vec],
            )
            written += 1

    dim = len(embedder.embed_query("test"))
    for name in ("metapath_embedding_index", "metapath_fulltext_index"):
        drop_index_if_exists(driver, name)
    create_vector_index(driver, "MetaPath", "embedding", "metapath_embedding_index", dimension=dim)
    create_fulltext_index(
        driver,
        "MetaPath",
        ["metaPathQuery", "metaPathText"],
        "metapath_fulltext_index",
    )
    return {"embeddings_written": written, "dimension": dim}
