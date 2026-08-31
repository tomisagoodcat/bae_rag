#!/usr/bin/env python3
"""Generate / expand dialogue_test_cases.json to 66 scenarios.

Pipeline:
  1. Environmental-science **expert** drafts scenarios (English queries, κ/l, modules).
  2. **Researcher** refines wording for realistic lab / stakeholder dialogue.
  3. Optional **qrels**: Neo4j hybrid pool + independent LLM judge → relevant_mp_ids.

Usage:
  python utilities/generate_dialogue_test_cases.py
  python utilities/generate_dialogue_test_cases.py --annotate-qrels-only
  python utilities/generate_dialogue_test_cases.py --skip-llm   # structure check only
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_JSON = PROJECT_ROOT / "data" / "dialogue_test_cases.json"
BACKUP_JSON = PROJECT_ROOT / "data" / "dialogue_test_cases.v1.json"
CHECKPOINT_JSON = PROJECT_ROOT / "data" / ".dialogue_gen_checkpoint.json"
TARGET_SCENARIOS = 66

TOP_LEVEL_MODULES = frozenset({"MPU", "EEM", "EBM"})
VALID_KAPPA = frozenset(
    {"first_turn", "drill_down", "roll_up", "sibling_nav", "drill_across"}
)
VALID_L = frozenset({"mid", "low"})

DOMAIN_CONTEXT = """
Knowledge graph domain: environmental mercury / methylmercury / heavy-metal pollution
in agricultural soils, rice systems, wetlands, and human exposure pathways.
Top-level graph modules:
  - MPU: mercury pollution understanding (sources, methylation drivers, fate)
  - EEM: environmental exposure mechanisms (uptake, biomarkers, pathways)
  - EBM: environmental behavior & management (remediation, QC, field trials, concentrations)
Queries should sound like real questions from environmental scientists, risk assessors,
or agronomists reviewing literature — not generic chatbot prompts.
""".strip()

ARCHETYPE_SPECS: Dict[str, Dict[str, Any]] = {
    "classic_3": {
        "turns": [
            ("first_turn", "mid"),
            ("drill_down", "low"),
            ("roll_up", "mid"),
        ],
        "hint": "Turn1 overview → Turn2 mechanism/detail drill-down → Turn3 roll-up summary.",
    },
    "sibling_3": {
        "turns": [
            ("first_turn", "mid"),
            ("sibling_nav", "mid"),
            ("roll_up", "mid"),
        ],
        "hint": "Turn2 switches to a related module/theme (sibling navigation), not deeper detail.",
    },
    "drill_across_3": {
        "turns": [
            ("first_turn", "mid"),
            ("drill_across", "low"),
            ("roll_up", "mid"),
        ],
        "hint": "Turn2 pivots to a parallel facet (e.g. QC, sampling, policy) at fine granularity.",
    },
    "two_turn_drill": {
        "turns": [
            ("first_turn", "mid"),
            ("drill_down", "low"),
        ],
        "hint": "Short dialogue: overview then one detailed follow-up only.",
    },
    "four_turn_mix": {
        "turns": [
            ("first_turn", "mid"),
            ("drill_down", "low"),
            ("sibling_nav", "mid"),
            ("roll_up", "mid"),
        ],
        "hint": "Longer session: drill, then switch module, then synthesize.",
    },
}

# 56 new slots: (archetype, topic_en, expected_modules_turn1)
NEW_SCENARIO_SLOTS: List[Tuple[str, str, List[str]]] = [
    # classic_3 × 12
    *[
        (
            "classic_3",
            t,
            m,
        )
        for t, m in [
            ("Wet-dry alternation in paddy soils and its effect on methylmercury production", ["MPU"]),
            ("Sulfate-reducing bacteria abundance as a proxy for Hg methylation potential", ["MPU", "EEM"]),
            ("Selenium amendment and antagonistic effects on MeHg uptake in rice grains", ["EEM", "EBM"]),
            ("Iron plaque formation on rice roots and mercury sequestration", ["MPU", "EEM"]),
            ("Flooding duration during grain filling and grain MeHg concentration", ["MPU", "EBM"]),
            ("Atmospheric Hg deposition vs irrigation water as dominant loading pathways", ["MPU"]),
            ("δ15N and δ13C isotopes tracing MeHg biomagnification in wetland food webs", ["EEM"]),
            ("Comparative total Hg vs MeHg speciation across soil horizons", ["EBM"]),
            ("Rhizosphere pH and Eh controls on Hg methylation near root surfaces", ["MPU", "EEM"]),
            ("Legacy artisanal mining sites and downstream rice paddy contamination", ["MPU", "EBM"]),
            ("Temperature sensitivity of microbial Hg methylation in anaerobic sediments", ["MPU"]),
            ("Organic matter quality (C/N ratio) regulating Hg bioavailability", ["MPU", "EBM"]),
        ]
    ],
    # sibling_3 × 14
    *[
        (
            "sibling_3",
            t,
            m,
        )
        for t, m in [
            ("Human dietary exposure to MeHg via rice consumption in southern China", ["EEM"]),
            ("ICP-MS detection limits and matrix interference for rice MeHg", ["EBM"]),
            ("Wastewater irrigation standards relevant to Hg in paddy systems", ["EBM", "MPU"]),
            ("Health-based reference doses for methylmercury in vulnerable populations", ["EEM"]),
            ("National soil environmental quality standards for mercury", ["EBM"]),
            ("Biochar application for mercury immobilization in contaminated paddies", ["EBM"]),
            ("Plant uptake coefficients for Hg species in pot experiments", ["EEM", "EBM"]),
            ("Household cooking and washing effects on grain Hg concentrations", ["EEM"]),
            ("Spatial GIS clustering of high-MeHg rice production zones", ["MPU", "EBM"]),
            ("Co-contamination with cadmium and arsenic in the same rice samples", ["EBM"]),
            ("Probabilistic risk assessment framework for dietary MeHg", ["EEM"]),
            ("Stakeholder communication of mercury results to farming communities", ["EEM", "EBM"]),
            ("Life-cycle assessment of mercury emissions from rice production chains", ["MPU"]),
            ("Meta-analysis heterogeneity in reported rice MeHg concentrations", ["EBM", "EEM"]),
        ]
    ],
    # drill_across_3 × 12
    *[
        (
            "drill_across_3",
            t,
            m,
        )
        for t, m in [
            ("Mercury methylation mechanisms in flooded rice soils", ["MPU"]),
            ("Field sampling design for mercury in soil–plant systems", ["EBM"]),
            ("Laboratory QA/QC for methylmercury analysis in biological samples", ["EBM"]),
            ("Exposure assessment linking soil Hg to dietary intake", ["EEM"]),
            ("Remediation options after mercury contamination in cropland", ["EBM"]),
            ("Hydrological management practices reducing MeHg export", ["MPU", "EBM"]),
            ("Methylation hotspots along redox gradients in profile cores", ["MPU"]),
            ("Peer comparison of analytical methods across published rice studies", ["EBM"]),
            ("Ecotoxicological endpoints for mercury in soil invertebrates", ["EEM"]),
            ("Policy instruments for mercury control in agricultural watersheds", ["EBM", "MPU"]),
            ("Stable isotope tracing of Hg sources in rice agroecosystems", ["MPU", "EEM"]),
            ("Uncertainty propagation in MeHg mass balance models", ["MPU", "EBM"]),
        ]
    ],
    # two_turn_drill × 10
    *[
        (
            "two_turn_drill",
            t,
            m,
        )
        for t, m in [
            ("Overview of mercury biogeochemical cycling in rice paddies", ["MPU"]),
            ("Key factors controlling MeHg accumulation in rice grains", ["MPU", "EEM"]),
            ("Summary of mercury measurement methods in environmental samples", ["EBM"]),
            ("Exposure pathways from soil mercury to human diet", ["EEM"]),
            ("Agricultural water management and mercury mobility", ["MPU", "EBM"]),
            ("Effects of straw incorporation on soil mercury speciation", ["MPU"]),
            ("Comparison of control vs treatment plots in mercury field trials", ["EBM"]),
            ("Background mercury levels in regional paddy soils", ["MPU", "EBM"]),
            ("Plant tissue partitioning of total Hg and MeHg", ["EEM"]),
            ("Mitigation measures for mercury in rice-based diets", ["EBM", "EEM"]),
        ]
    ],
    # four_turn_mix × 8
    *[
        (
            "four_turn_mix",
            t,
            m,
        )
        for t, m in [
            ("Integrated assessment of mercury risk in a rice-dominated watershed", ["MPU", "EEM", "EBM"]),
            ("From soil methylation to dietary exposure: end-to-end mercury pathway", ["MPU", "EEM"]),
            ("Field experiment on water regime, soil Hg, and grain MeHg", ["EBM", "MPU"]),
            ("Analytical workflow from sampling to reported rice MeHg data", ["EBM"]),
            ("Climate-driven changes in flooding and future MeHg risk in paddies", ["MPU", "EBM"]),
            ("Coupled soil microbiology and plant uptake of mercury species", ["MPU", "EEM"]),
            ("Regulatory compliance and scientific evidence for mercury in crops", ["EBM", "EEM"]),
            ("Multi-site survey design for mercury in rice production regions", ["EBM", "MPU"]),
        ]
    ],
]

EXPERT_BATCH_PROMPT = """You are a senior **environmental science expert** (mercury biogeochemistry, rice agroecosystems, exposure assessment).

{domain}

Draft **{count}** multi-turn dialogue test scenarios for GraphRAG OLAP routing evaluation.
Each scenario must follow its **archetype** κ/l sequence exactly.

Archetype definitions:
{archetype_block}

Batch assignments (generate one scenario per row, same order):
{assignments_block}

Return ONLY a JSON array (no markdown). Each element:
{{
  "name": "snake_case_unique_id",
  "archetype": "<archetype id>",
  "topic_en": "<short topic>",
  "expected_modules_turn1": ["MPU"|"EEM"|"EBM", ...],
  "turns": [
    {{
      "query": "<English, realistic scientist question>",
      "expected_kappa": "<from archetype>",
      "expected_l": "<mid|low from archetype>",
      "expected_modules": ["MPU", ...],
      "intent_note": "<one line: what the user wants this turn>"
    }}
  ],
  "expert_rationale": "<why this dialogue is realistic>"
}}

Rules:
- Turn count must match archetype length.
- expected_kappa / expected_l per turn must match archetype template.
- Turn1 expected_modules must equal expected_modules_turn1.
- For sibling_nav / drill_across turns, set expected_modules to the module(s) most appropriate (may differ from turn1).
- Queries must be specific to mercury/rice/soil/exposure/QC — avoid vague "tell me more".
- Use natural follow-up phrasing referencing prior turn without repeating turn1 verbatim.
"""

RESEARCHER_BATCH_PROMPT = """You are an **environmental science researcher** refining dialogue test queries for a retrieval benchmark.

Expert drafts (JSON array):
{draft_json}

Refine each scenario so queries sound like real multi-turn conversations in a research meeting:
- Fix awkward phrasing; keep scientific precision.
- Preserve expected_kappa, expected_l, expected_modules, archetype, and turn count exactly.
- Keep English queries; may add brief clause referencing prior context ("Given the methylation factors we discussed...").
- Do NOT change module codes or κ/l labels.

Return ONLY the same JSON array structure with added field per scenario:
"researcher_notes": "<what you changed and why>"

Each turn may add:
"relevance_criteria": "<1-2 sentences: what evidence would be relevant for qrels/judge>"
"""

EXPERT_SINGLE_PROMPT = """You are a senior **environmental science expert** (mercury biogeochemistry, rice agroecosystems).

{domain}

Draft **one** multi-turn dialogue test scenario.

Archetype **{archetype}**: turns must be exactly {turn_seq}.
Topic: {topic}
expected_modules_turn1: {modules}

{archetype_hint}

Return ONLY one JSON object (not array):
{{
  "name": "snake_case_unique",
  "archetype": "{archetype}",
  "topic_en": "{topic}",
  "expected_modules_turn1": {modules_json},
  "turns": [{{"query":"...", "expected_kappa":"...", "expected_l":"...", "expected_modules":[...], "intent_note":"..."}}],
  "expert_rationale": "..."
}}
"""

RESEARCHER_SINGLE_PROMPT = """You are an **environmental science researcher** refining one dialogue scenario.

Expert draft:
{draft_json}

Preserve κ/l/modules/archetype/turn count. Add "researcher_notes" and per-turn "relevance_criteria".
Return ONLY one JSON object.
"""

RESEARCHER_LEGACY_PROMPT = """You are an **environmental science researcher** refining legacy dialogue test cases.

{domain}

Input JSON array of {count} scenarios (keep names and source_no; archetype is classic_3):
{legacy_json}

Refine queries for realism; preserve expected_kappa, expected_l, turn count.
Add fields: "archetype": "classic_3", "researcher_notes", per-turn "relevance_criteria" where missing.

Return ONLY the JSON array.
"""


def _load_dotenv() -> None:
    from dotenv import load_dotenv

    for p in [
        PROJECT_ROOT / ".env",
        Path(os.environ.get("USERPROFILE", ""))
        / "OneDrive"
        / "LUCK"
        / "luck grpahrag"
        / "code"
        / "PaperExtract2"
        / "PaperExtract2"
        / ".env",
    ]:
        if p.is_file():
            load_dotenv(p)
            print(f"load_dotenv: {p}")
            return
    load_dotenv()


def _make_llm() -> Any:
    from neo4j_graphrag.llm import OpenAILLM

    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("需要 QWEN_API_KEY 或 OPENAI_API_KEY")
    return OpenAILLM(
        model_name=os.environ.get("QWEN_MODEL", "qwen-plus"),
        base_url=os.environ.get(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        api_key=api_key,
        model_params={
            "temperature": float(os.environ.get("GEN_LLM_TEMPERATURE", "0.3")),
            "max_tokens": int(os.environ.get("GEN_LLM_MAX_TOKENS", "8192")),
        },
    )


def _llm_text(llm: Any, prompt: str) -> str:
    resp = llm.invoke(prompt)
    content = getattr(resp, "content", resp)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"LLM 空响应: {resp!r}")
    return content.strip()


def _extract_json_value(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pattern in (r"\[[\s\S]*\]", r"\{[\s\S]*\}"):
            m = re.search(pattern, text)
            if m:
                return json.loads(m.group(0))
        raise


def _invoke_json_object(llm: Any, prompt: str, retries: int = 2) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    p = prompt
    for attempt in range(retries):
        try:
            data = _extract_json_value(_llm_text(llm, p))
            if isinstance(data, list) and len(data) == 1:
                data = data[0]
            if not isinstance(data, dict):
                raise ValueError(f"期望 JSON object，得到 {type(data)}")
            return data
        except Exception as exc:
            last_err = exc
            p = prompt + "\n\nIMPORTANT: Return ONLY one valid JSON object, no prose."
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"LLM JSON 解析失败: {last_err}") from last_err


def _invoke_json_array(llm: Any, prompt: str, retries: int = 2) -> List[Dict[str, Any]]:
    last_err: Optional[Exception] = None
    p = prompt
    for attempt in range(retries):
        try:
            data = _extract_json_value(_llm_text(llm, p))
            if isinstance(data, dict) and "scenarios" in data:
                data = data["scenarios"]
            if not isinstance(data, list):
                raise ValueError(f"期望 JSON array，得到 {type(data)}")
            return data
        except Exception as exc:
            last_err = exc
            p = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON array, no prose."
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"LLM JSON 解析失败: {last_err}") from last_err


def _format_archetype_block() -> str:
    lines = []
    for key, spec in ARCHETYPE_SPECS.items():
        seq = ", ".join(f"{k}/{l}" for k, l in spec["turns"])
        lines.append(f"- {key}: turns [{seq}] — {spec['hint']}")
    return "\n".join(lines)


def _format_assignments(slots: Sequence[Tuple[str, str, List[str]]]) -> str:
    rows = []
    for i, (arch, topic, mods) in enumerate(slots, 1):
        seq = ARCHETYPE_SPECS[arch]["turns"]
        rows.append(
            f"{i}. archetype={arch} | modules_turn1={mods} | topic: {topic} | κ/l sequence: {seq}"
        )
    return "\n".join(rows)


def _validate_scenario(sc: Dict[str, Any], *, require_name: bool = True) -> None:
    if require_name and not sc.get("name"):
        raise ValueError("scenario 缺少 name")
    arch = sc.get("archetype")
    if arch not in ARCHETYPE_SPECS:
        raise ValueError(f"未知 archetype: {arch}")
    expected_seq = ARCHETYPE_SPECS[arch]["turns"]
    turns = sc.get("turns")
    if not isinstance(turns, list) or len(turns) != len(expected_seq):
        raise ValueError(f"{sc.get('name')}: turn 数量应为 {len(expected_seq)}")
    mods1 = sc.get("expected_modules_turn1")
    if not mods1 or not all(m in TOP_LEVEL_MODULES for m in mods1):
        raise ValueError(f"{sc.get('name')}: invalid expected_modules_turn1")
    for i, (turn, (ek, el)) in enumerate(zip(turns, expected_seq)):
        if turn.get("expected_kappa") != ek:
            raise ValueError(f"{sc.get('name')} turn{i+1}: kappa 应为 {ek}")
        if turn.get("expected_l") != el:
            raise ValueError(f"{sc.get('name')} turn{i+1}: l 应为 {el}")
        if ek not in VALID_KAPPA or el not in VALID_L:
            raise ValueError(f"{sc.get('name')} turn{i+1}: 无效 κ/l")
        if not (turn.get("query") or "").strip():
            raise ValueError(f"{sc.get('name')} turn{i+1}: 空 query")
        em = turn.get("expected_modules") or mods1
        if not all(m in TOP_LEVEL_MODULES for m in em):
            raise ValueError(f"{sc.get('name')} turn{i+1}: invalid expected_modules")


def _normalize_scenario(raw: Dict[str, Any], slot: Optional[Tuple[str, str, List[str]]] = None) -> Dict[str, Any]:
    if slot:
        arch, topic, mods = slot
        raw.setdefault("archetype", arch)
        raw.setdefault("topic_en", topic)
        raw.setdefault("expected_modules_turn1", mods)
    arch = raw.get("archetype") or (slot[0] if slot else "classic_3")
    expected_seq = ARCHETYPE_SPECS[arch]["turns"]
    turns_out = []
    for j, t in enumerate(raw.get("turns") or []):
        ek, el = expected_seq[j] if j < len(expected_seq) else (
            t.get("expected_kappa"),
            t.get("expected_l"),
        )
        turn = {
            "query": str(t["query"]).strip(),
            "expected_kappa": ek,
            "expected_l": el,
        }
        if t.get("expected_modules"):
            turn["expected_modules"] = list(t["expected_modules"])
        if t.get("relevance_criteria"):
            turn["relevance_criteria"] = str(t["relevance_criteria"]).strip()
        if t.get("intent_note"):
            turn["intent_note"] = str(t["intent_note"]).strip()
        turns_out.append(turn)
    out: Dict[str, Any] = {
        "name": str(raw["name"]).strip(),
        "archetype": arch,
        "expected_modules_turn1": list(raw["expected_modules_turn1"]),
        "turns": turns_out,
    }
    if raw.get("source_no") is not None:
        out["source_no"] = raw["source_no"]
    if raw.get("topic_en"):
        out["topic_en"] = raw["topic_en"]
    if raw.get("expert_rationale"):
        out["expert_rationale"] = raw["expert_rationale"]
    if raw.get("researcher_notes"):
        out["researcher_notes"] = raw["researcher_notes"]
    return out


def _save_checkpoint(legacy: List[Dict[str, Any]], new_scenarios: List[Dict[str, Any]]) -> None:
    CHECKPOINT_JSON.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_JSON.write_text(
        json.dumps(
            {"legacy": legacy, "new_scenarios": new_scenarios},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _load_checkpoint() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not CHECKPOINT_JSON.is_file():
        return [], []
    data = json.loads(CHECKPOINT_JSON.read_text(encoding="utf-8"))
    return data.get("legacy") or [], data.get("new_scenarios") or []


def _generate_single(
    llm: Any,
    slot: Tuple[str, str, List[str]],
    idx: int,
) -> Dict[str, Any]:
    arch, topic, mods = slot
    spec = ARCHETYPE_SPECS[arch]
    turn_seq = ", ".join(f"{k}/{l}" for k, l in spec["turns"])
    expert_prompt = EXPERT_SINGLE_PROMPT.format(
        domain=DOMAIN_CONTEXT,
        archetype=arch,
        turn_seq=turn_seq,
        topic=topic,
        modules=mods,
        modules_json=json.dumps(mods),
        archetype_hint=spec["hint"],
    )
    draft = _invoke_json_object(llm, expert_prompt)
    draft.setdefault("name", f"gen_{idx:03d}_{arch}")
    refined = _invoke_json_object(
        llm,
        RESEARCHER_SINGLE_PROMPT.format(
            draft_json=json.dumps(draft, ensure_ascii=False, indent=2)
        ),
    )
    sc = _normalize_scenario(refined, slot)
    _validate_scenario(sc)
    return sc


def _generate_batch(
    llm: Any,
    slots: Sequence[Tuple[str, str, List[str]]],
    batch_id: int,
) -> List[Dict[str, Any]]:
    expert_prompt = EXPERT_BATCH_PROMPT.format(
        domain=DOMAIN_CONTEXT,
        count=len(slots),
        archetype_block=_format_archetype_block(),
        assignments_block=_format_assignments(slots),
    )
    print(f"\n[batch {batch_id}] expert draft ({len(slots)} scenarios)...")
    drafts = _invoke_json_array(llm, expert_prompt)
    if len(drafts) != len(slots):
        print(f"  warn: expert returned {len(drafts)} != {len(slots)}, aligning by index")
    researcher_prompt = RESEARCHER_BATCH_PROMPT.format(
        draft_json=json.dumps(drafts[: len(slots)], ensure_ascii=False, indent=2)
    )
    print(f"[batch {batch_id}] researcher refine...")
    refined = _invoke_json_array(llm, researcher_prompt)
    out = []
    for i, slot in enumerate(slots):
        item = refined[i] if i < len(refined) else drafts[i]
        sc = _normalize_scenario(item, slot)
        _validate_scenario(sc)
        out.append(sc)
    return out


def _load_refined_legacy_from_output() -> List[Dict[str, Any]]:
    """Prefer already-refined q01–q10 in dialogue_test_cases.json."""
    if DEFAULT_JSON.is_file():
        data = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
        legacy = [
            s
            for s in data.get("scenarios", [])
            if not str(s.get("name", "")).startswith("gen_")
        ]
        if len(legacy) == 10:
            for sc in legacy:
                sc.setdefault("archetype", "classic_3")
            return [_normalize_scenario(sc) for sc in legacy]
    ck_legacy, _ = _load_checkpoint()
    if len(ck_legacy) == 10:
        return ck_legacy
    return [
        _normalize_scenario({**sc, "archetype": "classic_3"}, None)
        for sc in _load_legacy_scenarios()
    ]


def _load_legacy_scenarios() -> List[Dict[str, Any]]:
    """Always take the original 10 scenarios from v1 backup when present."""
    src = BACKUP_JSON if BACKUP_JSON.is_file() else DEFAULT_JSON
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    legacy = data.get("scenarios") or []
    if len(legacy) > 10:
        legacy = legacy[:10]
    if len(legacy) != 10:
        raise RuntimeError(f"需要 10 条 legacy scenario，{src} 仅有 {len(legacy)} 条")
    return legacy


def _refine_legacy(
    llm: Any, legacy: List[Dict[str, Any]], *, chunk_size: int = 3
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for start in range(0, len(legacy), chunk_size):
        chunk = legacy[start : start + chunk_size]
        for sc in chunk:
            sc.setdefault("archetype", "classic_3")
        prompt = RESEARCHER_LEGACY_PROMPT.format(
            domain=DOMAIN_CONTEXT,
            count=len(chunk),
            legacy_json=json.dumps(chunk, ensure_ascii=False, indent=2),
        )
        print(f"\n[legacy] researcher refine scenarios {start+1}-{start+len(chunk)}...")
        refined = _invoke_json_array(llm, prompt)
        for i, orig in enumerate(chunk):
            item = refined[i] if i < len(refined) else orig
            item["source_no"] = orig.get("source_no", start + i + 1)
            item.setdefault("archetype", "classic_3")
            sc = _normalize_scenario(item)
            _validate_scenario(sc)
            out.append(sc)
        time.sleep(0.5)
    return out


def _template_scenario(slot: Tuple[str, str, List[str]], idx: int) -> Dict[str, Any]:
    """Fallback when --skip-llm: deterministic placeholder queries."""
    arch, topic, mods = slot
    seq = ARCHETYPE_SPECS[arch]["turns"]
    turns = []
    for j, (kappa, level) in enumerate(seq):
        if kappa == "first_turn":
            q = f"What are the main scientific findings regarding {topic.lower()}?"
        elif kappa == "drill_down":
            q = f"Please elaborate on experimental and mechanistic details for {topic.lower()}."
        elif kappa == "roll_up":
            q = f"Summarize at overview level what we know about {topic.lower()}."
        elif kappa == "sibling_nav":
            q = f"Switching focus: what does the literature say about related QC or exposure aspects of {topic.lower()}?"
        else:
            q = f"From another angle, what parallel evidence exists on sampling or methods for {topic.lower()}?"
        turns.append(
            {
                "query": q,
                "expected_kappa": kappa,
                "expected_l": level,
                "expected_modules": mods if j == 0 else mods,
            }
        )
    return _normalize_scenario(
        {
            "name": f"gen_{idx:03d}_{arch}",
            "archetype": arch,
            "topic_en": topic,
            "expected_modules_turn1": mods,
            "turns": turns,
            "researcher_notes": "template fallback (--skip-llm)",
        },
        slot,
    )


def _sanitize_lucene(text: str) -> str:
    return re.sub(r'[+\-&|!(){}\[\]^"~*?:\\/—–]', " ", text).strip()


def _init_neo4j_and_embed() -> Tuple[Any, Any]:
    from neo4j import GraphDatabase
    from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    model_path = os.environ.get("LOCAL_MODEL_PATH_BCE")
    if not all([uri, user, password, model_path]):
        raise RuntimeError("Neo4j qrels 需要 NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, LOCAL_MODEL_PATH_BCE")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    embed = SentenceTransformerEmbeddings(model=model_path)
    return driver, embed


def _hybrid_pool(
    driver: Any,
    embed: Any,
    query: str,
    modules: Sequence[str],
    path_level: Optional[str],
    top_k: int = 40,
) -> List[Dict[str, Any]]:
    from neo4j_graphrag.retrievers import HybridCypherRetriever
    from neo4j_graphrag.types import RetrieverResultItem

    from utilities.recall_cypher import build_cypher_for_subgraph, build_cypher_for_subgraph_flat

    import neo4j as neo4j_mod

    def formatter(record: neo4j_mod.Record) -> RetrieverResultItem:
        return RetrieverResultItem(content=dict(record), metadata=None)

    q = _sanitize_lucene(query)
    if not q:
        return []
    all_rows: List[Dict[str, Any]] = []
    for sg in modules:
        if path_level:
            cypher = build_cypher_for_subgraph(sg, path_level)
            scan = 300 if path_level == "mid" else 60
        else:
            cypher = build_cypher_for_subgraph_flat(sg)
            scan = 300
        retriever = HybridCypherRetriever(
            driver=driver,
            vector_index_name="metapath_embedding_index",
            fulltext_index_name="metapath_fulltext_index",
            embedder=embed,
            retrieval_query=cypher,
            result_formatter=formatter,
        )
        result = retriever.search(query_text=q, top_k=scan)
        items = getattr(result, "items", None) or []
        for it in items:
            content = getattr(it, "content", None) or {}
            if isinstance(content, dict):
                row = dict(content)
            else:
                continue
            row["score"] = getattr(it, "score", None) or row.get("score") or 0.0
            row["_subgraph"] = sg
            all_rows.append(row)
    seen: set = set()
    deduped = []
    for r in sorted(all_rows, key=lambda x: float(x.get("score") or 0.0), reverse=True):
        mp = r.get("mp_id")
        if not mp or mp in seen:
            continue
        seen.add(mp)
        deduped.append(r)
    return deduped[:top_k]


def _modules_for_turn(scenario: Dict[str, Any], turn: Dict[str, Any]) -> List[str]:
    em = turn.get("expected_modules")
    if em:
        return list(em)
    return list(scenario.get("expected_modules_turn1") or ["MPU"])


def annotate_qrels(
    scenarios: List[Dict[str, Any]],
    llm: Any,
    *,
    pool_size: int = 25,
    min_qrels: int = 3,
    max_qrels: int = 12,
    max_scenarios: Optional[int] = None,
) -> None:
    from utilities.rag_llm_judge import judge_metapath_relevance

    if max_scenarios is not None:
        scenarios = scenarios[:max_scenarios]
    driver, embed = _init_neo4j_and_embed()
    try:
        total_turns = sum(len(s["turns"]) for s in scenarios)
        n_done = 0
        for sc in scenarios:
            for turn in sc["turns"]:
                n_done += 1
                modules = _modules_for_turn(sc, turn)
                level = turn.get("expected_l")
                pool = _hybrid_pool(
                    driver,
                    embed,
                    turn["query"],
                    modules,
                    path_level=level,
                    top_k=pool_size,
                )
                judge_items = []
                for i, row in enumerate(pool[:20], 1):
                    preview = (row.get("metapath_text") or "")[:1200]
                    judge_items.append(
                        {
                            "rank": i,
                            "mp_id": str(row.get("mp_id")),
                            "preview": preview or str(row.get("meta_path_query") or ""),
                        }
                    )
                qrels: List[str] = []
                qrels_source = "neo4j_hybrid_judge"
                if judge_items:
                    try:
                        rel = judge_metapath_relevance(llm, turn["query"], judge_items)
                        qrels = [
                            judge_items[i]["mp_id"]
                            for i, ok in enumerate(rel)
                            if ok and judge_items[i]["mp_id"]
                        ]
                    except Exception as exc:
                        print(f"  judge fail {sc['name']}: {exc}")
                        qrels_source = "neo4j_hybrid_top_score_fallback"
                if len(qrels) < min_qrels:
                    qrels = [
                        str(r["mp_id"])
                        for r in pool[:max_qrels]
                        if r.get("mp_id")
                    ]
                    qrels_source = "neo4j_hybrid_top_score_fallback"
                turn["relevant_mp_ids"] = qrels[:max_qrels]
                turn["qrels_source"] = qrels_source
                print(
                    f"  [{n_done}/{total_turns}] {sc['name']} "
                    f"κ={turn['expected_kappa']} qrels={len(turn['relevant_mp_ids'])} ({qrels_source})"
                )
    finally:
        driver.close()


def _kappa_distribution(scenarios: List[Dict[str, Any]]) -> Dict[str, int]:
    dist: Dict[str, int] = {}
    for sc in scenarios:
        for t in sc["turns"]:
            k = t["expected_kappa"]
            dist[k] = dist.get(k, 0) + 1
    return dist


def build_corpus(
    llm: Optional[Any],
    *,
    skip_llm: bool,
    batch_size: int = 4,
    legacy_chunk: int = 3,
    single_mode: bool = True,
    resume: bool = False,
    legacy_only: bool = False,
    new_only: bool = False,
    max_new: Optional[int] = None,
) -> List[Dict[str, Any]]:
    legacy_src = _load_legacy_scenarios()
    ck_legacy, ck_new = _load_checkpoint() if resume else ([], [])

    if skip_llm:
        refined_legacy = [
            _normalize_scenario({**sc, "archetype": "classic_3"}, None) for sc in legacy_src
        ]
        new_scenarios = [
            _template_scenario(slot, i + 11)
            for i, slot in enumerate(NEW_SCENARIO_SLOTS)
        ]
    else:
        if llm is None:
            raise RuntimeError("llm required")
        if resume and ck_legacy:
            refined_legacy = ck_legacy
            print(f"resume: legacy {len(refined_legacy)} from checkpoint")
        elif not new_only:
            refined_legacy = _refine_legacy(
                llm, copy.deepcopy(legacy_src), chunk_size=legacy_chunk
            )
            _save_checkpoint(refined_legacy, ck_new)
        else:
            refined_legacy = _load_refined_legacy_from_output()

        new_scenarios: List[Dict[str, Any]] = list(ck_new) if resume else []
        if not legacy_only:
            slots = NEW_SCENARIO_SLOTS
            if max_new is not None:
                slots = slots[:max_new]
            start_idx = len(new_scenarios)
            if not single_mode:
                for b_start in range(start_idx, len(slots), batch_size):
                    batch = slots[b_start : b_start + batch_size]
                    batch_id = b_start // batch_size + 1
                    new_scenarios.extend(_generate_batch(llm, batch, batch_id))
                    _save_checkpoint(refined_legacy, new_scenarios)
                    time.sleep(0.5)
            else:
                for i, slot in enumerate(slots[start_idx:], start=start_idx):
                    idx = i + 11
                    try:
                        print(f"\n[new {i+1}/{len(slots)}] single generate {slot[0]}...")
                        sc = _generate_single(llm, slot, idx)
                        new_scenarios.append(sc)
                    except Exception as exc:
                        print(f"  FAIL slot {i}: {exc}")
                        _save_checkpoint(refined_legacy, new_scenarios)
                        raise
                    _save_checkpoint(refined_legacy, new_scenarios)
                    time.sleep(0.3)
            if len(new_scenarios) != len(slots):
                raise RuntimeError(
                    f"new scenarios {len(new_scenarios)} != expected {len(slots)}"
                )

    if legacy_only:
        all_scenarios = refined_legacy if not skip_llm else refined_legacy
        if len(all_scenarios) != 10:
            raise RuntimeError("legacy_only 应产出 10 条")
        return all_scenarios

    all_scenarios = refined_legacy + new_scenarios
    if max_new is None and len(all_scenarios) != TARGET_SCENARIOS:
        raise RuntimeError(f"scenario 数量 {len(all_scenarios)} != {TARGET_SCENARIOS}")
    names = [s["name"] for s in all_scenarios]
    if len(names) != len(set(names)):
        dup = [n for n in names if names.count(n) > 1]
        raise RuntimeError(f"重复 scenario name: {set(dup)}")
    for sc in all_scenarios:
        _validate_scenario(sc)
    return all_scenarios


def write_output(scenarios: List[Dict[str, Any]], *, annotate_stats: bool = True) -> None:
    qrels_turns = sum(
        1
        for sc in scenarios
        for t in sc["turns"]
        if t.get("relevant_mp_ids")
    )
    total_turns = sum(len(sc["turns"]) for sc in scenarios)
    arch_dist: Dict[str, int] = {}
    for sc in scenarios:
        arch_dist[sc["archetype"]] = arch_dist.get(sc["archetype"], 0) + 1

    doc = {
        "version": "2.0",
        "description": (
            "66 multi-turn OLAP dialogue scenarios for mercury/rice/heavy-metal GraphRAG. "
            "Generated via environmental-science expert draft → researcher refinement; "
            "optional Neo4j hybrid + independent LLM judge qrels (relevant_mp_ids). "
            "Diverse κ: first_turn, drill_down, roll_up, sibling_nav, drill_across."
        ),
        "generation": {
            "target_scenarios": TARGET_SCENARIOS,
            "legacy_count": 10,
            "new_count": 56,
            "archetype_distribution": arch_dist,
            "kappa_distribution": _kappa_distribution(scenarios),
            "qrels_turns": qrels_turns,
            "total_turns": total_turns,
            "retrieval_scoring": "qrels when relevant_mp_ids non-empty; else LLM judge at eval",
        },
        "scenarios": scenarios,
    }
    DEFAULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_JSON.is_file() and DEFAULT_JSON.is_file():
        BACKUP_JSON.write_text(DEFAULT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup → {BACKUP_JSON}")
    DEFAULT_JSON.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {DEFAULT_JSON} ({len(scenarios)} scenarios, {total_turns} turns)")
    if annotate_stats:
        print("archetype_distribution:", arch_dist)
        print("kappa_distribution:", doc["generation"]["kappa_distribution"])
        print(f"qrels_turns: {qrels_turns}/{total_turns}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 66 dialogue test scenarios")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Use template placeholders (no API); for structure validation",
    )
    parser.add_argument(
        "--annotate-qrels",
        action="store_true",
        help="After generation, run Neo4j hybrid + judge for relevant_mp_ids",
    )
    parser.add_argument(
        "--annotate-qrels-only",
        action="store_true",
        help="Only annotate qrels on existing dialogue_test_cases.json",
    )
    parser.add_argument(
        "--qrels-max-scenarios",
        type=int,
        default=None,
        help="Limit qrels annotation to first N scenarios",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--legacy-chunk",
        type=int,
        default=2,
        help="Legacy researcher refine chunk size (smaller = safer JSON)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume new scenario generation from checkpoint",
    )
    parser.add_argument("--legacy-only", action="store_true")
    parser.add_argument("--new-only", action="store_true")
    parser.add_argument(
        "--batch-mode",
        action="store_true",
        help="Use multi-scenario batch prompts (faster, less reliable)",
    )
    parser.add_argument(
        "--max-new",
        type=int,
        default=None,
        help="Cap count of new scenarios to generate (for incremental runs)",
    )
    args = parser.parse_args()

    _load_dotenv()
    llm = None if args.skip_llm else _make_llm()

    if args.annotate_qrels_only:
        with open(DEFAULT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        scenarios = data["scenarios"]
        if llm is None:
            llm = _make_llm()
        annotate_qrels(scenarios, llm, max_scenarios=args.qrels_max_scenarios)
        data["generation"] = data.get("generation") or {}
        data["generation"]["qrels_turns"] = sum(
            1 for sc in scenarios for t in sc["turns"] if t.get("relevant_mp_ids")
        )
        data["generation"]["kappa_distribution"] = _kappa_distribution(scenarios)
        DEFAULT_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("qrels annotation done.")
        return

    scenarios = build_corpus(
        llm,
        skip_llm=args.skip_llm,
        batch_size=args.batch_size,
        legacy_chunk=args.legacy_chunk,
        single_mode=not args.batch_mode,
        resume=args.resume,
        legacy_only=args.legacy_only,
        new_only=args.new_only,
        max_new=args.max_new,
    )

    if args.legacy_only and not args.skip_llm:
        print("legacy_only: merge with existing gen_* scenarios from JSON if present")
        if DEFAULT_JSON.is_file():
            cur = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
            cur_new = [
                s
                for s in cur.get("scenarios", [])
                if str(s.get("name", "")).startswith("gen_")
            ]
            if cur_new:
                scenarios = scenarios + cur_new
                print(f"  merged {len(cur_new)} existing gen_* scenarios")

    if args.annotate_qrels:
        if llm is None:
            llm = _make_llm()
        print("\n=== qrels annotation (Neo4j hybrid + independent judge) ===")
        annotate_qrels(scenarios, llm, max_scenarios=args.qrels_max_scenarios)

    if args.max_new is not None and len(scenarios) < TARGET_SCENARIOS and DEFAULT_JSON.is_file():
        cur = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
        legacy_part = [
            s
            for s in cur.get("scenarios", [])
            if not str(s.get("name", "")).startswith("gen_")
        ]
        legacy_names = {s["name"] for s in legacy_part}
        new_part = [s for s in scenarios if s.get("name") not in legacy_names]
        old_gens = [
            s
            for s in cur.get("scenarios", [])
            if str(s.get("name", "")).startswith("gen_")
        ]
        scenarios = legacy_part + new_part + old_gens[len(new_part) :]
        print(
            f"incremental merge: {len(legacy_part)} legacy + {len(new_part)} new LLM + "
            f"{max(0, len(old_gens) - len(new_part))} placeholders"
        )
    if len(scenarios) >= TARGET_SCENARIOS or args.legacy_only or args.max_new:
        if len(scenarios) < TARGET_SCENARIOS:
            print(f"write partial corpus ({len(scenarios)}/{TARGET_SCENARIOS})")
        write_output(scenarios)
    else:
        print(f"incomplete corpus ({len(scenarios)} scenarios); checkpoint saved, use --resume")


if __name__ == "__main__":
    main()
