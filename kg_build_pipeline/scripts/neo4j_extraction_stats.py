"""Neo4j extraction stats: global rel counts + per-parent log vs DB edge table."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from neo4j import GraphDatabase

from kg_build_pipeline.src.config import PipelineConfig

LOG_PATH = ROOT / "logs" / "build_20260831_110627.log"
FILENAME = "doc_04_松江区消费环节大米重金属污染状况及安全评价_石春红.md"

# Representative parents for deep comparison
PARENTS = [
    "大米中重金属暴露评估",
    "Dietary intake and health risk assessment",
    "大米重金属含量测定",
]

EDGE_RE = re.compile(
    r"\[(?P<phase>low_ll|low_repair|low_ml)\]\s+"
    r"(?P<fn>[^\|]+)\s*\|\s*(?:parent=(?P<parent>[^\|]+)\s*\|\s*)?"
    r"(?P<status>OK|NO_EDGE|FAIL|skip)\s*\|\s*"
    r"(?P<src>[\w]+)\s*-\[(?P<rel>[\w]+)\]->\s*(?P<tgt>[\w]+)"
)

LOW_REL_TYPES = [
    "whu_declareUsed", "whu_declaredUsed", "whu_declaredInput", "whu_declaredOutput",
    "whu_hasGoal", "whu_hasTarget", "iao_is_about", "p_plan_isStepOfPlan",
    "p_plan_isPrecededBy", "p_plan_hasInputVar", "p_plan_hasOutputVar",
    "prov_atLocation", "whu_hasContext", "whu_fellow", "mp_supports",
    "mp_challenges", "cito_cites", "p_plan_correspondsToStep",
]

SCHEMA_REL_FILE = ROOT.parent / "output" / "relation.json"


def parse_log_edges(log_path: Path, parent: str) -> dict[str, list[tuple[str, str, str, str]]]:
    """phase -> list of (status, src, rel, tgt)."""
    by_phase: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    current_parent: str | None = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "| parent=" in line:
            m_parent = re.search(r"\| parent=([^|]+) \|", line)
            if m_parent:
                current_parent = m_parent.group(1).strip()
        m = EDGE_RE.search(line)
        if not m:
            continue
        fn = m.group("fn").strip()
        if fn and FILENAME not in fn:
            continue
        logged_parent = (m.group("parent") or "").strip()
        effective_parent = logged_parent or current_parent
        if effective_parent != parent:
            continue
        by_phase[m.group("phase")].append(
            (m.group("status"), m.group("src"), m.group("rel"), m.group("tgt"))
        )
    return by_phase


def count_rel_type(session, rel_type: str) -> int:
    try:
        row = session.run(
            f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) AS c"
        ).single()
        return int(row["c"]) if row else 0
    except Exception:
        return -1


def count_pattern_global(session, src: str, rel: str, tgt: str) -> int:
    row = session.run(
        f"MATCH (s:`{src}`)-[r:`{rel}`]->(o:`{tgt}`) RETURN count(r) AS c"
    ).single()
    return int(row["c"]) if row else 0


def count_pattern_parent_scope(session, parent_eid: str, src: str, rel: str, tgt: str) -> int:
    row = session.run(
        f"""
        MATCH (p) WHERE elementId(p) = $pid
        MATCH (s:`{src}`)-[r:`{rel}`]->(o:`{tgt}`)
        WHERE elementId(s) = $pid OR elementId(o) = $pid
           OR s.whu_parent_scope_id = $pid OR o.whu_parent_scope_id = $pid
        RETURN count(r) AS c
        """,
        pid=parent_eid,
    ).single()
    return int(row["c"]) if row else 0


def find_parent_nodes(session, name: str, filename: str) -> list[dict]:
    return session.run(
        """
        MATCH (n)
        WHERE n.WHU_HASNAME = $name
          AND (
            n.source_doc CONTAINS $doc_key
            OR EXISTS {
              MATCH (c:Chunk)-[:FROM_CHUNK]-(n)
              WHERE c.filename = $filename
            }
          )
        RETURN elementId(n) AS eid, labels(n) AS labels, n.source_doc AS source_doc
        """,
        name=name,
        doc_key="doc_04",
        filename=filename,
    ).data()


def count_scoped_entities(session, parent_eid: str) -> dict[str, int]:
    rows = session.run(
        """
        MATCH (n)
        WHERE elementId(n) = $pid OR n.whu_parent_scope_id = $pid
        UNWIND labels(n) AS lab
        WITH lab, count(*) AS c
        WHERE NOT lab STARTS WITH '__'
        RETURN lab, c ORDER BY c DESC
        """,
        pid=parent_eid,
    ).data()
    return {r["lab"]: int(r["c"]) for r in rows}


def all_rel_types(session) -> list[tuple[str, int]]:
    rows = session.run(
        """
        MATCH ()-[r]->()
        RETURN type(r) AS t, count(r) AS c
        ORDER BY c DESC
        """
    ).data()
    return [(r["t"], int(r["c"])) for r in rows]


def db_overview(session) -> dict:
    nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    chunks = session.run("MATCH (c:Chunk) RETURN count(c) AS c").single()["c"]
    metapaths = session.run("MATCH (m:MetaPath) RETURN count(m) AS c").single()["c"]
    entity_nodes = session.run(
        """
        MATCH (n)
        WHERE NOT n:Chunk AND NOT n:MetaPath
          AND NOT n:__KGBuilder__ AND NOT n:__Entity__ AND NOT n:__Relationship__
        RETURN count(n) AS c
        """
    ).single()["c"]
    return {
        "total_nodes": int(nodes),
        "total_relationships": int(rels),
        "chunks": int(chunks),
        "metapaths": int(metapaths),
        "entity_nodes": int(entity_nodes),
    }


def label_counts(session) -> dict[str, int]:
    rows = session.run(
        """
        MATCH (n)
        WHERE NOT n:Chunk AND NOT n:MetaPath
          AND NOT n:__KGBuilder__
        UNWIND labels(n) AS lab
        WITH lab, count(DISTINCT n) AS c
        WHERE NOT lab STARTS WITH '__'
        RETURN lab, c ORDER BY c DESC
        """
    ).data()
    return {r["lab"]: int(r["c"]) for r in rows}


def pick_parent_eid(parents: list[dict]) -> str:
    for p in parents:
        labs = p.get("labels") or []
        if "whu_Computational_Experiment" in labs or "whu_BioChemical_Experiment" in labs:
            return p["eid"]
    return parents[0]["eid"]


def print_parent_table(session, parent_name: str) -> None:
    by_phase = parse_log_edges(LOG_PATH, parent_name)
    all_events: list[tuple[str, str, str, str, str]] = []
    for phase, events in sorted(by_phase.items()):
        for status, src, rel, tgt in events:
            all_events.append((phase, status, src, rel, tgt))

    print()
    print("=" * 90)
    print(f"Parent: {parent_name}")
    print("=" * 90)

    parents = find_parent_nodes(session, parent_name, FILENAME)
    if not parents:
        print("  WARNING: no matching parent node in Neo4j")
        print(f"  Log events: {len(all_events)}")
        return

    parent_eid = pick_parent_eid(parents)
    labs = [l for l in (parents[0].get("labels") or []) if not str(l).startswith("__")]
    for p in parents:
        plabs = [l for l in (p.get("labels") or []) if not str(l).startswith("__")]
        print(f"  Neo4j eid={p['eid']} labels={plabs}")
    print(f"  Using eid: {parent_eid}")

    scoped = count_scoped_entities(session, parent_eid)
    print(f"  Scoped nodes: {sum(scoped.values())}")
    for lab in ["whu_ResearchStep", "whu_Goal", "whu_TargetVariable", "whu_DataSet", "mp_Method", "iao_DataItem"]:
        if lab in scoped:
            print(f"    {lab}: {scoped[lab]}")

    # Aggregate patterns across phases
    pattern_log: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for phase, status, src, rel, tgt in all_events:
        pattern_log[(src, rel, tgt)][f"{phase}:{status}"] += 1

    print()
    print(f"  {'pattern':<52} {'log':>4} {'glob':>6} {'scope':>6} {'db':>4}")
    print("  " + "-" * 76)
    ok_in_db = 0
    missing = 0
    for (src, rel, tgt), counts in sorted(pattern_log.items()):
        log_n = sum(counts.values())
        pat = f"{src}-[{rel}]->{tgt}"
        glob = count_pattern_global(session, src, rel, tgt)
        scope = count_pattern_parent_scope(session, parent_eid, src, rel, tgt)
        in_db = "YES" if glob >= 1 or scope >= 1 else "NO"
        if in_db == "YES":
            ok_in_db += 1
        else:
            missing += 1
        status_summary = ",".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {pat:<52} {log_n:>4} {glob:>6} {scope:>6} {in_db:>4}  ({status_summary})")

    print("  " + "-" * 76)
    print(f"  unique patterns: {len(pattern_log)}, in DB: {ok_in_db}, missing: {missing}")
    print(f"  log lines total: {len(all_events)}")


def main() -> None:
    cfg = PipelineConfig.load()
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))

    print("=" * 90)
    print("Neo4j Extraction Stats")
    print("=" * 90)
    print(f"Log:      {LOG_PATH.name}")
    print(f"Database: {cfg.neo4j_database} @ {cfg.neo4j_uri}")
    print()

    try:
        with driver.session(database=cfg.neo4j_database) as session:
            overview = db_overview(session)
            print("--- Database overview ---")
            for k, v in overview.items():
                print(f"  {k}: {v}")
            print()

            print("--- All relationship types (top 40) ---")
            rels = all_rel_types(session)
            print(f"  {'type':<36} {'count':>8}")
            print("  " + "-" * 46)
            for t, c in rels[:40]:
                print(f"  {t:<36} {c:>8}")
            if len(rels) > 40:
                print(f"  ... and {len(rels) - 40} more types")
            print(f"  TOTAL distinct types: {len(rels)}, TOTAL rels: {sum(c for _, c in rels)}")
            print()

            print("--- Low/schema relation types ---")
            print(f"  {'type':<36} {'count':>8}")
            print("  " + "-" * 46)
            schema_rels = []
            if SCHEMA_REL_FILE.is_file():
                schema_rels = [
                    r["label"] for r in json.loads(SCHEMA_REL_FILE.read_text(encoding="utf-8")).get("relations", [])
                ]
            check_types = sorted(set(LOW_REL_TYPES + schema_rels))
            low_counts = {}
            for rt in check_types:
                c = count_rel_type(session, rt)
                if c > 0:
                    low_counts[rt] = c
                    print(f"  {rt:<36} {c:>8}")
            zero_low = [rt for rt in check_types if count_rel_type(session, rt) == 0]
            print(f"  (zero-count schema/low types: {len(zero_low)})")
            print()

            print("--- Entity label counts (top 20) ---")
            labels = label_counts(session)
            for i, (lab, c) in enumerate(sorted(labels.items(), key=lambda x: -x[1])):
                if i >= 20:
                    break
                print(f"  {lab:<36} {c:>6}")
            print()

            for parent in PARENTS:
                print_parent_table(session, parent)

            print()
            print("--- Summary JSON ---")
            summary = {
                "log": LOG_PATH.name,
                "overview": overview,
                "low_rel_counts_nonzero": low_counts,
                "zero_low_rel_types": zero_low,
                "top_labels": dict(sorted(labels.items(), key=lambda x: -x[1])[:15]),
                "all_rel_types_count": len(rels),
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
