"""Neo4j-only smoke for G_sub operators (no torch/LLM)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase

from utilities.dialogue_routing import N_l, build_gsub_mp_ids
from utilities.test_evaluation import load_test_cases, resolve_questions_csv

load_dotenv(ROOT.parent / "PaperExtract2" / "PaperExtract2" / ".env")

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)

with driver.session() as s:
    row = s.run(
        """
        MATCH (mp:MetaPath {path_level:'mid', subgraph:'MPU'})
        RETURN mp.mp_id AS mp_id LIMIT 1
        """
    ).single()
    mid_id = row["mp_id"]
    print(f"anchor mid: {mid_id}")

low_ids = N_l(driver, [mid_id], "low")
print(f"drill_down N_l: {len(low_ids)} low paths (sample: {low_ids[:3]})")

gsub = build_gsub_mp_ids(
    driver,
    kappa="drill_down",
    candidate_mp_ids=[mid_id],
    active_modules=["MPU"],
    path_level="low",
)
print(f"G_sub drill_down: {len(gsub)} ids")

cases = load_test_cases(resolve_questions_csv())
print(f"questions.csv: {len(cases)} cases, first expected={cases[0]['expected']}")

driver.close()
print("✅ Neo4j G_sub smoke OK")
