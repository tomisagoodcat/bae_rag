"""Fixture tests for judgement metrics (no Neo4j, no LLM)."""
from __future__ import annotations

from kg_build_pipeline.judgement.graph_read import (
    CYPHER_QUERIES,
    EdgeRec,
    NodeRec,
    assert_readonly_cypher,
)
from kg_build_pipeline.judgement.metrics import (
    duplicate_candidates,
    duplicate_entity_rate,
    has_legal_path_at_least,
    relation_conflict_rate,
    relation_schema_conformance,
    resolve_issue_node_id,
    shacl_conformance,
)
from kg_build_pipeline.judgement.report import render_markdown
from kg_build_pipeline.judgement.schema_view import instantiable_classes, legal_triples, load_judgement_schema


def _n(eid: str, label: str, *, name: str = "", ot: str = "", doc: str = "p.md", chunks=None) -> NodeRec:
    return NodeRec(
        eid=eid,
        labels=[label, "__Entity__"],
        bae_label=label,
        name=name,
        original_text=ot,
        source_doc=doc.replace(".md", ""),
        filenames=list(chunks if chunks is not None else [doc]),
        rejected=False,
    )


def _e(eid: str, src: str, rel: str, tgt: str, sl: str, tl: str) -> EdgeRec:
    return EdgeRec(eid=eid, src=src, tgt=tgt, rel_type=rel, src_label=sl, tgt_label=tl)


def test_rsc_legal_and_illegal() -> None:
    legal = {("whu_SupportGraph", "mp_supports", "mp_Claim")}
    edges = [
        _e("r1", "sg", "mp_supports", "cl", "whu_SupportGraph", "mp_Claim"),
        _e("r2", "sg", "mp_challenges", "cl", "whu_SupportGraph", "mp_Claim"),
    ]
    rsc = relation_schema_conformance(edges, legal)
    assert rsc["status"] == "OK"
    assert rsc["legal"] == 1
    assert rsc["total"] == 2
    assert rsc["illegal_samples"][0]["rel"] == "mp_challenges"


def test_rcr_self_loop_and_dual_polarity_not_conflict() -> None:
    legal = {
        ("whu_SupportGraph", "mp_supports", "mp_Claim"),
        ("whu_SupportGraph", "mp_challenges", "mp_Claim"),
    }
    edges = [
        _e("r1", "sg", "mp_supports", "cl", "whu_SupportGraph", "mp_Claim"),
        _e("r2", "sg", "mp_challenges", "cl", "whu_SupportGraph", "mp_Claim"),
        _e("r3", "x", "mp_supports", "x", "whu_SupportGraph", "mp_Claim"),
    ]
    rcr = relation_conflict_rate(edges, legal)
    assert rcr["duplicate_extra"] == 0
    assert rcr["self_loop"] == 1
    assert rcr["illegal_direction"] == 0
    assert rcr["mutex"]["status"] == "NOT_COMPUTABLE"
    assert all(s["src"] == s["tgt"] for s in rcr.get("samples") or [])


def test_rcr_duplicate_same_spo() -> None:
    legal = {("whu_SupportGraph", "mp_supports", "mp_Claim")}
    edges = [
        _e("r1", "sg", "mp_supports", "cl", "whu_SupportGraph", "mp_Claim"),
        _e("r2", "sg", "mp_supports", "cl", "whu_SupportGraph", "mp_Claim"),
    ]
    rcr = relation_conflict_rate(edges, legal)
    assert rcr["duplicate_extra"] == 1


def test_der_not_computable_and_ot_not_duplicate() -> None:
    der = duplicate_entity_rate()
    assert der["status"] == "NOT_COMPUTABLE"
    nodes = [
        _n("a", "whu_SupportGraph", name="n1", ot="same span", chunks=["p.md"]),
        _n("b", "whu_SupportGraph", name="n2", ot="same span", chunks=["p.md"]),
    ]
    cands = duplicate_candidates(nodes)
    assert cands and cands[0]["size"] == 2
    assert "not classified as duplicates" in cands[0]["note"]


def test_mpc_three_hop_and_two_hop() -> None:
    legal = {
        ("whu_ScienceEvidence", "prov_hadMember", "whu_DataSet"),
        ("whu_DataSet", "mp_supports", "mp_Statement"),
        ("mp_Statement", "mp_supports", "mp_Claim"),
        ("whu_ScienceEvidence", "mp_supports", "whu_SupportGraph"),
        ("whu_SupportGraph", "mp_supports", "mp_Claim"),
    }
    se, ds, st, cl = (
        _n("se", "whu_ScienceEvidence"),
        _n("ds", "whu_DataSet"),
        _n("st", "mp_Statement"),
        _n("cl", "mp_Claim"),
    )
    three = [
        _e("e1", "se", "prov_hadMember", "ds", "whu_ScienceEvidence", "whu_DataSet"),
        _e("e2", "ds", "mp_supports", "st", "whu_DataSet", "mp_Statement"),
        _e("e3", "st", "mp_supports", "cl", "mp_Statement", "mp_Claim"),
    ]
    assert has_legal_path_at_least([se, ds, st, cl], three, legal, 3)
    sg = _n("sg", "whu_SupportGraph")
    two = [
        _e("f1", "se", "mp_supports", "sg", "whu_ScienceEvidence", "whu_SupportGraph"),
        _e("f2", "sg", "mp_supports", "cl", "whu_SupportGraph", "mp_Claim"),
    ]
    assert not has_legal_path_at_least([se, sg, cl], two, legal, 3)


def test_scr_resolves_name_keyed_hard_issue() -> None:
    nodes = [_n("eid-sg", "whu_SupportGraph", name="SG1")]
    issue = {
        "rule_id": "M14",
        "bucket": "hard_violations",
        "severity": "Violation",
        "entity_id": "SG1",
        "entity_name": "SG1",
        "labels": ["whu_SupportGraph", "__Entity__"],
    }
    assert resolve_issue_node_id(issue, nodes) == "eid-sg"
    bound = dict(issue)
    bound["entity_id"] = "eid-sg"
    scr = shacl_conformance(["eid-sg"], [bound])
    assert scr["status"] == "OK"
    assert scr["hard_nodes"] == 1
    assert scr["value"] == 0.0


def test_readonly_cypher_guard() -> None:
    assert_readonly_cypher("MATCH (n) RETURN n")
    try:
        assert_readonly_cypher("MATCH (n) SET n.x = 1")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_judgement_sources_have_no_write_cypher() -> None:
    assert CYPHER_QUERIES
    for name, cypher in CYPHER_QUERIES.items():
        assert_readonly_cypher(cypher)


def test_schema_loads() -> None:
    classes, triples = load_judgement_schema()
    assert len(classes) == 26
    assert ("whu_SupportGraph", "mp_supports", "mp_Claim") in triples
    ents = [{"label": "whu_SupportGraph"}, {"label": "Chunk"}]
    assert instantiable_classes(ents) == ["whu_SupportGraph"]
    assert ("a", "r", "b") in legal_triples([["a", "r", "b", ["All"], "mid"]])


def test_empty_low_h01b_table() -> None:
    from kg_build_pipeline.src.stages.low_validate import check_h01b_research_type

    assert check_h01b_research_type([]) == []


def test_report_contains_glossary() -> None:
    md = render_markdown(
        {
            "generated_at": "20260101_000000",
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_database": "neo4j",
            "filenames": [],
            "stages_run": ["build_kg"],
            "summary": {
                "cr": {"value": 0.1, "status": "OK"},
                "ap": {"value": 1.0, "status": "OK"},
                "scr": {"status": "NOT_COMPUTABLE", "reason": "no inspected BAE nodes"},
                "or": {"status": "NOT_COMPUTABLE", "reason": "no orphan-eligible"},
                "dc": {"status": "NOT_COMPUTABLE", "reason": "none"},
                "mc": {"status": "NOT_COMPUTABLE", "reason": "none"},
                "mpc": {"status": "NOT_COMPUTABLE", "reason": "none"},
                "der": duplicate_entity_rate(),
                "rsc": {"status": "NOT_COMPUTABLE", "reason": "no edges"},
                "rcr": {
                    "status": "NOT_COMPUTABLE",
                    "reason": "no edges",
                    "mutex": {"status": "NOT_COMPUTABLE", "reason": "no mutex table"},
                },
                "pc": {"status": "NOT_COMPUTABLE", "reason": "no BAE"},
            },
            "class_population": {"mp_Claim": 0},
            "documents": [],
            "duplicate_candidates": [],
            "risks": {"site_matrix": [], "research_step_parent": []},
        }
    )
    assert "Class Richness (CR)" in md
    assert "NOT_COMPUTABLE" in md
    assert "不替代 Gold Standard" in md


def test_write_log_filename_and_glossary() -> None:
    import tempfile
    from pathlib import Path

    from kg_build_pipeline.judgement.report import write_log

    directory = Path(tempfile.mkdtemp())
    path = write_log(
        {
            "generated_at": "20260903_150500",
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_database": "neo4j",
            "filenames": ["paper.md"],
            "stages_run": ["build_kg"],
            "summary": {"der": duplicate_entity_rate()},
            "class_population": {"mp_Claim": 1},
            "documents": [],
            "duplicate_candidates": [],
            "risks": {"site_matrix": [], "research_step_parent": []},
        },
        log_dir=directory,
    )
    assert path.name == "judgement_20260903_150500.md"
    text = path.read_text(encoding="utf-8")
    assert "### 指标词典（每次相同）" in text
    assert "paper.md" in text
    assert "build_kg" in text
    path.unlink()
    directory.rmdir()


def main() -> None:
    test_rsc_legal_and_illegal()
    test_rcr_self_loop_and_dual_polarity_not_conflict()
    test_rcr_duplicate_same_spo()
    test_der_not_computable_and_ot_not_duplicate()
    test_mpc_three_hop_and_two_hop()
    test_scr_resolves_name_keyed_hard_issue()
    test_readonly_cypher_guard()
    test_judgement_sources_have_no_write_cypher()
    test_schema_loads()
    test_empty_low_h01b_table()
    test_report_contains_glossary()
    test_write_log_filename_and_glossary()
    print("test_judgement: ok")


if __name__ == "__main__":
    main()
