"""Mid-graph structural validation (SHACL BAE_mid_shapes → Neo4j Cypher/Python)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import Driver

from kg_build_pipeline.src.schema_tier import MID_CORE_ENTITY_LABELS, MID_MID_ALLOWED_TRIPLES

MID_LABELS_NO_CLAIM = sorted(MID_CORE_ENTITY_LABELS - {"mp_Claim"})

_STRUCT_RELS = [
    "whu_hasContext",
    "whu_fellow",
    "prov_wasDerivedFrom",
    "mp_supports",
    "mp_challenges",
    "prov_hadMember",
    "whu_hasGoal",
    "p_plan_isInputVarOf",
    "p_plan_isOutputVarOf",
    "bfo_has_part",
]

_IN_RELS = [
    "whu_hasContext",
    "whu_fellow",
    "prov_wasDerivedFrom",
    "mp_supports",
    "mp_challenges",
    "prov_hadMember",
    "p_plan_isStepOfPlan",
    "p_plan_isInputVarOf",
    "p_plan_isOutputVarOf",
    "prov_atLocation",
]


def _issue(
    rule_id: str,
    severity: str,
    entity_id: Any,
    message: str,
    *,
    entity_name: Any = None,
    labels: Any = None,
    bucket: str = "warnings",
) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "labels": labels,
        "message": message,
        "bucket": bucket,
    }


def _scope_where(alias: str = "n") -> str:
    """Scope mid nodes to one document via Chunk FROM_CHUNK or source_doc."""
    return f"""
    (
      {alias}.source_doc = $source_doc
      OR EXISTS {{
        MATCH (c:Chunk)-[:FROM_CHUNK]-({alias})
        WHERE c.filename = $filename
      }}
    )
    AND coalesce({alias}.whu_rejected, false) = false
    """


def _node_key(rec: Dict[str, Any]) -> Any:
    return rec.get("id") or rec.get("name") or rec.get("element_id")


def validate_mid_document(
    driver: Driver,
    database: str,
    filename: str,
) -> Dict[str, Any]:
    """Run active mid rules M00–M06, M09, M10, M13 for one document. Read-only."""
    source_doc = filename.replace(".md", "") if filename.endswith(".md") else filename
    params = {"filename": filename, "source_doc": source_doc}

    hard: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    isolated: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []

    with driver.session(database=database) as session:
        # M00 — non-empty WHU_HASORIGINALTEXT on mid containers
        q_m00 = f"""
        MATCH (n)
        WHERE ({_scope_where("n")})
          AND any(l IN labels(n) WHERE l IN $mid_labels)
          AND (
            n.WHU_HASORIGINALTEXT IS NULL
            OR trim(toString(n.WHU_HASORIGINALTEXT)) = ''
          )
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(n) AS labels
        """
        for rec in session.run(q_m00, **params, mid_labels=MID_LABELS_NO_CLAIM):
            hard.append(
                _issue(
                    "M00",
                    "Violation",
                    _node_key(rec),
                    "M00: mid entity missing non-empty WHU_HASORIGINALTEXT",
                    entity_name=rec.get("name"),
                    labels=rec.get("labels"),
                    bucket="hard_violations",
                )
            )

        # M01 — hasContext type + missing warning
        q_m01_bad = f"""
        MATCH (n:whu_SpecimenCollection)-[r:whu_hasContext]->(o)
        WHERE {_scope_where("n")}
          AND NOT o:whu_EnvironmentFeature
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(o) AS obj_labels
        """
        for rec in session.run(q_m01_bad, **params):
            hard.append(
                _issue(
                    "M01",
                    "Violation",
                    _node_key(rec),
                    f"M01: hasContext target is not EnvironmentFeature ({rec.get('obj_labels')})",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )
        q_m01_miss = f"""
        MATCH (n:whu_SpecimenCollection)
        WHERE {_scope_where("n")}
          AND NOT (n)-[:whu_hasContext]->(:whu_EnvironmentFeature)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m01_miss, **params):
            issue = _issue(
                "M01",
                "Warning",
                _node_key(rec),
                "M01: SpecimenCollection has no hasContext→EnvironmentFeature; check sampling site in text",
                entity_name=rec.get("name"),
                bucket="missing_relation_candidates",
            )
            warnings.append(issue)
            missing.append(issue)

        # M02 — Preprocessing fellow
        q_m02_bad = f"""
        MATCH (n:whu_SpecimenPreprocessing)-[:whu_fellow]->(o)
        WHERE {_scope_where("n")} AND NOT o:whu_SpecimenCollection
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(o) AS obj_labels
        """
        for rec in session.run(q_m02_bad, **params):
            hard.append(
                _issue(
                    "M02",
                    "Violation",
                    _node_key(rec),
                    f"M02: fellow target must be SpecimenCollection ({rec.get('obj_labels')})",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )
        q_m02_miss = f"""
        MATCH (n:whu_SpecimenPreprocessing)
        WHERE {_scope_where("n")} AND NOT (n)-[:whu_fellow]->(:whu_SpecimenCollection)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m02_miss, **params):
            issue = _issue(
                "M02",
                "Warning",
                _node_key(rec),
                "M02: SpecimenPreprocessing missing fellow→SpecimenCollection",
                entity_name=rec.get("name"),
                bucket="missing_relation_candidates",
            )
            warnings.append(issue)
            missing.append(issue)

        # M03 — BioChemical fellow types
        q_m03_bad = f"""
        MATCH (n:whu_BioChemical_Experiment)-[:whu_fellow]->(o)
        WHERE {_scope_where("n")}
          AND NOT (o:whu_SpecimenPreprocessing OR o:whu_BioChemical_Experiment)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(o) AS obj_labels
        """
        for rec in session.run(q_m03_bad, **params):
            hard.append(
                _issue(
                    "M03",
                    "Violation",
                    _node_key(rec),
                    f"M03: BioChemical fellow target illegal ({rec.get('obj_labels')})",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )
        q_m03_miss = f"""
        MATCH (n:whu_BioChemical_Experiment)
        WHERE {_scope_where("n")} AND NOT (n)-[:whu_fellow]->()
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m03_miss, **params):
            issue = _issue(
                "M03",
                "Warning",
                _node_key(rec),
                "M03: BioChemicalExperiment has no fellow upstream relation",
                entity_name=rec.get("name"),
                bucket="missing_relation_candidates",
            )
            warnings.append(issue)
            missing.append(issue)

        # M04 — Computational fellow
        q_m04_bad = f"""
        MATCH (n:whu_Computational_Experiment)-[:whu_fellow]->(o)
        WHERE {_scope_where("n")}
          AND NOT (o:whu_BioChemical_Experiment OR o:whu_Computational_Experiment)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(o) AS obj_labels
        """
        for rec in session.run(q_m04_bad, **params):
            hard.append(
                _issue(
                    "M04",
                    "Violation",
                    _node_key(rec),
                    f"M04: Computational fellow target illegal ({rec.get('obj_labels')})",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )
        q_m04_miss = f"""
        MATCH (n:whu_Computational_Experiment)
        WHERE {_scope_where("n")} AND NOT (n)-[:whu_fellow]->()
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m04_miss, **params):
            issue = _issue(
                "M04",
                "Warning",
                _node_key(rec),
                "M04: ComputationalExperiment has no fellow upstream relation",
                entity_name=rec.get("name"),
                bucket="missing_relation_candidates",
            )
            warnings.append(issue)
            missing.append(issue)

        # M05 — SE wasDerivedFrom type when present
        q_m05 = f"""
        MATCH (n:whu_ScienceEvidence)-[:prov_wasDerivedFrom]->(o)
        WHERE {_scope_where("n")} AND NOT o:whu_Computational_Experiment
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(o) AS obj_labels
        """
        for rec in session.run(q_m05, **params):
            hard.append(
                _issue(
                    "M05",
                    "Violation",
                    _node_key(rec),
                    f"M05: wasDerivedFrom target must be ComputationalExperiment ({rec.get('obj_labels')})",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )

        # M06 — SE must support/challenge SupportGraph only (never Claim directly)
        q_m06 = f"""
        MATCH (n:whu_ScienceEvidence)
        WHERE {_scope_where("n")}
          AND NOT (n)-[:mp_supports|mp_challenges]->(:whu_SupportGraph)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m06, **params):
            issue = _issue(
                "M06",
                "Warning",
                _node_key(rec),
                "M06: ScienceEvidence has no mp_supports/mp_challenges to SupportGraph; must not link Claim directly",
                entity_name=rec.get("name"),
                bucket="missing_relation_candidates",
            )
            warnings.append(issue)
            missing.append(issue)

        q_m06_bad = f"""
        MATCH (n:whu_ScienceEvidence)-[:mp_supports|mp_challenges]->(:mp_Claim)
        WHERE {_scope_where("n")}
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m06_bad, **params):
            hard.append(
                _issue(
                    "M06",
                    "Violation",
                    _node_key(rec),
                    "M06: ScienceEvidence must not mp_supports/mp_challenges Claim directly; link SupportGraph only",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )

        # M13 — SupportGraph must have focal Claim via supports/challenges
        q_m13 = f"""
        MATCH (n:whu_SupportGraph)
        WHERE {_scope_where("n")}
          AND NOT (n)-[:mp_supports|mp_challenges]->(:mp_Claim)
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name
        """
        for rec in session.run(q_m13, **params):
            hard.append(
                _issue(
                    "M13",
                    "Violation",
                    _node_key(rec),
                    "M13: SupportGraph has no mp_supports/mp_challenges to Claim (missing focal Claim link)",
                    entity_name=rec.get("name"),
                    bucket="hard_violations",
                )
            )

        # M09 — illegal mid–mid structural edges
        mid_set = set(MID_LABELS_NO_CLAIM)
        q_m09 = f"""
        MATCH (a)-[r]->(b)
        WHERE {_scope_where("a")}
          AND type(r) IN $struct_rels
          AND any(l IN labels(a) WHERE l IN $mid_labels)
          AND any(l IN labels(b) WHERE l IN $mid_labels)
        RETURN elementId(a) AS element_id, a.WHU_HASNAME AS name,
               labels(a) AS a_labels, type(r) AS rel, labels(b) AS b_labels
        """
        for rec in session.run(
            q_m09,
            **params,
            struct_rels=[
                "whu_hasContext",
                "whu_fellow",
                "prov_wasDerivedFrom",
                "mp_supports",
                "mp_challenges",
                "prov_hadMember",
            ],
            mid_labels=list(mid_set | {"mp_Claim"}),
        ):
            a_labs = [l for l in (rec.get("a_labels") or []) if l in mid_set or l == "mp_Claim"]
            b_labs = [l for l in (rec.get("b_labels") or []) if l in mid_set or l == "mp_Claim"]
            rel = rec.get("rel")
            legal = False
            for sa in a_labs:
                for ob in b_labs:
                    if (sa, rel, ob) in MID_MID_ALLOWED_TRIPLES:
                        legal = True
                        break
                if legal:
                    break
            if not legal:
                # Only flag when both ends are mid-core (exclude Claim-only mid2low noise)
                if not (set(a_labs) & mid_set and set(b_labs) & (mid_set | {"mp_Claim"})):
                    continue
                hard.append(
                    _issue(
                        "M09",
                        "Violation",
                        _node_key(rec),
                        f"M09: illegal mid triple {a_labs}-[{rel}]->{b_labs}",
                        entity_name=rec.get("name"),
                        labels=rec.get("a_labels"),
                        bucket="hard_violations",
                    )
                )

        # M10 — isolated mid nodes
        q_m10 = f"""
        MATCH (n)
        WHERE {_scope_where("n")}
          AND any(l IN labels(n) WHERE l IN $mid_labels)
          AND NOT (n)-[r_out]->() WHERE type(r_out) IN $out_rels
        WITH n
        WHERE NOT ()-[r_in]->(n) WHERE type(r_in) IN $in_rels
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(n) AS labels
        """
        # Neo4j may not like WHERE after pattern that way — use FILTER style
        q_m10 = f"""
        MATCH (n)
        WHERE {_scope_where("n")}
          AND any(l IN labels(n) WHERE l IN $mid_labels)
          AND NOT EXISTS {{
            MATCH (n)-[r_out]->()
            WHERE type(r_out) IN $out_rels
          }}
          AND NOT EXISTS {{
            MATCH ()-[r_in]->(n)
            WHERE type(r_in) IN $in_rels
          }}
        RETURN elementId(n) AS element_id, n.WHU_HASNAME AS name, labels(n) AS labels
        """
        for rec in session.run(
            q_m10,
            **params,
            mid_labels=MID_LABELS_NO_CLAIM,
            out_rels=_STRUCT_RELS,
            in_rels=_IN_RELS,
        ):
            issue = _issue(
                "M10",
                "Warning",
                _node_key(rec),
                "M10: mid entity is structurally isolated",
                entity_name=rec.get("name"),
                labels=rec.get("labels"),
                bucket="isolated_nodes",
            )
            warnings.append(issue)
            isolated.append(issue)

    report = {
        "filename": filename,
        "source_doc": source_doc,
        "hard_violations": hard,
        "warnings": warnings,
        "isolated_nodes": isolated,
        "missing_relation_candidates": missing,
        "hard_count": len(hard),
        "warning_count": len(warnings),
    }
    return report


def run_mid_validate(
    cfg,
    driver: Driver,
    filenames: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate mid graph for selected or all document filenames found on Chunks."""
    with driver.session(database=cfg.neo4j_database) as session:
        if filenames:
            docs = list(filenames)
        else:
            docs = [
                r["filename"]
                for r in session.run(
                    "MATCH (c:Chunk) WHERE c.filename IS NOT NULL "
                    "RETURN DISTINCT c.filename AS filename"
                )
            ]
    reports = []
    total_hard = 0
    for fn in docs:
        rep = validate_mid_document(driver, cfg.neo4j_database, fn)
        reports.append(rep)
        total_hard += int(rep["hard_count"])
    return {
        "documents": len(reports),
        "total_hard": total_hard,
        "reports": reports,
    }
