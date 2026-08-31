"""MetaPath path_level (mid/low) build, link, and verification."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

PAGERANK_PROP_BY_SUBGRAPH: Dict[str, str] = {
    "MPU": "mpu_pagerank",
    "EEM": "eem_pagerank",
    "EBM": "ebm_pagerank",
}

SUBGRAPH_FOR_PLAN = {
    "whu_SpecimenCollection": "EBM",
    "whu_SpecimenPreprocessing": "EBM",
    "whu_BioChemical_Experiment": "EEM",
    "whu_Bio_chemical_Experiment": "EEM",
    "whu_Computational_Experiment": "EEM",
}
SUBGRAPH_FOR_CONTAINER = {
    "whu_SupportGraph": "MPU",
    "whu_ScienceEvidence": "MPU",
}
VALID_PATH_LEVELS = frozenset({"low", "mid"})
PLAN_LABELS_ORDERED = (
    "whu_SpecimenCollection",
    "whu_SpecimenPreprocessing",
    "whu_BioChemical_Experiment",
    "whu_Bio_chemical_Experiment",
    "whu_Computational_Experiment",
)


def _session(driver, database: Optional[str] = None):
    """Open a Neo4j session; optional database for multi-db deployments."""
    if database:
        return driver.session(database=database)
    return driver.session()


def _resolve_plan_label(plan_labels: List[str]) -> str:
    """Pick canonical Plan label; ignore __KGBuilder__ etc."""
    label_set = set(plan_labels)
    for lbl in PLAN_LABELS_ORDERED:
        if lbl in label_set:
            return lbl
    raise ValueError(
        f"No known Plan label in {plan_labels}; expected one of {PLAN_LABELS_ORDERED}"
    )


def _subgraph_for_plan(plan_label: str) -> str:
    if plan_label not in SUBGRAPH_FOR_PLAN:
        raise ValueError(
            f"Unknown plan label '{plan_label}'; expected one of {sorted(SUBGRAPH_FOR_PLAN)}"
        )
    return SUBGRAPH_FOR_PLAN[plan_label]


def _subgraph_for_container(container_label: str) -> str:
    if container_label not in SUBGRAPH_FOR_CONTAINER:
        raise ValueError(
            f"Unknown container label '{container_label}'; "
            f"expected one of {sorted(SUBGRAPH_FOR_CONTAINER)}"
        )
    return SUBGRAPH_FOR_CONTAINER[container_label]


def pagerank_prop_for_subgraph(subgraph: str) -> str:
    """Return E-segment pagerank property name for a top-level subgraph."""
    prop = PAGERANK_PROP_BY_SUBGRAPH.get(subgraph)
    if prop is None:
        raise ValueError(
            f"未知 subgraph '{subgraph}'; 期望 {sorted(PAGERANK_PROP_BY_SUBGRAPH)}"
        )
    return prop


def compute_max_pagerank_for_linked_entities(
    session,
    entity_element_ids: Sequence[str],
    subgraph: str,
    *,
    mp_id: str,
) -> float:
    """
    Unified maxPageRank rule (low / mid identical):

    maxPageRank(mp) = max( e.{sg}_pagerank
                           for e in {(mp)-[:metaPathRelation]->(e)} )

    Every linked entity must exist and have a non-null pagerank. Prefer the
    property for mp.subgraph; if the node was not in that GDS projection (e.g.
    cross-subgraph F1 templates), fall back via COALESCE to other sg pageranks.
    """
    if not entity_element_ids:
        raise ValueError(
            f"MetaPath {mp_id}: 无 metaPathRelation 关联基础节点"
        )
    pr_prop = pagerank_prop_for_subgraph(subgraph)
    all_props = list(PAGERANK_PROP_BY_SUBGRAPH.values())
    coalesce_expr = "COALESCE(" + ", ".join(
        f"n.{p}" for p in ([pr_prop] + [p for p in all_props if p != pr_prop])
    ) + ")"
    pageranks: List[float] = []
    for eid in entity_element_ids:
        row = session.run(
            f"""
            MATCH (n) WHERE elementId(n) = $eid
            RETURN {coalesce_expr} AS pr, labels(n) AS labels
            """,
            eid=eid,
        ).single()
        if row is None:
            raise ValueError(
                f"MetaPath {mp_id}: 关联基础节点不存在 elementId={eid}"
            )
        if row["pr"] is None:
            lbls = row.get("labels") or []
            raise ValueError(
                f"MetaPath {mp_id}: 关联节点 elementId={eid} labels={lbls} "
                f"缺少 {pr_prop}（请先执行 E 段 GDS 写回；"
                f"若为 __KGBuilder__ 等占位节点，应排除出 F1 模板匹配）"
            )
        pageranks.append(float(row["pr"]))
    return max(pageranks)


def build_metapath_for_relation(
    driver,
    subgraph: str,
    source_label: str,
    relation_type: str,
    target_label: str,
    pagerank_prop: str,
    id_counter_start: int,
    *,
    database: Optional[str] = None,
) -> int:
    """F1: atomic 2-hop MetaPath instances; path_level is always 'low'.

    Entity filter uses ``:__Entity__`` (neo4j_graphrag ontology nodes), aligning
    with Notebook F1 acceptance (no ``NOT __KGBuilder__``, which excludes all
    graphrag entities). Chunk/Document nodes lack ``__Entity__`` and are skipped.
    """
    path_type = f"{source_label}-[{relation_type}]->{target_label}"

    query_match = f"""
    MATCH (s:{source_label})-[r:{relation_type}]->(t:{target_label})
    WHERE s:__Entity__ AND t:__Entity__
    WITH s, r, t,
         "[{source_label}: " + COALESCE(s.WHU_HASNAME, "") + "] " +
         COALESCE(s.WHU_HASORIGINALTEXT, "") +
         " -[{relation_type}] " + COALESCE(r.WHU_HASORIGINALTEXT, "") +
         " -> [{target_label}: " + COALESCE(t.WHU_HASNAME, "") + "] " +
         COALESCE(t.WHU_HASORIGINALTEXT, "")
         AS metapath_text,
         elementId(s) AS source_id,
         elementId(t) AS target_id,
         r.WHU_HASORIGINALTEXT AS relation_text
    RETURN source_id,
           target_id,
           metapath_text,
           relation_text
    """

    with _session(driver, database) as session:
        results = session.run(query_match).data()

    if not results:
        print(f"  ⚠️  {path_type}: 无匹配实例（模板在 KG 中为空）")
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

    with _session(driver, database) as session:
        for row in results:
            mp_id = f"{subgraph}_{counter:06d}"
            max_pagerank = compute_max_pagerank_for_linked_entities(
                session,
                [row["source_id"], row["target_id"]],
                subgraph,
                mp_id=mp_id,
            )
            session.run(
                query_create,
                source_id=row["source_id"],
                target_id=row["target_id"],
                mp_id=mp_id,
                metapath_text=row["metapath_text"],
                max_pagerank=max_pagerank,
                subgraph=subgraph,
                path_type=path_type,
                relation_text=row["relation_text"],
                anchor_label=source_label,
            )
            counter += 1
            created_count += 1

    print(f"  ✅ {path_type}: 创建 {created_count} 条 low")
    return created_count


def build_all_metapaths(
    driver,
    subgraph_relations: Dict,
    pagerank_prop: Dict,
    *,
    database: Optional[str] = None,
) -> Dict[str, int]:
    """Run F1 over SUBGRAPH_RELATIONS; raise if any template raises."""
    subgraph_counters = {"MPU": 1, "EEM": 1, "EBM": 1}
    summary = {"MPU": 0, "EEM": 0, "EBM": 0}
    errors: List[str] = []

    for subgraph, relations in subgraph_relations.items():
        print(f"\n{'=' * 60}")
        print(f"构建子图：{subgraph}（{len(relations)} 条关系模板）")
        print("=" * 60)
        pr_prop = pagerank_prop[subgraph]
        for source_label, relation_type, target_label in relations:
            try:
                created = build_metapath_for_relation(
                    driver=driver,
                    subgraph=subgraph,
                    source_label=source_label,
                    relation_type=relation_type,
                    target_label=target_label,
                    pagerank_prop=pr_prop,
                    id_counter_start=subgraph_counters[subgraph],
                    database=database,
                )
                subgraph_counters[subgraph] += created
                summary[subgraph] += created
            except Exception as exc:
                msg = (
                    f"{subgraph} | {source_label}-[{relation_type}]->{target_label}: {exc}"
                )
                errors.append(msg)
                print(f"  ❌ {msg}")

    print(f"\n{'=' * 60}\n构建完成\n{'=' * 60}")
    for sg, count in summary.items():
        print(f"  {sg}: {count} 条 low MetaPath")
    print(f"  总计 low: {sum(summary.values())}")

    if errors:
        raise RuntimeError(
            f"F1 构建失败 {len(errors)} 条:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    total_low = sum(summary.values())
    if total_low == 0:
        raise RuntimeError(
            "F1 未创建任何 low MetaPath；请检查："
            "(1) build_kg 是否完成且实体带 __Entity__ 标签；"
            "(2) SUBGRAPH_RELATIONS 与当前 schema/图谱是否对齐；"
            "(3) 是否已执行 pagerank 阶段写回 {sg}_pagerank"
        )
    return summary


def build_mid_metapaths_for_plans(
    driver,
    id_counters: Dict[str, int],
    *,
    database: Optional[str] = None,
) -> Dict[str, int]:
    """F4: one mid MetaPath per Plan instance."""
    query = """
    MATCH (step)-[:p_plan_isStepOfPlan]->(plan)
    WHERE (step:whu_ResearchStep
           OR step:whu_Specimen_CollectionStep OR step:whu_Specimen_ProcessingStep
           OR step:whu_BioChemicalStep OR step:whu_ComputationalStep)
      AND (plan:whu_SpecimenCollection OR plan:whu_SpecimenPreprocessing
           OR plan:whu_BioChemical_Experiment OR plan:whu_Bio_chemical_Experiment
           OR plan:whu_Computational_Experiment)
    WITH plan, labels(plan) AS plan_labels, collect(DISTINCT step) AS steps
    RETURN elementId(plan) AS plan_id,
           plan_labels AS plan_labels,
           plan.WHU_HASNAME AS plan_name,
           plan.WHU_HASORIGINALTEXT AS plan_text,
           [s IN steps | COALESCE(s.WHU_HASNAME, '')] AS step_names
    """
    created = 0
    with _session(driver, database) as session:
        rows = session.run(query).data()
        if not rows:
            raise RuntimeError(
                "F4 Plan: 未找到任何 Step-[:p_plan_isStepOfPlan]->Plan 实例"
            )
        for row in rows:
            plan_label = _resolve_plan_label(row["plan_labels"])
            sg = _subgraph_for_plan(plan_label)
            counter = id_counters[sg]
            mp_id = f"{sg}_MID_{counter:05d}"
            step_part = "; ".join(n for n in row["step_names"] if n)[:8]
            text = (
                f"[{plan_label}: {row.get('plan_name') or ''}] "
                f"{row.get('plan_text') or ''} "
                f"| comprises steps: {step_part}"
            ).strip()
            if len(text) < 10:
                raise ValueError(f"Plan mid metaPathText 过短: plan_id={row['plan_id']}")
            max_pagerank = compute_max_pagerank_for_linked_entities(
                session,
                [row["plan_id"]],
                sg,
                mp_id=mp_id,
            )
            session.run(
                """
                MATCH (plan) WHERE elementId(plan) = $plan_id
                CREATE (mp:MetaPath {
                  mp_id: $mp_id,
                  metaPathText: $text,
                  metaPathQuery: null,
                  embedding: null,
                  maxPageRank: $max_pagerank,
                  subgraph: $subgraph,
                  path_type: $path_type,
                  path_level: 'mid',
                  anchor_label: $plan_label
                })
                CREATE (mp)-[:metaPathRelation {position: 1, relationText: null}]->(plan)
                """,
                plan_id=row["plan_id"],
                mp_id=mp_id,
                text=text[:8000],
                max_pagerank=max_pagerank,
                subgraph=sg,
                path_type=f"mid_plan-{plan_label}",
                plan_label=plan_label,
            )
            id_counters[sg] = counter + 1
            created += 1
    print(f"  ✅ Plan mid MetaPath: {created} 条")
    return id_counters


def build_mid_metapaths_for_containers(
    driver,
    id_counters: Dict[str, int],
    *,
    database: Optional[str] = None,
) -> Dict[str, int]:
    """F4: one mid MetaPath per SupportGraph / ScienceEvidence instance."""
    query = """
    MATCH (container)-[m:whu_hasPart|prov_hadMember]->(part)
    WHERE container:whu_SupportGraph OR container:whu_ScienceEvidence
    WITH container, labels(container) AS container_labels,
         collect(DISTINCT part) AS parts
    RETURN elementId(container) AS container_id,
           container_labels,
           container.WHU_HASNAME AS container_name,
           [p IN parts | labels(p)[0] + ':' + COALESCE(p.WHU_HASNAME,'')] AS part_summaries
    """
    created = 0
    with _session(driver, database) as session:
        rows = session.run(query).data()
        if not rows:
            raise RuntimeError(
                "F4 Container: 未找到 SupportGraph/ScienceEvidence-[:whu_hasPart|prov_hadMember]->part"
            )
        for row in rows:
            labels = row["container_labels"]
            if "whu_SupportGraph" in labels:
                cl = "whu_SupportGraph"
            elif "whu_ScienceEvidence" in labels:
                cl = "whu_ScienceEvidence"
            else:
                raise ValueError(f"No known container label in {labels}")
            sg = _subgraph_for_container(cl)
            counter = id_counters[sg]
            mp_id = f"{sg}_MID_{counter:05d}"
            parts = ", ".join(row["part_summaries"][:12])
            text = f"[{cl}: {row.get('container_name') or ''}] aggregates parts: {parts}"
            if len(text) < 10:
                raise ValueError(
                    f"Container mid metaPathText 过短: container_id={row['container_id']}"
                )
            max_pagerank = compute_max_pagerank_for_linked_entities(
                session,
                [row["container_id"]],
                sg,
                mp_id=mp_id,
            )
            session.run(
                """
                MATCH (c) WHERE elementId(c) = $cid
                CREATE (mp:MetaPath {
                  mp_id: $mp_id,
                  metaPathText: $text,
                  metaPathQuery: null,
                  embedding: null,
                  maxPageRank: $max_pagerank,
                  subgraph: $subgraph,
                  path_type: $path_type,
                  path_level: 'mid',
                  anchor_label: $container_label
                })
                CREATE (mp)-[:metaPathRelation {position: 1, relationText: null}]->(c)
                """,
                cid=row["container_id"],
                mp_id=mp_id,
                text=text[:8000],
                max_pagerank=max_pagerank,
                subgraph=sg,
                path_type=f"mid_{cl}",
                container_label=cl,
            )
            id_counters[sg] = counter + 1
            created += 1
    print(f"  ✅ Container mid MetaPath: {created} 条")
    return id_counters


def link_mid_to_low(
    driver,
    *,
    database: Optional[str] = None,
    allow_empty_detail_links: bool = True,
) -> Dict[str, int]:
    """
    Create hasDetailPath (mid->low) and detailOf (low->mid).

    链接依据：mid 锚点实体与 low 路径实体共享 FROM_CHUNK 的 Chunk（同子图）。
    说明：当前 KG 中 F1 low 路径上的 Step/part 节点 ID 与
    isStepOfPlan/whu_hasPart 结构中的节点 ID 无交集，故不用纯图拓扑匹配。

    allow_empty_detail_links: when True (default), detail_edges==0 is a warning.
    Pass False for notebook/CLI strict acceptance.
    """
    q_link = """
    MATCH (mid:MetaPath {path_level: 'mid'})-[:metaPathRelation]->(anchor)
    MATCH (low:MetaPath {path_level: 'low'})
    WHERE low.subgraph = mid.subgraph AND mid <> low
    MATCH (low)-[:metaPathRelation]->(entity)
    WHERE EXISTS {
      MATCH (anchor)-[:FROM_CHUNK]->(c:Chunk)<-[:FROM_CHUNK]-(entity)
    }
    WITH DISTINCT mid, low
    MERGE (mid)-[hd:hasDetailPath]->(low)
    MERGE (low)-[dt:detailOf]->(mid)
    RETURN count(hd) AS c
    """
    with _session(driver, database) as session:
        low_count = session.run(
            "MATCH (mp:MetaPath {path_level:'low'}) RETURN count(mp) AS c"
        ).single()["c"]
        mid_count = session.run(
            "MATCH (mp:MetaPath {path_level:'mid'}) RETURN count(mp) AS c"
        ).single()["c"]
        if low_count == 0:
            raise RuntimeError(
                "link_mid_to_low: F1 未创建任何 low MetaPath，无法连 hasDetailPath；"
                "请先修复 F1（实体 __Entity__ 过滤、SUBGRAPH_RELATIONS、pagerank 前置）"
            )
        detail_edges = session.run(q_link).single()["c"]
    stats = {
        "detail_edges": detail_edges,
        "low_count": low_count,
        "mid_count": mid_count,
        "empty_detail_allowed": bool(allow_empty_detail_links),
    }
    print(f"  ✅ 层级边（Chunk 共现）: hasDetailPath={detail_edges}")
    if detail_edges == 0:
        msg = (
            "link_mid_to_low: 未创建任何 hasDetailPath 边；"
            f"low={low_count}, mid={mid_count}；"
            "检查 mid/low 锚点与路径实体是否共享 FROM_CHUNK 的 Chunk（同 subgraph）"
        )
        if allow_empty_detail_links:
            print(f"  ⚠ {msg}（lenient：继续）")
            stats["warning"] = msg
        else:
            raise RuntimeError(msg)
    return stats


def refresh_metapath_max_pagerank(
    driver,
    pagerank_prop: Optional[Dict[str, str]] = None,
    *,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Recompute maxPageRank for every MetaPath (low / mid unified):

    max over all (mp)-[:metaPathRelation]->(e) using mp.subgraph's {sg}_pagerank.
    """
    prop_map = pagerank_prop or PAGERANK_PROP_BY_SUBGRAPH
    for sg in ("MPU", "EEM", "EBM"):
        if sg not in prop_map:
            raise ValueError(f"pagerank_prop 缺少子图 {sg}")

    updated = 0
    errors: List[str] = []
    pending: List[tuple[str, float]] = []

    with _session(driver, database) as session:
        rows = session.run(
            """
            MATCH (mp:MetaPath)
            OPTIONAL MATCH (mp)-[:metaPathRelation]->(e)
            WITH mp, collect(elementId(e)) AS endpoint_ids
            RETURN mp.mp_id AS mp_id,
                   mp.subgraph AS subgraph,
                   endpoint_ids,
                   size(endpoint_ids) AS endpoint_count
            ORDER BY mp.mp_id
            """
        ).data()

        for row in rows:
            mp_id = row["mp_id"]
            subgraph = row["subgraph"]
            endpoint_ids = row["endpoint_ids"]
            if subgraph not in prop_map:
                errors.append(f"{mp_id}: 未知 subgraph={subgraph}")
                continue
            if row["endpoint_count"] == 0:
                errors.append(f"{mp_id}: 无 metaPathRelation 关联基础节点")
                continue
            try:
                max_pr = compute_max_pagerank_for_linked_entities(
                    session,
                    endpoint_ids,
                    subgraph,
                    mp_id=mp_id,
                )
                pending.append((mp_id, max_pr))
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            sample = errors[:10]
            raise RuntimeError(
                f"refresh_metapath_max_pagerank 失败 {len(errors)} 条（未写入任何更新）:\n"
                + "\n".join(f"  - {e}" for e in sample)
                + (f"\n  ... 另有 {len(errors) - len(sample)} 条" if len(errors) > 10 else "")
            )

        for mp_id, max_pr in pending:
            session.run(
                """
                MATCH (mp:MetaPath {mp_id: $mp_id})
                SET mp.maxPageRank = $pr
                """,
                mp_id=mp_id,
                pr=max_pr,
            )
            updated += 1

    result = {"updated_total": updated, "metapath_count": len(rows)}
    print(f"  ✅ maxPageRank 刷新完成: 共 {updated} 条 MetaPath")
    return result


def report_metapath_max_pagerank_stats(
    driver, *, database: Optional[str] = None
) -> Dict[str, Any]:
    """Print and return maxPageRank distribution per path_level."""
    with _session(driver, database) as session:
        total = session.run("MATCH (mp:MetaPath) RETURN count(mp) AS c").single()["c"]
        if total == 0:
            raise RuntimeError("report_metapath_max_pagerank_stats: 无 MetaPath 节点")

        null_cnt = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.maxPageRank IS NULL
            RETURN count(mp) AS c
            """
        ).single()["c"]
        if null_cnt:
            raise RuntimeError(
                f"report_metapath_max_pagerank_stats: {null_cnt} 个 MetaPath 缺少 maxPageRank"
            )

        rows = session.run(
            """
            MATCH (mp:MetaPath)
            RETURN mp.path_level AS level,
                   count(*) AS total,
                   avg(mp.maxPageRank) AS avg_pr,
                   min(mp.maxPageRank) AS min_pr,
                   max(mp.maxPageRank) AS max_pr,
                   sum(CASE WHEN mp.maxPageRank = 0.0 THEN 1 ELSE 0 END) AS zero_cnt,
                   sum(CASE WHEN mp.maxPageRank > 0.0 THEN 1 ELSE 0 END) AS positive_cnt
            ORDER BY level
            """
        ).data()

        by_subgraph = session.run(
            """
            MATCH (mp:MetaPath)
            RETURN mp.path_level AS level,
                   mp.subgraph AS subgraph,
                   count(*) AS total,
                   avg(mp.maxPageRank) AS avg_pr,
                   sum(CASE WHEN mp.maxPageRank = 0.0 THEN 1 ELSE 0 END) AS zero_cnt
            ORDER BY level, subgraph
            """
        ).data()

    print("=" * 60)
    print("maxPageRank 统计")
    print("=" * 60)
    print(f"  MetaPath 总数: {total}")
    for row in rows:
        print(
            f"  [{row['level']}] n={row['total']}, "
            f"avg={row['avg_pr']:.6f}, min={row['min_pr']:.6f}, max={row['max_pr']:.6f}, "
            f"zero={row['zero_cnt']}, positive={row['positive_cnt']}"
        )
    print("  --- 按 subgraph ---")
    for row in by_subgraph:
        print(
            f"  [{row['level']}/{row['subgraph']}] n={row['total']}, "
            f"avg={row['avg_pr']:.6f}, zero={row['zero_cnt']}"
        )

    return {
        "total": total,
        "by_level": rows,
        "by_level_subgraph": by_subgraph,
    }


def verify_metapath_max_pagerank_consistency(
    driver, *, database: Optional[str] = None
) -> int:
    """Recompute maxPageRank from graph; raise if any stored value differs."""
    mismatches: List[str] = []
    with _session(driver, database) as session:
        rows = session.run(
            """
            MATCH (mp:MetaPath)
            OPTIONAL MATCH (mp)-[:metaPathRelation]->(e)
            WITH mp, collect(elementId(e)) AS endpoint_ids
            RETURN mp.mp_id AS mp_id,
                   mp.subgraph AS subgraph,
                   mp.maxPageRank AS stored,
                   endpoint_ids
            ORDER BY mp.mp_id
            """
        ).data()
        for row in rows:
            mp_id = row["mp_id"]
            expected = compute_max_pagerank_for_linked_entities(
                session,
                row["endpoint_ids"],
                row["subgraph"],
                mp_id=mp_id,
            )
            stored = row["stored"]
            if stored is None:
                mismatches.append(f"{mp_id}: maxPageRank 为 NULL，期望 {expected}")
                continue
            if float(stored) != float(expected):
                mismatches.append(
                    f"{mp_id}: 存储={stored}，重算={expected}"
                )
    if mismatches:
        sample = mismatches[:10]
        raise RuntimeError(
            f"maxPageRank 一致性校验失败 {len(mismatches)} 条:\n"
            + "\n".join(f"  - {m}" for m in sample)
            + (
                f"\n  ... 另有 {len(mismatches) - len(sample)} 条"
                if len(mismatches) > 10
                else ""
            )
        )
    print(f"  ✅ maxPageRank 一致性校验通过（{len(rows)} 条）")
    return len(rows)


def refresh_and_verify_metapath_max_pagerank(
    driver,
    pagerank_prop: Optional[Dict[str, str]] = None,
    *,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """Refresh maxPageRank from E-segment properties, then print stats (strict)."""
    refresh_info = refresh_metapath_max_pagerank(
        driver, pagerank_prop=pagerank_prop, database=database
    )
    stats = report_metapath_max_pagerank_stats(driver, database=database)
    consistency = verify_metapath_max_pagerank_consistency(driver, database=database)
    print("✅ maxPageRank 刷新、统计与一致性验收通过")
    return {
        "refresh": refresh_info,
        "stats": stats,
        "consistency_checked": consistency,
    }


def verify_metapath_path_level(
    driver,
    *,
    require_mid: bool = True,
    database: Optional[str] = None,
    allow_orphan_mid: bool = True,
    max_orphan_mid_ratio: Optional[float] = None,
) -> Dict[str, Any]:
    """Accept MetaPath path_level / hierarchy invariants.

    Hard fails (always): missing path_level, illegal hasDetailPath direction,
    low→hasDetailPath out-edges, missing mid when require_mid.

    Orphan mid (mid without hasDetailPath→low):
    - default allow_orphan_mid=True → warn only (pipeline / incomplete Low).
    - allow_orphan_mid=False → hard fail (strict notebook acceptance).
    - optionally fail if orphan ratio exceeds max_orphan_mid_ratio (0..1).
      None or >=1.0 means no ratio cap when orphans are allowed.
    """
    with _session(driver, database) as session:
        missing_level = session.run(
            """
            MATCH (mp:MetaPath)
            WHERE mp.path_level IS NULL OR NOT mp.path_level IN ['low', 'mid']
            RETURN count(mp) AS c
            """
        ).single()["c"]

        levels = session.run(
            """
            MATCH (mp:MetaPath)
            RETURN mp.path_level AS level, mp.subgraph AS sg, count(*) AS c
            ORDER BY sg, level
            """
        ).data()

        bad_edges = session.run(
            """
            MATCH (a:MetaPath)-[:hasDetailPath]->(b:MetaPath)
            WHERE a.path_level <> 'mid' OR b.path_level <> 'low'
            RETURN count(*) AS c
            """
        ).single()["c"]

        low_to_mid = session.run(
            """
            MATCH (a:MetaPath {path_level:'low'})-[:hasDetailPath]->()
            RETURN count(*) AS c
            """
        ).single()["c"]

        orphan_mid = session.run(
            """
            MATCH (m:MetaPath {path_level: 'mid'})
            WHERE NOT (m)-[:hasDetailPath]->(:MetaPath {path_level: 'low'})
            RETURN m.mp_id AS mp_id
            """
        ).data()

        mid_total = session.run(
            "MATCH (m:MetaPath {path_level: 'mid'}) RETURN count(m) AS c"
        ).single()["c"]

        detail_count = session.run(
            """
            MATCH (:MetaPath {path_level:'mid'})-[hd:hasDetailPath]->(:MetaPath {path_level:'low'})
            RETURN count(hd) AS c
            """
        ).single()["c"]

    print("=" * 60)
    print("MetaPath path_level 验收")
    print("=" * 60)
    for row in levels:
        print(f"  {row['sg']} / {row['level']}: {row['c']}")
    print(f"  hasDetailPath 边数: {detail_count}")
    orphan_n = len(orphan_mid)
    orphan_ratio = (orphan_n / mid_total) if mid_total else 0.0
    if orphan_n:
        print(
            f"  orphan mid: {orphan_n}/{mid_total} "
            f"(ratio={orphan_ratio:.2f}, allow={allow_orphan_mid})"
        )

    problems: List[str] = []
    warnings: List[str] = []
    if missing_level:
        problems.append(f"{missing_level} 个 MetaPath 缺少合法 path_level")
    if bad_edges:
        problems.append(f"{bad_edges} 条非法 hasDetailPath（非 mid->low）")
    if low_to_mid:
        problems.append(f"{low_to_mid} 条 low 错误地 hasDetailPath 出边")
    if require_mid and not any(r["level"] == "mid" for r in levels):
        problems.append("无 mid MetaPath（F4 未执行或失败）")
    if orphan_mid:
        ids = [r["mp_id"] for r in orphan_mid[:5]]
        orphan_msg = (
            f"{orphan_n} 个 mid 无 hasDetailPath 子路径（示例: {ids}）"
        )
        ratio_cap = max_orphan_mid_ratio
        if ratio_cap is not None:
            try:
                ratio_cap = float(ratio_cap)
            except (TypeError, ValueError):
                ratio_cap = None
        over_ratio = (
            ratio_cap is not None
            and ratio_cap < 1.0
            and orphan_ratio > ratio_cap + 1e-12
        )
        if not allow_orphan_mid or over_ratio:
            if over_ratio and allow_orphan_mid:
                problems.append(
                    f"{orphan_msg}；orphan ratio {orphan_ratio:.2f} "
                    f"> max_orphan_mid_ratio={ratio_cap}"
                )
            else:
                problems.append(orphan_msg)
        else:
            warnings.append(orphan_msg)
            print(f"  ⚠ {orphan_msg}（lenient：不阻断）")

    if problems:
        raise RuntimeError("MetaPath 验收失败:\n  - " + "\n  - ".join(problems))

    print("✅ path_level 与层级边验收通过")
    return {
        "levels": levels,
        "detail_edges": detail_count,
        "orphan_mid_count": orphan_n,
        "orphan_mid_ratio": orphan_ratio,
        "warnings": warnings,
        "plan_part_stats": None,
    }
