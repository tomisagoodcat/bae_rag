"""Neo4j acceptance snapshot for schema migration (read-only by default)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "tomis1cat"
NEO4J_DB = "neo4j"

OLD_STEP_LABELS = [
    "whu_BioChemicalActivityStep",
    "whu_ComputationalActivityStep",
    "whu_Specimen_Collection_Activity",
    "whu_Specimen_Processing_Activity",
]
NEW_STEP_LABELS = [
    "whu_BioChemicalStep",
    "whu_ComputationalStep",
    "whu_Specimen_CollectionStep",
    "whu_Specimen_ProcessingStep",
]
NEW_REL_TYPES = [
    "p_plan_isStepOfPlan",
    "p_plan_hasInputVar",
    "p_plan_hasOutputVar",
    "whu_hasContext",
    "whu_atLocation",
]


def run_snapshot(clear: bool = False) -> int:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DB) as session:
            if clear:
                session.run("MATCH (n) DETACH DELETE n")
                print("Cleared all nodes and relationships.")

            total_n = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            total_r = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            print(f"Total nodes: {total_n} | relationships: {total_r}")

            print("\nTop labels:")
            for row in session.run(
                "MATCH (n) RETURN labels(n)[0] AS l, count(*) AS c ORDER BY c DESC LIMIT 25"
            ):
                print(f"  {row['l']}: {row['c']}")

            print("\nOld vs new Step labels:")
            for label in OLD_STEP_LABELS + NEW_STEP_LABELS:
                c = session.run(
                    "MATCH (n) WHERE $l IN labels(n) RETURN count(n) AS c", l=label
                ).single()["c"]
                if c:
                    print(f"  {label}: {c}")

            print("\nNew P-Plan / context relations:")
            for rel in NEW_REL_TYPES:
                c = session.run(
                    "MATCH ()-[r]->() WHERE type(r) = $t RETURN count(r) AS c", t=rel
                ).single()["c"]
                if c:
                    print(f"  {rel}: {c}")

            deprecated = session.run(
                """
                MATCH ()-[r]->()
                WHERE type(r) IN ['whu_hasActivity','prov_used','prov_generated',
                                   'prov_wasInformedBy','prov_atLocation']
                RETURN type(r) AS t, count(r) AS c ORDER BY c DESC
                """
            ).data()
            if deprecated:
                print("\nDeprecated relation counts (should trend to 0 after rebuild):")
                for row in deprecated:
                    print(f"  {row['t']}: {row['c']}")

        return 0
    except Exception as e:
        print(f"Neo4j error: {e}", file=sys.stderr)
        return 1
    finally:
        driver.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clear", action="store_true", help="DETACH DELETE all graph data")
    args = p.parse_args()
    if args.clear:
        confirm = input("Type YES to clear Neo4j: ")
        if confirm.strip() != "YES":
            print("Aborted.")
            return 1
    sys.exit(run_snapshot(clear=args.clear))


if __name__ == "__main__":
    main()
