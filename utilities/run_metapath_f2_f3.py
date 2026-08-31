"""Resume F2 metaPathQuery + F3 embedding/index only."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env")

from neo4j import GraphDatabase
from neo4j_graphrag.llm import OpenAILLM


def main() -> None:
    import numpy as np
    from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
    from neo4j_graphrag.indexes import (
        create_fulltext_index,
        create_vector_index,
        drop_index_if_exists,
    )

    password = os.environ.get("NEO4J_PASSWORD", "tomis1cat")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )

    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise EnvironmentError("QWEN_API_KEY not set")

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

    with driver.session() as session:
        pending = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.metaPathQuery IS NULL AND mp.metaPathText IS NOT NULL
            RETURN mp.mp_id AS mp_id, mp.metaPathText AS text
            """
        ).data()

    total = len(pending)
    print(f"F2 pending: {total}")
    failed = 0
    t0 = time.time()
    with driver.session() as session:
        for idx, row in enumerate(pending, 1):
            query = None
            last_err = None
            for attempt in range(3):
                try:
                    resp = llm.invoke(prompt_tpl.format(metapath_text=row["text"]))
                    query = resp.content.strip().strip('"\'')
                    if len(query) < 20:
                        raise ValueError(f"too short: {len(query)}")
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(2)
            if query is None:
                failed += 1
                print(f"  FAIL [{idx}/{total}] {row['mp_id']}: {last_err}")
                continue
            session.run(
                "MATCH (mp:MetaPath {mp_id: $id}) SET mp.metaPathQuery = $q",
                id=row["mp_id"],
                q=query,
            )
            if idx % 25 == 0 or idx == total:
                print(f"  [{idx}/{total}] failed={failed}")

    print(f"F2 done: failed={failed}/{total}, {time.time()-t0:.0f}s")
    if failed:
        raise RuntimeError(f"F2 failed {failed} items")

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

    print(f"F3 pending embeddings: {len(pending_emb)}")
    batch_size = 32
    emb_failed = 0
    t1 = time.time()
    with driver.session() as session:
        for start in range(0, len(pending_emb), batch_size):
            batch = pending_emb[start : start + batch_size]
            texts = [r["q"] for r in batch]
            try:
                embs = (
                    [embed_model.embed_query(texts[0])]
                    if len(texts) == 1
                    else [embed_model.embed_query(t) for t in texts]
                )
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
                print(f"  emb batch fail @ {start}: {e}")
            if (start + batch_size) % 256 == 0 or start + batch_size >= len(pending_emb):
                print(f"  emb progress {min(start+batch_size, len(pending_emb))}/{len(pending_emb)}")

    if emb_failed:
        raise RuntimeError(f"F3 embedding failed: {emb_failed}")
    print(f"F3 embeddings done in {time.time()-t1:.0f}s")

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
    print("Indexes created")

    with driver.session() as session:
        stats = session.run(
            """
            MATCH (mp:MetaPath)
            RETURN mp.path_level AS level,
                   count(*) AS total,
                   sum(CASE WHEN mp.metaPathQuery IS NOT NULL THEN 1 ELSE 0 END) AS q,
                   sum(CASE WHEN mp.embedding IS NOT NULL THEN 1 ELSE 0 END) AS e
            ORDER BY level
            """
        ).data()
        edges = session.run(
            "MATCH ()-[h:hasDetailPath]->() RETURN count(h) AS c"
        ).single()["c"]
    print("FINAL", stats, "hasDetailPath", edges)
    driver.close()


if __name__ == "__main__":
    main()
