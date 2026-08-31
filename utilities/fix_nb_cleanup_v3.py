"""Second-pass cleanup for 3_0_2 Retevie.ipynb after patch_nb_structure_v3."""
from __future__ import annotations

import json
import re
from pathlib import Path

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
    if "def recall_node" in src:
        return "n4_recall"
    if "def _build_cypher_for_subgraph" in src:
        return "prep_cypher"
    if "def rerank_node" in src:
        return "n5_rerank"
    if "def answer_generator_node" in src:
        return "n6_answer"
    if "report_stateful = evaluate_dialogue_scenarios" in src:
        return "e5_olap"
    if "CORE_METRIC_KEYS" in src and "from utilities.test_evaluation import" in src:
        return "e2_eval_import"
    if "run_dialogue_scenario" in src and "load_dialogue_test_cases" in src:
        return "e3_dialogue"
    if "综合测试 - 精简" in src:
        return "e4_short"
    if "综合测试" in src and "evaluate_test_cases" in src:
        return "e4_comprehensive"
    return ""


def _should_drop_md(src: str, next_cell: dict | None) -> bool:
    s = src.strip()
    if s.startswith("##### "):
        return True
    if s.startswith("## 术语表（读代码 / 评估"):
        return True
    if s.startswith("# 流程（论文"):
        return True
    if s.startswith("##### 综合测试") or s == "##### OLAP 对比评估 (Stateful vs Stateless)":
        return True
    # duplicate ### P2 right before g7 pipeline
    if s.startswith("### P2 对话状态") and next_cell and _code_marker(_src(next_cell)) == "g7_pipeline":
        return True
    # duplicate ### E5 only when two E5 markdown cells are adjacent
    if s.startswith("### E5 OLAP") and next_cell and next_cell["cell_type"] == "markdown":
        if _src(next_cell).strip().startswith("### E5"):
            return True
    return False


def cleanup(cells: list[dict]) -> list[dict]:
    out: list[dict] = []
    i = 0
    while i < len(cells):
        cell = cells[i]
        nxt = cells[i + 1] if i + 1 < len(cells) else None
        if cell["cell_type"] == "markdown" and _should_drop_md(_src(cell), nxt):
            i += 1
            continue
        if cell["cell_type"] == "code" and _code_marker(_src(cell)) == "e4_short":
            i += 1
            continue
        out.append(cell)
        i += 1
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
        src = _src(c)
        if "CORE_METRIC_KEYS" in src:
            e2 = i
        if _code_marker(src) == "e5_olap":
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
    cells = cleanup(nb["cells"])
    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    pipeline_idx = find_pipeline_indices(cells)
    e2, e5 = find_eval_indices(cells)
    patch_run_retrieval_eval(pipeline_idx, e2, e5)

    print(f"✅ cleanup → {len(cells)} cells")
    print(f"   PIPELINE_CELL_INDICES = {pipeline_idx}")
    print(f"   EVAL_IMPORT_CELL = {e2}, OLAP_COMPARE_CELL = {e5}")
    for i, c in enumerate(cells):
        if c["cell_type"] == "code":
            m = _code_marker(_src(c))
            if m:
                print(f"   [{i}] {m}")


if __name__ == "__main__":
    main()
