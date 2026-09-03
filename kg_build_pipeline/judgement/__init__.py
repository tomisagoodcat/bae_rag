"""Isolated read-only KG judgement package (no LLM, no KG writes)."""
from __future__ import annotations

from kg_build_pipeline.judgement.run import run_judgement

__all__ = ["run_judgement"]
