"""
EBM+EEM (MPU=0) Pilot export for Label Studio process testing (read-only Neo4j).

Filter:
  EBM_num > 0 AND EEM_num > 0 AND MPU_num = 0

Outputs under output/ebm_pilot/:
  - ebm_eem_pilot_candidates.csv
  - ebm_eem_pilot_sample.csv
  - ebm_eem_labelstudio_tasks.json
  - ebm_eem_pilot_report.md

random_seed = 20260813
Does NOT modify Neo4j. No Entity/Relation/MetaPath pre-annotations.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "ebm_pilot"

DEFAULT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_USER = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
DEFAULT_PASSWORD = os.environ.get("NEO4J_PASSWORD", "tomis1cat")
DEFAULT_DB = os.environ.get("NEO4J_DATABASE", "neo4j")

RANDOM_SEED = 20260813
SAMPLE_N = 12

REQUIRED_CHUNK_KEYS = {
    "text",
    "source_doc",
    "from_section",
    "index",
    "EBM_num",
    "EEM_num",
    "MPU_num",
}

FIELDS = [
    "chunk_id",
    "document_id",
    "section",
    "text",
    "chunk_index",
    "EBM_num",
    "EEM_num",
    "MPU_num",
]

FETCH_CYPHER = """
MATCH (c:Chunk)
RETURN
  elementId(c) AS chunk_id,
  c.source_doc AS document_id,
  c.from_section AS section,
  c.text AS text,
  c.index AS chunk_index,
  c.EBM_num AS EBM_num,
  c.EEM_num AS EEM_num,
  c.MPU_num AS MPU_num
ORDER BY document_id, chunk_index, chunk_id
"""


def _neo4j():
    from neo4j import GraphDatabase

    return GraphDatabase


def schema_probe(session) -> List[str]:
    keys = [
        r["k"]
        for r in session.run(
            "MATCH (c:Chunk) UNWIND keys(c) AS k RETURN DISTINCT k AS k ORDER BY k"
        )
    ]
    missing = sorted(REQUIRED_CHUNK_KEYS - set(keys))
    if missing:
        raise RuntimeError(f"Chunk missing required properties: {missing}; have={keys}")
    return keys


def fetch_chunks(session) -> List[Dict[str, Any]]:
    rows = []
    for r in session.run(FETCH_CYPHER):
        d = dict(r)
        for k in ("EBM_num", "EEM_num", "MPU_num", "chunk_index"):
            if d.get(k) is not None:
                d[k] = int(d[k])
        rows.append(d)
    return rows


def is_ebm_eem_mpu0(c: Dict[str, Any]) -> bool:
    """EBM+EEM with MPU absent: EBM_num>0 AND EEM_num>0 AND MPU_num=0."""
    return (
        int(c.get("EBM_num") or 0) > 0
        and int(c.get("EEM_num") or 0) > 0
        and int(c.get("MPU_num") or 0) == 0
    )


def ebm_bucket(ebm: int) -> str:
    if ebm <= 2:
        return "1-2"
    if ebm <= 10:
        return "3-10"
    if ebm <= 30:
        return "11-30"
    return ">30"


def sample_diverse(candidates: List[Dict[str, Any]], n: int, seed: int) -> List[Dict[str, Any]]:
    """Document-diverse + EBM_num level coverage; reproducible."""
    if len(candidates) <= n:
        return list(candidates)

    rng = random.Random(seed)
    by_bucket: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        by_bucket[ebm_bucket(int(c["EBM_num"]))].append(c)
    for b in by_bucket:
        rng.shuffle(by_bucket[b])

    # Round-robin across buckets that still have items, with doc diversity
    bucket_order = ["1-2", "3-10", "11-30", ">30"]
    selected: List[Dict[str, Any]] = []
    doc_counts: Counter = Counter()

    def take_from_bucket(b: str) -> Optional[Dict[str, Any]]:
        pool = by_bucket.get(b) or []
        # remaining not yet selected
        remaining = [
            c
            for c in pool
            if c["chunk_id"] not in {s["chunk_id"] for s in selected}
        ]
        if not remaining:
            return None
        min_doc = min(doc_counts[c.get("document_id") or ""] for c in remaining)
        choice = next(
            c
            for c in remaining
            if doc_counts[c.get("document_id") or ""] == min_doc
        )
        return choice

    # Prefer filling one from each nonempty bucket first, then continue RR
    while len(selected) < n:
        progressed = False
        for b in bucket_order:
            if len(selected) >= n:
                break
            choice = take_from_bucket(b)
            if choice is None:
                continue
            selected.append(choice)
            doc_counts[choice.get("document_id") or ""] += 1
            progressed = True
        if not progressed:
            break

    # If still short (shouldn't if candidates >= n), fill from shuffled all
    if len(selected) < n:
        rest = [c for c in candidates if c["chunk_id"] not in {s["chunk_id"] for s in selected}]
        rng.shuffle(rest)
        while len(selected) < n and rest:
            # diversity among rest
            min_doc = min(doc_counts[c.get("document_id") or ""] for c in rest)
            choice = next(
                c for c in rest if doc_counts[c.get("document_id") or ""] == min_doc
            )
            selected.append(choice)
            doc_counts[choice.get("document_id") or ""] += 1
            rest = [c for c in rest if c["chunk_id"] != choice["chunk_id"]]

    selected.sort(
        key=lambda c: (
            c.get("document_id") or "",
            c.get("chunk_index") if c.get("chunk_index") is not None else -1,
            c["chunk_id"],
        )
    )
    return selected


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def build_report(
    all_chunks: List[Dict[str, Any]],
    ebm_pos: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    sample: List[Dict[str, Any]],
    chunk_keys: List[str],
    used_all: bool,
    csv_ls_ids_match: bool,
) -> str:
    ebm_vals = [int(c["EBM_num"]) for c in candidates]
    eem_vals = [int(c["EEM_num"]) for c in candidates]
    hist = Counter(ebm_vals)
    sample_docs = Counter((c.get("document_id") or "") for c in sample)
    cand_ids = [c["chunk_id"] for c in candidates]
    sample_ids = [c["chunk_id"] for c in sample]
    texts = [c.get("text") or "" for c in candidates]
    empty_text = sum(1 for t in texts if not str(t).strip())
    text_dup = sum(1 for t, n in Counter(texts).items() if t and n > 1)

    bad = [c for c in sample if not is_ebm_eem_mpu0(c)]
    filter_label = "EBM_num > 0 AND EEM_num > 0 AND MPU_num = 0"

    lines = [
        "# EBM+EEM (MPU=0) Pilot report",
        "",
        f"- Generated (UTC): `{datetime.now(timezone.utc).isoformat()}`",
        f"- Script: `utilities/export_ebm_only_pilot.py`",
        f"- random_seed: `{RANDOM_SEED}`",
        f"- Filter: `{filter_label}`",
        "",
        "## Schema probe",
        "",
        f"- Chunk keys: {', '.join(f'`{k}`' for k in chunk_keys)}",
        f"- Required keys present: **yes**",
        "",
        "## Counts",
        "",
        f"- Chunk total: **{len(all_chunks)}**",
        f"- EBM_num > 0: **{len(ebm_pos)}**",
        f"- EBM+EEM (MPU=0) candidates: **{len(candidates)}**",
        f"- Pilot sample size: **{len(sample)}**"
        + (" (all candidates; fewer than 12)" if used_all else ""),
        f"- Distinct documents in sample: **{len(sample_docs)}**",
        "",
        "## Among EBM_num > 0 (context)",
        "",
        f"- EBM only (EEM=0, MPU=0): **{sum(1 for c in ebm_pos if int(c.get('EEM_num') or 0)==0 and int(c.get('MPU_num') or 0)==0)}**",
        f"- EBM+EEM (MPU=0): **{sum(1 for c in ebm_pos if int(c.get('EEM_num') or 0)>0 and int(c.get('MPU_num') or 0)==0)}**",
        f"- EBM+MPU (EEM=0): **{sum(1 for c in ebm_pos if int(c.get('EEM_num') or 0)==0 and int(c.get('MPU_num') or 0)>0)}**",
        f"- EBM+EEM+MPU: **{sum(1 for c in ebm_pos if int(c.get('EEM_num') or 0)>0 and int(c.get('MPU_num') or 0)>0)}**",
        "",
        "## Candidate EBM_num / EEM_num stats",
        "",
    ]
    if ebm_vals:
        lines.extend(
            [
                f"- EBM_num min/max/mean/median: **{min(ebm_vals)}** / **{max(ebm_vals)}** / "
                f"**{statistics.mean(ebm_vals):.2f}** / **{statistics.median(ebm_vals)}**",
                f"- EEM_num min/max/mean/median: **{min(eem_vals)}** / **{max(eem_vals)}** / "
                f"**{statistics.mean(eem_vals):.2f}** / **{statistics.median(eem_vals)}**",
                "",
                "| EBM_num | count |",
                "|--------:|------:|",
            ]
        )
        for k in sorted(hist):
            lines.append(f"| {k} | {hist[k]} |")
    else:
        lines.append("- (no candidates)")

    lines.extend(
        [
            "",
            "## Sample by document",
            "",
            "| document_id | n |",
            "|-------------|--:|",
        ]
    )
    for doc, n in sample_docs.most_common():
        lines.append(f"| `{doc}` | {n} |")

    lines.extend(
        [
            "",
            "## Pilot sample summary",
            "",
            "| chunk_id | document_id | section | EBM_num | EEM_num | MPU_num | text_length |",
            "| -------- | ----------- | ------- | ------: | ------: | ------: | ----------: |",
        ]
    )
    for c in sample:
        text = c.get("text") or ""
        doc = (c.get("document_id") or "").replace("|", "\\|")
        sec = (c.get("section") or "").replace("|", "\\|")
        lines.append(
            f"| `{c['chunk_id']}` | `{doc}` | {sec} | "
            f"{c['EBM_num']} | {c['EEM_num']} | {c['MPU_num']} | {len(text)} |"
        )

    lines.extend(
        [
            "",
            "## QC",
            "",
            f"- Duplicate chunk_id in candidates: **{len(cand_ids) - len(set(cand_ids))}**",
            f"- Duplicate chunk_id in sample: **{len(sample_ids) - len(set(sample_ids))}**",
            f"- Empty text in candidates: **{empty_text}**",
            f"- Exact-duplicate texts in candidates (distinct texts with count>1): **{text_dup}**",
            f"- Sample rows violating EBM+EEM (MPU=0) filter: **{len(bad)}**",
            f"- CSV sample chunk_ids == LS task chunk_ids: **{csv_ls_ids_match}**",
            "",
            "## Confirmations",
            "",
            "1. Neo4j was **not** modified (read-only).",
            f"2. All Pilot samples satisfy `{filter_label}` "
            f"(violations={len(bad)}).",
            "3. Label Studio tasks contain Chunk attributes only — **no** Entity/Relation/MetaPath "
            "pre-annotations.",
            "4. `text` is unchanged from Neo4j `Chunk.text`.",
            "5. Sample CSV and Label Studio JSON use the same ordered `chunk_id` list.",
            f"6. Reproducible via `RANDOM_SEED={RANDOM_SEED}` in "
            "`utilities/export_ebm_only_pilot.py`.",
            "",
            "This EBM+EEM (MPU=0) filter is for Pilot / Label Studio process testing only — "
            "**not** the final Gold Standard sampling policy.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="EBM+EEM (MPU=0) Pilot export")
    p.add_argument("--uri", default=DEFAULT_URI)
    p.add_argument("--user", default=DEFAULT_USER)
    p.add_argument("--password", default=DEFAULT_PASSWORD)
    p.add_argument("--database", default=DEFAULT_DB)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--seed", type=int, default=RANDOM_SEED)
    p.add_argument("--sample-n", type=int, default=SAMPLE_N)
    args = p.parse_args(argv)

    GraphDatabase = _neo4j()
    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        driver.verify_connectivity()
        with driver.session(database=args.database) as session:
            chunk_keys = schema_probe(session)
            print(f"SCHEMA_OK n_keys={len(chunk_keys)}", flush=True)
            all_chunks = fetch_chunks(session)
    finally:
        driver.close()

    ebm_pos = [c for c in all_chunks if int(c.get("EBM_num") or 0) > 0]
    candidates = [c for c in all_chunks if is_ebm_eem_mpu0(c)]
    used_all = len(candidates) <= args.sample_n
    sample = sample_diverse(candidates, args.sample_n, args.seed)

    assert all(is_ebm_eem_mpu0(c) for c in sample), "sample must be EBM+EEM (MPU=0)"

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cand_path = args.out_dir / "ebm_eem_pilot_candidates.csv"
    sample_path = args.out_dir / "ebm_eem_pilot_sample.csv"
    ls_path = args.out_dir / "ebm_eem_labelstudio_tasks.json"
    report_path = args.out_dir / "ebm_eem_pilot_report.md"

    write_csv(cand_path, candidates, FIELDS)
    write_csv(sample_path, sample, FIELDS)

    tasks = [
        {
            "data": {
                "chunk_id": c["chunk_id"],
                "document_id": c.get("document_id") or "",
                "section": c.get("section") or "",
                "chunk_index": c.get("chunk_index"),
                "EBM_num": c["EBM_num"],
                "EEM_num": c["EEM_num"],
                "MPU_num": c["MPU_num"],
                "text": c.get("text") or "",
            }
        }
        for c in sample
    ]
    ls_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    ls_ids = [t["data"]["chunk_id"] for t in tasks]
    sample_ids = [c["chunk_id"] for c in sample]
    report = build_report(
        all_chunks,
        ebm_pos,
        candidates,
        sample,
        chunk_keys,
        used_all,
        csv_ls_ids_match=(sample_ids == ls_ids),
    )
    report_path.write_text(report, encoding="utf-8")

    print(
        f"total={len(all_chunks)} ebm_pos={len(ebm_pos)} "
        f"ebm_eem_mpu0={len(candidates)} sample={len(sample)} used_all={used_all}"
    )
    print(report)
    print(f"Wrote {cand_path.resolve()}")
    print(f"Wrote {sample_path.resolve()}")
    print(f"Wrote {ls_path.resolve()}")
    print(f"Wrote {report_path.resolve()}")

    print("\n=== FINAL CHECKS ===")
    print("1. Neo4j unmodified: YES (read-only)")
    print(f"2. All samples EBM+EEM (MPU=0): {all(is_ebm_eem_mpu0(c) for c in sample)}")
    print("3. No Entity/Relation/MetaPath in LS tasks: YES")
    print("4. text from Neo4j raw: YES")
    print(f"5. CSV↔JSON chunk_id 1:1 same order: {sample_ids == ls_ids}")
    print(f"6. seed={args.seed} in utilities/export_ebm_only_pilot.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
