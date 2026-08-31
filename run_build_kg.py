# -*- coding: utf-8 -*-
"""Run KG build pipeline from 1_2_0_2build_kg__neo4j.ipynb (cells 3, 5, 7, 13)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def _install_torch_stub() -> None:
    """Prevent broken torch DLL from blocking spacy / sentence_transformers imports."""
    if "torch" in sys.modules:
        return

    import types

    stub = types.ModuleType("torch")
    stub.__version__ = "0.0.0+stub"
    stub.Tensor = object
    stub.device = lambda *args, **kwargs: "cpu"
    stub.cuda = types.SimpleNamespace(is_available=lambda: False)
    stub.nn = types.SimpleNamespace()
    stub.no_grad = lambda fn=None: (lambda f: f)(fn) if fn else types.SimpleNamespace(
        __enter__=lambda s: None, __exit__=lambda s, *a: None
    )
    stub.long = int
    stub.float = float
    stub.int = int
    stub.bool = bool
    stub.save = lambda *a, **k: None
    stub.load = lambda *a, **k: {}
    stub.from_numpy = lambda arr: arr
    stub.as_tensor = lambda data, *a, **k: data
    stub.zeros = lambda *shape, **k: [0.0] * (shape[0] if shape else 0)
    stub.ones = lambda *shape, **k: [1.0] * (shape[0] if shape else 0)
    stub.tensor = lambda data, *a, **k: data
    stub.get_default_device = lambda: "cpu"
    stub.set_default_device = lambda *a, **k: None
    stub.serialization = types.SimpleNamespace(
        register_package=lambda *a, **k: (lambda fn: fn)
    )
    stub._load_dll_libraries = lambda: None
    sys.modules["torch"] = stub
    sys.modules["torch.nn"] = stub.nn
    sys.modules["torch.cuda"] = stub.cuda


_install_torch_stub()

FALLBACK_HELPERS = '''
from neo4j_graphrag.embeddings.base import Embedder

class HashEmbedder(Embedder):
    """Deterministic pseudo-embeddings when torch/sentence-transformers unavailable."""
    DIM = 384

    def embed_query(self, text: str) -> list[float]:
        import numpy as np
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        v = np.random.default_rng(seed).standard_normal(self.DIM)
        norm = float(np.linalg.norm(v)) or 1.0
        return (v / norm).tolist()


class FallbackSplitter:
    """Structure-based splitter (no semantic embedding)."""
    def __init__(self, embed_model=None, section_role_inferrer=None, chunk_size=300, **kwargs):
        self._section_role_inferrer = section_role_inferrer
        self.chunk_size = chunk_size

    def get_nodes_from_documents(self, documents, **kwargs):
        nodes = []
        for doc in documents:
            text = doc.text or ""
            md = dict(doc.metadata or {})
            chunks = split_by_structure(text, chunk_size=self.chunk_size)
            for chunk in chunks:
                meta = dict(md)
                header = meta.get("header_path", "Unknown")
                if self._section_role_inferrer and "section_role" not in meta:
                    try:
                        meta["section_role"] = self._section_role_inferrer(chunk, header)
                    except Exception:
                        meta["section_role"] = "Other"
                nodes.append(TextNode(text=chunk, metadata=meta))
        return nodes
'''


def _patch_cell_source(idx: int, src: str) -> str:
    if idx == 5:
        src = src.replace(
            "from llama_index.embeddings.huggingface import HuggingFaceEmbedding\n", ""
        )
        src = src.replace(
            "from llama_index.core.node_parser import SemanticSplitterNodeParser\n", ""
        )
        src = src.replace(
            "from llama_index.llms.deepseek import DeepSeek\n", ""
        )
        marker = "class SafeSemanticSplitter"
        if marker in src:
            src = src.replace(
                src[src.find(marker): src.find("\n\ndef create_section_inferrer")],
                FALLBACK_HELPERS.strip() + "\n\n",
            )
    if idx == 13:
        src = src.replace(
            "from llama_index.embeddings.huggingface import HuggingFaceEmbedding\n", ""
        )
        src = src.replace(
            "embed_for_split = HuggingFaceEmbedding(model_name=LOCAL_EMBEDDING_PATH)\n        ",
            "",
        )
        src = src.replace(
            "from llama_index.llms.deepseek import DeepSeek\n        weight_llm = DeepSeek(model=DEEPSEEK_MODEL, api_key=api_key)\n        print(f\"   ✅ 权重 LLM 已初始化\")",
            "weight_llm = None\n        print(f\"   ⚠️ 权重 LLM 跳过（避免 torch 依赖）\")",
        )
        src = src.replace(
            "from langchain_openai import ChatOpenAI\n        llm_langchain = ChatOpenAI(\n            model=DEEPSEEK_MODEL, api_key=api_key,\n            base_url=DEEPSEEK_BASE_URL, temperature=0, max_tokens=1000,\n        )\n        print(f\"   ✅ Section LLM 已初始化\")",
            "llm_langchain = None\n        print(f\"   ⚠️ Section LLM 跳过（仅规则推断 section_role）\")",
        )
        src = src.replace(
            "section_role_inferrer = create_section_inferrer(llm=llm_langchain)",
            "section_role_inferrer = create_section_inferrer(llm=None)",
        )
        src = src.replace("SafeSemanticSplitter", "FallbackSplitter")
        src = src.replace("            embed_model=embed_for_split,\n", "")
        src = src.replace(
            "splitter = FallbackSplitter(\n            section_role_inferrer=section_role_inferrer,\n            similarity_threshold=0.72,\n            chunk_size=300,\n            window_size=2,\n        )",
            "splitter = FallbackSplitter(\n            section_role_inferrer=section_role_inferrer,\n            chunk_size=300,\n        )",
        )
        src = src.replace(
            "from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings\n        embed_model = SentenceTransformerEmbeddings(model=LOCAL_EMBEDDING_PATH)\n        print(f\"   ✅ KG-Embedding 从本地加载: {LOCAL_EMBEDDING_PATH}\")",
            "try:\n            from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings\n            embed_model = SentenceTransformerEmbeddings(model=LOCAL_EMBEDDING_PATH)\n            print(f\"   ✅ KG-Embedding 从本地加载: {LOCAL_EMBEDDING_PATH}\")\n        except Exception as e:\n            print(f\"   ⚠️ 本地 embedding 不可用 ({e})，使用 HashEmbedder\")\n            embed_model = HashEmbedder()",
        )
    return src


def _exec_notebook_cells(indices: list[int]) -> dict:
    nb = json.loads((ROOT / "1_2_0_2build_kg__neo4j.ipynb").read_text(encoding="utf-8"))
    g: dict = {"__name__": "kg_pipeline", "__file__": str(ROOT / "run_build_kg.py"), "hashlib": hashlib}
    for idx in indices:
        src = "".join(nb["cells"][idx].get("source", []))
        if not src.strip():
            continue
        if idx == 13 and 'if __name__ == "__main__":' in src:
            src = src.split('if __name__ == "__main__":')[0].rstrip()
        src = _patch_cell_source(idx, src)
        print(f"\n>>> Executing notebook cell {idx} ...")
        exec(compile(src, f"cell_{idx}", "exec"), g, g)
    return g


def _patch_kg_writer_sanitize() -> None:
    """Neo4j rejects list properties containing null elements."""
    from neo4j_graphrag.experimental.components import kg_writer as kw

    def _clean(value):
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [_clean(v) for v in value]
            cleaned = [v for v in cleaned if v is not None]
            return cleaned or None
        if isinstance(value, dict):
            cleaned = {k: _clean(v) for k, v in value.items()}
            cleaned = {k: v for k, v in cleaned.items() if v is not None}
            return cleaned or None
        return value

    def _sanitize_props(props):
        if not props:
            return {}
        out = {}
        for key, val in props.items():
            cleaned = _clean(val)
            if cleaned is not None:
                out[key] = cleaned
        return out

    _orig_nodes = kw.Neo4jWriter._nodes_to_rows

    @staticmethod
    def _nodes_to_rows(nodes, lexical_graph_config):
        rows = _orig_nodes(nodes, lexical_graph_config)
        for row in rows:
            props = row.get("properties")
            if props:
                row["properties"] = _sanitize_props(props)
        return rows

    _orig_rels = kw.Neo4jWriter._relationships_to_rows

    @staticmethod
    def _relationships_to_rows(relationships):
        rows = _orig_rels(relationships)
        for row in rows:
            props = row.get("properties")
            if props:
                row["properties"] = _sanitize_props(props)
        return rows

    kw.Neo4jWriter._nodes_to_rows = _nodes_to_rows
    kw.Neo4jWriter._relationships_to_rows = _relationships_to_rows
    print("✅ KG writer property sanitizer patched")


def main() -> int:
    max_docs = os.environ.get("MAX_DOCS", "all")
    if max_docs != "all":
        max_docs = int(max_docs)

    auto_metadata = os.environ.get("AUTO_METADATA", "0") == "1"
    cell_indices = [3, 5, 7, 13] if auto_metadata else [5, 7, 13]
    g = _exec_notebook_cells(cell_indices)
    _patch_kg_writer_sanitize()

    clear_neo4j_database = g["clear_neo4j_database"]
    build_knowledge_graph = g["build_knowledge_graph"]
    DEEPSEEK_API_KEY = g["DEEPSEEK_API_KEY"]

    print("\n" + "=" * 80)
    print("🗑️  清空 Neo4j 数据库...")
    clear_neo4j_database()

    print(f"🚀 开始构建 KG (max_docs={max_docs}, auto_metadata={auto_metadata})")
    ok = asyncio.run(
        build_knowledge_graph(
            directory_path=r".\data\markdown\forTest",
            schema_base_path=r".\output",
            api_key=DEEPSEEK_API_KEY,
            auto_extract_metadata=auto_metadata,
            max_docs=max_docs,
        )
    )
    print("\n" + "=" * 80)
    print("🎉 知识图谱构建成功！" if ok else "❌ 知识图谱构建失败，请检查日志")
    print("=" * 80)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
