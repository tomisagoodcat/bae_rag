"""One-shot patch: add module 4 subgraph assignment to 1_2_0_2build_kg__neo4j.ipynb"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "1_2_0_2build_kg__neo4j.ipynb"

MODULE4_MD = {
    "cell_type": "markdown",
    "id": "mod4-subgraph-md",
    "metadata": {},
    "source": [
        "# 模块4：子图属性标注（subgraph / subgraphs）\n",
        "\n",
        "根据 [`output/subgraph_mapping.json`](../output/subgraph_mapping.json) 为 Neo4j **实体节点**写入子图归属：\n",
        "\n",
        "| 属性 | 规则 |\n",
        "|------|------|\n",
        "| `subgraphs` | `List[str]`，取值 `MPU` / `EBM` / `EEM`，**始终写入** |\n",
        "| `subgraph` | 仅当节点类型只属于 **一个** 子图时写入标量；跨子图节点 **不写入** |\n",
        "\n",
        "**依赖**：须先运行 **模块3（Cell 13）** 以加载 `NEO4J_*`、`load_schema`、`_load_json`、`build_neo4j_driver` 等。\n",
        "\n",
        "**执行**：运行下方代码 Cell 后调用 `run_subgraph_assignment()`。\n",
        "\n",
        "**严格校验**（失败即 `SubgraphMappingError`，不兜底）：mapping 与 entity.json 完全一致；所有 ontology 实体节点必须有 `subgraphs`。\n",
    ],
}

MODULE4_CODE_SOURCE = r'''# ==================== 模块4: 子图属性标注 ====================
from __future__ import annotations

from typing import Any, Dict, List, Set

SUBGRAPH_NAMES: tuple[str, ...] = ("MPU", "EBM", "EEM")
EXCLUDED_NODE_LABELS: frozenset[str] = frozenset({
    "Chunk",
    "MetaPath",
    "__Entity__",
    "__KGBuilder__",
    "__Relationship__",
})


class SubgraphMappingError(Exception):
    """subgraph_mapping 或 Neo4j 标注校验失败。"""


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


def _require_module4_dependencies() -> None:
    required = (
        "_load_json",
        "load_schema",
        "build_neo4j_driver",
        "neo4j_is_alive",
        "NEO4J_DATABASE",
    )
    missing = [name for name in required if name not in globals()]
    if missing:
        raise RuntimeError(
            "模块4 依赖模块3：请先运行模块3（Cell 13）。缺少: "
            + ", ".join(missing)
        )


def _assign_label_batch(session, label: str, subgraphs: List[str]) -> int:
    params: Dict[str, Any] = {
        "excluded": list(EXCLUDED_NODE_LABELS),
        "subgraphs": subgraphs,
    }
    if len(subgraphs) == 1:
        cypher = f"""
        MATCH (n:`{label}`)
        WHERE NOT any(x IN labels(n) WHERE x IN $excluded)
        SET n.subgraphs = $subgraphs,
            n.subgraph = $subgraph
        RETURN count(n) AS cnt
        """
        params["subgraph"] = subgraphs[0]
    else:
        cypher = f"""
        MATCH (n:`{label}`)
        WHERE NOT any(x IN labels(n) WHERE x IN $excluded)
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
    _require_module4_dependencies()
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
              AND NOT any(x IN labels(n) WHERE x IN $excluded)
              AND n.subgraphs IS NULL
            RETURN count(n) AS cnt
            """,
            entity_labels=list(entity_labels),
            excluded=list(EXCLUDED_NODE_LABELS),
        ).single()["cnt"]
        if missing:
            sample = session.run(
                """
                MATCH (n)
                WHERE any(l IN labels(n) WHERE l IN $entity_labels)
                  AND NOT any(x IN labels(n) WHERE x IN $excluded)
                  AND n.subgraphs IS NULL
                WITH n, [l IN labels(n) WHERE l IN $entity_labels][0] AS label
                RETURN label, count(*) AS cnt
                ORDER BY cnt DESC
                LIMIT 10
                """,
                entity_labels=list(entity_labels),
                excluded=list(EXCLUDED_NODE_LABELS),
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
    _require_module4_dependencies()
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


print("✅ 模块4 子图属性标注函数已定义")
print("   执行: run_subgraph_assignment()")
'''


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

    # Fix typo if present in template
    code = MODULE4_CODE_SOURCE

    module4_code = {
        "cell_type": "code",
        "execution_count": None,
        "id": "mod4-subgraph-code",
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in code.splitlines()],
    }

    if not any(c.get("id") == "mod4-subgraph-md" for c in nb["cells"]):
        nb["cells"].insert(14, MODULE4_MD)
        nb["cells"].insert(15, module4_code)

    cell13_src = "".join(nb["cells"][13]["source"])
    hook = '        print("\\n" + "=" * 80)\n        print("🔍 步骤7: 最终验证")'
    step65 = '''        if succeeded_docs > 0:
            for _dep in ("assign_subgraph_properties", "verify_subgraph_assignment", "SUBGRAPH_NAMES"):
                if _dep not in globals():
                    raise RuntimeError(
                        "步骤6.5 需要模块4：请先运行「模块4：子图属性标注」代码 Cell，再执行 build_knowledge_graph。"
                    )
            print("\\n" + "=" * 80)
            print("📌 步骤6.5: 子图属性标注")
            print("-" * 80)
            entity_labels_for_sg = {e["label"] for e in entities}
            sg_stats = assign_subgraph_properties(neo4j_driver, schema_base_path)
            verify_subgraph_assignment(neo4j_driver, entity_labels_for_sg)
            print(f"   已标注节点: {sg_stats['labeled_nodes_total']}")
            for _sg in SUBGRAPH_NAMES:
                print(f"   {_sg}: {sg_stats['nodes_per_subgraph_membership'][_sg]}")
            print("   ✅ 子图属性标注与验收通过")

        print("\\n" + "=" * 80)
        print("🔍 步骤7: 最终验证")'''

    if "步骤6.5: 子图属性标注" not in cell13_src:
        if hook not in cell13_src:
            raise SystemExit("hook not found in cell 13")
        cell13_src = cell13_src.replace(hook, step65)
        nb["cells"][13]["source"] = [cell13_src]

    NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB_PATH}")


if __name__ == "__main__":
    main()
