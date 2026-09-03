"""Unit tests for entity_normalize (pure Python; no Neo4j required)."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from kg_build_pipeline.src.entity_normalize.constants import (
    EXCLUDED_LABELS,
    EXTERNAL_CONCEPT_LABELS,
    HARD_MERGE_LABELS,
    SPECIMEN_NO_DIRECT_ONTOLOGY,
)
from kg_build_pipeline.src.entity_normalize.hard_merge import (
    merge_keeper_and_sources,
    unique_merge_nodes,
)
from kg_build_pipeline.src.entity_normalize.llm_align import LlmAligner, resolve_external_hit
from kg_build_pipeline.src.entity_normalize.ontology_lookup import OntologyIndex
from kg_build_pipeline.src.entity_normalize.text_keys import (
    extract_lookup_keys,
    hard_merge_key,
    normalize_reagent_for_lookup,
    ontology_lookup_query,
)


def _make_index(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE ontology_terms (
            external_id TEXT PRIMARY KEY,
            external_uri TEXT NOT NULL,
            pref_label TEXT NOT NULL,
            source_ontology TEXT NOT NULL
        );
        CREATE TABLE ontology_labels (
            label_text TEXT NOT NULL,
            external_id TEXT NOT NULL,
            label_kind TEXT NOT NULL,
            PRIMARY KEY (label_text, external_id)
        );
        """
    )
    conn.execute(
        "INSERT INTO ontology_terms VALUES (?,?,?,?)",
        ("CHEBI:16136", "http://purl.obolibrary.org/obo/CHEBI_16136", "mercury atom", "chebi"),
    )
    conn.execute(
        "INSERT INTO ontology_labels VALUES (?,?,?)",
        ("Hg", "CHEBI:16136", "synonym"),
    )
    conn.execute(
        "INSERT INTO ontology_labels VALUES (?,?,?)",
        ("mercury atom", "CHEBI:16136", "exact"),
    )
    conn.execute(
        "INSERT INTO ontology_terms VALUES (?,?,?,?)",
        ("ENVO:00001998", "http://purl.obolibrary.org/obo/ENVO_00001998", "soil", "envo"),
    )
    conn.execute(
        "INSERT INTO ontology_labels VALUES (?,?,?)",
        ("soil", "ENVO:00001998", "exact"),
    )
    conn.commit()
    conn.close()


def test_unique_merge_nodes_drops_duplicate_ids() -> None:
    nodes = [
        {"id": "a", "original_text": "Hg"},
        {"id": "a", "original_text": "Hg"},
        {"id": "b", "original_text": "Hg"},
    ]
    uniq = unique_merge_nodes(nodes)
    assert [n["id"] for n in uniq] == ["a", "b"]
    assert unique_merge_nodes([{"id": "a"}, {"id": "a"}]) == [{"id": "a"}]


def test_merge_keeper_skips_single_node_fanout() -> None:
    keeper, sources = merge_keeper_and_sources(
        [{"id": "hg1", "original_text": "Hg"}, {"id": "hg1", "original_text": "Hg"}]
    )
    assert keeper is None
    assert sources == []
    keeper, sources = merge_keeper_and_sources(
        [{"id": "a"}, {"id": "b"}, {"id": "a"}]
    )
    assert keeper is not None
    assert keeper["id"] == "a"
    assert [s["id"] for s in sources] == ["b"]


def test_hard_merge_key_requires_nonempty_original_text() -> None:
    assert hard_merge_key("whu_ChemicalEntity", "doc_04", "Hg") == (
        "whu_ChemicalEntity",
        "doc_04",
        "Hg",
    )
    assert hard_merge_key("whu_ChemicalEntity", "doc_04", "  ") is None
    assert hard_merge_key("whu_ChemicalEntity", "", "Hg") is None


def test_reagent_strip_concentration() -> None:
    assert normalize_reagent_for_lookup("65% suprapure HNO3") == "HNO3"
    assert ontology_lookup_query("whu_Reagent", "65% suprapure HNO3") == "HNO3"


def test_ontology_exact_lookup_case_sensitive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        hit = idx.exact_lookup("Hg")
        assert hit is not None
        assert hit.external_id == "CHEBI:16136"
        assert idx.exact_lookup("hg") is None
        idx.close()


def test_ontology_no_fuzzy_match() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        assert idx.exact_lookup("mercur") is None
        idx.close()


def test_ontology_element_atom_tiebreak() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE ontology_terms (
                external_id TEXT PRIMARY KEY,
                external_uri TEXT NOT NULL,
                pref_label TEXT NOT NULL,
                source_ontology TEXT NOT NULL
            );
            CREATE TABLE ontology_labels (
                label_text TEXT NOT NULL,
                external_id TEXT NOT NULL,
                label_kind TEXT NOT NULL,
                PRIMARY KEY (label_text, external_id)
            );
            """
        )
        conn.execute(
            "INSERT INTO ontology_terms VALUES (?,?,?,?)",
            ("CHEBI:25195", "http://purl.obolibrary.org/obo/CHEBI_25195", "mercury atom", "chebi"),
        )
        conn.execute(
            "INSERT INTO ontology_terms VALUES (?,?,?,?)",
            ("CHEBI:16170", "http://purl.obolibrary.org/obo/CHEBI_16170", "mercury(0)", "chebi"),
        )
        conn.execute(
            "INSERT INTO ontology_labels VALUES (?,?,?)",
            ("Hg", "CHEBI:25195", "related"),
        )
        conn.execute(
            "INSERT INTO ontology_labels VALUES (?,?,?)",
            ("Hg", "CHEBI:16170", "related"),
        )
        conn.commit()
        conn.close()
        idx = OntologyIndex(db, "chebi")
        hit = idx.exact_lookup("Hg")
        assert hit is not None
        assert hit.external_id == "CHEBI:25195"
        idx.close()


def test_ontology_ambiguous_formula_misses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE ontology_terms (
                external_id TEXT PRIMARY KEY,
                external_uri TEXT NOT NULL,
                pref_label TEXT NOT NULL,
                source_ontology TEXT NOT NULL
            );
            CREATE TABLE ontology_labels (
                label_text TEXT NOT NULL,
                external_id TEXT NOT NULL,
                label_kind TEXT NOT NULL,
                PRIMARY KEY (label_text, external_id)
            );
            """
        )
        conn.execute(
            "INSERT INTO ontology_terms VALUES (?,?,?,?)",
            ("CHEBI:1", "http://example.org/1", "glucose", "chebi"),
        )
        conn.execute(
            "INSERT INTO ontology_terms VALUES (?,?,?,?)",
            ("CHEBI:2", "http://example.org/2", "fructose", "chebi"),
        )
        conn.execute(
            "INSERT INTO ontology_labels VALUES (?,?,?)",
            ("C6H12O6", "CHEBI:1", "formula"),
        )
        conn.execute(
            "INSERT INTO ontology_labels VALUES (?,?,?)",
            ("C6H12O6", "CHEBI:2", "formula"),
        )
        conn.commit()
        conn.close()
        idx = OntologyIndex(db, "chebi")
        assert idx.exact_lookup("C6H12O6") is None
        idx.close()


def test_ontology_related_and_formula_unique_hit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE ontology_terms (
                external_id TEXT PRIMARY KEY,
                external_uri TEXT NOT NULL,
                pref_label TEXT NOT NULL,
                source_ontology TEXT NOT NULL
            );
            CREATE TABLE ontology_labels (
                label_text TEXT NOT NULL,
                external_id TEXT NOT NULL,
                label_kind TEXT NOT NULL,
                PRIMARY KEY (label_text, external_id)
            );
            """
        )
        conn.execute(
            "INSERT INTO ontology_terms VALUES (?,?,?,?)",
            ("CHEBI:25195", "http://purl.obolibrary.org/obo/CHEBI_25195", "mercury atom", "chebi"),
        )
        conn.execute(
            "INSERT INTO ontology_labels VALUES (?,?,?)",
            ("Hg", "CHEBI:25195", "related"),
        )
        conn.commit()
        conn.close()
        idx = OntologyIndex(db, "chebi")
        hit = idx.exact_lookup("Hg")
        assert hit is not None
        assert hit.external_id == "CHEBI:25195"
        idx.close()


def test_extract_lookup_keys_symbol_from_modifier() -> None:
    keys = extract_lookup_keys("总 Hg")
    assert "Hg" in keys
    keys_as = extract_lookup_keys("无机 As")
    assert "As" in keys_as
    assert "HNO3" in extract_lookup_keys("65% suprapure HNO3")


def test_harvest_and_lookup_by_id() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        cands = idx.harvest_candidates(extract_lookup_keys("总 Hg"))
        assert any(c.external_id == "CHEBI:16136" for c in cands)
        by_id = idx.lookup_by_id("CHEBI:16136")
        assert by_id is not None
        assert by_id.pref_label == "mercury atom"
        assert idx.lookup_by_id("CHEBI:99999") is None
        idx.close()


def test_resolve_exact_wins_without_llm() -> None:
    calls: list[str] = []

    def complete(prompt: str):
        calls.append(prompt)
        return {"keys": ["should-not-run"], "external_id": "CHEBI:16136"}

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        result = resolve_external_hit(
            idx,
            label="whu_ChemicalEntity",
            original_text="Hg",
            query="Hg",
            aligner=LlmAligner(complete_json=complete),
            llm_labels={"whu_ChemicalEntity"},
        )
        assert result is not None
        assert result.match_type == "exact"
        assert result.method == "lexical"
        assert result.hit.external_id == "CHEBI:16136"
        assert calls == []
        idx.close()


def test_resolve_llm_from_symbol_candidates() -> None:
    def complete(prompt: str):
        if "candidates:" in prompt:
            return {"external_id": "CHEBI:16136"}
        return {"keys": []}

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        result = resolve_external_hit(
            idx,
            label="whu_ChemicalEntity",
            original_text="总 Hg",
            query="总 Hg",
            aligner=LlmAligner(complete_json=complete),
            llm_labels={"whu_ChemicalEntity"},
        )
        assert result is not None
        assert result.match_type == "llm"
        assert result.method == "llm"
        assert result.hit.external_id == "CHEBI:16136"
        idx.close()


def test_resolve_empty_candidates_skip() -> None:
    def complete(prompt: str):
        return {"keys": [], "external_id": "CHEBI:16136"}

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        result = resolve_external_hit(
            idx,
            label="whu_ChemicalEntity",
            original_text="foobar",
            query="foobar",
            aligner=LlmAligner(complete_json=complete),
            llm_labels={"whu_ChemicalEntity"},
        )
        assert result is None
        idx.close()


def test_resolve_id_not_in_candidates_skip() -> None:
    def complete(prompt: str):
        if "candidates:" in prompt:
            return {"external_id": "CHEBI:99999"}
        return {"keys": []}

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        result = resolve_external_hit(
            idx,
            label="whu_ChemicalEntity",
            original_text="总 Hg",
            query="总 Hg",
            aligner=LlmAligner(complete_json=complete),
            llm_labels={"whu_ChemicalEntity"},
        )
        assert result is None
        idx.close()


def test_resolve_material_skips_llm() -> None:
    def complete(prompt: str):
        return {"keys": ["Hg"], "external_id": "CHEBI:16136"}

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "chebi.sqlite"
        _make_index(db)
        idx = OntologyIndex(db, "chebi")
        result = resolve_external_hit(
            idx,
            label="envo_EnvironmentMaterial",
            original_text="总 Hg",
            query="总 Hg",
            aligner=LlmAligner(complete_json=complete),
            llm_labels={"whu_ChemicalEntity", "whu_Reagent"},
        )
        assert result is None
        idx.close()


def test_label_whitelists_disjoint_excluded() -> None:
    assert HARD_MERGE_LABELS.isdisjoint(EXCLUDED_LABELS)
    assert SPECIMEN_NO_DIRECT_ONTOLOGY <= EXTERNAL_CONCEPT_LABELS
    assert "whu_EnvironmentFeature" in EXCLUDED_LABELS
    assert "whu_Device" in EXCLUDED_LABELS


def main() -> None:
    test_unique_merge_nodes_drops_duplicate_ids()
    test_merge_keeper_skips_single_node_fanout()
    test_hard_merge_key_requires_nonempty_original_text()
    test_reagent_strip_concentration()
    test_ontology_exact_lookup_case_sensitive()
    test_ontology_no_fuzzy_match()
    test_ontology_ambiguous_formula_misses()
    test_ontology_related_and_formula_unique_hit()
    test_ontology_element_atom_tiebreak()
    test_extract_lookup_keys_symbol_from_modifier()
    test_harvest_and_lookup_by_id()
    test_resolve_exact_wins_without_llm()
    test_resolve_llm_from_symbol_candidates()
    test_resolve_empty_candidates_skip()
    test_resolve_id_not_in_candidates_skip()
    test_resolve_material_skips_llm()
    test_label_whitelists_disjoint_excluded()
    print("test_entity_normalize: OK")


if __name__ == "__main__":
    main()
