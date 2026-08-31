"""First-pass (and targeted) Low extraction for one mid parent."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Callable, Dict, List, Optional, Set

from neo4j import Driver

from kg_build_pipeline.src.config import PipelineConfig
from kg_build_pipeline.src.low_parent_context import (
    ParentContext,
    context_to_text_nodes,
    text_supported_by_corpus,
)
from kg_build_pipeline.src.low_schema_router import (
    LocalLowSchema,
    _row_triple,
    filter_low_rows_for_present_types,
    partition_schema_batches,
    research_type_for_parent,
)
from kg_build_pipeline.src.schema_tier import schema_closure
from kg_build_pipeline.src.stages.build_kg import (
    InsufficientBalanceError,
    _is_insufficient_balance,
    extract_document_schemas,
)

# Parents that may own Goal / hasGoal (schema). Others must not invent them.
_EXPERIMENT_PARENT_LABELS = frozenset(
    {"whu_BioChemical_Experiment", "whu_Computational_Experiment"}
)
_SE_BANNED_ENTITY_LABELS = frozenset({"whu_Goal", "whu_ResearchStep"})

EventCallback = Callable[[Dict[str, Any]], None]

# Shared HARD ban for Bio↔Comp isStepOfPlan cross-links (append-only; do not rewrite).
RESEARCHTYPE_ISSTEP_CROSSLINK_BAN = """
# WHU_RESEARCHTYPE ↔ p_plan_isStepOfPlan consistency (HARD)
WHU_RESEARCHTYPE must be consistent with the experiment linked by p_plan_isStepOfPlan.
A ResearchStep with WHU_RESEARCHTYPE = BioChemical may only be linked to a BioChemicalExperiment.
A ResearchStep with WHU_RESEARCHTYPE = Computational may only be linked to a ComputationalExperiment.
Never link a BioChemical ResearchStep to a ComputationalExperiment.
Never link a Computational ResearchStep to a BioChemicalExperiment.
The presence of both experiment types in the same Chunk does not justify cross-linking their ResearchSteps.
"""

LOW_EXTRACT_PROMPT_SUFFIX = """

# Low hierarchical expansion (parent-scoped)

You are extracting **low / mid2low** entities and relations for ONE mid-level parent.

Constraints:
- Only use facts grounded in the provided text window (roles are labeled).
- Do **not** invent entities solely to satisfy a relation.
- Prefer attaching ResearchStep / Goal / members to the named mid parent when the text supports it.
- Preserve evidence spans in original_text; do not copy neighbor-only text into parent-internal ResearchStep/Goal unless it also appears in parent original or current chunk.
- Relation order hint: entities and parent attach first; then low-to-low links (e.g. isPrecededBy).
""" + RESEARCHTYPE_ISSTEP_CROSSLINK_BAN

ENTITY_ONLY_PROMPT = """
# Low entity extraction (entities only)

Extract ONLY low-level entities grounded in the text window below.
Do NOT emit relationships. Relationship extraction happens in a later phase.

Rules:
- Only use the allowed entity labels listed.
- Every entity must have name and original_text as verbatim / contiguous spans from the text.
- Do not invent entities to satisfy a schema.
- If ResearchStep is allowed and present in text, set researchType exactly to the required value when provided.
""" + RESEARCHTYPE_ISSTEP_CROSSLINK_BAN + """
Return JSON only:
{"entities":[{"label":"<allowed label>","name":"...","original_text":"...","researchType":null}]}
"""

LOW_LOW_PROMPT_SUFFIX = """

# Low–Low relation extraction (existing entities only)

You may ONLY create relations between entities that already exist (listed below).
Do NOT create new entity nodes to satisfy a relation.
If a required endpoint entity is missing, omit that relation (do not invent the node).
Only emit a relation when the text window explicitly supports it.
Do NOT invent relations to cover every schema row.

Return JSON only:
{"relations":[{"src_name":"...","src_label":"...","rel":"...","tgt_name":"...","tgt_label":"..."}]}
"""


def parent_is_experiment(parent_labels: List[str] | None) -> bool:
    return bool(_EXPERIMENT_PARENT_LABELS & {str(x) for x in (parent_labels or [])})


def _parse_relations_json(raw: str) -> List[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return []
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    rels = data.get("relations") if isinstance(data, dict) else None
    if not isinstance(rels, list):
        return []
    out: List[Dict[str, Any]] = []
    for r in rels:
        if not isinstance(r, dict):
            continue
        src_name = str(r.get("src_name") or "").strip()
        tgt_name = str(r.get("tgt_name") or "").strip()
        src_label = str(r.get("src_label") or "").strip()
        tgt_label = str(r.get("tgt_label") or "").strip()
        rel = str(r.get("rel") or "").strip()
        if not (src_name and tgt_name and src_label and tgt_label and rel):
            continue
        out.append(
            {
                "src_name": src_name,
                "src_label": src_label,
                "rel": rel,
                "tgt_name": tgt_name,
                "tgt_label": tgt_label,
            }
        )
    return out


def filter_entities_for_write(
    entities: List[Dict[str, Any]],
    *,
    allowed_labels: Set[str],
    parent_labels: List[str] | None,
    evidence_corpus: str,
    max_entities_per_parent: int = 40,
    max_per_label: int = 0,
) -> Dict[str, Any]:
    """Evidence filter + dedupe + optional safety fuse. Never invents entities."""
    banned: Set[str] = set()
    if not parent_is_experiment(parent_labels):
        banned |= set(_SE_BANNED_ENTITY_LABELS)

    kept: List[Dict[str, Any]] = []
    dropped_banned = 0
    dropped_evidence = 0
    dropped_dup = 0
    dropped_fuse = 0
    seen: Set[tuple[str, str]] = set()
    per_label: Dict[str, int] = {}

    for e in entities:
        label = str(e.get("label") or "").strip()
        name = str(e.get("name") or "").strip()
        if not label or not name or label not in allowed_labels:
            continue
        if label in banned:
            dropped_banned += 1
            continue
        ot = str(e.get("original_text") or name).strip()
        if ot and evidence_corpus and not text_supported_by_corpus(ot, evidence_corpus):
            dropped_evidence += 1
            continue
        key = (label, name.lower())
        if key in seen:
            dropped_dup += 1
            continue
        if max_per_label > 0 and per_label.get(label, 0) >= max_per_label:
            dropped_fuse += 1
            continue
        if max_entities_per_parent > 0 and len(kept) >= max_entities_per_parent:
            dropped_fuse += 1
            continue
        seen.add(key)
        per_label[label] = per_label.get(label, 0) + 1
        kept.append({**e, "label": label, "name": name, "original_text": ot})

    return {
        "entities": kept,
        "dropped_banned": dropped_banned,
        "dropped_evidence": dropped_evidence,
        "dropped_dup": dropped_dup,
        "dropped_fuse": dropped_fuse,
    }


def write_low_low_relations(
    driver: Driver,
    database: str,
    *,
    filename: str,
    parent_element_id: str,
    relations: List[Dict[str, Any]],
    present_map: Dict[str, List[str]],
    allowed_triples: Set[tuple[str, str, str]],
) -> Dict[str, Any]:
    """MERGE relations only when both endpoints exist under parent scope."""
    source_doc = _source_doc(filename)
    name_sets: Dict[str, Set[str]] = {
        lab: {n.strip() for n in names if n and str(n).strip()}
        for lab, names in present_map.items()
    }
    written = 0
    dropped_unknown = 0
    dropped_schema = 0
    verified: List[tuple[str, str, str]] = []

    with driver.session(database=database) as session:
        for r in relations:
            s_lab = r["src_label"]
            o_lab = r["tgt_label"]
            rel = r["rel"]
            s_name = r["src_name"]
            o_name = r["tgt_name"]
            triple = (s_lab, rel, o_lab)
            if allowed_triples and triple not in allowed_triples:
                dropped_schema += 1
                continue
            if s_name not in name_sets.get(s_lab, set()) or o_name not in name_sets.get(
                o_lab, set()
            ):
                dropped_unknown += 1
                continue
            cypher = f"""
            MATCH (s:`{s_lab}`)
            WHERE coalesce(s.whu_rejected, false) = false
              AND s.WHU_HASNAME = $s_name
              AND (
                elementId(s) = $pid
                OR s.whu_parent_scope_id = $pid
              )
              AND (
                s.source_doc = $source_doc
                OR EXISTS {{
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(s) WHERE c.filename = $filename
                }}
                OR elementId(s) = $pid
              )
            MATCH (o:`{o_lab}`)
            WHERE coalesce(o.whu_rejected, false) = false
              AND o.WHU_HASNAME = $o_name
              AND (
                elementId(o) = $pid
                OR o.whu_parent_scope_id = $pid
              )
              AND (
                o.source_doc = $source_doc
                OR EXISTS {{
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(o) WHERE c.filename = $filename
                }}
                OR elementId(o) = $pid
              )
            MERGE (s)-[r:`{rel}`]->(o)
            RETURN count(*) AS cnt
            """
            row = session.run(
                cypher,
                s_name=s_name,
                o_name=o_name,
                pid=parent_element_id,
                filename=filename,
                source_doc=source_doc,
            ).single()
            n = int(row["cnt"]) if row else 0
            if n:
                written += n
                verified.append(triple)
            else:
                dropped_unknown += 1
    return {
        "written": written,
        "dropped_unknown_endpoint": dropped_unknown,
        "dropped_schema": dropped_schema,
        "verified_patterns": verified,
    }


def parent_scoped_isstep_hint(parent_labels: List[str]) -> str:
    """One-line Parent-scoped ban for the current Mid parent (append-only)."""
    labs = {str(x) for x in (parent_labels or [])}
    if "whu_BioChemical_Experiment" in labs:
        return (
            "\nCurrent parent = BioChemicalExperiment "
            "→ extracted ResearchStep must not be linked to ComputationalExperiment.\n"
        )
    if "whu_Computational_Experiment" in labs:
        return (
            "\nCurrent parent = ComputationalExperiment "
            "→ extracted ResearchStep must not be linked to BioChemicalExperiment.\n"
        )
    return ""


class LlmCallBudget:
    """Hard cap on LLM calls for one parent (token-burn guard)."""

    def __init__(self, max_calls: int) -> None:
        self.max_calls = max(0, int(max_calls))
        self.used = 0

    def remaining(self) -> int:
        return max(0, self.max_calls - self.used)

    def consume(self, n: int = 1) -> bool:
        if self.used + n > self.max_calls:
            return False
        self.used += n
        return True


def _source_doc(filename: str) -> str:
    return filename.replace(".md", "") if filename.endswith(".md") else filename


def _parse_entities_json(raw: str) -> List[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return []
    # Strip markdown fences if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    ents = data.get("entities") if isinstance(data, dict) else None
    if not isinstance(ents, list):
        return []
    out: List[Dict[str, Any]] = []
    for e in ents:
        if not isinstance(e, dict):
            continue
        label = str(e.get("label") or "").strip()
        name = str(e.get("name") or "").strip()
        if not label or not name:
            continue
        out.append(
            {
                "label": label,
                "name": name,
                "original_text": str(e.get("original_text") or name).strip(),
                "researchType": e.get("researchType"),
            }
        )
    return out


async def _llm_text(llm, prompt: str) -> str:
    try:
        if hasattr(llm, "ainvoke"):
            resp = await llm.ainvoke(prompt)
        elif hasattr(llm, "invoke"):
            resp = await asyncio.to_thread(llm.invoke, prompt)
        else:
            raise RuntimeError("LLM has no invoke/ainvoke")
    except Exception as e:
        if _is_insufficient_balance(e):
            raise InsufficientBalanceError(str(e)) from e
        raise
    if isinstance(resp, str):
        return resp
    content = getattr(resp, "content", None)
    if content is not None:
        return str(content)
    return str(resp)


def stamp_parent_scope(
    driver: Driver,
    database: str,
    *,
    filename: str,
    parent_element_id: str,
    labels: Set[str],
) -> int:
    """SET whu_parent_scope_id on recent low nodes in this doc lacking scope."""
    if not labels:
        return 0
    source_doc = _source_doc(filename)
    with driver.session(database=database) as session:
        result = session.run(
            """
            UNWIND $labels AS lab
            MATCH (n)
            WHERE lab IN labels(n)
              AND coalesce(n.whu_rejected, false) = false
              AND (
                n.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(n) WHERE c.filename = $filename
                }
              )
              AND (
                n.whu_parent_scope_id IS NULL
                OR n.whu_parent_scope_id = $scope
              )
            SET n.whu_parent_scope_id = $scope
            RETURN count(n) AS cnt
            """,
            labels=sorted(labels),
            filename=filename,
            source_doc=source_doc,
            scope=parent_element_id,
        ).single()
        return int(result["cnt"]) if result else 0


def fetch_scoped_entity_labels(
    driver: Driver,
    database: str,
    *,
    parent_element_id: str,
    filename: str,
) -> Dict[str, List[str]]:
    """label → names for entities under parent_scope (plus mid parent itself)."""
    source_doc = _source_doc(filename)
    with driver.session(database=database) as session:
        rows = session.run(
            """
            MATCH (n)
            WHERE coalesce(n.whu_rejected, false) = false
              AND (
                elementId(n) = $scope
                OR n.whu_parent_scope_id = $scope
              )
              AND (
                n.source_doc = $source_doc
                OR EXISTS {
                  MATCH (c:Chunk)-[:FROM_CHUNK]-(n) WHERE c.filename = $filename
                }
                OR elementId(n) = $scope
              )
            RETURN labels(n) AS labels, n.WHU_HASNAME AS name
            """,
            scope=parent_element_id,
            filename=filename,
            source_doc=source_doc,
        ).data()
    by_label: Dict[str, List[str]] = {}
    for r in rows:
        name = r.get("name")
        if not name:
            continue
        for lab in r.get("labels") or []:
            if str(lab).startswith("__"):
                continue
            by_label.setdefault(str(lab), []).append(str(name))
    return by_label


def write_low_entities(
    driver: Driver,
    database: str,
    *,
    filename: str,
    parent_element_id: str,
    entities: List[Dict[str, Any]],
    allowed_labels: Set[str],
    research_type: Optional[str],
    chunk_id: Optional[str] = None,
) -> int:
    """MERGE low entities with parent_scope; optional FROM_CHUNK."""
    source_doc = _source_doc(filename)
    written = 0
    with driver.session(database=database) as session:
        for e in entities:
            label = e.get("label")
            name = e.get("name")
            if label not in allowed_labels or not name:
                continue
            props = {
                "name": name,
                "original_text": e.get("original_text") or name,
                "source_doc": source_doc,
                "scope": parent_element_id,
            }
            rt = e.get("researchType") or research_type
            if label == "whu_ResearchStep" and rt:
                props["research_type"] = str(rt)
            else:
                props["research_type"] = None
            # Dynamic label in Cypher via APOC-free pattern: MATCH/CREATE with label filter
            cypher = f"""
            MERGE (n:{label} {{WHU_HASNAME: $name, source_doc: $source_doc}})
            ON CREATE SET
              n.WHU_HASORIGINALTEXT = $original_text,
              n.whu_parent_scope_id = $scope,
              n:__Entity__
            ON MATCH SET
              n.WHU_HASORIGINALTEXT = coalesce(n.WHU_HASORIGINALTEXT, $original_text),
              n.whu_parent_scope_id = coalesce(n.whu_parent_scope_id, $scope)
            FOREACH (_ IN CASE WHEN $research_type IS NULL THEN [] ELSE [1] END |
              SET n.WHU_RESEARCHTYPE = $research_type
            )
            WITH n
            OPTIONAL MATCH (c:Chunk)
            WHERE $chunk_id IS NOT NULL AND (
              elementId(c) = $chunk_id
              OR c.id = $chunk_id
              OR toString(elementId(c)) = toString($chunk_id)
            )
            FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
              MERGE (n)-[:FROM_CHUNK]->(c)
            )
            RETURN elementId(n) AS id
            """
            session.run(
                cypher,
                name=props["name"],
                original_text=props["original_text"],
                source_doc=props["source_doc"],
                scope=props["scope"],
                research_type=props["research_type"],
                chunk_id=chunk_id,
            )
            written += 1
    return written


async def extract_for_parent(
    *,
    ctx: ParentContext,
    routed_schema: List[Any],
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    neo4j_driver: Driver,
    embed_model,
    custom_prompt: str,
    cfg: PipelineConfig,
    extract_phase: str = "low_pass1",
    prompt_suffix: str = "",
    on_event: Optional[EventCallback] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Run batched extract_document_schemas over parent context text."""
    text_nodes = context_to_text_nodes(ctx)
    batches = partition_schema_batches(routed_schema)
    total_ok = 0
    batch_stats: List[Dict[str, Any]] = []
    suffix = (prompt_suffix or "") + LOW_EXTRACT_PROMPT_SUFFIX
    if ctx.parent_name:
        suffix += f"\nMid parent name: {ctx.parent_name}\nLabels: {ctx.parent_labels}\n"
    suffix += parent_scoped_isstep_hint(list(ctx.parent_labels or []))

    def _on_event(ev: Dict[str, Any]) -> None:
        if on_event:
            if ev.get("type") == "schema_extract" and ctx.parent_name:
                ev = {**ev, "parent": ctx.parent_name}
            on_event(ev)

    for batch_name, rows in batches:
        if not rows:
            continue
        ents, rels, _, _ = schema_closure(entities, relations, rows)
        ok = await extract_document_schemas(
            final_nodes=text_nodes,
            custom_prompt=custom_prompt,
            potential_schema=rows,
            entities=ents,
            relations=rels,
            llm=llm,
            neo4j_driver=neo4j_driver,
            embed_model=embed_model,
            cfg=cfg,
            text_nodes_override=text_nodes,
            prompt_suffix=suffix,
            on_event=_on_event if on_event else None,
            filename=filename or ctx.filename,
            emit_schema_events=True,
            extract_phase=extract_phase,
            parent_element_id=ctx.parent_element_id,
        )
        total_ok += int(ok or 0)
        batch_stats.append({"batch": batch_name, "schema_rows": len(rows), "ok": ok})
        if on_event:
            on_event(
                {
                    "type": "low_extract_batch",
                    "filename": filename or ctx.filename,
                    "parent": ctx.parent_name,
                    "parent_element_id": ctx.parent_element_id,
                    "batch": batch_name,
                    "schema_rows": len(rows),
                    "ok": ok,
                    "phase": extract_phase,
                }
            )
        await asyncio.sleep(0)

    return {
        "ok": total_ok,
        "batches": batch_stats,
        "context": ctx.to_dict(),
        "schema_rows": len(routed_schema),
    }


async def extract_low_entities_for_parent(
    *,
    ctx: ParentContext,
    local: LocalLowSchema,
    entities: List[Dict[str, Any]],
    llm,
    neo4j_driver: Driver,
    cfg: PipelineConfig,
    budget: LlmCallBudget,
    on_event: Optional[EventCallback] = None,
    filename: Optional[str] = None,
    label_subset: Optional[Set[str]] = None,
    max_entities_per_parent: int = 40,
    max_per_label: int = 0,
) -> Dict[str, Any]:
    """Entity-only LLM extract + MERGE with whu_parent_scope_id (counts as 1 LLM call)."""
    fname = filename or ctx.filename
    allowed = set(label_subset) if label_subset is not None else set(local.entity_labels)
    allowed &= set(local.entity_labels) if local.entity_labels else allowed
    if not allowed:
        return {"ok": 0, "written": 0, "skipped": "no_allowed_labels", "llm_calls": 0}

    if not budget.consume(1):
        return {
            "ok": 0,
            "written": 0,
            "skipped": "llm_budget_exhausted",
            "llm_calls": 0,
            "budget_used": budget.used,
        }

    plabel = local.parent_label
    for lab in ctx.parent_labels or []:
        if research_type_for_parent(str(lab)):
            plabel = str(lab)
            break
    rt = research_type_for_parent(plabel)
    type_lines = sorted(allowed)
    label_docs = []
    for e in entities:
        lab = e.get("label")
        if lab in allowed:
            desc = (e.get("description") or "")[:400]
            label_docs.append(f"- {lab}: {desc}")

    prompt = (
        ENTITY_ONLY_PROMPT
        + f"\nAllowed labels:\n"
        + "\n".join(f"- {x}" for x in type_lines)
        + (f"\nRequired ResearchStep.researchType: {rt}\n" if rt else "")
        + (f"\nMid parent: {ctx.parent_name}\nLabels: {ctx.parent_labels}\n" if ctx.parent_name else "")
        + parent_scoped_isstep_hint(list(ctx.parent_labels or []))
        + "\nLabel guidance:\n"
        + "\n".join(label_docs[:40])
        + "\n\n# Text window\n"
        + ctx.extraction_text()
    )
    if on_event:
        on_event(
            {
                "type": "low_entity",
                "filename": fname,
                "parent": ctx.parent_name,
                "parent_element_id": ctx.parent_element_id,
                "allowed_labels": len(allowed),
                "budget_used": budget.used,
            }
        )

    raw = await _llm_text(llm, prompt)
    parsed = _parse_entities_json(raw)
    filtered = filter_entities_for_write(
        parsed,
        allowed_labels=allowed,
        parent_labels=list(ctx.parent_labels or []),
        evidence_corpus=ctx.evidence_corpus(),
        max_entities_per_parent=max_entities_per_parent,
        max_per_label=max_per_label,
    )
    kept = filtered["entities"]
    home = ctx.home_chunks[0] if ctx.home_chunks else None
    chunk_id = home.chunk_id if home else None
    written = write_low_entities(
        neo4j_driver,
        cfg.neo4j_database,
        filename=fname,
        parent_element_id=ctx.parent_element_id,
        entities=kept,
        allowed_labels=allowed,
        research_type=rt,
        chunk_id=str(chunk_id) if chunk_id else None,
    )
    return {
        "ok": 1 if kept else 0,
        "written": written,
        "parsed": len(parsed),
        "kept": len(kept),
        "dropped_banned": filtered["dropped_banned"],
        "dropped_evidence": filtered["dropped_evidence"],
        "dropped_dup": filtered["dropped_dup"],
        "dropped_fuse": filtered["dropped_fuse"],
        "llm_calls": 1,
        "budget_used": budget.used,
        "research_type": rt,
        "context": ctx.to_dict(),
    }


async def extract_low_low_for_parent(
    *,
    ctx: ParentContext,
    local: LocalLowSchema,
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    llm,
    neo4j_driver: Driver,
    embed_model,
    custom_prompt: str,
    cfg: PipelineConfig,
    budget: LlmCallBudget,
    on_event: Optional[EventCallback] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Low–Low relations among scoped entities via JSON + Cypher MERGE (no SimpleKG)."""
    del entities, relations, embed_model, custom_prompt  # unused; kept for call-site compat
    fname = filename or ctx.filename
    present_map = fetch_scoped_entity_labels(
        neo4j_driver,
        cfg.neo4j_database,
        parent_element_id=ctx.parent_element_id,
        filename=fname,
    )
    present_labels = set(present_map.keys())
    runnable, missing = filter_low_rows_for_present_types(local.low_rows, present_labels)
    if on_event:
        on_event(
            {
                "type": "low_ll",
                "filename": fname,
                "parent": ctx.parent_name,
                "parent_element_id": ctx.parent_element_id,
                "present_labels": sorted(present_labels),
                "runnable_rows": len(runnable),
                "missing_triples": len(missing),
                "budget_used": budget.used,
            }
        )
    if not runnable:
        return {
            "ok": 0,
            "schema_rows": 0,
            "missing_triples": missing,
            "missing_labels": sorted(
                {lab for t in missing for lab in (t[0], t[2]) if lab not in present_labels}
            ),
            "llm_calls": 0,
            "skipped": "no_runnable_low_rows",
        }

    if not budget.consume(1):
        return {
            "ok": 0,
            "schema_rows": len(runnable),
            "missing_triples": missing,
            "skipped": "llm_budget_exhausted",
            "llm_calls": 0,
            "budget_used": budget.used,
        }

    allowed_triples: Set[tuple[str, str, str]] = set()
    schema_lines: List[str] = []
    for row in runnable:
        t = _row_triple(row)
        if not t:
            continue
        allowed_triples.add(t)
        schema_lines.append(f"- {t[0]} -[{t[1]}]-> {t[2]}")

    name_block_lines = []
    for lab, names in sorted(present_map.items()):
        uniq = sorted({n for n in names if n})
        name_block_lines.append(f"- {lab}: {', '.join(uniq[:40])}")

    prompt = (
        LOW_LOW_PROMPT_SUFFIX
        + "\nExisting entities (ONLY these may appear in relations):\n"
        + "\n".join(name_block_lines)
        + "\n\nAllowed schema triples:\n"
        + "\n".join(schema_lines[:80])
        + (f"\nMid parent name: {ctx.parent_name}\n" if ctx.parent_name else "")
        + parent_scoped_isstep_hint(list(ctx.parent_labels or []))
        + "\n\n# Text window\n"
        + ctx.extraction_text()
    )
    raw = await _llm_text(llm, prompt)
    parsed = _parse_relations_json(raw)
    write_stats = write_low_low_relations(
        neo4j_driver,
        cfg.neo4j_database,
        filename=fname,
        parent_element_id=ctx.parent_element_id,
        relations=parsed,
        present_map=present_map,
        allowed_triples=allowed_triples,
    )
    ok_n = int(write_stats.get("written") or 0)
    if on_event:
        for src, rel, tgt in write_stats.get("verified_patterns") or []:
            on_event(
                {
                    "type": "schema_extract",
                    "phase": "low_ll",
                    "filename": fname,
                    "parent": ctx.parent_name,
                    "status": "OK",
                    "source": src,
                    "relation": rel,
                    "target": tgt,
                    "message": "merged onto scoped entities",
                }
            )
        for r in parsed:
            t = (r["src_label"], r["rel"], r["tgt_label"])
            if t in (write_stats.get("verified_patterns") or []):
                continue
            # Already counted as dropped; emit NO_EDGE only for schema-ok unknown endpoints
            if allowed_triples and t not in allowed_triples:
                continue
            on_event(
                {
                    "type": "schema_extract",
                    "phase": "low_ll",
                    "filename": fname,
                    "parent": ctx.parent_name,
                    "status": "NO_EDGE",
                    "source": r["src_label"],
                    "relation": r["rel"],
                    "target": r["tgt_label"],
                    "message": "dropped_unknown_endpoint_or_no_match",
                }
            )

    return {
        "ok": ok_n,
        "verified_edges": ok_n,
        "parsed_relations": len(parsed),
        "dropped_unknown_endpoint": write_stats.get("dropped_unknown_endpoint", 0),
        "dropped_schema": write_stats.get("dropped_schema", 0),
        "schema_rows": len(runnable),
        "missing_triples": missing,
        "missing_labels": sorted(
            {lab for t in missing for lab in (t[0], t[2]) if lab not in present_labels}
        ),
        "llm_calls": 1,
        "budget_used": budget.used,
        "context": ctx.to_dict(),
    }
