"""Patch 3_0_2 Retevie.ipynb evaluation cells to use utilities/test_evaluation.py."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "3_0_2 Retevie.ipynb"


def _code(s: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": s.splitlines(keepends=True),
    }


def _md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


EVAL_IMPORTS = '''# ══════════════════════════════════════════════════════════════
# 评估共享模块（单次 invoke / 用例 + 路由命中率）
# ══════════════════════════════════════════════════════════════

from utilities.test_evaluation import (
    resolve_questions_csv,
    load_test_cases,
    load_dialogue_test_cases,
    evaluate_test_cases,
    run_dialogue_scenario,
    print_evaluation_summary,
    run_single_case,
)

QUESTIONS_CSV = str(resolve_questions_csv())
print(f"✅ 测试 CSV: {QUESTIONS_CSV}")
'''

FAITHFULNESS = '''# ══════════════════════════════════════════════════════════════
# Faithfulness（引用覆盖率；底层单次 invoke 见 evaluate_test_cases）
# ══════════════════════════════════════════════════════════════

import re

def _analyze_citations(answer, retrieval_count):
    citations = re.findall(r"\\[[\\d,\\s]+\\]", answer or "")
    cited_ids = set()
    for c in citations:
        cited_ids.update(re.findall(r"\\d+", c))
    coverage = len(cited_ids) / retrieval_count if retrieval_count > 0 else 0.0
    return {
        "has_citation": len(citations) > 0,
        "citation_count": len(citations),
        "cited_ids": sorted(list(cited_ids), key=int),
        "coverage": coverage,
    }

def evaluate_faithfulness(test_cases):
    report = evaluate_test_cases(
        graph_app, make_initial_state, test_cases,
        embedder=neo4j_embed_model, verbose=True,
    )
    details = [
        {k: d[k] for k in (
            "query", "answer_length", "has_citation", "citation_count",
            "cited_ids", "retrieval_count", "coverage", "error",
        ) if k in d}
        for d in report["details"]
    ]
    valid = [d for d in details if "error" not in d]
    summary = {
        "total": len(details),
        "citation_rate": sum(1 for d in valid if d.get("has_citation")) / len(valid) if valid else 0,
        "avg_citations": sum(d.get("citation_count", 0) for d in valid) / len(valid) if valid else 0,
        "avg_coverage": sum(d.get("coverage", 0) for d in valid) / len(valid) if valid else 0,
        "with_citation": sum(1 for d in valid if d.get("has_citation")),
        "without_citation": sum(1 for d in valid if not d.get("has_citation")),
    }
    return {"summary": summary, "details": details}

print("✅ Faithfulness 模块（共享 evaluate_test_cases）")
'''

RELEVANCY = '''# ══════════════════════════════════════════════════════════════
# Answer Relevancy（使用 make_initial_state + 共享 run_single_case）
# ══════════════════════════════════════════════════════════════

import numpy as np

def evaluate_answer_relevancy(test_cases):
    print("\\n" + "=" * 80)
    print("Answer Relevancy 评估")
    print("=" * 80)
    results = []
    for i, case in enumerate(test_cases, 1):
        q = case["query"]
        print(f"\\n[{i}/{len(test_cases)}] {q[:70]}")
        row = run_single_case(graph_app, make_initial_state, q, embedder=neo4j_embed_model)
        if "error" in row:
            print(f"  ❌ {row['error'][:80]}")
            results.append({"query": q, "error": row["error"]})
            continue
        score = row["relevancy_score"] or 0.0
        results.append({
            "query": q,
            "answer_length": row["answer_length"],
            "relevancy_score": score,
            "relevancy_level": row["relevancy_level"],
        })
        print(f"  相关性: {score:.3f} ({row['relevancy_level']})")
    valid = [r for r in results if "error" not in r]
    scores = [r["relevancy_score"] for r in valid]
    summary = {
        "total": len(valid),
        "avg_relevancy": float(np.mean(scores)) if scores else 0.0,
        "std_relevancy": float(np.std(scores)) if scores else 0.0,
        "high": sum(1 for s in scores if s >= 0.8),
        "medium": sum(1 for s in scores if 0.6 <= s < 0.8),
        "low": sum(1 for s in scores if s < 0.6),
    }
    return {"summary": summary, "details": results}

print("✅ Answer Relevancy 模块")
'''

PRECISION = '''# ══════════════════════════════════════════════════════════════
# Context Precision（共享 run_single_case）
# ══════════════════════════════════════════════════════════════

import numpy as np

def evaluate_context_precision(test_cases):
    print("\\n" + "=" * 80)
    print("Context Precision 评估")
    print("=" * 80)
    results = []
    for i, case in enumerate(test_cases, 1):
        q = case["query"]
        print(f"\\n[{i}/{len(test_cases)}] {q[:70]}")
        row = run_single_case(graph_app, make_initial_state, q)
        if "error" in row:
            results.append({"query": q, "error": row["error"]})
            continue
        results.append({
            "query": q,
            "retrieval_count": row["retrieval_count"],
            "used_count": row["used_count"],
            "precision": row["precision"],
            "cited_ids": row["cited_ids"],
        })
    valid = [r for r in results if "error" not in r]
    precs = [r["precision"] for r in valid]
    summary = {
        "total": len(valid),
        "avg_precision": float(np.mean(precs)) if precs else 0.0,
        "std_precision": float(np.std(precs)) if precs else 0.0,
        "avg_retrieval": float(np.mean([r["retrieval_count"] for r in valid])) if valid else 0.0,
        "avg_used": float(np.mean([r["used_count"] for r in valid])) if valid else 0.0,
        "high": sum(1 for p in precs if p >= 0.3),
        "medium": sum(1 for p in precs if 0.1 <= p < 0.3),
        "low": sum(1 for p in precs if p < 0.1),
    }
    return {"summary": summary, "details": results}

print("✅ Context Precision 模块")
'''

COMPREHENSIVE = '''# ══════════════════════════════════════════════════════════════
# 综合测试（单次 invoke / 用例 + 路由 hit_any/hit_all）
# ══════════════════════════════════════════════════════════════

from utilities.test_evaluation import (
    resolve_questions_csv,
    load_test_cases,
    evaluate_test_cases,
    print_evaluation_summary,
)

QUESTIONS_CSV = str(resolve_questions_csv())
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

# 路由明细
print("\\n路由命中明细:")
for i, d in enumerate(report["details"], 1):
    if "error" in d:
        print(f"  [{i}] ❌ {d['error'][:80]}")
    else:
        print(
            f"  [{i}] hit_any={d['route_hit_any']} hit_all={d['route_hit_all']} "
            f"expected={d['expected']} actual={d['actual_modules']}"
        )
'''

COMPREHENSIVE_SHORT = '''# ══════════════════════════════════════════════════════════════
# 综合测试 - 精简输出
# ══════════════════════════════════════════════════════════════

import io, sys
from utilities.test_evaluation import (
    resolve_questions_csv,
    load_test_cases,
    evaluate_test_cases,
    print_evaluation_summary,
)

QUESTIONS_CSV = str(resolve_questions_csv())
test_cases = load_test_cases(QUESTIONS_CSV)

class _Suppress:
    def __enter__(self):
        self._orig = sys.stdout
        sys.stdout = io.StringIO()
    def __exit__(self, *_):
        sys.stdout = self._orig

with _Suppress():
    report = evaluate_test_cases(
        graph_app, make_initial_state, test_cases,
        embedder=neo4j_embed_model, verbose=False,
    )
print_evaluation_summary(report)
'''

DIALOGUE_TEST = '''# ══════════════════════════════════════════════════════════════
# 多轮对话测试（dialogue_test_cases.json）
# ══════════════════════════════════════════════════════════════

for scenario in load_dialogue_test_cases():
    print("\\n" + "=" * 60)
    print(f"Scenario: {scenario['name']}")
    print("=" * 60)
    result = run_dialogue_scenario(graph_app, make_initial_state, scenario)
    for t in result["turns"]:
        if "error" in t:
            print(f"  Turn {t['turn']} ❌ {t['error']}")
        else:
            ok_k = (not t.get("expected_kappa")) or t.get("kappa") == t.get("expected_kappa")
            ok_l = (not t.get("expected_l")) or t.get("path_level") == t.get("expected_l")
            mark = "✅" if ok_k and ok_l else "⚠️"
            print(
                f"  {mark} Turn {t['turn']}: κ={t['kappa']} l={t['path_level']} "
                f"r={t['modules']} |P*|={t['|P*|']}"
            )
'''

COMPREHENSIVE_MD = """##### 综合测试模块

- 数据源：`data/questions.csv`（项目内相对路径，经 `resolve_questions_csv()` 解析）
- **单次 invoke / 用例** 同时计算 Faithfulness、Relevancy、Precision、**路由 hit_any/hit_all**
- 多轮测试见 `data/dialogue_test_cases.json`
"""

DIALOGUE_MD = """##### G Cell 8: 多轮对话测试

使用 `dialogue_test_cases.json` 验证 κ / l 在多轮状态传递下是否生效。
"""


def patch() -> None:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    cells = nb["cells"]

    # Insert eval imports before faithfulness (cell 30)
    cells.insert(29, _code(EVAL_IMPORTS))

    # indices shifted +1
    for i, c in enumerate(cells):
        s = "".join(c.get("source", []))
        if s.startswith("# Cell 15: Faithfulness"):
            cells[i] = _code(FAITHFULNESS)
        elif "Cell 17: Answer Relevancy" in s:
            cells[i] = _code(RELEVANCY)
        elif "Cell 19: Context Precision" in s:
            cells[i] = _code(PRECISION)
        elif "Cell 21: 统一评估入口" in s and "精简" not in s:
            cells[i] = _code(COMPREHENSIVE)
        elif "精简输出版" in s:
            cells[i] = _code(COMPREHENSIVE_SHORT)
        elif s.strip() == "##### 综合测试模块":
            cells[i] = _md(COMPREHENSIVE_MD)

    # Insert dialogue test after pipeline cell (find G Cell 7 pipeline code)
    for i, c in enumerate(cells):
        if "G Cell 7: Pipeline + 多轮测试" in "".join(c.get("source", [])):
            cells.insert(i + 1, _md(DIALOGUE_MD))
            cells.insert(i + 2, _code(DIALOGUE_TEST))
            break

    nb["cells"] = cells
    NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Patched {NB} ({len(cells)} cells)")


if __name__ == "__main__":
    patch()
