#!/usr/bin/env python3
"""
Apply OOPS!-driven fixes to BAE_v3_clean.ttl and write schema/ttl/V6/BAE.ttl.

Independent of kg_build_pipeline / Neo4j runtime. Fixes map to OOPS report for
BAE_v3_clean (Important: P10/P11; Minor: P04/P08/P32). Skips P13 and the
symmetric/transitive suggestion (would distort extraction semantics).

Usage (from repo root):
  python schema/oops_revise/apply_oops_fixes.py
"""
from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, BNode
from rdflib.collection import Collection

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "schema" / "ttl" / "BAE_v3_clean.ttl"
OUT_DIR = REPO / "schema" / "ttl" / "V6"
OUT_TTL = OUT_DIR / "BAE.ttl"

WHU = Namespace("https://bdi.whu.edu.cn/")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")
ENVO = Namespace("http://purl.obolibrary.org/obo/ENVO_")
OBI = Namespace("http://purl.obolibrary.org/obo/OBI_")
MP = Namespace("http://purl.org/mp#")
PPLAN = Namespace("http://purl.org/net/p-plan#")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
GN = Namespace("http://www.geonames.org/ontology#")
SCHEMA = Namespace("https://schema.org/")

OLD_ONT = WHU["BAE_v3_clean"]
NEW_ONT = WHU["BAE"]


def _en(text: str) -> Literal:
    return Literal(text, lang="en")


def _ensure_label_comment(g: Graph, s, label: str | None = None, comment: str | None = None) -> None:
    if label and not list(g.objects(s, RDFS.label)):
        g.add((s, RDFS.label, _en(label)))
    if comment and not list(g.objects(s, RDFS.comment)):
        g.add((s, RDFS.comment, _en(comment)))


def _union(g: Graph, members) -> BNode:
    node = BNode()
    g.add((node, RDF.type, OWL.Class))
    col = BNode()
    Collection(g, col, list(members))
    g.add((node, OWL.unionOf, col))
    return node


def apply_fixes(g: Graph) -> list[str]:
    log: list[str] = []

    # --- Ontology IRI / version ---
    for p, o in list(g.predicate_objects(OLD_ONT)):
        g.remove((OLD_ONT, p, o))
        g.add((NEW_ONT, p, o))
    g.set((NEW_ONT, RDF.type, OWL.Ontology))
    g.set((NEW_ONT, RDFS.label, _en("BAE Ontology")))
    g.set(
        (
            NEW_ONT,
            RDFS.comment,
            _en(
                "BAE (Background–Argumentation–Experiment) core ontology. "
                "Derived from BAE_v3_clean with OOPS!-driven repairs (P10/P11/P04/P08/P32)."
            ),
        )
    )
    g.set((NEW_ONT, OWL.versionInfo, Literal("6.0-oops")))
    log.append("Renamed ontology IRI to https://bdi.whu.edu.cn/BAE (version 6.0-oops)")

    # --- P11: domains for datatype properties missing domain ---
    named_entities = _union(
        g,
        [
            IAO["0000030"],
            WHU.ResearchMaterial,
            PPLAN.Plan,
            PPLAN.Step,
            PROV.Entity,
            PROV.Location,
            WHU.SemanticModule,
        ],
    )
    for prop in (WHU.hasName, WHU.hasOriginalText):
        for old in list(g.objects(prop, RDFS.domain)):
            g.remove((prop, RDFS.domain, old))
        g.add((prop, RDFS.domain, named_entities))
    g.set(
        (WHU.hasName, RDFS.comment, _en("Canonical short name of a BAE entity grounded in source text."))
    )
    g.set(
        (WHU.hasOriginalText, RDFS.comment, _en("Verbatim source-text span supporting creation of the entity."))
    )

    # isAboutDimension: edge-style attribute; domain on ICE subject of aboutness
    for old in list(g.objects(WHU.isAboutDimension, RDFS.domain)):
        g.remove((WHU.isAboutDimension, RDFS.domain, old))
    g.add((WHU.isAboutDimension, RDFS.domain, IAO["0000030"]))
    g.set(
        (
            WHU.isAboutDimension,
            RDFS.comment,
            _en(
                "Optional measurement-dimension tag for iao:is_about. In Neo4j it is stored "
                "as an edge property; in OWL the approximate domain is the ICE subject."
            ),
        )
    )
    log.append("P11: added rdfs:domain for hasName, hasOriginalText, isAboutDimension")

    # --- P32: distinct label for whu:DataSet vs IAO_0000100 ---
    g.set((WHU.DataSet, RDFS.label, _en("BAE scientific dataset")))
    log.append("P32: relabeled whu:DataSet to avoid same-label clash with IAO_0000100")

    # --- P04: connect EBM/EEM/MPU via SemanticModule + belongsToModule ---
    g.add((WHU.SemanticModule, RDF.type, OWL.Class))
    g.set((WHU.SemanticModule, RDFS.label, _en("BAE semantic module")))
    g.set(
        (
            WHU.SemanticModule,
            RDFS.comment,
            _en(
                "Abstract grouping for EBM/EEM/MPU documentation views. Not materialized as KG instances."
            ),
        )
    )
    for mod in (WHU.EBM, WHU.EEM, WHU.MPU):
        g.add((mod, RDFS.subClassOf, WHU.SemanticModule))

    g.add((WHU.belongsToModule, RDF.type, OWL.ObjectProperty))
    g.set((WHU.belongsToModule, RDFS.label, _en("belongs to module")))
    g.set(
        (
            WHU.belongsToModule,
            RDFS.comment,
            _en(
                "Documentation link from a BAE domain class to its semantic module (EBM/EEM/MPU). "
                "Not used by Neo4j extraction."
            ),
        )
    )
    g.add(
        (
            WHU.belongsToModule,
            RDFS.domain,
            _union(
                g,
                [
                    WHU.EnvironmentFeature,
                    WHU.SpecimenCollection,
                    WHU.SpecimenPreprocessing,
                    WHU.Specimen,
                    WHU.ProcessedSpecimen,
                    WHU.BioChemicalExperiment,
                    WHU.ComputationalExperiment,
                    WHU.ResearchStep,
                    WHU.DataSet,
                    WHU.ScienceEvidence,
                    WHU.SupportGraph,
                    MP.Claim,
                    MP.Statement,
                    MP.Method,
                    MP.Attribution,
                    MP.Reference,
                ],
            ),
        )
    )
    g.add(
        (
            WHU.belongsToModule,
            RDFS.range,
            _union(g, [WHU.EBM, WHU.EEM, WHU.MPU]),
        )
    )
    # Anchor imported classes that OOPS flagged as unconnected via subclass/comments
    _ensure_label_comment(g, PPLAN.Step, "step", "P-PLAN step; BAE ResearchStep specializes this class.")
    g.add((WHU.ResearchStep, RDFS.subClassOf, PPLAN.Step))  # already present; ensure
    _ensure_label_comment(g, PROV.Location, "location", "PROV location; BAE EnvironmentFeature specializes this.")
    _ensure_label_comment(g, BFO["0000031"], "generically dependent continuant")
    _ensure_label_comment(g, BFO["0000040"], "material entity")
    _ensure_label_comment(g, BFO["0000015"], "process")
    _ensure_label_comment(g, BFO["0000023"], "role")
    _ensure_label_comment(g, ENVO["00002297"], "environmental feature")
    log.append("P04: SemanticModule hierarchy + belongsToModule; labels on flagged anchors")

    # --- P10: disjointness (only among siblings; never class vs its superclass) ---
    def disjoint_all(classes):
        for i, a in enumerate(classes):
            for b in classes[i + 1 :]:
                g.add((a, OWL.disjointWith, b))

    disjoint_all([WHU.EBM, WHU.EEM, WHU.MPU])
    disjoint_all(
        [
            WHU.SpecimenCollection,
            WHU.SpecimenPreprocessing,
            WHU.BioChemicalExperiment,
            WHU.ComputationalExperiment,
        ]
    )
    disjoint_all([WHU.Specimen, WHU.ProcessedSpecimen, WHU.ChemicalEntity])
    disjoint_all([WHU.Device, WHU.Reagent])
    disjoint_all([WHU.ScienceEvidence, WHU.SupportGraph])
    disjoint_all([MP.Attribution, MP.Reference, MP.Method, MP.Data])
    # Claim ⊑ Statement: do not disjoint Claim with Statement
    g.add((MP.Attribution, OWL.disjointWith, MP.Statement))
    g.add((MP.Reference, OWL.disjointWith, MP.Statement))
    g.add((MP.Method, OWL.disjointWith, MP.Statement))
    g.add((MP.Data, OWL.disjointWith, MP.Statement))
    g.add((WHU.Goal, OWL.disjointWith, WHU.TargetVariable))
    g.add((WHU.Goal, OWL.disjointWith, WHU.Software))
    g.add((WHU.Software, OWL.disjointWith, WHU.TargetVariable))
    log.append("P10: added owl:disjointWith axioms among sibling domain classes")

    # --- P08: labels/comments on elements missing human-readable annotations ---
    class_ann = {
        MP.Representation: ("representation", "Micropublication representation (information content)."),
        MP.Statement: ("statement", "Evaluable proposition; Claim is a specialized Statement."),
        MP.Claim: ("claim", "Focal argumentative proposition."),
        MP.Data: ("data", "Micropublication data representation."),
        MP.Method: ("method", "Named scientific method as information content."),
        MP.Attribution: ("attribution", "Provenance qualifier for a representation."),
        MP.Reference: ("reference", "Cited bibliographic or dataset source."),
        PROV.Entity: ("entity", "PROV entity."),
        PROV.Activity: ("activity", "PROV activity / process."),
        PROV.Collection: ("collection", "PROV collection."),
        PROV.Plan: ("PROV plan", "PROV-O plan entity."),
        PPLAN.Plan: ("P-PLAN plan", "P-PLAN plan; BAE mid-level plans specialize this."),
        PPLAN.Step: ("P-PLAN step", "P-PLAN step; BAE ResearchStep specializes this class."),
        IAO["0000109"]: ("measurement datum", "IAO measurement datum."),
    }
    for s, (lab, com) in class_ann.items():
        # Force distinct labels where OOPS P32 previously collided
        if s in (PROV.Plan, PPLAN.Plan, PPLAN.Step):
            g.set((s, RDFS.label, _en(lab)))
            if not list(g.objects(s, RDFS.comment)):
                g.add((s, RDFS.comment, _en(com)))
        else:
            _ensure_label_comment(g, s, lab, com)

    # Imported OBO anchors: ensure both label and comment (OOPS P08)
    obo_ann = [
        (BFO["0000031"], "generically dependent continuant", "BFO generically dependent continuant."),
        (BFO["0000040"], "material entity", "BFO material entity."),
        (BFO["0000015"], "process", "BFO process."),
        (BFO["0000023"], "role", "BFO role."),
        (ENVO["00002297"], "environmental feature", "ENVO environmental feature."),
        (ENVO["00010483"], "environmental material", "ENVO environmental material."),
        (IAO["0000030"], "information content entity", "IAO information content entity."),
        (IAO["0000100"], "IAO data set", "IAO data set class (distinct from whu:DataSet)."),
        (IAO["0000027"], "data item", "IAO data item."),
        (IAO["0000032"], "scalar measurement datum", "IAO scalar measurement datum."),
        (OBI["0100026"], "organism", "OBI organism."),
    ]
    for s, lab, com in obo_ann:
        g.set((s, RDFS.label, _en(lab)))
        g.set((s, RDFS.comment, _en(com)))

    prop_comments = {
        WHU.hasTarget: "Links a Goal to its TargetVariable.",
        WHU.hasGoal: "Links an experiment plan to an explicit Goal.",
        WHU.declaredInput: "Step-level declared input entity.",
        WHU.declaredOutput: "Step-level declared output entity.",
        WHU.declaredUsed: "Step-level declared used resource.",
        WHU.hasContext: "Collection plan environmental context.",
        WHU.fellow: "Mid-level upstream adjacency between plans/experiments.",
        WHU.researchType: "Controlled research-step type string.",
        WHU.hasComparator: "Optional comparator on a scalar measurement.",
        WHU.softwareBrand: "Software vendor/brand when stated.",
        CITO.isCitedBy: "Cited reference is cited by a representation.",
        PROV.wasDerivedFrom: "Material/provenance derivation.",
        PROV.hadMember: "Collection membership.",
        PROV.atLocation: "Entity or step located at an environment feature.",
        PPLAN.isStepOfPlan: "ResearchStep membership in a plan.",
        PPLAN.isPrecededBy: "Ordering between research steps.",
        PPLAN.correspondsToStep: "Executed activity corresponds to a research step.",
        PPLAN.isInputVarOf: "Plan-level input shortcut.",
        PPLAN.isOutputVarOf: "Plan-level output shortcut.",
        DCTERMS.hasPart: "DataSet contains DataItem members.",
        MP.supports: "Positive argumentative support.",
        MP.challenges: "Negative argumentative challenge.",
        BFO["0000051"]: "Mereological has-part.",
        IAO["0000136"]: "Information-content aboutness.",
        IAO["0000004"]: "Numeric measurement value.",
        GEO.lat: "Latitude of an environment feature.",
        GEO.long: "Longitude of an environment feature.",
        GEO.alt: "Altitude of an environment feature.",
        GN.population: "Stated population for an environment feature.",
        SCHEMA.brand: "Device brand/manufacturer.",
        SCHEMA.model: "Device model designation.",
        SCHEMA.serialNumber: "Device serial number.",
        SCHEMA.softwareVersion: "Software version string.",
    }
    for s, com in prop_comments.items():
        _ensure_label_comment(g, s, comment=com)
        if not list(g.objects(s, RDFS.label)):
            # fallback short label from local name
            local = str(s).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            g.add((s, RDFS.label, _en(local)))

    # Ensure labels exist on BFO/IAO/OBI anchors already partly labeled
    for s, lab in [
        (IAO["0000030"], "information content entity"),
        (IAO["0000100"], "IAO data set"),
        (IAO["0000027"], "data item"),
        (IAO["0000032"], "scalar measurement datum"),
        (OBI["0100026"], "organism"),
        (ENVO["00010483"], "environmental material"),
    ]:
        _ensure_label_comment(g, s, lab)

    log.append("P08: ensured rdfs:label/rdfs:comment on previously unannotated elements")
    log.append("Skipped P13 (inverseOf) and symmetric/transitive suggestion by design")
    return log


def main() -> int:
    if not SRC.is_file():
        raise SystemExit(f"Missing source ontology: {SRC}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    g = Graph()
    g.bind("whu", WHU)
    g.bind("bfo", BFO)
    g.bind("iao", IAO)
    g.bind("envo", ENVO)
    g.bind("obi", OBI)
    g.bind("mp", MP)
    g.bind("p-plan", PPLAN)
    g.bind("prov", PROV)
    g.bind("cito", CITO)
    g.bind("dcterms", DCTERMS)
    g.bind("geo", GEO)
    g.bind("gn", GN)
    g.bind("schema", SCHEMA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)

    g.parse(SRC, format="turtle")
    log = apply_fixes(g)
    g.serialize(destination=str(OUT_TTL), format="turtle")

    changelog = OUT_DIR / "CHANGELOG_OOPS.md"
    lines = [
        "# BAE.ttl OOPS! revision changelog",
        "",
        f"- Source: `{SRC.relative_to(REPO).as_posix()}`",
        f"- Output: `{OUT_TTL.relative_to(REPO).as_posix()}`",
        f"- Triples after revision: {len(g)}",
        "",
        "## Applied fixes",
        "",
    ]
    for item in log:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Intentionally not applied")
    lines.append("")
    lines.append("- P13 (`owl:inverseOf`): extraction / Neo4j use single-direction edges.")
    lines.append("- Suggestion (symmetric/transitive on supports/challenges/isPrecededBy): semantically incorrect for BAE.")
    changelog.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_TTL} ({len(g)} triples)")
    for item in log:
        print(" ", item)
    print(f"Wrote {changelog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
