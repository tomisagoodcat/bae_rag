"""Low SHACL mirror tests 1–6, 8–10 (pure Python fixtures; no Neo4j)."""
from __future__ import annotations

from kg_build_pipeline.src.stages.low_validate import (
    check_h04_research_steps,
    check_h09_evidence,
    check_schema_type_violation,
)


def _hard(issues):
    return [i for i in issues if i.get("bucket") == "hard_violations"]


def _warn(issues):
    return [i for i in issues if i.get("bucket") == "warnings"]


def test1_single_step_pass() -> None:
    steps = [{"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p"}]
    issues = check_h04_research_steps(steps, [], parent_id="p")
    assert _hard(issues) == []
    assert _warn(issues) == []


def test2_two_steps_linked_pass() -> None:
    steps = [
        {"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p"},
        {"id": "s2", "name": "S2", "labels": ["whu_ResearchStep"], "parent_id": "p"},
    ]
    issues = check_h04_research_steps(steps, [("s2", "s1")], parent_id="p")
    assert _hard(issues) == []
    assert _warn(issues) == []


def test3_two_steps_no_order_warning() -> None:
    steps = [
        {"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p"},
        {"id": "s2", "name": "S2", "labels": ["whu_ResearchStep"], "parent_id": "p"},
    ]
    issues = check_h04_research_steps(steps, [], parent_id="p")
    assert _hard(issues) == []
    assert len(_warn(issues)) >= 1


def test4_self_loop_hard() -> None:
    steps = [{"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p"}]
    issues = check_h04_research_steps(steps, [("s1", "s1")], parent_id="p")
    assert any("self-loop" in i["message"] for i in _hard(issues))


def test5_cycle_hard() -> None:
    steps = [
        {"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p"},
        {"id": "s2", "name": "S2", "labels": ["whu_ResearchStep"], "parent_id": "p"},
    ]
    issues = check_h04_research_steps(steps, [("s1", "s2"), ("s2", "s1")], parent_id="p")
    assert any("cycle" in i["message"].lower() for i in _hard(issues))


def test6_cross_parent_hard() -> None:
    steps = [
        {"id": "s1", "name": "S1", "labels": ["whu_ResearchStep"], "parent_id": "p1"},
        {"id": "s2", "name": "S2", "labels": ["whu_ResearchStep"], "parent_id": "p2"},
    ]
    issues = check_h04_research_steps(steps, [("s1", "s2")], parent_id="p1")
    assert any("cross" in i["message"].lower() for i in _hard(issues))


def test8_shared_method_neighbor_not_hard() -> None:
    issues = check_h09_evidence(
        research_steps=[
            {
                "id": "s1",
                "name": "S1",
                "labels": ["whu_ResearchStep"],
                "original_text": "wash cells",
            }
        ],
        goals=[],
        shared_entities=[
            {
                "id": "m1",
                "name": "PCR",
                "labels": ["mp_Method"],
                "original_text": "only in neighbor chunk text",
            }
        ],
        parent_corpus="wash cells with PBS",
    )
    assert _hard(issues) == []
    assert any(i.get("rule_id") == "H09-B" for i in _warn(issues))


def test9_orphan_goal_hard() -> None:
    issues = check_h09_evidence(
        research_steps=[],
        goals=[
            {
                "id": "g1",
                "name": "G",
                "labels": ["whu_Goal"],
                "original_text": "measure X",
                "orphan": True,
            }
        ],
        shared_entities=[],
        parent_corpus="measure X in samples",
    )
    assert any("orphan" in i["message"].lower() for i in _hard(issues))


def test10_comp_exp_reagent_schema_hard() -> None:
    viol = check_schema_type_violation(
        parent_labels=["whu_Computational_Experiment"],
        child_labels=["whu_Reagent"],
        allowed_child_labels={"whu_ResearchStep", "whu_DataSet", "mp_Method", "whu_Software"},
        entity_id="r1",
        entity_name="Buffer",
    )
    assert viol is not None
    assert viol["bucket"] == "hard_violations"


def main() -> None:
    test1_single_step_pass()
    test2_two_steps_linked_pass()
    test3_two_steps_no_order_warning()
    test4_self_loop_hard()
    test5_cycle_hard()
    test6_cross_parent_hard()
    test8_shared_method_neighbor_not_hard()
    test9_orphan_goal_hard()
    test10_comp_exp_reagent_schema_hard()
    print("test_low_validate: OK (1-6,8-10)")


if __name__ == "__main__":
    main()
