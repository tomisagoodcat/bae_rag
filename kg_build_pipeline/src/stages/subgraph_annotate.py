"""Subgraph property assignment (from 1_2_0_2 module4)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.schema_loader import load_schema

SUBGRAPH_NAMES: tuple[str, ...] = ("MPU", "EBM", "EEM")
EXCLUDED_NODE_LABELS: frozenset[str] = frozenset({"Chunk", "MetaPath"})


class SubgraphMappingError(Exception):
    """subgraph_mapping or Neo4j annotation validation failed."""


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_subgraph_mapping_file(mapping_path: Path) -> Dict[str, Any]:
    data = _load_json(mapping_path)
    mappings = data.get("mappings")
    if not isinstance(mappings, dict):
        raise SubgraphMappingError(f"mappings missing: {mapping_path}")
    for sg in SUBGRAPH_NAMES:
        if sg not in mappings:
            raise SubgraphMappingError(f"subgraph_mapping missing subgraph: {sg}")
        labels = mappings[sg]
        if not isinstance(labels, list) or not labels:
            raise SubgraphMappingError(f"subgraph {sg} has empty entity list")
        if len(labels) != len(set(labels)):
            raise SubgraphMappingError(f"subgraph {sg} has duplicate labels")
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
    entity_labels: Set[str], label_to_sgs: Dict[str, List[str]]
) -> None:
    mapped = set(label_to_sgs)
    missing = entity_labels - mapped
    extra = mapped - entity_labels
    errors: List[str] = []
    if missing:
        errors.append(f"entity.json labels not in subgraph_mapping: {sorted(missing)}")
    if extra:
        errors.append(f"subgraph_mapping labels not in entity.json: {sorted(extra)}")
    if errors:
        raise SubgraphMappingError("\n".join(errors))


def _assign_label_batch(session, label: str, subgraphs: List[str]) -> int:
    params: Dict[str, Any] = {"subgraphs": subgraphs}
    if len(subgraphs) == 1:
        cypher = f"""
        MATCH (n:`{label}`)
        WHERE NOT n:Chunk AND NOT n:MetaPath
        SET n.subgraphs = $subgraphs, n.subgraph = $subgraph
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
    return int(session.run(cypher, params).single()["cnt"])


def assign_subgraph_properties(driver: Driver, schema_dir: Path, database: str) -> Dict[str, Any]:
    entities, _, _ = load_schema(schema_dir)
    entity_labels = {e["label"] for e in entities}
    mapping_path = schema_dir / "subgraph_mapping.json"
    mapping_data = load_subgraph_mapping_file(mapping_path)
    label_to_sgs = build_label_to_subgraphs(mapping_data["mappings"])
    validate_mapping_vs_entity_schema(entity_labels, label_to_sgs)

    stats: Dict[str, Any] = {
        "entity_labels_total": len(entity_labels),
        "labeled_nodes_total": 0,
        "by_label": {},
        "nodes_per_subgraph_membership": {sg: 0 for sg in SUBGRAPH_NAMES},
    }
    with driver.session(database=database) as session:
        for label in sorted(label_to_sgs):
            sgs = label_to_sgs[label]
            cnt = _assign_label_batch(session, label, sgs)
            stats["by_label"][label] = {"node_count": cnt, "subgraphs": sgs}
            stats["labeled_nodes_total"] += cnt
            for sg in sgs:
                stats["nodes_per_subgraph_membership"][sg] += cnt
    return stats


def verify_subgraph_assignment(driver: Driver, entity_labels: Set[str], database: str) -> None:
    with driver.session(database=database) as session:
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
            raise SubgraphMappingError(f"{missing} entity nodes missing subgraphs property")


def run_subgraph_annotate(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Write subgraph/subgraphs on entity nodes; verify coverage."""
    entities, _, _ = load_schema(cfg.schema_dir)
    entity_labels = {e["label"] for e in entities}
    stats = assign_subgraph_properties(driver, cfg.schema_dir, cfg.neo4j_database)
    verify_subgraph_assignment(driver, entity_labels, cfg.neo4j_database)
    if stats["labeled_nodes_total"] <= 0:
        raise SubgraphMappingError("No entity nodes labeled; build KG first.")
    return stats
