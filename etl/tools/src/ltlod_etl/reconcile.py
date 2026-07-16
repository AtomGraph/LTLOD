"""Wikidata reconciliation + image enrichment for LTLOD datasets.

Matches entities to Wikidata using natural keys / closed candidate sets pulled
via WDQS (deterministic), emits owl:sameAs + image triples (foaf:depiction,
schema:logo) into the entity's own named graph, written to a separate
alignments.trig so instance re-runs never clobber alignment results.

Usage:
    ltlod-reconcile admin-units --base https://linkeddata.lt/ \
        --input counties.trig --input municipalities.trig --input elderships.trig \
        --output alignments.trig --report unmatched.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict

from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, OWL, SKOS

from . import wikidata

CV = Namespace("http://data.europa.eu/m8g/")
DCT = Namespace("http://purl.org/dc/terms/")
SCHEMA = Namespace("https://schema.org/")
ATU_TYPE = Namespace("http://publications.europa.eu/resource/authority/atu-type/")

ELDERSHIP_OF_LITHUANIA = "Q2298305"
MEMBER_OF_SEIMAS = "Q18507240"

ISO_CANDIDATES_QUERY = """
SELECT ?item ?label ?coa ?img ?logo WHERE {
    ?item wdt:P300 ?iso .
    FILTER(STRSTARTS(?iso, "LT-"))
    ?item rdfs:label ?label . FILTER(LANG(?label) = "lt")
    OPTIONAL { ?item wdt:P94 ?coa }
    OPTIONAL { ?item wdt:P18 ?img }
    OPTIONAL { ?item wdt:P154 ?logo }
}
"""

ELDERSHIP_CANDIDATES_QUERY = f"""
SELECT ?item ?label ?parent ?coa ?img WHERE {{
    ?item wdt:P31 wd:{ELDERSHIP_OF_LITHUANIA} .
    ?item rdfs:label ?label . FILTER(LANG(?label) = "lt")
    OPTIONAL {{ ?item wdt:P131 ?parent }}
    OPTIONAL {{ ?item wdt:P94 ?coa }}
    OPTIONAL {{ ?item wdt:P18 ?img }}
}}
"""


def load_units(paths: list[str]) -> list[dict]:
    """Collect (doc, entity, label, level, parent) from entity-per-graph TriG files."""
    ds = Dataset()
    for p in paths:
        ds.parse(p, format="trig")

    units = []
    for graph in ds.graphs():
        if graph.identifier == URIRef("urn:x-rdflib:default"):
            continue
        doc = graph.identifier
        entity = graph.value(doc, FOAF.primaryTopic)
        if entity is None:
            continue
        label = None
        for lbl in graph.objects(entity, SKOS.prefLabel):
            if isinstance(lbl, Literal) and lbl.language == "lt":
                label = str(lbl)
                break
        units.append({
            "doc": doc,
            "entity": entity,
            "label": label,
            "level": graph.value(entity, CV.level),
            "parent": graph.value(entity, DCT.isPartOf),
        })
    return units


def index_candidates(rows: list[dict]) -> dict[str, list[dict]]:
    by_label: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, dict] = {}
    for row in rows:
        item = row["item"]
        cand = seen.setdefault(item, {"item": item, "label": row["label"],
                                      "parents": set(), "images": set(), "logos": set()})
        if row.get("parent"):
            cand["parents"].add(row["parent"])
        for key, bucket in (("coa", "images"), ("img", "images"), ("logo", "logos")):
            if row.get(key):
                cand[bucket].add(row[key])
    for cand in seen.values():
        by_label[cand["label"].strip().casefold()].append(cand)
    return by_label


def match_units(units: list[dict], by_label: dict[str, list[dict]],
                matched_qids: dict[URIRef, str]) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Exact-label match against the closed candidate set; disambiguate by parent QID."""
    matches, unmatched = [], []
    for unit in units:
        if not unit["label"]:
            unmatched.append(unit)
            continue
        candidates = by_label.get(unit["label"].strip().casefold(), [])
        if len(candidates) > 1 and unit["parent"] in matched_qids:
            parent_qid = matched_qids[unit["parent"]]
            candidates = [c for c in candidates if parent_qid in c["parents"]]
        if len(candidates) == 1:
            matches.append((unit, candidates[0]))
            matched_qids[unit["entity"]] = candidates[0]["item"]
        else:
            unmatched.append(unit)
    return matches, unmatched


MP_CANDIDATES_QUERY = f"""
SELECT ?item ?label ?img WHERE {{
    ?item p:P39/ps:P39 wd:{MEMBER_OF_SEIMAS} .
    ?item rdfs:label ?label . FILTER(LANG(?label) IN ("lt", "en"))
    OPTIONAL {{ ?item wdt:P18 ?img }}
}}
"""


def persons(args: argparse.Namespace) -> None:
    """Reconcile persons by full name against all-time Seimas members on Wikidata."""
    units = load_units(args.input)
    # person graphs label via foaf:name (no language tag), not skos:prefLabel@lt
    ds = Dataset()
    for p in args.input:
        ds.parse(p, format="trig")
    for u in units:
        name = ds.graph(u["doc"]).value(u["entity"], FOAF.name)
        if name:
            u["label"] = str(name)

    candidates = index_candidates(wikidata.sparql(MP_CANDIDATES_QUERY))
    matches, unmatched = match_units(units, candidates, {})
    write_alignments(matches, args.output)
    report(matches, unmatched, args.report)


def admin_units(args: argparse.Namespace) -> None:
    units = load_units(args.input)
    by_level = defaultdict(list)
    for u in units:
        by_level[u["level"]].append(u)

    atu_levels = {ATU_TYPE.LTU_APS, ATU_TYPE.LTU_MSV, ATU_TYPE.LTU_RSV, ATU_TYPE.LTU_SV}
    iso_units = [u for level in atu_levels for u in by_level.get(level, [])]
    eldership_units = by_level.get(ATU_TYPE.LTU_SEN, [])

    matched_qids: dict[URIRef, str] = {}
    matches: list[tuple[dict, dict]] = []
    unmatched: list[dict] = []

    if iso_units:
        candidates = index_candidates(wikidata.sparql(ISO_CANDIDATES_QUERY))
        m, u = match_units(iso_units, candidates, matched_qids)
        matches += m
        unmatched += u
    if eldership_units:
        candidates = index_candidates(wikidata.sparql(ELDERSHIP_CANDIDATES_QUERY))
        m, u = match_units(eldership_units, candidates, matched_qids)
        matches += m
        unmatched += u

    write_alignments(matches, args.output)
    report(matches, unmatched, args.report)


def write_alignments(matches: list[tuple[dict, dict]], output: str) -> None:
    ds = Dataset()
    for unit, cand in matches:
        g = ds.graph(unit["doc"])
        g.add((unit["entity"], OWL.sameAs, URIRef(cand["item"])))
        for img in sorted(cand["images"]):
            g.add((unit["entity"], FOAF.depiction, URIRef(img)))
        for logo in sorted(cand["logos"]):
            g.add((unit["entity"], SCHEMA.logo, URIRef(logo)))
    ds.serialize(destination=output, format="trig")


def report(matches: list, unmatched: list[dict], report_path: str | None) -> None:
    total = len(matches) + len(unmatched)
    print(f"reconciled {len(matches)}/{total} entities "
          f"({sum(1 for _, c in matches if c['images'] or c['logos'])} with images)",
          file=sys.stderr)
    if report_path and unmatched:
        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["entity", "label", "level"])
            for u in unmatched:
                writer.writerow([u["entity"], u["label"], u["level"]])
        print(f"unmatched entities listed in {report_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    au = sub.add_parser("admin-units", help="Reconcile Lithuanian administrative units")
    au.add_argument("--input", action="append", required=True, help="TriG input file (repeatable)")
    au.add_argument("--output", required=True, help="alignments TriG output")
    au.add_argument("--report", help="CSV report of unmatched entities")
    au.set_defaults(func=admin_units)

    pe = sub.add_parser("persons", help="Reconcile Seimas members")
    pe.add_argument("--input", action="append", required=True, help="TriG input file (repeatable)")
    pe.add_argument("--output", required=True, help="alignments TriG output")
    pe.add_argument("--report", help="CSV report of unmatched entities")
    pe.set_defaults(func=persons)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
