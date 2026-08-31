"""MetaPath F1/F4/F2/F3 pipeline (wraps utilities/metapath_path_level)."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.paths import ensure_repo_on_syspath
from kg_build_pipeline.src.schema_loader import load_metapath_relations
from kg_build_pipeline.src.stages.metapath_validate import validate_f1_prerequisites


def _acceptance_options(cfg: PipelineConfig) -> Dict[str, Any]:
    """Parse metapath.acceptance; default mode=lenient for pipeline stability."""
    raw = (cfg.metapath or {}).get("acceptance") or {}
    mode = str(raw.get("mode", "lenient")).strip().lower()
    if mode not in ("strict", "lenient"):
        mode = "lenient"
    allow_orphan = bool(raw.get("allow_orphan_mid", mode == "lenient"))
    allow_empty = bool(raw.get("allow_empty_has_detail_path", mode == "lenient"))
    ratio_raw = raw.get("max_orphan_mid_ratio", 1.0 if mode == "lenient" else None)
    ratio: Optional[float]
    if ratio_raw is None:
        ratio = None
    else:
        try:
            ratio = float(ratio_raw)
        except (TypeError, ValueError):
            ratio = 1.0 if mode == "lenient" else None
    return {
        "mode": mode,
        "allow_orphan_mid": allow_orphan,
        "allow_empty_has_detail_path": allow_empty,
        "max_orphan_mid_ratio": ratio,
    }


def run_metapath(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Clean old MetaPath nodes, build low/mid paths, optional F2/F3."""
    ensure_repo_on_syspath()
    import importlib

    import utilities.metapath_path_level as _mpl

    importlib.reload(_mpl)
    build_all_metapaths = _mpl.build_all_metapaths
    build_mid_metapaths_for_containers = _mpl.build_mid_metapaths_for_containers
    build_mid_metapaths_for_plans = _mpl.build_mid_metapaths_for_plans
    link_mid_to_low = _mpl.link_mid_to_low
    refresh_and_verify_metapath_max_pagerank = _mpl.refresh_and_verify_metapath_max_pagerank
    verify_metapath_path_level = _mpl.verify_metapath_path_level

    subgraph_relations, pagerank_prop = load_metapath_relations(cfg.schema_dir)
    db = cfg.neo4j_database
    stats: Dict[str, Any] = {}
    accept = _acceptance_options(cfg)
    stats["acceptance"] = accept
    print(
        f"[metapath] acceptance mode={accept['mode']} "
        f"allow_orphan_mid={accept['allow_orphan_mid']} "
        f"allow_empty_has_detail_path={accept['allow_empty_has_detail_path']} "
        f"max_orphan_mid_ratio={accept.get('max_orphan_mid_ratio')}"
    )

    with driver.session(database=db) as session:
        n_before = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
        session.run("MATCH (mp:MetaPath) DETACH DELETE mp")
        stats["deleted_metapaths"] = n_before

    try:
        from neo4j_graphrag.indexes import drop_index_if_exists

        drop_index_if_exists(driver, "metapath_embedding_index")
        drop_index_if_exists(driver, "metapath_fulltext_index")
    except Exception as e:
        stats["index_drop_warning"] = str(e)

    stats["f1_preflight"] = validate_f1_prerequisites(
        cfg, driver, subgraph_relations=subgraph_relations
    )

    stats["f1"] = build_all_metapaths(
        driver, subgraph_relations, pagerank_prop, database=db
    )
    stats["verify_f1"] = verify_metapath_path_level(
        driver,
        require_mid=False,
        database=db,
        allow_orphan_mid=True,
        max_orphan_mid_ratio=1.0,
    )

    mid_counters = {"MPU": 1, "EBM": 1, "EEM": 1}
    mid_counters = build_mid_metapaths_for_plans(driver, mid_counters, database=db)
    mid_counters = build_mid_metapaths_for_containers(driver, mid_counters, database=db)
    stats["link"] = link_mid_to_low(
        driver,
        database=db,
        allow_empty_detail_links=bool(accept["allow_empty_has_detail_path"]),
    )
    try:
        stats["verify_f4"] = verify_metapath_path_level(
            driver,
            require_mid=True,
            database=db,
            allow_orphan_mid=bool(accept["allow_orphan_mid"]),
            max_orphan_mid_ratio=accept.get("max_orphan_mid_ratio"),
        )
    except RuntimeError as exc:
        msg = str(exc)
        orphan_only = (
            bool(accept.get("allow_orphan_mid", True))
            and "无 hasDetailPath 子路径" in msg
            and "缺少合法 path_level" not in msg
            and "非法 hasDetailPath" not in msg
            and "错误地 hasDetailPath" not in msg
            and "无 mid MetaPath" not in msg
        )
        if not orphan_only:
            raise
        print(f"[metapath] orphan-mid soft-pass: {msg}")
        stats["verify_f4"] = {
            "soft_passed": True,
            "warning": msg,
            "acceptance": accept,
        }
    stats["pagerank"] = refresh_and_verify_metapath_max_pagerank(
        driver, pagerank_prop=pagerank_prop, database=db
    )

    skip_f2 = bool(cfg.metapath.get("skip_f2_without_qwen", True))
    api_key = os.environ.get("QWEN_API_KEY")
    if skip_f2 and not api_key:
        stats["f2"] = {"skipped": True, "reason": "QWEN_API_KEY not set"}
        stats["f3"] = {"skipped": True, "reason": "F2 skipped"}
    else:
        stats["f2"] = _run_f2(cfg, driver)
        stats["f3"] = _run_f3(cfg, driver)

    with driver.session(database=db) as session:
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
    create_vector_index(
        driver,
        "metapath_embedding_index",
        label="MetaPath",
        embedding_property="embedding",
        dimensions=dim,
        similarity_fn="cosine",
        neo4j_database=cfg.neo4j_database,
    )
    create_fulltext_index(
        driver,
        "metapath_fulltext_index",
        label="MetaPath",
        node_properties=["metaPathQuery", "metaPathText"],
        neo4j_database=cfg.neo4j_database,
    )
    return {"embeddings_written": written, "dimension": dim}
