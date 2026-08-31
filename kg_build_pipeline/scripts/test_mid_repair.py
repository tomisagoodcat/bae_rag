"""Quick checks for mid_repair (run: python -m kg_build_pipeline.scripts.test_mid_repair)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from kg_build_pipeline.src.mid_repair import (
    _parse_m09_triple_from_reason,
    filter_potential_schema_by_rule,
    merge_repair_issues,
    reject_violation_nodes,
    resolve_chunk_nodes,
    violations_for_reject,
)


def _node(text: str, **metadata):
    return SimpleNamespace(
        metadata=metadata,
        get_text=lambda t=text: t,
    )


def main() -> None:
    ps = [
        ["whu_ScienceEvidence", "mp_supports", "whu_SupportGraph", ["All"], "mid"],
        ["whu_ScienceEvidence", "mp_challenges", "whu_SupportGraph", ["All"], "mid"],
        [
            "whu_SpecimenCollection",
            "whu_hasContext",
            "whu_EnvironmentFeature",
            ["Methods_Materials"],
            "mid",
        ],
    ]
    f = filter_potential_schema_by_rule({"rule_id": "M06"}, ps)
    assert len(f) == 2, f
    ps_m13 = ps + [
        ["whu_SupportGraph", "mp_supports", "mp_Claim", ["All"], "mid"],
        ["whu_SupportGraph", "mp_challenges", "mp_Claim", ["All"], "mid"],
    ]
    f13 = filter_potential_schema_by_rule({"rule_id": "M13"}, ps_m13)
    assert len(f13) == 2, f13
    f1 = filter_potential_schema_by_rule({"rule_id": "M01"}, ps)
    assert len(f1) == 1, f1
    unknown = filter_potential_schema_by_rule({"rule_id": "M99"}, ps)
    assert len(unknown) == len(ps), unknown
    reason = "M09: illegal mid triple ['whu_ScienceEvidence']-[mp_supports]->['mp_Claim']"
    t = _parse_m09_triple_from_reason(reason)
    assert t == ("whu_ScienceEvidence", "mp_supports", "mp_Claim"), t
    f9 = filter_potential_schema_by_rule({"rule_id": "M09", "reason": reason}, ps)
    assert len(f9) == len(ps), "M09 triple not in ps -> fallback full list"

    text = "Topsoil samples were collected from the SWU paddy field for analysis."
    nodes = [_node(text, chunk_id=2, section_role="Methods_Materials")]
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    session.run.return_value.single.side_effect = [
        {"chunk_index": 2, "chunk_id": None, "text_head": text[:80]},
        None,
    ]
    resolved, method = resolve_chunk_nodes(
        driver,
        "neo4j",
        "doc.md",
        nodes,
        {"entity": "SWU paddy field", "source_chunk": None},
    )
    assert resolved == nodes, resolved
    assert method == "neo4j_from_chunk", method

    resolved2, method2 = resolve_chunk_nodes(
        driver,
        "neo4j",
        "doc.md",
        nodes,
        {"entity": "missing", "source_chunk": "2"},
    )
    assert resolved2 == nodes, resolved2
    assert method2 == "reviewer_source_chunk", method2

    report = {
        "hard_violations": [
            {"rule_id": "M13", "entity_name": "SG orphan A", "message": "no claim"},
            {"rule_id": "M13", "entity_name": "SG orphan B", "message": "no claim"},
            {"rule_id": "M09", "entity_name": "bad edge", "message": "illegal"},
        ],
        "warnings": [
            {"rule_id": "M06", "entity_name": "SE orphan", "message": "no sg"},
            {"rule_id": "M01", "entity_name": "collection", "message": "no context"},
        ],
    }
    reject_list = violations_for_reject(report, ["M13", "M06"])
    assert len(reject_list) == 3, reject_list
    assert all(v["rule_id"] in ("M13", "M06") for v in reject_list)

    review_issues = [
        {
            "rule_id": "M13",
            "entity": "SG orphan A",
            "suggested_action": "REEXTRACT",
            "source_chunk": "3",
            "reason": "reviewer note",
        }
    ]
    merged = merge_repair_issues(review_issues, report, max_issues=15)
    assert len(merged) == 5, merged
    keys = {(i["rule_id"], i["entity"]) for i in merged}
    assert ("M13", "SG orphan A") in keys
    assert ("M13", "SG orphan B") in keys
    assert ("M06", "SE orphan") in keys
    assert ("M01", "collection") in keys
    assert ("M09", "bad edge") in keys
    reviewer_a = next(i for i in merged if i["entity"] == "SG orphan A")
    assert reviewer_a.get("source_chunk") == "3", reviewer_a

    merged_cap = merge_repair_issues(review_issues, report, max_issues=2)
    assert len(merged_cap) == 2, merged_cap

    reject_driver = MagicMock()
    reject_session = MagicMock()
    reject_driver.session.return_value.__enter__.return_value = reject_session
    reject_session.run.return_value.single.return_value = {"c": 2}
    mark_stats = reject_violation_nodes(
        reject_driver,
        "neo4j",
        "doc.md",
        reject_list,
        mode="mark",
    )
    assert mark_stats["mode"] == "mark"
    assert mark_stats["count"] == 6, mark_stats
    assert len(mark_stats["names"]) == 3

    reject_session.run.return_value.single.return_value = {"c": 3}
    del_stats = reject_violation_nodes(
        reject_driver,
        "neo4j",
        "doc.md",
        reject_list,
        mode="delete",
    )
    assert del_stats["mode"] == "delete"
    assert del_stats["count"] == 3

    print("mid_repair checks OK")


if __name__ == "__main__":
    main()
