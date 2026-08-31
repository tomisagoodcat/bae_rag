"""F1 preflight checks before MetaPath build (mirrors Notebook F1 acceptance cell)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.schema_loader import load_metapath_relations

_PAGERANK_PROPS = ("mpu_pagerank", "eem_pagerank", "ebm_pagerank")


def validate_f1_prerequisites(
    cfg: PipelineConfig,
    driver: Driver,
    subgraph_relations: Dict[str, List] | None = None,
) -> Dict[str, Any]:
    """
    Mirror Notebook F1 acceptance: count template matches without __KGBuilder__
    filter, and verify E-segment pagerank properties exist on entities.
    """
    if subgraph_relations is None:
        subgraph_relations, _ = load_metapath_relations(cfg.schema_dir)

    db = cfg.neo4j_database
    template_rows: List[Dict[str, Any]] = []
    total_instances = 0

    with driver.session(database=db) as session:
        for sg, triples in subgraph_relations.items():
            for source_label, relation_type, target_label in triples:
                q = (
                    f"MATCH (s:{source_label})-[r:{relation_type}]->(t:{target_label}) "
                    "RETURN count(*) AS c"
                )
                count = session.run(q).single()["c"]
                total_instances += count
                template_rows.append(
                    {
                        "subgraph": sg,
                        "source": source_label,
                        "relation": relation_type,
                        "target": target_label,
                        "count": count,
                        "ok": count > 0,
                    }
                )

        pagerank_sample: Dict[str, int] = {}
        for prop in _PAGERANK_PROPS:
            pagerank_sample[prop] = session.run(
                f"""
                MATCH (n:__Entity__)
                WHERE n.{prop} IS NOT NULL
                RETURN count(n) AS c
                """
            ).single()["c"]

    matched_templates = sum(1 for r in template_rows if r["ok"])
    zero_templates = [r for r in template_rows if not r["ok"]]
    by_subgraph: Dict[str, Dict[str, int]] = {}
    for sg in ("MPU", "EBM", "EEM"):
        sub = [r for r in template_rows if r["subgraph"] == sg]
        by_subgraph[sg] = {
            "total": len(sub),
            "matched": sum(1 for r in sub if r["ok"]),
        }

    result: Dict[str, Any] = {
        "matched_templates": matched_templates,
        "total_templates": len(template_rows),
        "zero_templates": len(zero_templates),
        "total_instances": total_instances,
        "by_subgraph": by_subgraph,
        "pagerank_entity_counts": pagerank_sample,
        "sample_zero_templates": zero_templates[:10],
    }

    if total_instances == 0:
        raise RuntimeError(
            "F1 预检失败：SUBGRAPH_RELATIONS 在 Neo4j 中无任何匹配实例；"
            "请确认 build_kg 已完成且 schema 模板与当前图谱对齐"
        )

    if not any(pagerank_sample.values()):
        raise RuntimeError(
            "F1 预检失败：实体上未找到任何 {mpu,eem,ebm}_pagerank；"
            "请先执行 pagerank 阶段（E 段 GDS 写回）"
        )

    return result
