"""
Common helper utilities for Neo4j GraphRAG workflows.

Includes:
- LoggingLLM: wrap an LLM to log prompts/responses to disk
- APOC availability helpers
- Debug helpers to inspect LLM responses per chunk
- Safe SimpleKGPipeline runner with APOC pre-check
"""

from __future__ import annotations

import os
import re
import json
import datetime as _dt
from typing import Optional, Callable, Any, List, Tuple

from neo4j_graphrag.llm import LLMInterface, OpenAILLM
from neo4j_graphrag.embeddings.sentence_transformers import (
    SentenceTransformerEmbeddings,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from neo4j import GraphDatabase


custom_prompt = """
You are a **domain-specialized scientific information extraction agent**, highly precise in analyzing environmental science literature. 
You are designed to construct **structured knowledge graphs** by extracting entities, relations, and attributes. 
You also possess **ontology expertise**, enabling you to map extracted information to well-defined ontology classes and properties.
# Context
You are tasked with **extracting entities, relationships, and relevant attributes** from environmental science publications.  
Your goal is to **transform natural language text into structured triples (subject–predicate–object) and associated properties**, ensuring they are aligned with ontology definitions and ready for integration into a knowledge graph. 

---
# Task
## TASK INSTRUCTIONS:
- Extract the entities (nodes) and specify their types based on the schema.
- Extract the relationships (edges) between these nodes.
- Assign appropriate properties to nodes and relationships when clearly indicated.

---

# SYSTEM CONSTRAINTS:
Your output will be directly used in downstream systems like Neo4j and semantic publishing platforms. Therefore, your output must follow these strict constraints:

1. Only use the node types and relationship types defined in the schema below.
2. Only extract triples that conform to the pattern (Subject → Predicate → Object).
3. Assign a unique string ID (e.g., "0", "1", ...) to each node, and reuse it to build relationships.
4. Respect the directionality and domain-range constraints of each relationship type.
5. Do not invent new node or relationship types that are not present in the schema.
6. Avoid hallucination, guessing, or over-generalization. Only extract what is explicitly or unambiguously stated.

---

OUTPUT FORMAT:
Return the result as a **valid JSON object** using the following format:

{{
  "nodes": [
    {{
      "id": "0",
      "label": "Person",
      "properties": {{
        "name": "John"
      }}
    }}
  ],
  "relationships": [
    {{
      "type": "KNOWS",
      "start_node_id": "0",
      "end_node_id": "1",
      "properties": {{
        "since": "2024-08-01"
      }}
    }}
  ]
}}

Use only the following nodes and relationships (if provided):
{schema}

---

## STRICT JSON RULES:
- Output only the JSON object — no explanations, commentary, or code blocks.
- Do not wrap the JSON object in a list or markdown backticks.
- Do not include extra text before or after the JSON.
- Use double quotes for all property names and string values.
- Return a well-structured JSON object compliant with the schema above.

---
## NOTES:
### 1. these nodes and relations are very important, please try your best to extract them. 
#### 1.1 entitiy:"WHU_BIO_CHEMICAL_EXPERIMENT","WHU_BIOCHEMICALACTIVITYSTEP",
#### 1.2 relation:    [ "WHU_BIOCHEMICALACTIVITYSTEP","P_PLAN_ISSTEPOFPLAN","WHU_BIO_CHEMICAL_EXPERIMENT"]
### 2. The text may contain multiple instances of `mp:Micropublication`(MP_MICROPUBLICATION). Please extract each MPU as a distinct structured unit.


EXAMPLES:
{examples}

---

INPUT TEXT:
{text}
"""


def return_llm_database(remotedatebase=False, embed_model="neo4j"):
    # DeepSeek API调用配置
    llm = OpenAILLM(
        model_name="deepseek-chat",  # DeepSeek模型名称
        api_key="YOUR_DEEPSEEK_API_KEY",  # DeepSeek API密钥
        base_url="https://api.deepseek.com",  # DeepSeek API基础URL（移除/beta）
    )

    if embed_model == "neo4j":
        embed_model = SentenceTransformerEmbeddings(
            model="maidalun1020/bce-embedding-base_v1"
        )
    else:
        embed_model = HuggingFaceEmbedding(
            model_name="maidalun1020/bce-embedding-base_v1"
        )  # 中文语义支持强

    if remotedatebase == True:
        NEO4J_URI = "neo4j+s://1b6c92d6.databases.neo4j.io"
        NEO4J_USERNAME = "neo4j"
        NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"

        neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    else:
        config = {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "boy@wuhan7224492",
        }

        neo4j_driver = GraphDatabase.driver(
            config["url"], auth=(config["username"], config["password"])
        )

    return llm, embed_model, neo4j_driver


class LoggingLLM(LLMInterface):
    """Wrap an LLM and log every prompt/response to disk for debugging."""

    def __init__(self, llm: LLMInterface, log_dir: str = "llm_logs"):
        self._llm = llm
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._counter = 0

    def _prefix(self) -> str:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        idx = self._counter
        self._counter += 1
        return os.path.join(self.log_dir, f"{idx:05d}_{ts}")

    def generate(self, prompts, **kwargs):  # type: ignore[override]
        prefix = self._prefix()
        try:
            with open(prefix + "_prompt.txt", "w", encoding="utf-8") as f:
                f.write(
                    "\n\n".join(
                        prompts if isinstance(prompts, list) else [str(prompts)]
                    )
                )
        except Exception:
            pass
        resp = self._llm.generate(prompts, **kwargs)
        try:
            text = (
                getattr(resp, "generations", [[None]])[0][0].text
                if hasattr(resp, "generations")
                else str(resp)
            )
            with open(prefix + "_response.txt", "w", encoding="utf-8") as f:
                f.write(text if text is not None else "")
        except Exception:
            pass
        
        return resp

    async def agenerate(self, prompts, **kwargs):  # type: ignore[override]
        prefix = self._prefix()
        try:
            with open(prefix + "_prompt.txt", "w", encoding="utf-8") as f:
                f.write(
                    "\n\n".join(
                        prompts if isinstance(prompts, list) else [str(prompts)]
                    )
                )
        except Exception:
            pass
        resp = await self._llm.agenerate(prompts, **kwargs)
        try:
            text = (
                getattr(resp, "generations", [[None]])[0][0].text
                if hasattr(resp, "generations")
                else str(resp)
            )
            with open(prefix + "_response.txt", "w", encoding="utf-8") as f:
                f.write(text if text is not None else "")
        except Exception:
            pass
        
        return resp

    # New: implement required abstract methods of LLMInterface
    def invoke(self, prompt: str, **kwargs):  # type: ignore[override]
        prefix = self._prefix()
        try:
            with open(prefix + "_prompt.txt", "w", encoding="utf-8") as f:
                f.write(str(prompt))
        except Exception:
            pass

        # Prefer the wrapped LLM's invoke if available; otherwise fall back to generate
        if hasattr(self._llm, "invoke"):
            resp = self._llm.invoke(prompt, **kwargs)
        else:
            resp = self._llm.generate([prompt], **kwargs)

        # Best-effort response text extraction for logging
        try:
            if isinstance(resp, str):
                text = resp
            elif hasattr(resp, "text"):
                text = getattr(resp, "text")
            elif hasattr(resp, "content"):
                text = getattr(resp, "content")
            elif hasattr(resp, "generations"):
                text = getattr(resp, "generations")[0][0].text
            else:
                text = str(resp)
            with open(prefix + "_response.txt", "w", encoding="utf-8") as f:
                f.write(text if text is not None else "")
        except Exception:
            pass

        return resp

    async def ainvoke(self, prompt: str, **kwargs):  # type: ignore[override]
        prefix = self._prefix()
        try:
            with open(prefix + "_prompt.txt", "w", encoding="utf-8") as f:
                f.write(str(prompt))
        except Exception:
            pass

        if hasattr(self._llm, "ainvoke"):
            resp = await self._llm.ainvoke(prompt, **kwargs)
        else:
            resp = await self._llm.agenerate([prompt], **kwargs)

        try:
            if isinstance(resp, str):
                text = resp
            elif hasattr(resp, "text"):
                text = getattr(resp, "text")
            elif hasattr(resp, "content"):
                text = getattr(resp, "content")
            elif hasattr(resp, "generations"):
                text = getattr(resp, "generations")[0][0].text
            else:
                text = str(resp)
            with open(prefix + "_response.txt", "w", encoding="utf-8") as f:
                f.write(text if text is not None else "")
        except Exception:
            pass

        return resp

    def __getattr__(self, name):
        # Delegate all other attributes/methods to the wrapped LLM
        return getattr(self._llm, name)


def _list_json_files_sorted(directory: str) -> list[str]:
    files = []
    try:
        for name in os.listdir(directory):
            if name.lower().endswith(".json"):
                files.append(name)
    except FileNotFoundError:
        return []

    def _key(n: str):
        try:
            # sort by leading integer before first underscore if present
            return int(os.path.splitext(n)[0].split("_")[0])
        except Exception:
            return float("inf")

    return [os.path.join(directory, n) for n in sorted(files, key=_key)]


def ingest_llm_json_dir_to_neo4j(
    directory: str,
    driver,
    use_apoc: Optional[bool] = None,
    database: Optional[str] = None,
) -> None:
    """Ingest numbered LLM JSON files into Neo4j as a knowledge graph.

    JSON shape per file:
      {
        "nodes": [{"id": "0", "label": "TYPE", "properties": {...}}, ...],
        "relationships": [
          {"type": "REL", "start_node_id": "0", "end_node_id": "1", "properties": {...}}, ...
        ]
      }

    Nodes are keyed by ext_id "<filename>:<node.id>" so that IDs are local to files.
    When APOC is available, dynamic labels and relationship types are applied.
    Otherwise, a generic label :__Entity__ and relationship :RELATED are used,
    and original label/type are preserved as properties.
    """

    files = _list_json_files_sorted(directory)
    if not files:
        print(f"未找到JSON文件: {directory}")
        return

    if use_apoc is None:
        # auto-detect APOC availability
        try:
            with driver.session(database=database) as s:
                rec = s.run("RETURN apoc.version() AS v").single()
                use_apoc = bool(rec and rec.get("v"))
        except Exception:
            use_apoc = False

    total_nodes = 0
    total_rels = 0

    with driver.session(database=database) as session:
        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"跳过无法读取的文件 {path}: {e}")
                continue

            base = os.path.basename(path)
            raw_nodes = data.get("nodes", []) or []
            raw_rels = data.get("relationships", []) or []

            nodes_param = []
            for n in raw_nodes:
                ext_id = f"{base}:{n.get('id')}"
                nodes_param.append(
                    {
                        "ext_id": ext_id,
                        "label": n.get("label") or "__Entity__",
                        "properties": n.get("properties") or {},
                    }
                )

            rels_param = []
            for r in raw_rels:
                start_ext = f"{base}:{r.get('start_node_id')}"
                end_ext = f"{base}:{r.get('end_node_id')}"
                rels_param.append(
                    {
                        "type": r.get("type") or "RELATED",
                        "start": start_ext,
                        "end": end_ext,
                        "properties": r.get("properties") or {},
                    }
                )

            if not nodes_param and not rels_param:
                continue

            if use_apoc:
                # upsert nodes with dynamic label via APOC
                cy_nodes = (
                    "UNWIND $nodes AS n "
                    "MERGE (e:__Entity__ {ext_id: n.ext_id}) "
                    "SET e += n.properties "
                    "WITH e, n "
                    "CALL apoc.create.addLabels(e, [n.label]) YIELD node "
                    "RETURN count(*) AS c"
                )
                if nodes_param:
                    session.run(cy_nodes, nodes=nodes_param)
                    total_nodes += len(nodes_param)

                cy_rels = (
                    "UNWIND $rels AS r "
                    "MATCH (s:__Entity__ {ext_id: r.start}), (t:__Entity__ {ext_id: r.end}) "
                    "CALL apoc.create.relationship(s, r.type, r.properties, t) YIELD rel "
                    "RETURN count(*) AS c"
                )
                if rels_param:
                    session.run(cy_rels, rels=rels_param)
                    total_rels += len(rels_param)
            else:
                # fallback: no APOC, keep generic label and store originals as properties
                cy_nodes = (
                    "UNWIND $nodes AS n "
                    "MERGE (e:__Entity__ {ext_id: n.ext_id}) "
                    "SET e += n.properties, e.original_label = n.label "
                    "RETURN count(*) AS c"
                )
                if nodes_param:
                    session.run(cy_nodes, nodes=nodes_param)
                    total_nodes += len(nodes_param)

                cy_rels = (
                    "UNWIND $rels AS r "
                    "MATCH (s:__Entity__ {ext_id: r.start}), (t:__Entity__ {ext_id: r.end}) "
                    "MERGE (s)-[rel:RELATED {__ext__: r.start + '>' + r.end + '>' + r.type}]->(t) "
                    "SET rel += r.properties, rel.original_type = r.type "
                    "RETURN count(*) AS c"
                )
                if rels_param:
                    session.run(cy_rels, rels=rels_param)
                    total_rels += len(rels_param)

    print(f"✅ 导入完成：节点 {total_nodes}，关系 {total_rels}（APOC={'ON' if use_apoc else 'OFF'}）")
