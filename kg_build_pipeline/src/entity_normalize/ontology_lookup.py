"""SQLite exact-match ontology index (no fuzzy / no LLM — anti-hallucination)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


@dataclass(frozen=True)
class OntologyHit:
    external_id: str
    external_uri: str
    pref_label: str
    source_ontology: str
    matched_label: str


_SCHEMA = """
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


_KIND_RANK = {"exact": 0, "synonym": 1, "related": 2, "formula": 3}


class OntologyIndex:
    """Read-only exact lookup against a pre-built SQLite index."""

    def __init__(self, db_path: Path, source_ontology: str):
        self.db_path = db_path
        self.source_ontology = source_ontology
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def available(self) -> bool:
        return self.db_path.is_file()

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def exact_lookup(self, query: str) -> Optional[OntologyHit]:
        """Case-sensitive exact match. Ambiguous labels miss unless one pref is '<x> atom'."""
        q = (query or "").strip()
        if not q:
            return None
        if not self.available:
            return None
        rows = self._connection().execute(
            """
            SELECT t.external_id, t.external_uri, t.pref_label, t.source_ontology,
                   l.label_text AS matched_label, l.label_kind AS label_kind
            FROM ontology_labels l
            JOIN ontology_terms t ON t.external_id = l.external_id
            WHERE l.label_text = ?
            """,
            (q,),
        ).fetchall()
        if not rows:
            return None
        best_rank = min(_KIND_RANK.get(str(r["label_kind"]), 99) for r in rows)
        top = [r for r in rows if _KIND_RANK.get(str(r["label_kind"]), 99) == best_rank]
        chosen = _unique_or_element_atom(top)
        if chosen is None:
            return None
        return OntologyHit(
            external_id=chosen["external_id"],
            external_uri=chosen["external_uri"],
            pref_label=chosen["pref_label"],
            source_ontology=chosen["source_ontology"] or self.source_ontology,
            matched_label=chosen["matched_label"],
        )

    def lookup_by_id(self, external_id: str) -> Optional[OntologyHit]:
        """Exact term-table lookup by ontology ID (no label matching)."""
        eid = (external_id or "").strip()
        if not eid or not self.available:
            return None
        row = self._connection().execute(
            """
            SELECT external_id, external_uri, pref_label, source_ontology
            FROM ontology_terms
            WHERE external_id = ?
            LIMIT 1
            """,
            (eid,),
        ).fetchone()
        if row is None:
            return None
        return OntologyHit(
            external_id=row["external_id"],
            external_uri=row["external_uri"],
            pref_label=row["pref_label"],
            source_ontology=row["source_ontology"] or self.source_ontology,
            matched_label=row["pref_label"],
        )

    def harvest_candidates(
        self,
        keys: Sequence[str],
        *,
        max_candidates: int = 8,
    ) -> list[OntologyHit]:
        """Exact-lookup each key; unique IDs, insertion order, capped."""
        cap = max(1, int(max_candidates))
        hits: list[OntologyHit] = []
        seen: set[str] = set()
        for raw in keys:
            hit = self.exact_lookup(str(raw or ""))
            if hit is None or hit.external_id in seen:
                continue
            seen.add(hit.external_id)
            hits.append(hit)
            if len(hits) >= cap:
                break
        return hits

    @staticmethod
    def create_empty(db_path: Path, source_ontology: str) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO ontology_terms VALUES (?,?,?,?)",
                ("TEST:1", "http://example.org/TEST_1", "test term", source_ontology),
            )
            conn.commit()
        finally:
            conn.close()


def _unique_or_element_atom(rows) -> Optional[sqlite3.Row]:
    """Return the only ID, or the only '* atom' preferred label among ties."""
    by_id = {}
    for r in rows:
        by_id[str(r["external_id"])] = r
    if len(by_id) == 1:
        return next(iter(by_id.values()))
    atom_rows = [
        r for r in by_id.values() if str(r["pref_label"] or "").endswith(" atom")
    ]
    if len(atom_rows) == 1:
        return atom_rows[0]
    return None


class OntologyIndexRegistry:
    """Lazy-loaded registry of ontology SQLite indexes."""

    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self._cache: dict[str, OntologyIndex] = {}

    def for_ontology(self, ontology_name: str) -> OntologyIndex:
        if ontology_name not in self._cache:
            path = self.index_dir / f"{ontology_name}.sqlite"
            self._cache[ontology_name] = OntologyIndex(path, ontology_name)
        return self._cache[ontology_name]

    def close(self) -> None:
        for idx in self._cache.values():
            idx.close()
        self._cache.clear()
