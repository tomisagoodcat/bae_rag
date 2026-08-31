"""Update module 4 cell to be self-contained (no torch dependency)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "1_2_0_2build_kg__neo4j.ipynb"

MODULE4_CODE = r'''# ==================== 模块4: 子图属性标注（可独立运行） ====================
from __future__ import annotations

import json
from typing import Any, Dict, List, Set, Tuple

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "tomis1cat"
NEO4J_DATABASE = "neo4j"

SUBGRAPH_NAMES: tuple[str, ...] = ("MPU", "EBM", "EEM")
EXCLUDED_NODE_LABELS: frozenset[str] = frozenset({
    "Chunk",
    "MetaPath",
})


class SubgraphMappingError(Exception):
    """subgraph_mapping 或 Neo4j 标注校验失败。"""


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(base_path: str) -> Tuple[List[Dict], List[Dict], List[List]]:
    entities = _load_json(f"{base_path}\\entity.json").get("entities", [])
    relations = _load_json(f"{base_path}\\relation.json").get("relations", [])
    potential_schema = _load_json(f"{base_path}\\potential_schema.json").get(
        "potential_schema", []
    )
    if not entities:
        raise SubgraphMappingError(f"entity.json 无 entities: {base_path}")
    return entities, relations, potential_schema


def build_neo4j_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        max_connection_lifetime=3600,
        connection_timeout=30,
    )


def neo4j_is_alive(driver) -> bool:
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            session.run("RETURN 1").consume()
        return True
    except Exception:
        return False


def load_subgraph_mapping_file(mapping_path: str) -> Dict[str, Any]:
    data = _load_json(mapping_path)
    mappings = data.get("mappings")
    if not isinstance(mappings, dict):
        raise SubgraphMappingError(f"mappings 缺失或类型错误: {mapping_path}")
    for sg in SUBGRAPH_NAMES:
        if sg not in mappings:
            raise SubgraphMappingError(f"subgraph_mapping 缺少子图: {sg}")
        labels = mappings[sg]
        if not isinstance(labels, list) or not labels:
            raise SubgraphMappingError(f"子图 {sg} 的实体列表为空")
        if len(labels) != len(set(labels)):
            raise SubgraphMappingError(f"子图 {sg} 存在重复 entity label")
    return data


def build_label_to_subgraphs(mappings: Dict[str, List[str]]) -> Dict[str, List[str]]:
    label_to_sgs: Dict[str, List[str]] = {}
    order = {name: i for i, name in enumerate(SUBGRAPH_NAMES)}
    for sg in SUBGRAPH_NAMES:
        for label in mappings[sg]:
            label_to_sgs.setdefault(label, []).append(sg)
    for label, sgs in label_to_sgs.items():
        label_to_sgs[label] = sorted(set(sgs), key=lambda x: order[x])
    return label_to_sgs


def validate_mapping_vs_entity_schema(
    entity_labels: Set[str],
    label_to_sgs: Dict[str, List[str]],
) -> None:
    mapped = set(label_to_sgs)
    missing = entity_labels - mapped
    extra = mapped - entity_labels
    errors: List[str] = []
    if missing:
        errors.append(
            f"entity.json 未在 subgraph_mapping 中定义: {sorted(missing)}"
        )
    if extra:
        errors.append(
            f"subgraph_mapping 含 entity.json 不存在的 label: {sorted(extra)}"
        )
    if errors:
        raise SubgraphMappingError("\n".join(errors))


def _assign_label_batch(session, label: str, subgraphs: List[str]) -> int:
    params: Dict[str, Any] = {"subgraphs": subgraphs}
    if len(subgraphs) == 1:
        cypher = f"""
        MATCH (n:`{label}`)
        WHERE NOT n:Chunk AND NOT n:MetaPath
        SET n.subgraphs = $subgraphs,
            n.subgraph = $subgraph
        RETURN count(n) AS cnt
        """
        params["subgraph"] = subgraphs[0]
    else:
        cypher = f"""
        MATCH (n:`{label}`)
        WHERE NOT n:Chunk AND NOT n:MetaPath
        SET n.subgraphs = $subgraphs
        REMOVE n.subgraph
        RETURN count(n) AS cnt
        """
    row = session.run(cypher, params).single()
    return int(row["cnt"])


def assign_subgraph_properties(
    driver,
    schema_base_path: str = r".\output",
) -> Dict[str, Any]:
    entities, _, _ = load_schema(schema_base_path)
    entity_labels = {e["label"] for e in entities}

    mapping_path = f"{schema_base_path}\\subgraph_mapping.json"
    mapping_data = load_subgraph_mapping_file(mapping_path)
    label_to_sgs = build_label_to_subgraphs(mapping_data["mappings"])
    validate_mapping_vs_entity_schema(entity_labels, label_to_sgs)

    stats: Dict[str, Any] = {
        "entity_labels_total": len(entity_labels),
        "labeled_nodes_total": 0,
        "by_label": {},
        "nodes_per_subgraph_membership": {sg: 0 for sg in SUBGRAPH_NAMES},
    }

    with driver.session(database=NEO4J_DATABASE) as session:
        for label in sorted(label_to_sgs):
            sgs = label_to_sgs[label]
            cnt = _assign_label_batch(session, label, sgs)
            stats["by_label"][label] = {"node_count": cnt, "subgraphs": sgs}
            stats["labeled_nodes_total"] += cnt
            for sg in sgs:
                stats["nodes_per_subgraph_membership"][sg] += cnt

    return stats


def verify_subgraph_assignment(driver, entity_labels: Set[str]) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        missing = session.run(
            """
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $entity_labels)
              AND NOT n:Chunk AND NOT n:MetaPath
              AND n.subgraphs IS NULL
            RETURN count(n) AS cnt
            """,
            entity_labels=list(entity_labels),
        ).single()["cnt"]
        if missing:
            sample = session.run(
                """
                MATCH (n)
                WHERE any(l IN labels(n) WHERE l IN $entity_labels)
                  AND NOT n:Chunk AND NOT n:MetaPath
                  AND n.subgraphs IS NULL
                WITH n, [l IN labels(n) WHERE l IN $entity_labels][0] AS label
                RETURN label, count(*) AS cnt
                ORDER BY cnt DESC
                LIMIT 10
                """,
                entity_labels=list(entity_labels),
            ).data()
            raise SubgraphMappingError(
                f"{missing} 个实体节点缺少 subgraphs 属性。样例: {sample}"
            )

        bad_single = session.run(
            """
            MATCH (n)
            WHERE n.subgraphs IS NOT NULL
              AND size(n.subgraphs) = 1
              AND (n.subgraph IS NULL OR n.subgraph <> n.subgraphs[0])
            RETURN count(n) AS cnt
            """
        ).single()["cnt"]
        if bad_single:
            raise SubgraphMappingError(
                f"{bad_single} 个单属节点 subgraph 与 subgraphs[0] 不一致"
            )

        bad_multi = session.run(
            """
            MATCH (n)
            WHERE n.subgraphs IS NOT NULL
              AND size(n.subgraphs) > 1
              AND n.subgraph IS NOT NULL
            RETURN count(n) AS cnt
            """
        ).single()["cnt"]
        if bad_multi:
            raise SubgraphMappingError(
                f"{bad_multi} 个跨子图节点错误地保留了 subgraph 标量"
            )

        invalid_vals = session.run(
            """
            MATCH (n)
            WHERE n.subgraphs IS NOT NULL
            UNWIND n.subgraphs AS sg
            WITH DISTINCT sg
            WHERE NOT sg IN $allowed
            RETURN collect(sg) AS bad
            """,
            allowed=list(SUBGRAPH_NAMES),
        ).single()["bad"]
        if invalid_vals:
            raise SubgraphMappingError(f"subgraphs 含非法值: {invalid_vals}")

        orphan_entity = session.run(
            """
            MATCH (n:__Entity__)
            WHERE NOT any(l IN labels(n) WHERE l IN $entity_labels)
            RETURN count(n) AS cnt
            """,
            entity_labels=list(entity_labels),
        ).single()["cnt"]
        if orphan_entity:
            raise SubgraphMappingError(
                f"{orphan_entity} 个 __Entity__ 节点缺少 ontology label，无法标注子图"
            )


def run_subgraph_assignment(schema_base_path: str = r".\output") -> Dict[str, Any]:
    driver = build_neo4j_driver()
    try:
        if not neo4j_is_alive(driver):
            raise SubgraphMappingError(
                f"Neo4j 不可达: {NEO4J_URI} / db={NEO4J_DATABASE}"
            )

        entities, _, _ = load_schema(schema_base_path)
        entity_labels = {e["label"] for e in entities}

        print("=" * 60)
        print("模块4: 子图属性标注")
        print("=" * 60)

        stats = assign_subgraph_properties(driver, schema_base_path)
        verify_subgraph_assignment(driver, entity_labels)
        _assert_labeled_nodes_exist(stats)

        print(f"  ontology labels: {stats['entity_labels_total']}")
        print(f"  已标注节点总数: {stats['labeled_nodes_total']}")
        for sg in SUBGRAPH_NAMES:
            print(
                f"  子图 {sg} 成员节点（按 label 计数）: "
                f"{stats['nodes_per_subgraph_membership'][sg]}"
            )
        zero_labels = [
            lbl for lbl, info in stats["by_label"].items() if info["node_count"] == 0
        ]
        if zero_labels:
            print(f"  无实例的 label ({len(zero_labels)}): {zero_labels}")
        print("  验收: 通过")
        print("=" * 60)
        return stats
    finally:
        driver.close()


def _assert_labeled_nodes_exist(stats: Dict[str, Any]) -> None:
    if stats["labeled_nodes_total"] <= 0:
        raise SubgraphMappingError(
            "未标注任何实体节点：Neo4j 中不存在 ontology label 匹配的节点，"
            "或 EXCLUDED_NODE_LABELS 过滤过宽。请先确认 KG 已构建。"
        )


print("✅ 模块4 子图属性标注函数已定义（可独立运行）")
print("   执行: run_subgraph_assignment()")
'''

MODULE4_MD_SOURCE = [
    "# 模块4：子图属性标注（subgraph / subgraphs）\n",
    "\n",
    "根据 [`output/subgraph_mapping.json`](../output/subgraph_mapping.json) 为 Neo4j **实体节点**写入子图归属：\n",
    "\n",
    "| 属性 | 规则 |\n",
    "|------|------|\n",
    "| `subgraphs` | `List[str]`，取值 `MPU` / `EBM` / `EEM`，**始终写入** |\n",
    "| `subgraph` | 仅当节点类型只属于 **一个** 子图时写入标量；跨子图节点 **不写入** |\n",
    "\n",
    "**本 Cell 可独立运行**（不依赖模块3 的 torch/LLM 导入）。KG 已存在时直接 `run_subgraph_assignment()`。\n",
    "\n",
    "若通过模块3 `build_knowledge_graph` 自动执行步骤 6.5，须在同 Kernel **先运行本 Cell** 以注册函数。\n",
    "\n",
    "**严格校验**（失败即 `SubgraphMappingError`）：mapping 与 entity.json 完全一致；所有 ontology 实体节点必须有 `subgraphs`。\n",
]


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    idx = next(i for i, c in enumerate(nb["cells"]) if c.get("id") == "mod4-subgraph-code")
    nb["cells"][idx]["source"] = [line + "\n" for line in MODULE4_CODE.splitlines()]
    md_idx = next(i for i, c in enumerate(nb["cells"]) if c.get("id") == "mod4-subgraph-md")
    nb["cells"][md_idx]["source"] = MODULE4_MD_SOURCE
    NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Updated module 4 cell to self-contained version")


if __name__ == "__main__":
    main()
