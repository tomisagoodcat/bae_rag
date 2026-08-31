"""Load ontology schema from kg_build_pipeline/schema/."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from kg_build_pipeline.src.paths import REPO_ROOT, SCHEMA_DIR


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(schema_dir: Path | None = None) -> Tuple[List[Dict], List[Dict], List[List]]:
    base = schema_dir or SCHEMA_DIR
    entities = _load_json(base / "entity.json").get("entities", [])
    relations = _load_json(base / "relation.json").get("relations", [])
    potential_schema = _load_json(base / "potential_schema.json").get("potential_schema", [])
    if not entities:
        raise FileNotFoundError(f"entity.json has no entities: {base}")
    return entities, relations, potential_schema


def load_subgraph_mapping(schema_dir: Path | None = None) -> Dict[str, Any]:
    base = schema_dir or SCHEMA_DIR
    return _load_json(base / "subgraph_mapping.json")


def load_table3_section_bae(schema_dir: Path | None = None) -> Dict[str, Any]:
    """Table 3: section_role -> DoCO/Deo type and prior BAE roles."""
    base = schema_dir or SCHEMA_DIR
    path = base / "table3_section_bae.json"
    if not path.is_file():
        raise FileNotFoundError(f"table3_section_bae.json not found: {path}")
    data = _load_json(path)
    if not isinstance(data.get("mappings"), dict):
        raise ValueError(f"table3_section_bae.json missing mappings: {path}")
    return data


def load_metapath_relations(schema_dir: Path | None = None) -> Tuple[Dict[str, List], Dict[str, str]]:
    """Load F1 SUBGRAPH_RELATIONS and PAGERANK_PROP from schema/metapath_relations.json."""
    base = schema_dir or SCHEMA_DIR
    data = _load_json(base / "metapath_relations.json")
    return data["SUBGRAPH_RELATIONS"], data["PAGERANK_PROP"]


def validate_schema_dir(schema_dir: Path | None = None) -> None:
    """Run utilities/validate_schema.py against pipeline schema dir."""
    base = schema_dir or SCHEMA_DIR
    try:
        rel = base.relative_to(REPO_ROOT)
        rel_str = rel.as_posix()
    except ValueError:
        rel_str = str(base)
    cmd = [sys.executable, str(REPO_ROOT / "utilities" / "validate_schema.py"), "--dir", rel_str]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Schema validation failed:\n{proc.stdout}\n{proc.stderr}")
    print(proc.stdout.strip())
