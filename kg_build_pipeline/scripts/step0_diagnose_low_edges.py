"""Step 0: Compare low_ll/low_repair log OK vs Neo4j edge counts for one parent."""
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

LOG_PATH = ROOT / "logs" / "build_20260831_092557.log"
FILENAME = "doc_04_松江区消费环节大米重金属污染状况及安全评价_石春红.md"
PARENT_NAME = "Dietary intake and health risk assessment"

OK_RE = re.compile(
    r"\[(?P<phase>low_ll|low_repair|low_ml)\]\s+"
    r"(?P<fn>[^\|]+)\s*\|\s*(?:parent=(?P<parent>[^\|]+)\s*\|\s*)?"
    r"(?P<status>OK|FAIL|skip)\s*\|\s*"
    r"(?P<src>[\w]+)\s*-\[(?P<rel>[\w]+)\]->\s*(?P<tgt>[\w]+)"
)


def parse_log_ok_triples(log_path: Path, parent: str) -> dict[str, list[tuple[str, str, str]]]:
    """Return phase -> list of (src_label, rel, tgt_label) logged as OK for parent."""
    by_phase: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    if not log_path.is_file():
        return by_phase
    current_parent: str | None = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "| parent=" in line:
            m_parent = re.search(r"\| parent=([^|]+) \|", line)
            if m_parent:
                current_parent = m_parent.group(1).strip()
        m = OK_RE.search(line)
        if not m or m.group("status") != "OK":
            continue
        phase = m.group("phase")
        fn = m.group("fn").strip()
        if fn and FILENAME not in fn:
            continue
        logged_parent = (m.group("parent") or "").strip()
        effective_parent = logged_parent or current_parent
        if effective_parent != parent:
            continue
        by_phase[phase].append((m.group("src"), m.group("rel"), m.group("tgt")))
    return by_phase


def count_rel_type(session, rel_type: str) -> int:
    row = session.run(
        f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c"
    ).single()
    return int(row["c"]) if row else 0


def count_pattern_global(session, src: str, rel: str, tgt: str) -> int:
    row = session.run(
        f"""
        MATCH (s:{src})-[r:{rel}]->(o:{tgt})
        RETURN count(r) AS c
        """
    ).single()
    return int(row["c"]) if row else 0


def count_pattern_parent_scope(
    session, parent_eid: str, src: str, rel: str, tgt: str
) -> int:
    """Edges where source or target is under parent scope (or is parent)."""
    row = session.run(
        f"""
        MATCH (p) WHERE elementId(p) = $pid
        MATCH (s:{src})-[r:{rel}]->(o:{tgt})
        WHERE elementId(s) = $pid OR elementId(o) = $pid
           OR s.whu_parent_scope_id = $pid OR o.whu_parent_scope_id = $pid
        RETURN count(r) AS c
        """,
        pid=parent_eid,
    ).single()
    return int(row["c"]) if row else 0


def find_parent_nodes(session, name: str, filename: str) -> list[dict]:
    rows = session.run(
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
    return rows


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


def main() -> None:
    cfg = PipelineConfig.load()
    by_phase = parse_log_ok_triples(LOG_PATH, PARENT_NAME)

    print("=" * 72)
    print("Step 0 Diagnosis: Log OK vs Neo4j")
    print("=" * 72)
    print(f"Log file:   {LOG_PATH.name}")
    print(f"Document:   {FILENAME}")
    print(f"Parent:     {PARENT_NAME}")
    print()

    for phase, triples in sorted(by_phase.items()):
        print(f"Log [{phase}] OK count: {len(triples)}")
    print()

    driver = GraphDatabase.driver(
        cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password)
    )
    try:
        with driver.session(database=cfg.neo4j_database) as session:
            parents = find_parent_nodes(session, PARENT_NAME, FILENAME)
            print(f"Neo4j parent nodes matching name: {len(parents)}")
            for p in parents:
                labs = [l for l in p["labels"] if not str(l).startswith("__")]
                print(f"  eid={p['eid']} labels={labs} source_doc={p.get('source_doc')}")
            print()

            if not parents:
                print("ERROR: No parent node found in Neo4j.")
                sys.exit(1)

            # Prefer Computational_Experiment if multiple
            parent_eid = parents[0]["eid"]
            for p in parents:
                labs = p.get("labels") or []
                if "whu_Computational_Experiment" in labs:
                    parent_eid = p["eid"]
                    break

            print(f"Using parent elementId: {parent_eid}")
            scoped = count_scoped_entities(session, parent_eid)
            print(f"Scoped entities (parent + whu_parent_scope_id): {sum(scoped.values())} nodes")
            key_labels = [
                "whu_ResearchStep", "whu_Goal", "whu_TargetVariable",
                "whu_DataSet", "mp_Method", "iao_DataItem",
            ]
            for lab in key_labels:
                if lab in scoped:
                    print(f"  {lab}: {scoped[lab]}")
            print()

            # Unique relation types from low_ll OK
            low_ll_triples = by_phase.get("low_ll", [])
            rel_types = sorted({t[1] for t in low_ll_triples})

            print("Relation type counts (global DB) for low_ll OK types:")
            print(f"{'relation_type':<28} {'global':>8}")
            print("-" * 40)
            for rel in rel_types:
                print(f"{rel:<28} {count_rel_type(session, rel):>8}")
            print()

            print("Per-pattern comparison (low_ll log OK vs Neo4j):")
            print(
                f"{'pattern':<55} {'log':>4} {'glob':>6} {'scope':>6} {'match':>6}"
            )
            print("-" * 82)

            pattern_counts: dict[tuple[str, str, str], int] = defaultdict(int)
            for t in low_ll_triples:
                pattern_counts[t] += 1

            mismatches = 0
            matches = 0
            for (src, rel, tgt), log_n in sorted(pattern_counts.items()):
                pat = f"{src}-[{rel}]->{tgt}"
                glob = count_pattern_global(session, src, rel, tgt)
                scope = count_pattern_parent_scope(session, parent_eid, src, rel, tgt)
                ok = glob >= log_n or scope >= 1
                mark = "YES" if ok else "NO"
                if not ok:
                    mismatches += 1
                else:
                    matches += 1
                print(f"{pat:<55} {log_n:>4} {glob:>6} {scope:>6} {mark:>6}")

            print("-" * 82)
            print(f"low_ll patterns: {len(pattern_counts)} unique, {len(low_ll_triples)} log OK lines")
            print(f"  verified (glob>=1 or scope>=1): {matches}")
            print(f"  NOT in DB (glob=0 AND scope=0): {mismatches}")
            print()

            # low_repair comparison
            repair_triples = by_phase.get("low_repair", [])
            if repair_triples:
                print("low_repair OK vs Neo4j:")
                repair_patterns: dict[tuple[str, str, str], int] = defaultdict(int)
                for t in repair_triples:
                    repair_patterns[t] += 1
                for (src, rel, tgt), log_n in sorted(repair_patterns.items()):
                    pat = f"{src}-[{rel}]->{tgt}"
                    glob = count_pattern_global(session, src, rel, tgt)
                    scope = count_pattern_parent_scope(session, parent_eid, src, rel, tgt)
                    mark = "YES" if glob >= 1 or scope >= 1 else "NO"
                    print(f"  {pat:<50} log={log_n} glob={glob} scope={scope} {mark}")

            print()
            print("Summary JSON:")
            summary = {
                "parent_name": PARENT_NAME,
                "parent_eid": parent_eid,
                "low_ll_log_ok": len(low_ll_triples),
                "low_ll_unique_patterns": len(pattern_counts),
                "low_ll_mismatch_patterns": mismatches,
                "low_ll_match_patterns": matches,
                "scoped_entity_labels": scoped,
                "global_rel_counts": {r: count_rel_type(session, r) for r in rel_types},
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
