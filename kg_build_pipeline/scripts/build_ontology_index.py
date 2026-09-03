"""Build SQLite exact-match indexes from OWL files (offline; run once).

Indexes rdfs:label, oboInOwl:hasExactSynonym, oboInOwl:hasRelatedSynonym,
and chemrof/chebi formula strings. Lookup remains exact string equality
(no fuzzy matching, no LLM).
"""
from __future__ import annotations

import gzip
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_ROOT = PIPELINE_ROOT / "resources" / "ontologies"
INDEX_DIR = ONTOLOGY_ROOT / "_index"

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OBOINOWL = "{http://www.geneontology.org/formats/oboInOwl#}"
CHEMROF = "{https://w3id.org/chemrof/}"
CHEBI_NS = "{http://purl.obolibrary.org/obo/chebi/}"

KIND_RANK = {"exact": 0, "synonym": 1, "related": 2, "formula": 3}

_INDEXED_TAGS: Dict[str, str] = {
    f"{RDFS}label": "exact",
    f"{OBOINOWL}hasExactSynonym": "synonym",
    f"{OBOINOWL}hasRelatedSynonym": "related",
    f"{CHEMROF}generalized_empirical_formula": "formula",
    f"{CHEBI_NS}formula": "formula",
}

_ID_PATTERNS = {
    "chebi": re.compile(r"CHEBI[_:](\d+)", re.I),
    "envo": re.compile(r"ENVO[_:](\d+)", re.I),
    "ncbitaxon": re.compile(r"NCBITaxon[_:](\d+)", re.I),
}


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ontology_terms (
            external_id TEXT NOT NULL,
            external_uri TEXT NOT NULL,
            pref_label TEXT NOT NULL,
            source_ontology TEXT NOT NULL,
            PRIMARY KEY (external_id)
        );
        CREATE TABLE IF NOT EXISTS ontology_labels (
            label_text TEXT NOT NULL,
            external_id TEXT NOT NULL,
            label_kind TEXT NOT NULL DEFAULT 'synonym',
            PRIMARY KEY (label_text, external_id),
            FOREIGN KEY (external_id) REFERENCES ontology_terms(external_id)
        );
        CREATE INDEX IF NOT EXISTS idx_ontology_labels_text ON ontology_labels(label_text);
        """
    )


def _external_id_from_uri(uri: str, ontology: str) -> Optional[str]:
    pat = _ID_PATTERNS.get(ontology)
    if not pat:
        return None
    m = pat.search(uri)
    if not m:
        return None
    prefix = {"chebi": "CHEBI", "envo": "ENVO", "ncbitaxon": "NCBITaxon"}[ontology]
    return f"{prefix}:{m.group(1)}"


def _owl_paths(ontology: str) -> list[Path]:
    folder = ONTOLOGY_ROOT / ontology
    if not folder.is_dir():
        return []
    paths: list[Path] = []
    for p in sorted(folder.rglob("*")):
        if p.suffix in (".owl", ".xml") and p.is_file():
            paths.append(p)
        elif p.name.endswith(".owl.gz") and p.is_file():
            paths.append(p)
    return paths


def _open_owl(path: Path):
    if path.suffix == ".gz" or path.name.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")


def _better_kind(existing: str, incoming: str) -> str:
    if KIND_RANK.get(incoming, 99) < KIND_RANK.get(existing, 99):
        return incoming
    return existing


def _iter_classes(owl_path: Path) -> Iterator[Tuple[str, str, Dict[str, str]]]:
    """Yield (uri, pref_label, {label_text: kind}) per OWL resource with OBO-style URI."""
    with _open_owl(owl_path) as fh:
        stack: list[ET.Element] = []
        context: dict[str, dict[str, object]] = {}
        for event, elem in ET.iterparse(fh, events=("start", "end")):
            if event == "start":
                stack.append(elem)
                continue
            parent_about = None
            if len(stack) >= 2:
                parent = stack[-2]
                parent_about = parent.attrib.get(f"{RDF}about")
                if not parent_about:
                    pid = parent.attrib.get(f"{RDF}ID")
                    if pid:
                        parent_about = f"http://purl.obolibrary.org/obo/{pid}"
            kind = _INDEXED_TAGS.get(elem.tag)
            if parent_about and kind and elem.text:
                text = elem.text.strip()
                if text:
                    bucket = context.setdefault(
                        parent_about,
                        {"labels": {}, "pref": ""},
                    )
                    labels = bucket["labels"]
                    assert isinstance(labels, dict)
                    prev = labels.get(text)
                    labels[text] = _better_kind(prev, kind) if prev else kind
                    if kind == "exact" and not bucket["pref"]:
                        bucket["pref"] = text
            if stack:
                stack.pop()
            elem.clear()
        for uri, data in context.items():
            labels = data["labels"]
            if isinstance(labels, dict) and labels:
                pref = str(data["pref"] or sorted(labels)[0])
                yield uri, pref, labels


def build_index(ontology: str, *, limit_terms: Optional[int] = None) -> Path:
    out = INDEX_DIR / f"{ontology}.sqlite"
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(out)
    try:
        _schema(conn)
        conn.execute("DELETE FROM ontology_labels")
        conn.execute("DELETE FROM ontology_terms")
        inserted = 0
        for owl_path in _owl_paths(ontology):
            for uri, pref, labels in _iter_classes(owl_path):
                ext_id = _external_id_from_uri(uri, ontology)
                if not ext_id:
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO ontology_terms VALUES (?,?,?,?)",
                    (ext_id, uri, pref, ontology),
                )
                for label, kind in labels.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO ontology_labels VALUES (?,?,?)",
                        (label, ext_id, kind),
                    )
                inserted += 1
                if limit_terms and inserted >= limit_terms:
                    break
            if limit_terms and inserted >= limit_terms:
                break
        conn.commit()
    finally:
        conn.close()
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build ontology SQLite indexes")
    parser.add_argument(
        "--ontology",
        choices=["chebi", "envo", "ncbitaxon", "all"],
        default="all",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max terms per ontology (0=all)")
    args = parser.parse_args()
    names = ["chebi", "envo", "ncbitaxon"] if args.ontology == "all" else [args.ontology]
    limit = args.limit or None
    for name in names:
        path = build_index(name, limit_terms=limit)
        print(f"Built {path}")


if __name__ == "__main__":
    main()
