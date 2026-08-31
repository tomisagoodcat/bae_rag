"""
Run MetaPath pipeline: clean -> F1 -> F4 -> verify -> F2 -> F3.
Execute from repo root: python utilities/run_metapath_pipeline.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase

for _env in [
    ROOT / ".env",
    ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env",
    ROOT.parent / "PaperExtract" / ".env",
]:
    if _env.is_file():
        load_dotenv(_env)
        break

NB_PATH = ROOT / "1_2_1_2pagerankMetapath.ipynb"

NEO4J_DEFAULTS = {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "tomis1cat",
}


def _exec_cell_source(source: str, glb: dict) -> None:
    exec(source, glb)  # noqa: S102


def _load_subgraph_relations() -> dict:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    g = {"__builtins__": __builtins__}
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if "SUBGRAPH_RELATIONS = {" in src and "PAGERANK_PROP" in src:
            _exec_cell_source(src, g)
            return g["SUBGRAPH_RELATIONS"], g["PAGERANK_PROP"]
    raise RuntimeError("SUBGRAPH_RELATIONS cell not found in notebook")


def main() -> None:
    from utilities.metapath_path_level import (
        build_all_metapaths,
        build_mid_metapaths_for_containers,
        build_mid_metapaths_for_plans,
        link_mid_to_low,
        refresh_and_verify_metapath_max_pagerank,
        verify_metapath_path_level,
    )

    uri = os.environ.get("NEO4J_URI", NEO4J_DEFAULTS["NEO4J_URI"])
    user = os.environ.get("NEO4J_USER", NEO4J_DEFAULTS["NEO4J_USER"])
    password = os.environ.get("NEO4J_PASSWORD", NEO4J_DEFAULTS["NEO4J_PASSWORD"])

    driver = GraphDatabase.driver(uri, auth=(user, password))
    subgraph_relations, pagerank_prop = _load_subgraph_relations()

    print("\n" + "=" * 60)
    print("STEP 0: 清理旧 MetaPath + 索引")
    print("=" * 60)
    with driver.session() as session:
        n_before = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
        session.run("MATCH (mp:MetaPath) DETACH DELETE mp")
        print(f"  删除 MetaPath: {n_before}")
    try:
        from neo4j_graphrag.indexes import drop_index_if_exists

        drop_index_if_exists(driver, "metapath_embedding_index")
        drop_index_if_exists(driver, "metapath_fulltext_index")
        print("  索引已删除")
    except Exception as e:
        print(f"  索引删除: {e}")

    print("\n" + "=" * 60)
    print("STEP 1: F1 low MetaPath")
    print("=" * 60)
    summary = build_all_metapaths(driver, subgraph_relations, pagerank_prop)
    print("  summary:", summary)
    verify_metapath_path_level(driver, require_mid=False)

    print("\n" + "=" * 60)
    print("STEP 2: F4 mid + 层级边")
    print("=" * 60)
    mid_counters = {"MPU": 1, "EBM": 1, "EEM": 1}
    mid_counters = build_mid_metapaths_for_plans(driver, mid_counters)
    mid_counters = build_mid_metapaths_for_containers(driver, mid_counters)
    link_stats = link_mid_to_low(driver)
    print("  link_stats:", link_stats)
    verify_metapath_path_level(driver, require_mid=True)

    print("\n" + "=" * 60)
    print("STEP 2b: maxPageRank 刷新与统计（基于 E 段实体 pagerank）")
    print("=" * 60)
    pr_stats = refresh_and_verify_metapath_max_pagerank(driver, pagerank_prop=pagerank_prop)
    print("  pr_stats:", pr_stats["refresh"])

    print("\n" + "=" * 60)
    print("STEP 3: F2 metaPathQuery (LLM)")
    print("=" * 60)
    from neo4j_graphrag.llm import OpenAILLM

    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise EnvironmentError("QWEN_API_KEY not set for F2")

    llm = OpenAILLM(
        model_name="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key,
        model_params={"temperature": 0.1, "max_tokens": 200},
    )

    prompt_tpl = """You are a scientific knowledge expert.
Rewrite the following structured knowledge path into ONE natural English sentence for semantic search.
Requirements: keep entities and technical terms; ONE sentence only; 20-60 words.

Input: {metapath_text}
Output:"""

    with driver.session() as session:
        pending = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.metaPathQuery IS NULL AND mp.metaPathText IS NOT NULL
            RETURN mp.mp_id AS mp_id, mp.metaPathText AS metapath_text
            """
        ).data()

    total = len(pending)
    print(f"  待生成 metaPathQuery: {total}")
    failed = 0
    t0 = time.time()
    with driver.session() as session:
        for idx, row in enumerate(pending, 1):
            mp_id = row["mp_id"]
            text = row["metapath_text"]
            query = None
            last_err = None
            for attempt in range(3):
                try:
                    resp = llm.invoke(prompt_tpl.format(metapath_text=text))
                    query = resp.content.strip().strip('"\'')
                    if len(query) < 20:
                        raise ValueError(f"query too short ({len(query)} chars)")
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(2)
            if query is None:
                failed += 1
                print(f"  ❌ [{idx}/{total}] {mp_id}: {last_err}")
                continue
            session.run(
                "MATCH (mp:MetaPath {mp_id: $mp_id}) SET mp.metaPathQuery = $q",
                mp_id=mp_id,
                q=query,
            )
            if idx % 50 == 0 or idx == total:
                print(f"  [{idx}/{total}] ok, failed={failed}")

    elapsed = time.time() - t0
    print(f"  F2 完成: success={total - failed}, failed={failed}, {elapsed:.1f}s")
    if failed:
        raise RuntimeError(f"F2: {failed}/{total} metaPathQuery 生成失败")

    print("\n" + "=" * 60)
    print("STEP 4: F3 embedding + indexes")
    print("=" * 60)
    import numpy as np
    from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
    from neo4j_graphrag.indexes import (
        create_fulltext_index,
        create_vector_index,
        drop_index_if_exists,
    )

    model_path = os.environ.get("LOCAL_MODEL_PATH_BCE")
    if not model_path:
        raise EnvironmentError("LOCAL_MODEL_PATH_BCE not set")
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    embed_model = SentenceTransformerEmbeddings(model=model_path)

    with driver.session() as session:
        pending_emb = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.metaPathQuery IS NOT NULL AND mp.embedding IS NULL
            RETURN mp.mp_id AS mp_id, mp.metaPathQuery AS q
            """
        ).data()

    print(f"  待生成 embedding: {len(pending_emb)}")
    batch_size = 32
    emb_failed = 0
    with driver.session() as session:
        for start in range(0, len(pending_emb), batch_size):
            batch = pending_emb[start : start + batch_size]
            texts = [r["q"] for r in batch]
            try:
                if len(texts) == 1:
                    embs = [embed_model.embed_query(texts[0])]
                else:
                    embs = [embed_model.embed_query(t) for t in texts]
                for row, emb in zip(batch, embs):
                    if isinstance(emb, np.ndarray):
                        emb = emb.tolist()
                    session.run(
                        "MATCH (mp:MetaPath {mp_id: $id}) SET mp.embedding = $e",
                        id=row["mp_id"],
                        e=emb,
                    )
            except Exception as e:
                emb_failed += len(batch)
                print(f"  ❌ embedding batch @ {start}: {e}")

    if emb_failed:
        raise RuntimeError(f"F3: {emb_failed} embedding 写入失败")

    drop_index_if_exists(driver, "metapath_embedding_index")
    drop_index_if_exists(driver, "metapath_fulltext_index")
    create_vector_index(
        driver=driver,
        name="metapath_embedding_index",
        label="MetaPath",
        embedding_property="embedding",
        dimensions=768,
        similarity_fn="cosine",
    )
    create_fulltext_index(
        driver=driver,
        name="metapath_fulltext_index",
        label="MetaPath",
        node_properties=["metaPathText"],
    )
    print("  ✅ 索引 metapath_embedding_index, metapath_fulltext_index")

    print("\n" + "=" * 60)
    print("FINAL 统计")
    print("=" * 60)
    with driver.session() as session:
        stats = session.run(
            """
            MATCH (mp:MetaPath)
            RETURN mp.path_level AS level,
                   count(*) AS total,
                   sum(CASE WHEN mp.metaPathQuery IS NOT NULL THEN 1 ELSE 0 END) AS with_query,
                   sum(CASE WHEN mp.embedding IS NOT NULL THEN 1 ELSE 0 END) AS with_emb
            ORDER BY level
            """
        ).data()
        edges = session.run(
            """
            MATCH (:MetaPath {path_level:'mid'})-[h:hasDetailPath]->(:MetaPath {path_level:'low'})
            RETURN count(h) AS c
            """
        ).single()["c"]
    for row in stats:
        print(f"  {row['level']}: nodes={row['total']}, query={row['with_query']}, emb={row['with_emb']}")
    print(f"  hasDetailPath edges: {edges}")
    driver.close()
    print("\n✅ Pipeline 全部完成")


if __name__ == "__main__":
    main()
