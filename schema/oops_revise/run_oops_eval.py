#!/usr/bin/env python3
"""
Submit an ontology to the OOPS! online REST service and write XML + Markdown reports.

Usage (from repo root):
  python schema/oops_revise/run_oops_eval.py
  python schema/oops_revise/run_oops_eval.py --ttl schema/ttl/V6/BAE.ttl --out-dir schema/ttl/V6
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from rdflib import Graph
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
OOPS_URL = "https://oops.linkeddata.es/rest"
NS = {"oops": "http://www.oeg-upm.net/oops"}

PREFIXES = [
    ("https://bdi.whu.edu.cn/", "whu:"),
    ("http://purl.obolibrary.org/obo/", "obo:"),
    ("http://www.w3.org/ns/prov#", "prov:"),
    ("http://purl.org/mp#", "mp:"),
    ("http://purl.org/spar/cito/", "cito:"),
    ("http://purl.org/dc/terms/", "dcterms:"),
    ("http://purl.org/net/p-plan#", "p-plan:"),
    ("http://www.w3.org/2003/01/geo/wgs84_pos#", "geo:"),
    ("http://www.geonames.org/ontology#", "gn:"),
    ("https://schema.org/", "schema:"),
    ("http://schema.org/", "schema:"),
]


def short(uri: str) -> str:
    for pref, alias in PREFIXES:
        if uri.startswith(pref):
            return alias + uri[len(pref) :]
    return uri


def collect_elems(node) -> list[str]:
    out: list[str] = []
    if node is None:
        return out
    for ae in node.findall(".//oops:AffectedElement", NS):
        if ae.text and ae.text.strip():
            out.append(ae.text.strip())
    return out


def ttl_to_rdfxml(ttl: Path, rdf: Path) -> int:
    g = Graph()
    g.parse(ttl, format="turtle")
    g.serialize(destination=str(rdf), format="xml")
    return len(g)


def post_oops(rdf_xml_text: str, request_path: Path) -> bytes:
    safe = rdf_xml_text.replace("]]>", "]]]]><![CDATA[>")
    req_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<OOPSRequest>
  <OntologyUrl></OntologyUrl>
  <OntologyContent><![CDATA[{safe}]]></OntologyContent>
  <Pitfalls></Pitfalls>
  <OutputFormat>XML</OutputFormat>
</OOPSRequest>
"""
    request_path.write_text(req_xml, encoding="utf-8")
    r = requests.post(
        OOPS_URL,
        data=req_xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
        timeout=300,
    )
    r.raise_for_status()
    return r.content


def render_md(xml_bytes: bytes, ttl: Path, triple_count: int, out_md: Path) -> dict:
    root = ET.fromstring(xml_bytes)
    pitfalls = []
    for p in root.findall("oops:Pitfall", NS):
        code = (p.findtext("oops:Code", default="", namespaces=NS) or "").strip()
        name = (p.findtext("oops:Name", default="", namespaces=NS) or "").strip()
        desc = (p.findtext("oops:Description", default="", namespaces=NS) or "").strip()
        imp = (p.findtext("oops:Importance", default="", namespaces=NS) or "").strip()
        n = (p.findtext("oops:NumberAffectedElements", default="", namespaces=NS) or "").strip()
        affects = p.find("oops:Affects", NS)
        sections: list[tuple[str, list[str]]] = []
        if affects is not None:
            flat = [
                ae.text.strip()
                for ae in affects.findall("oops:AffectedElement", NS)
                if ae.text
            ]
            if flat:
                sections.append(("Elements", flat))
            for child in list(affects):
                tag = child.tag.replace("{http://www.oeg-upm.net/oops}", "")
                if tag == "AffectedElement":
                    continue
                nested = collect_elems(child)
                if nested:
                    sections.append((tag, nested))
        pitfalls.append(
            dict(code=code, name=name, desc=desc, imp=imp, n=n, sections=sections)
        )

    suggestions = []
    for s in root.findall("oops:Suggestion", NS):
        name = (s.findtext("oops:Name", default="", namespaces=NS) or "").strip()
        desc = (s.findtext("oops:Description", default="", namespaces=NS) or "").strip()
        n = (s.findtext("oops:NumberAffectedElements", default="", namespaces=NS) or "").strip()
        elems = collect_elems(s.find("oops:Affects", NS))
        suggestions.append(dict(name=name, desc=desc, n=n, elems=elems))

    warnings = root.findall("oops:Warning", NS)
    by_imp: dict[str, list] = defaultdict(list)
    for p in pitfalls:
        by_imp[p["imp"]].append(p)

    try:
        rel_ttl = ttl.resolve().relative_to(REPO).as_posix()
    except ValueError:
        rel_ttl = str(ttl)

    lines = [
        f"# OOPS! Report for {ttl.stem}",
        "",
        f"Source: [OOPS! REST]({OOPS_URL}) via OntologyContent (RDF/XML of `{rel_ttl}`)",
        f"Evaluated at (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"Ontology triples (rdflib parse): {triple_count}",
        f"Total pitfalls reported: **{len(pitfalls)}**",
        f"Warnings: **{len(warnings)}**; Suggestions: **{len(suggestions)}**",
        "",
        "HTTP status of OOPS! call: **200**",
        "",
    ]
    for imp in ("Critical", "Important", "Minor"):
        group = by_imp.get(imp, [])
        if not group:
            continue
        lines.append(f"## {imp} ({len(group)})")
        lines.append("")
        for p in sorted(group, key=lambda x: x["code"]):
            lines.append(f"### {p['code']} — {p['name']}")
            lines.append(f"- Importance: {p['imp']}")
            lines.append(f"- Affected elements: {p['n']}")
            lines.append(f"- Description: {p['desc']}")
            for title, elems in p["sections"]:
                lines.append(f"- {title}:")
                for e in elems:
                    lines.append(f"  - {short(e)}")
            lines.append("")

    if suggestions:
        lines.append(f"## Suggestions ({len(suggestions)})")
        lines.append("")
        for s in suggestions:
            lines.append(f"### {s['name'] or 'SUGGESTION'}")
            lines.append(f"- Affected elements: {s['n']}")
            lines.append(f"- Description: {s['desc']}")
            if s["elems"]:
                lines.append("- Elements:")
                for e in s["elems"]:
                    lines.append(f"  - {short(e)}")
            lines.append("")

    lines.append("## Evidence files")
    lines.append("")
    lines.append("| File | Role |")
    lines.append("|------|------|")
    lines.append(f"| `{rel_ttl}` | Input Turtle |")
    lines.append("| `*.rdf` | RDF/XML submitted as OntologyContent |")
    lines.append("| `*_oops_request.xml` | OOPSRequest wrapper |")
    lines.append("| `*_oops_report.xml` | Raw OOPS! XML response (authoritative) |")
    lines.append("| `*_oops_report.md` | This human-readable rendering |")
    lines.append("")
    lines.append(
        "This report is a human-readable rendering of the OOPS! XML response; "
        "no pitfalls were invented offline."
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "pitfalls": len(pitfalls),
        "warnings": len(warnings),
        "suggestions": len(suggestions),
        "by_imp": {k: [p["code"] for p in v] for k, v in by_imp.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="OOPS! online ontology evaluation")
    ap.add_argument(
        "--ttl",
        type=Path,
        default=REPO / "schema" / "ttl" / "V6" / "BAE.ttl",
        help="Input Turtle ontology",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: same as TTL parent)",
    )
    args = ap.parse_args()
    ttl = args.ttl if args.ttl.is_absolute() else REPO / args.ttl
    out_dir = args.out_dir or ttl.parent
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = ttl.stem
    rdf = out_dir / f"{stem}.rdf"
    req = out_dir / f"{stem}_oops_request.xml"
    xml_out = out_dir / f"{stem}_oops_report.xml"
    md_out = out_dir / f"{stem}_oops_report.md"

    print(f"Parsing {ttl} ...")
    n = ttl_to_rdfxml(ttl, rdf)
    print(f"  triples={n}, rdf={rdf}")
    print(f"POST {OOPS_URL} ...")
    xml_bytes = post_oops(rdf.read_text(encoding="utf-8"), req)
    xml_out.write_bytes(xml_bytes)
    summary = render_md(xml_bytes, ttl, n, md_out)
    print(f"Saved {xml_out}")
    print(f"Saved {md_out}")
    print(
        f"Result: pitfalls={summary['pitfalls']} "
        f"warnings={summary['warnings']} suggestions={summary['suggestions']} "
        f"by_importance={summary['by_imp']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
