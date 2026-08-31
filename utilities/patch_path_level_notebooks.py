"""Patch 1_2_1_2pagerankMetapath.ipynb and 3_0_2 Retevie.ipynb for path_level."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_MP = ROOT / "1_2_1_2pagerankMetapath.ipynb"
NB_RET = ROOT / "3_0_2 Retevie.ipynb"


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _set_cell(nb: dict, idx: int, source: str, cell_type: str = "code") -> None:
    nb["cells"][idx]["source"] = source
    nb["cells"][idx]["cell_type"] = cell_type
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None


def patch_pagerank_nb() -> None:
    nb = json.loads(NB_MP.read_text(encoding="utf-8"))

    cell10 = '''def build_metapath_for_relation(
    driver,
    subgraph: str,
    source_label: str,
    relation_type: str,
    target_label: str,
    pagerank_prop: str,
    id_counter_start: int,
) -> int:
    """F1: 原子 2-hop MetaPath，path_level='low'。"""
    path_type = f"{source_label}-[{relation_type}]->{target_label}"

    query_match = f"""
    MATCH (s:{source_label})-[r:{relation_type}]->(t:{target_label})
    WITH s, r, t,
         "[{source_label}: " + COALESCE(s.WHU_HASNAME, "") + "] " +
         COALESCE(s.WHU_HASORIGINALTEXT, "") +
         " -[{relation_type}] " + COALESCE(r.WHU_HASORIGINALTEXT, "") +
         " -> [{target_label}: " + COALESCE(t.WHU_HASNAME, "") + "] " +
         COALESCE(t.WHU_HASORIGINALTEXT, "")
         AS metapath_text,
         CASE
            WHEN COALESCE(s.{pagerank_prop}, 0.0) > COALESCE(t.{pagerank_prop}, 0.0)
            THEN COALESCE(s.{pagerank_prop}, 0.0)
            ELSE COALESCE(t.{pagerank_prop}, 0.0)
         END AS max_pagerank
    RETURN elementId(s) AS source_id,
           elementId(t) AS target_id,
           metapath_text,
           max_pagerank,
           r.WHU_HASORIGINALTEXT AS relation_text
    """

    try:
        with driver.session() as session:
            results = session.run(query_match).data()
    except Exception as e:
        print(f"  ❌ {path_type}: 查询失败 - {str(e)[:100]}")
        return 0

    if not results:
        print(f"  ⚠️  {path_type}: 无匹配实例")
        return 0

    query_create = """
    MATCH (s) WHERE elementId(s) = $source_id
    MATCH (t) WHERE elementId(t) = $target_id
    CREATE (mp:MetaPath {
      mp_id:         $mp_id,
      metaPathText:  $metapath_text,
      metaPathQuery: null,
      embedding:     null,
      maxPageRank:   $max_pagerank,
      subgraph:      $subgraph,
      path_type:     $path_type,
      path_level:    'low',
      anchor_label:  $anchor_label
    })
    CREATE (mp)-[:metaPathRelation {position: 1, relationText: $relation_text}]->(s)
    CREATE (mp)-[:metaPathRelation {position: 2, relationText: null}]->(t)
    RETURN mp.mp_id AS mp_id
    """

    counter = id_counter_start
    created_count = 0
    failed_count = 0

    with driver.session() as session:
        for row in results:
            mp_id = f"{subgraph}_{counter:06d}"
            try:
                session.run(
                    query_create,
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    mp_id=mp_id,
                    metapath_text=row["metapath_text"],
                    max_pagerank=row["max_pagerank"],
                    subgraph=subgraph,
                    path_type=path_type,
                    relation_text=row["relation_text"],
                    anchor_label=source_label,
                )
                counter += 1
                created_count += 1
            except Exception as e:
                print(f"    ❌ 创建失败 {mp_id}: {str(e)[:80]}")
                failed_count += 1

    status = "✅" if failed_count == 0 else "⚠️"
    print(f"  {status} {path_type}: 创建 {created_count} 条 low"
          + (f"（失败 {failed_count} 条）" if failed_count else ""))
    return created_count


print("✅ MetaPath 构建函数已定义（path_level=low）")
'''

    cell12 = '''def verify_metapath_creation(driver):
    """验证 MetaPath：含 path_level 与层级边统计。"""
    with driver.session() as session:
        result = session.run("""
            MATCH (mp:MetaPath)
            RETURN mp.subgraph AS subgraph, mp.path_level AS path_level, count(mp) AS count
            ORDER BY subgraph, path_level
        """).data()

        print("=" * 60)
        print("MetaPath 数量（subgraph × path_level）")
        print("=" * 60)
        for row in result:
            print(f"  {row['subgraph']} / {row['path_level']}: {row['count']} 条")

        hier = session.run("""
            MATCH (mid:MetaPath {path_level:'mid'})-[hd:hasDetailPath]->(low:MetaPath {path_level:'low'})
            RETURN count(hd) AS detail_edges
        """).single()["detail_edges"]
        print(f"\\n  hasDetailPath 边数: {hier}")

        bad = session.run("""
            MATCH (a:MetaPath)-[:hasDetailPath]->(b:MetaPath)
            WHERE a.path_level <> 'mid' OR b.path_level <> 'low'
            RETURN count(*) AS c
        """).single()["c"]
        print(f"  非法层级边: {bad}（应为 0）")

        sample = session.run("""
            MATCH (mp:MetaPath)
            RETURN mp LIMIT 3
        """).data()

        print("\\n随机抽查 3 条:")
        for row in sample:
            mp = row["mp"]
            print(f"  mp_id={mp.get('mp_id')} level={mp.get('path_level')} "
                  f"sg={mp.get('subgraph')} type={mp.get('path_type','')[:50]}")


# verify_metapath_creation(neo4j_driver)
'''

    f4_md = """### F4 构建 middle / low level MetaPath

- **low**：F1 `SUBGRAPH_RELATIONS` 实例（`path_level='low'`）
- **mid**：Plan / SupportGraph 聚合（`path_level='mid'`）
- **层级边**：`hasDetailPath`（mid→low）、`detailOf`（low→mid）

先运行 F1 全量构建，再运行下方 F4 cell。
"""

    f4_code = '''# ══════════════════════════════════════════════════════════════
# F4: mid MetaPath + hasDetailPath / detailOf
# ══════════════════════════════════════════════════════════════

def build_mid_metapaths_for_plans(driver, id_counters):
    query = """
    MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
    WHERE (step:whu_Specimen_CollectionStep OR step:whu_Specimen_ProcessingStep
           OR step:whu_BioChemicalStep OR step:whu_ComputationalStep)
    WITH plan, labels(plan)[0] AS plan_label, collect(DISTINCT step) AS steps
    RETURN elementId(plan) AS plan_id, plan_label,
           plan.WHU_HASNAME AS plan_name,
           [s IN steps | COALESCE(s.WHU_HASNAME,'')] AS step_names
    """
    subgraph_map = {
        "whu_SpecimenCollection": "EBM",
        "whu_SpecimenPreprocessing": "EBM",
        "whu_Bio_chemical_Experiment": "EEM",
        "whu_Computational_Experiment": "EEM",
    }
    n = 0
    with driver.session() as session:
        for row in session.run(query).data():
            sg = subgraph_map.get(row["plan_label"], "EEM")
            cnt = id_counters.get(sg, 1)
            mp_id = f"{sg}_MID_{cnt:05d}"
            steps = "; ".join([x for x in row["step_names"] if x][:8])
            text = f"[{row['plan_label']}: {row.get('plan_name') or ''}] comprises steps: {steps}"
            session.run("""
                MATCH (plan) WHERE elementId(plan) = $pid
                CREATE (mp:MetaPath {
                  mp_id: $mp_id, metaPathText: $text, metaPathQuery: null,
                  embedding: null, maxPageRank: 0.0, subgraph: $sg,
                  path_type: $pt, path_level: 'mid', anchor_label: $al
                })
                CREATE (mp)-[:metaPathRelation {position:1, relationText:null}]->(plan)
            """, pid=row["plan_id"], mp_id=mp_id, text=text[:8000], sg=sg,
                pt=f"mid-{row['plan_label']}", al=row["plan_label"])
            id_counters[sg] = cnt + 1
            n += 1
    print(f"  ✅ Plan mid: {n}")
    return id_counters


def build_mid_metapaths_for_containers(driver, id_counters):
    query = """
    MATCH (c)-[:whu_hasPart]->(part)
    WHERE c:whu_SupportGraph OR c:whu_ScienceEvidence
    WITH c, labels(c)[0] AS cl, collect(DISTINCT labels(part)[0]) AS part_labels
    RETURN elementId(c) AS cid, cl, c.WHU_HASNAME AS name, part_labels
    """
    n = 0
    with driver.session() as session:
        for row in session.run(query).data():
            sg = "MPU"
            cnt = id_counters.get(sg, 1)
            mp_id = f"{sg}_MID_{cnt:05d}"
            text = f"[{row['cl']}: {row.get('name') or ''}] hasPart: {', '.join(row['part_labels'])}"
            session.run("""
                MATCH (c) WHERE elementId(c) = $cid
                CREATE (mp:MetaPath {
                  mp_id: $mp_id, metaPathText: $text, metaPathQuery: null,
                  embedding: null, maxPageRank: 0.0, subgraph: $sg,
                  path_type: $pt, path_level: 'mid', anchor_label: $cl
                })
                CREATE (mp)-[:metaPathRelation {position:1, relationText:null}]->(c)
            """, cid=row["cid"], mp_id=mp_id, text=text[:8000], sg=sg,
                pt=f"mid-{row['cl']}", cl=row["cl"])
            id_counters[sg] = cnt + 1
            n += 1
    print(f"  ✅ Container mid: {n}")
    return id_counters


def link_mid_to_low(driver):
    q1 = """
    MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(plan)
    MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
    MATCH (low:MetaPath {path_level:'low'})-[:metaPathRelation]->(step)
    MERGE (mid)-[:hasDetailPath]->(low)
    MERGE (low)-[:detailOf]->(mid)
    RETURN count(*) AS c
    """
    q2 = """
    MATCH (mid:MetaPath {path_level:'mid'})-[:metaPathRelation]->(container)
    WHERE container:whu_SupportGraph OR container:whu_ScienceEvidence
    MATCH (container)-[:whu_hasPart]->(part)
    MATCH (low:MetaPath {path_level:'low'})-[:metaPathRelation]->(part)
    MERGE (mid)-[:hasDetailPath]->(low)
    MERGE (low)-[:detailOf]->(mid)
    RETURN count(*) AS c
    """
    with driver.session() as session:
        c1 = session.run(q1).single()["c"]
        c2 = session.run(q2).single()["c"]
    print(f"  ✅ 层级边 plan={c1}, hasPart={c2}")
    return {"plan": c1, "hasPart": c2}


mid_counters = {"MPU": 1, "EBM": 1, "EEM": 1}
mid_counters = build_mid_metapaths_for_plans(neo4j_driver, mid_counters)
mid_counters = build_mid_metapaths_for_containers(neo4j_driver, mid_counters)
link_stats = link_mid_to_low(neo4j_driver)
verify_metapath_creation(neo4j_driver)
'''

    _set_cell(nb, 10, cell10)
    _set_cell(nb, 12, cell12)
    _set_cell(nb, 13, f4_md, "markdown")
    _set_cell(nb, 14, f4_code)

    # F2: ensure processes all MetaPath with path_level
    for i, c in enumerate(nb["cells"]):
        src = "".join(c.get("source", []))
        if "def batch_generate_metapath_query" in src and "MATCH (mp:MetaPath)" in src:
            src = src.replace(
                "MATCH (mp:MetaPath)\n        WHERE mp.metaPathQuery IS NULL",
                "MATCH (mp:MetaPath)\n        WHERE mp.metaPathQuery IS NULL\n          AND mp.metaPathText IS NOT NULL",
            )
            _set_cell(nb, i, src)

    NB_MP.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB_MP}")


def patch_retrieval_nb() -> None:
    nb = json.loads(NB_RET.read_text(encoding="utf-8"))

    for i, c in enumerate(nb["cells"]):
        src = "".join(c.get("source", []))

        if "class SimplifiedGraphRAGState(TypedDict):" in src:
            if "path_level:" not in src:
                src = src.replace(
                    "    target_subgraphs:  List[str]  # 目标子图列表，如 [\"MPU\", \"EEM\"]\n",
                    "    target_subgraphs:  List[str]  # 目标子图列表，如 [\"MPU\", \"EEM\"]\n\n"
                    "    # ── 对话状态 M_t（论文 §5.1）────────────────────────────\n"
                    "    path_level:        str        # \"mid\" | \"low\"，对应 l\n"
                    "    kappa:             str        # first_turn|drill_down|roll_up|sibling_nav\n"
                    "    anchor_mp_ids:     List[str]  # C_{t-1} 锚点 mp_id 列表\n"
                    "    dialogue_turn:     int        # 轮次计数\n",
                )
            _set_cell(nb, i, src)

        if "def make_initial_state(query: str)" in src and '"path_level"' not in src:
            src = src.replace(
                '        "target_subgraphs":  [],   # 空列表，由 Node2 填充\n',
                '        "target_subgraphs":  [],   # 空列表，由 Node2 填充\n'
                '        "path_level":        "mid",\n'
                '        "kappa":             "first_turn",\n'
                '        "anchor_mp_ids":     [],\n'
                '        "dialogue_turn":     0,\n',
            )
            _set_cell(nb, i, src)

        if "def _build_cypher_for_subgraph(subgraph: str) -> str:" in src:
            src = '''# ══════════════════════════════════════════════════════════════
# Cell 9.5: Subgraph Cypher（含 path_level 过滤）
# ══════════════════════════════════════════════════════════════

def _build_cypher_for_subgraph(subgraph: str, path_level: str = "mid") -> str:
    return f"""
WITH node
WHERE node.subgraph = '{subgraph}' AND node.path_level = '{path_level}'
OPTIONAL MATCH (node)-[r:metaPathRelation]->(entity)-[:FROM_CHUNK]->(chunk:Chunk)
WITH node, r.position AS position, chunk
ORDER BY position ASC
WITH node, COLLECT(chunk.text) AS chunk_texts_ordered
WITH node,
     reduce(acc = [], x IN chunk_texts_ordered |
            CASE WHEN x IN acc OR x IS NULL OR size(x) <= 10
                 THEN acc ELSE acc + x END) AS chunk_texts
RETURN
    node.metaPathText AS metapath_text,
    chunk_texts AS chunk_texts,
    COALESCE(node.maxPageRank, 0.0) AS graph_score,
    node.mp_id AS mp_id,
    node.path_level AS path_level
"""


SUBGRAPH_CYPHER = {
    "MPU": _build_cypher_for_subgraph("MPU", "mid"),
    "EEM": _build_cypher_for_subgraph("EEM", "mid"),
    "EBM": _build_cypher_for_subgraph("EBM", "mid"),
}

print("✅ Subgraph Cypher（path_level=mid 默认）:", list(SUBGRAPH_CYPHER.keys()))
'''
            _set_cell(nb, i, src)

        if "def _search_single_subgraph(query_text: str, subgraph: str)" in src:
            # Insert hierarchy helpers before hybrid_retriever_node
            if "def _fetch_hierarchy_results" not in src:
                insert = '''

def detect_kappa_and_level(query: str, anchor_mp_ids=None, prev_path_level="mid"):
    q = (query or "").lower()
    anchors = anchor_mp_ids or []
    if any(k in q for k in ["also", "另外", "同时", "换模块", "邻接", "sibling"]):
        return "sibling_nav", prev_path_level or "mid", anchors
    if anchors and any(k in q for k in ["detail", "specific", "下钻", "具体", "展开"]):
        return "drill_down", "low", anchors
    if anchors and any(k in q for k in ["summary", "overview", "上卷", "概括", "总结"]):
        return "roll_up", "mid", anchors
    return "first_turn", "mid", []


def _fetch_hierarchy_results(anchor_mp_ids, kappa):
    if not anchor_mp_ids:
        return []
    if kappa == "drill_down":
        cypher = """
        UNWIND $ids AS mpid
        MATCH (mid:MetaPath {path_level:'mid', mp_id: mpid})
        MATCH (mid)-[:hasDetailPath]->(low:MetaPath {path_level:'low'})
        OPTIONAL MATCH (low)-[:metaPathRelation]->(e)-[:FROM_CHUNK]->(c:Chunk)
        WITH low, collect(DISTINCT c.text) AS chunk_texts
        RETURN low.metaPathText AS metapath_text,
               [x IN chunk_texts WHERE x IS NOT NULL AND size(x)>10] AS chunk_texts,
               COALESCE(low.maxPageRank,0.0) AS graph_score,
               low.mp_id AS mp_id, low.path_level AS path_level, low.subgraph AS subgraph
        LIMIT 30
        """
    else:
        cypher = """
        UNWIND $ids AS mpid
        MATCH (low:MetaPath {path_level:'low', mp_id: mpid})
        MATCH (low)-[:detailOf]->(mid:MetaPath {path_level:'mid'})
        OPTIONAL MATCH (mid)-[:metaPathRelation]->(e)-[:FROM_CHUNK]->(c:Chunk)
        WITH mid, collect(DISTINCT c.text) AS chunk_texts
        RETURN mid.metaPathText AS metapath_text,
               [x IN chunk_texts WHERE x IS NOT NULL AND size(x)>10] AS chunk_texts,
               COALESCE(mid.maxPageRank,0.0) AS graph_score,
               mid.mp_id AS mp_id, mid.path_level AS path_level, mid.subgraph AS subgraph
        LIMIT 20
        """
    with neo4j_driver.session() as session:
        rows = session.run(cypher, ids=anchor_mp_ids).data()
    for r in rows:
        r["_subgraph"] = r.get("subgraph", "MPU")
        r["score"] = 1.0
    return rows


def _search_single_subgraph(query_text: str, subgraph: str, path_level: str = "mid") -> List[Dict]:
'''
                src = src.replace(
                    "def _search_single_subgraph(query_text: str, subgraph: str) -> List[Dict]:",
                    insert.strip() + "\n\n\ndef _search_single_subgraph(query_text: str, subgraph: str, path_level: str = \"mid\") -> List[Dict]:",
                )
                src = src.replace(
                    "retrieval_query = _get_retrieval_query_for_subgraph(subgraph)",
                    "retrieval_query = _build_cypher_for_subgraph(subgraph, path_level)",
                )
            _set_cell(nb, i, src)

        if "def hybrid_retriever_node(state: SimplifiedGraphRAGState)" in src:
            src = re.sub(
                r"def hybrid_retriever_node\(state: SimplifiedGraphRAGState\) -> Dict:.*?"
                r'return \{"retrieval_results": results_json\}',
                '''def hybrid_retriever_node(state: SimplifiedGraphRAGState) -> Dict:
    print("\\n" + "=" * 60)
    print("Node 4: HybridRetriever（path_level + κ）")
    print("=" * 60)

    query_text = sanitize_for_lucene(state["rewritten_query"])
    subgraphs = state.get("target_subgraphs", ["MPU"])
    if not subgraphs:
        subgraphs = ["MPU", "EEM", "EBM"]

    anchor_mp_ids = state.get("anchor_mp_ids") or []
    prev_level = state.get("path_level") or "mid"
    kappa, path_level, anchors = detect_kappa_and_level(
        query_text, anchor_mp_ids, prev_level
    )
    if anchors:
        anchor_mp_ids = anchors

    print(f"查询: {query_text[:80]}...")
    print(f"子图: {subgraphs} | κ={kappa} | path_level={path_level}")

    all_results: List[Dict] = []

    if kappa in ("drill_down", "roll_up"):
        all_results = _fetch_hierarchy_results(anchor_mp_ids, kappa)
        print(f"  [层级导航] {kappa}: {len(all_results)} 条")
    else:
        for subgraph in subgraphs:
            print(f"\\n  ── 检索 {subgraph} (level={path_level}) ──")
            results = _search_single_subgraph(query_text, subgraph, path_level)
            print(f"  返回: {len(results)} 条")
            all_results.extend(results)

    if not all_results:
        merged = []
    else:
        pr_values = [r.get("graph_score") or 0.0 for r in all_results]
        pr_min, pr_max = min(pr_values), max(pr_values)
        pr_range = (pr_max - pr_min) if pr_max > pr_min else 1.0
        for r in all_results:
            pr_norm = ((r.get("graph_score") or 0.0) - pr_min) / pr_range
            vec_norm = r.get("score", 0.0)
            r["combined_score"] = 0.8 * vec_norm + 0.2 * pr_norm
        all_results.sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)
        merged = _deduplicate_by_mp_id(all_results)[:20]

    formatted = _format_retrieval_results(merged)
    top_ids = [x.get("mp_id") for x in formatted[:5] if x.get("mp_id")]

    return {
        "retrieval_results": json.dumps(formatted, ensure_ascii=False, indent=2),
        "kappa": kappa,
        "path_level": path_level,
        "anchor_mp_ids": top_ids,
        "dialogue_turn": state.get("dialogue_turn", 0) + 1,
    }''',
                src,
                flags=re.DOTALL,
            )
            _set_cell(nb, i, src)

        if "def subgraph_router_node(state: SimplifiedGraphRAGState)" in src and "path_level" not in src:
            src = src.replace(
                '        return {"target_subgraphs": subgraphs}',
                '        pl = state.get("path_level") or "mid"\n'
                '        return {"target_subgraphs": subgraphs, "path_level": pl, "kappa": "first_turn"}',
                1,
            )
            src = src.replace(
                '        return {"target_subgraphs": subgraphs}',
                '        pl = state.get("path_level") or "mid"\n'
                '        return {"target_subgraphs": subgraphs, "path_level": pl, "kappa": "first_turn"}',
            )
            _set_cell(nb, i, src)

    NB_RET.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Patched {NB_RET}")


def main() -> None:
    patch_pagerank_nb()
    patch_retrieval_nb()


if __name__ == "__main__":
    main()
