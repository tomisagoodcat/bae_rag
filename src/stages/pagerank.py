"""GDS PageRank E segment: write mpu/eem/ebm pagerank on entity nodes."""
from __future__ import annotations

from typing import Any, Dict

from graphdatascience import GraphDataScience
from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.stages.pagerank_config import SUBGRAPH_CONFIGS


def _drop_if_exists(gds: GraphDataScience, proj_name: str) -> None:
    try:
        gds.graph.drop(gds.graph.get(proj_name))
    except Exception:
        pass


def _compute_and_write(gds: GraphDataScience, G, sg: str) -> None:
    prefix = sg
    gds.degree.write(G, writeProperty=f"{prefix}_degree")
    gds.pageRank.write(
        G,
        writeProperty=f"{prefix}_pagerank",
        maxIterations=20,
        dampingFactor=0.85,
    )
    gds.betweenness.write(G, writeProperty=f"{prefix}_betweenness")
    gds.closeness.write(G, writeProperty=f"{prefix}_closeness")

    node_labels = SUBGRAPH_CONFIGS[sg]["nodes"]
    label_filter = " OR ".join(f"n:{lbl}" for lbl in node_labels)
    df = gds.run_cypher(
        f"""
        MATCH (n)
        WHERE ({label_filter}) AND n.{prefix}_pagerank IS NOT NULL
        RETURN id(n) AS nodeId,
               n.{prefix}_degree AS degree,
               n.{prefix}_pagerank AS pagerank,
               n.{prefix}_betweenness AS betweenness,
               n.{prefix}_closeness AS closeness
        """
    )
    if df.empty:
        return
    for col in ["degree", "pagerank", "betweenness", "closeness"]:
        mn, mx = df[col].min(), df[col].max()
        df[f"{col}_norm"] = (df[col] - mn) / (mx - mn + 1e-10)
    df[f"{prefix}_combined"] = df[
        ["degree_norm", "pagerank_norm", "betweenness_norm", "closeness_norm"]
    ].mean(axis=1)
    records = df[["nodeId", f"{prefix}_combined"]].to_dict("records")
    gds.run_cypher(
        f"""
        UNWIND $rows AS row
        MATCH (n) WHERE id(n) = row.nodeId
        SET n.{prefix}_combined = row.{prefix}_combined
        """,
        params={"rows": records},
    )


def run_pagerank(cfg: PipelineConfig, driver: Driver) -> Dict[str, Any]:
    """Run E-segment GDS projections and write subgraph pagerank properties."""
    gds = GraphDataScience(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    summary: Dict[str, Any] = {"subgraphs": {}}
    for sg, sg_cfg in SUBGRAPH_CONFIGS.items():
        proj_name = sg_cfg["projection"]
        _drop_if_exists(gds, proj_name)
        G, result = gds.graph.project(
            proj_name,
            node_spec=sg_cfg["nodes"],
            relationship_spec=sg_cfg["relationships"],
        )
        _compute_and_write(gds, G, sg)
        gds.graph.drop(G)
        summary["subgraphs"][sg] = {
            "nodeCount": result["nodeCount"],
            "relationshipCount": result["relationshipCount"],
        }
    return summary
