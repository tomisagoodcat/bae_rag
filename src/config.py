"""Load config.yaml with ${ENV_VAR} substitution."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from kg_build_pipeline.src.paths import DEFAULT_CONFIG, REPO_ROOT, resolve_repo_path

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
_DOTENV_LOADED = False


def _load_repo_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except ImportError:
            pass
    _DOTENV_LOADED = True


def _subst_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            key = m.group(1)
            return os.environ.get(key, m.group(0))

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _subst_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_subst_env(v) for v in value]
    return value


@dataclass
class PipelineConfig:
    schema_dir: Path
    markdown_dir: Path
    custom_prompt: Path
    embedding_model: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    stages: Dict[str, bool] = field(default_factory=dict)
    build_kg: Dict[str, Any] = field(default_factory=dict)
    metapath: Dict[str, Any] = field(default_factory=dict)
    entity_merge: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "PipelineConfig":
        _load_repo_dotenv()
        path = config_path or DEFAULT_CONFIG
        data = _subst_env(yaml.safe_load(path.read_text(encoding="utf-8")))
        paths = data.get("paths", {})
        neo4j = data.get("neo4j", {})
        llm = data.get("llm", {})
        pwd = neo4j.get("password", "")
        if pwd.startswith("${") or not pwd:
            pwd = os.environ.get("NEO4J_PASSWORD", "tomis1cat")
        api_key = llm.get("deepseek_api_key", "")
        if api_key.startswith("${") or not api_key:
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            schema_dir=resolve_repo_path(paths.get("schema_dir", "kg_build_pipeline/schema")),
            markdown_dir=resolve_repo_path(paths.get("markdown_dir", "data/markdown/forTest")),
            custom_prompt=resolve_repo_path(paths.get("custom_prompt", "custom_prompt.md")),
            embedding_model=paths.get("embedding_model", "C:/model/bce-embedding-base_v1"),
            neo4j_uri=neo4j.get("uri", "bolt://localhost:7687"),
            neo4j_user=neo4j.get("user", "neo4j"),
            neo4j_password=pwd,
            neo4j_database=neo4j.get("database", "neo4j"),
            deepseek_api_key=api_key,
            deepseek_base_url=llm.get("deepseek_base_url", "https://api.deepseek.com/v1"),
            deepseek_model=llm.get("deepseek_model", "deepseek-chat"),
            stages=data.get("stages", {}),
            build_kg=data.get("build_kg", {}),
            metapath=data.get("metapath", {}),
            entity_merge=data.get("entity_merge", {}),
            raw=data,
        )

    def stage_enabled(self, name: str) -> bool:
        return bool(self.stages.get(name, False))
