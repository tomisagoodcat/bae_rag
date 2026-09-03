"""Run read-only KG judgement and write a markdown log."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from neo4j import Driver

from kg_build_pipeline.judgement.constants import SAMPLE_LIMIT, SITE_MATRIX_LABELS
from kg_build_pipeline.judgement.graph_read import (
    GraphSnapshot,
    fetch_materials,
    fetch_research_steps,
    fetch_site_matrix_rows,
    fetch_snapshot,
)
from kg_build_pipeline.judgement.metrics import (
    average_population,
    bind_issues_to_nodes,
    class_population,
    class_richness,
    duplicate_candidates,
    duplicate_entity_rate,
    mean_ratio,
    multi_hop_path_coverage,
    orphan_rate,
    per_document_metrics,
    provenance_coverage,
    relation_conflict_rate,
    relation_schema_conformance,
    shacl_conformance,
)
from kg_build_pipeline.judgement.report import write_log
from kg_build_pipeline.judgement.schema_view import load_judgement_schema


def _collect_validator_issues(
    driver: Driver,
    database: str,
    filenames: Sequence[str],
    run_low: bool,
) -> List[Dict[str, Any]]:
    from kg_build_pipeline.src.stages.mid_validate import validate_mid_document

    issues: List[Dict[str, Any]] = []
    for fn in filenames:
        mid = validate_mid_document(driver, database, fn)
        issues.extend(mid.get("hard_violations") or [])
        issues.extend(mid.get("warnings") or [])
        issues.extend(mid.get("missing_relation_candidates") or [])
        if run_low:
            from kg_build_pipeline.src.stages.low_validate import validate_low_document_final

            low = validate_low_document_final(driver, database, fn)
            issues.extend(low.get("hard_violations") or [])
            issues.extend(low.get("warnings") or [])
    return issues


def _site_matrix_risks(
    driver: Driver,
    database: str,
    instantiable: Sequence[str],
    legal,
) -> List[Dict[str, Any]]:
    from kg_build_pipeline.src.stages.low_validate import check_h14_material_not_place

    out: List[Dict[str, Any]] = []
    for row in fetch_site_matrix_rows(driver, database, instantiable):
        s, t, rel = row.get("src_label"), row.get("tgt_label"), row.get("rel_type")
        if not s or not t:
            continue
        if s not in SITE_MATRIX_LABELS and t not in SITE_MATRIX_LABELS:
            continue
        if (s, rel, t) not in legal:
            out.append(
                {
                    "kind": "illegal_site_matrix_edge",
                    "message": f"({s}, {rel}, {t}) not in potential_schema",
                    "src_name": row.get("src_name"),
                    "tgt_name": row.get("tgt_name"),
                    "rel": rel,
                }
            )
    materials = fetch_materials(driver, database)
    for iss in check_h14_material_not_place(materials):
        out.append(
            {
                "kind": "H14",
                "message": iss.get("message"),
                "src_name": iss.get("entity_name"),
                "tgt_name": "",
                "rel": "",
            }
        )
    return out[:SAMPLE_LIMIT]


def _research_step_risks(driver: Driver, database: str) -> List[Dict[str, Any]]:
    from kg_build_pipeline.src.stages.low_validate import check_h01b_research_type

    steps = fetch_research_steps(driver, database)
    if not steps:
        return []
    return check_h01b_research_type(steps)[:SAMPLE_LIMIT]


def evaluate_snapshot(
    snap: GraphSnapshot,
    instantiable: Sequence[str],
    legal,
    issues: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    pop = class_population(snap.nodes, instantiable)
    rsc = relation_schema_conformance(snap.edges, legal)
    rcr = relation_conflict_rate(snap.edges, legal)
    docs = per_document_metrics(snap, legal)
    bound = bind_issues_to_nodes(issues, snap.nodes)
    inspected = [n.eid for n in snap.nodes]
    hard = [
        i
        for i in bound
        if str(i.get("bucket")) == "hard_violations" or str(i.get("severity")) == "Violation"
    ]
    return {
        "class_population": pop,
        "summary": {
            "cr": class_richness(pop),
            "ap": average_population(pop),
            "scr": shacl_conformance(inspected, hard),
            "or": orphan_rate(snap.nodes, bound),
            "dc": mean_ratio(docs, "dc"),
            "mc": mean_ratio(docs, "mc"),
            "mpc": multi_hop_path_coverage(docs),
            "der": duplicate_entity_rate(),
            "rsc": rsc,
            "rcr": rcr,
            "pc": provenance_coverage(snap.nodes),
        },
        "documents": docs,
        "duplicate_candidates": duplicate_candidates(snap.nodes),
    }


def run_judgement(
    cfg,
    driver: Driver,
    *,
    stages_run: Optional[Sequence[str]] = None,
    log_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Read-only evaluation. Never writes to Neo4j. Failures must be handled by caller."""
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    instantiable, legal = load_judgement_schema(cfg.schema_dir)
    snap = fetch_snapshot(
        driver,
        cfg.neo4j_database,
        instantiable,
        uri=getattr(cfg, "neo4j_uri", ""),
    )
    issues = _collect_validator_issues(
        driver,
        cfg.neo4j_database,
        snap.filenames,
        run_low=snap.research_step_count > 0,
    )
    body = evaluate_snapshot(snap, instantiable, legal, issues)
    payload: Dict[str, Any] = {
        "generated_at": generated_at,
        "neo4j_uri": getattr(cfg, "neo4j_uri", ""),
        "neo4j_database": cfg.neo4j_database,
        "filenames": snap.filenames,
        "stages_run": list(stages_run or []),
        "risks": {
            "site_matrix": _site_matrix_risks(
                driver, cfg.neo4j_database, instantiable, legal
            ),
            "research_step_parent": _research_step_risks(driver, cfg.neo4j_database),
        },
        **body,
    }
    path = write_log(payload, log_dir=log_dir)
    payload["log_path"] = str(path)
    payload["ok"] = True
    return payload


def write_fail_soft_log(
    cfg,
    error: str,
    *,
    stages_run: Optional[Sequence[str]] = None,
    log_dir: Optional[Path] = None,
) -> str:
    """Write a glossary markdown even when judgement itself failed."""
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload: Dict[str, Any] = {
        "generated_at": generated_at,
        "neo4j_uri": getattr(cfg, "neo4j_uri", ""),
        "neo4j_database": getattr(cfg, "neo4j_database", ""),
        "filenames": [],
        "stages_run": list(stages_run or []),
        "error": error,
        "summary": {"der": duplicate_entity_rate()},
        "class_population": {},
        "documents": [],
        "duplicate_candidates": [],
        "risks": {"site_matrix": [], "research_step_parent": []},
    }
    return str(write_log(payload, log_dir=log_dir))
