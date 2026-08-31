"""Restore missing Cypher cell, N4 md, G7 md, and reorder Part 4 eval cells."""
from __future__ import annotations

import json
import re
from pathlib import Path

from patch_retrieve_pipeline_v2 import CYPHER_CODE
from patch_olap_eval_nb import EVAL_IMPORTS, DIALOGUE_CORE, OLAP_COMPARE
from patch_nb_structure_v3 import (
    MD_E1,
    MD_E2,
    MD_E3,
    MD_E4,
    MD_E5,
    MD_G7,
    MD_N4,
    MD_N5_CYPHER,
    _md,
)

NB = Path(__file__).resolve().parents[1] / "3_0_2 Retevie.ipynb"
RUN_EVAL = Path(__file__).resolve().parents[1] / "utilities" / "run_retrieval_eval.py"


def _src(cell: dict) -> str:
    return "".join(cell.get("source", []))


def _code_marker(src: str) -> str:
    if "def build_graph_rag_pipeline" in src:
        return "g7_pipeline"
    if "def make_initial_state" in src or "class SimplifiedGraphRAGState" in src:
        return "p2_state"
    if "Cell 1: 导入依赖" in src or "# Cell 1: 导入依赖" in src:
        return "p0_import"
    if "环境与模型初始化" in src or (
        "neo4j_embed_model" in src and "GraphDatabase.driver" in src
    ):
        return "p3_connect"
    if "def query_rewriter_node" in src:
        return "n1_rewriter"
    if "def route_node" in src:
        return "n2_route"
    if "G_sub 算子" in src and "build_gsub_mp_ids" in src:
        return "prep_import"
    if "def gsub_builder_node" in src:
        return "n3_gsub"
    if "def _build_cypher_for_subgraph" in src:
        return "prep_cypher"
    if "def recall_node" in src:
        return "n4_recall"
    if "def rerank_node" in src:
        return "n5_rerank"
    if "def answer_generator_node" in src:
        return "n6_answer"
    if "report_stateful = evaluate_dialogue_scenarios" in src:
        return "e5_olap"
    if "CORE_METRIC_KEYS" in src and "from utilities.test_evaluation import" in src:
        return "e2_eval_import"
    if "dialogue_report = evaluate_dialogue_scenarios" in src:
        return "e3_dialogue"
    if "综合测试" in src and "evaluate_test_cases" in src:
        return "e4_comprehensive"
    if "for scenario in load_dialogue_test_cases" in src and "run_dialogue_scenario" in src:
        return "e3_legacy_loop"
    return ""


def _cell_md(text: str, cid: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "id": cid, "source": _md(text)}


def _cell_code(text: str, cid: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "id": cid,
        "source": _md(text.rstrip() + "\n"),
    }


def restore(cells: list[dict]) -> list[dict]:
    g7_end = None
    for i, c in enumerate(cells):
        if c["cell_type"] == "code" and _code_marker(_src(c)) == "g7_pipeline":
            g7_end = i + 1
            break
    if g7_end is None:
        raise RuntimeError("g7_pipeline cell not found")
    out = list(cells[:g7_end])

    # Insert Cypher + N4 md if missing
    has_cypher = any(
        c["cell_type"] == "code" and "def _build_cypher_for_subgraph" in _src(c) for c in out
    )
    if not has_cypher:
        recall_i = next(
            i
            for i, c in enumerate(out)
            if c["cell_type"] == "code" and "def recall_node" in _src(c)
        )
        insert = [
            _cell_md(MD_N4, "md_n4_recall"),
            _cell_md(MD_N5_CYPHER, "md_prep_cypher2"),
            _cell_code(CYPHER_CODE, "prep_cypher_code"),
        ]
        out[recall_i:recall_i] = insert

    # MD before g7
    g7_i = next(
        i for i, c in enumerate(out) if c["cell_type"] == "code" and "def build_graph_rag_pipeline" in _src(c)
    )
    if g7_i == 0 or _src(out[g7_i - 1]).strip() != MD_G7.strip():
        out.insert(g7_i, _cell_md(MD_G7, "md_g7_pipeline"))

    # Part 4 tail
    out.extend(
        [
            _cell_md(MD_E1, "part4_e1"),
            _cell_md(MD_E2, "md_e2_import"),
            _cell_code(EVAL_IMPORTS, "e2_eval_import"),
            _cell_md(MD_E3, "md_e3_dialogue"),
            _cell_code(DIALOGUE_CORE, "e3_dialogue"),
            _cell_md(MD_E4, "md_e4_comprehensive"),
            _cell_code(
                """# ══════════════════════════════════════════════════════════════
# E4: 单轮综合测试（questions.csv，可选）
# ══════════════════════════════════════════════════════════════

test_cases = load_test_cases(QUESTIONS_CSV)
for case in test_cases:
    print(f"  {case['query'][:42]:<42} → {case['expected']}")

report = evaluate_test_cases(
    graph_app,
    make_initial_state,
    test_cases,
    embedder=neo4j_embed_model,
    verbose=True,
)
print_evaluation_summary(report)
""",
                "e4_comprehensive",
            ),
            _cell_md(MD_E5, "md_e5_olap"),
            _cell_code(OLAP_COMPARE, "e5_olap"),
        ]
    )

    # Fix Part 2 formula markdown
    for c in out:
        if c["cell_type"] == "markdown" and "Part 2 · 检索与重排" in _src(c):
            c["source"] = _md(
                _src(c).replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "(").replace(r"\)", ")")
            )
            break

    return out


def find_pipeline_indices(cells: list[dict]) -> list[int]:
    markers = [
        "p0_import",
        "p2_state",
        "p3_connect",
        "n1_rewriter",
        "n2_route",
        "prep_import",
        "n3_gsub",
        "prep_cypher",
        "n4_recall",
        "n5_rerank",
        "n6_answer",
        "g7_pipeline",
    ]
    idx_map: dict[str, int] = {}
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        m = _code_marker(_src(c))
        if m:
            idx_map[m] = i
    return [idx_map[m] for m in markers if m in idx_map]


def find_eval_indices(cells: list[dict]) -> tuple[int | None, int | None]:
    e2 = e5 = None
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        m = _code_marker(_src(c))
        if m == "e2_eval_import":
            e2 = i
        if m == "e5_olap":
            e5 = i
    return e2, e5


def patch_run_retrieval_eval(indices: list[int], e2: int | None, e5: int | None) -> None:
    text = RUN_EVAL.read_text(encoding="utf-8")
    text = re.sub(
        r"PIPELINE_CELL_INDICES = \[.*?\]",
        f"PIPELINE_CELL_INDICES = {indices}",
        text,
        count=1,
    )
    if e2 is not None:
        text = re.sub(r"EVAL_IMPORT_CELL = \d+", f"EVAL_IMPORT_CELL = {e2}", text, count=1)
    if e5 is not None:
        text = re.sub(r"OLAP_COMPARE_CELL = \d+", f"OLAP_COMPARE_CELL = {e5}", text, count=1)
    RUN_EVAL.write_text(text, encoding="utf-8")


def main() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = restore(nb["cells"])
    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    pipeline_idx = find_pipeline_indices(cells)
    e2, e5 = find_eval_indices(cells)
    patch_run_retrieval_eval(pipeline_idx, e2, e5)

    print(f"✅ restore → {len(cells)} cells")
    print(f"   PIPELINE_CELL_INDICES = {pipeline_idx}")
    print(f"   EVAL_IMPORT_CELL = {e2}, OLAP_COMPARE_CELL = {e5}")


if __name__ == "__main__":
    main()
