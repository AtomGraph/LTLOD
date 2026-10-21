"""Audit the name-based links to persons/: sample them for human review, then score the review.

Every link that rests on a name rather than a shared code carries ltlod:matchMethod
(taxonomies/match-methods/: alias, exact-name, name-and-office). Precision differs by link
type and method, so the sample is stratified by both: up to --per-stratum links each
(all of them in smaller strata), drawn with a fixed --seed so a re-run on unchanged data
gives the same sample.

``sample`` writes one review CSV per link type into --out. Each row puts the evidence side by
side — the source's own name and context (occupation, institution, listed position, group,
date) next to the matched person's name and the offices they held around that date — plus an
automatic note and an empty ``verdict`` column. A reviewer sets verdict to ``ok`` (the same
person), ``wrong`` (a different person) or ``unsure``, and may add a ``note``. Files that
already hold verdicts are never overwritten (--force to discard them).

``score`` reads the filled CSVs and prints precision per link type and method with a Wilson
95 % interval: with 0 wrong in 50 reviewed, precision is at least ~93 %; in 100, ~96 %.

Usage:
    ltlod-audit sample --datasets ../../datasets/current --base https://linkeddata.lt/ \
        --per-stratum 50 --seed 2026 --out reviews/
    ltlod-audit score --reviews reviews/
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

from rdflib import Dataset

from ltlod_etl.vtek import OFFICES_QUERY, office_kind, relative

PREFIXES = """
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX schema: <https://schema.org/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>
"""

# link type -> (files, query). Every query binds ?node ?method ?person ?name ?context ?date
# (?date: xsd:date or a year); the evidence a reviewer needs from the source side.
LINKS = {
    "lobbying-contacts": (["vtek/lobbying.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?declaration ltlod:contact ?node ; ltlod:activityDate ?date .
  ?node ltlod:influencedPerson ?person ; ltlod:matchMethod ?method .
  OPTIONAL { ?node ltlod:contactName ?name }
  OPTIONAL { ?node ltlod:occupation ?occupation }
  OPTIONAL { ?node ltlod:institutionName ?institution }
  BIND(CONCAT(COALESCE(STR(?occupation), ""), " | ", COALESCE(STR(?institution), "")) AS ?context)
}"""),
    "pinreg-declarants": (["vtek/interests.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a ltlod:InterestDeclaration ; ltlod:declarant ?person ; ltlod:matchMethod ?method ;
        dct:issued ?date ; dct:title ?title .
  OPTIONAL { ?node ltlod:positionName ?position }
  OPTIONAL { ?node ltlod:workplaceName ?workplace }
  BIND(STRBEFORE(STR(?title), ":") AS ?name)
  BIND(CONCAT(COALESCE(STR(?position), ""), " | ", COALESCE(STR(?workplace), "")) AS ?context)
}"""),
    "lobbyists": (["vtek/lobbyists.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a ltlod:Lobbyist ; ltlod:agent ?person ; ltlod:matchMethod ?method ; foaf:name ?name .
  OPTIONAL { ?node ltlod:registrationDate ?date }
  BIND("registered lobbyist" AS ?context)
}"""),
    "vmi-declarants": (["declarations/declarations.trig", "taxonomies/declarant-groups.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a ltlod:AssetDeclaration ; ltlod:declarant ?person ; ltlod:matchMethod ?method ;
        dct:title ?title ; dct:temporal ?year .
  OPTIONAL { ?node dct:type ?group . ?group skos:prefLabel ?groupLabel FILTER(LANG(?groupLabel) = "lt") }
  BIND(STRBEFORE(STR(?title), ":") AS ?name)
  BIND(STRBEFORE(STRAFTER(STR(?year), "/calendar/"), "/") AS ?date)
  BIND(CONCAT("VMI group: ", COALESCE(STR(?groupLabel), "?")) AS ?context)
}"""),
    "vrk-candidates": (["elections/contests.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a ltlod:CandidateResult ; ltlod:candidate ?person ; ltlod:matchMethod ?method ; schema:name ?name .
  OPTIONAL { ?node ltlod:nominatorName ?nominator }
  OPTIONAL { ?node ltlod:elected ?elected }
  BIND(REPLACE(STR(?node), "^.*/election-results/[a-z]+-([0-9]{4})-.*$", "$1") AS ?date)
  BIND(CONCAT("candidate, nominated by: ", COALESCE(STR(?nominator), "self"),
              IF(COALESCE(?elected, false), "; elected", "")) AS ?context)
}"""),
    "vrk-campaign-participants": (["elections/campaign-finance.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a ltlod:CampaignParticipant ; ltlod:campaignOf ?person ; ltlod:matchMethod ?method ;
        schema:name ?name .
  FILTER(CONTAINS(STR(?person), "/persons/"))
  OPTIONAL { ?node ltlod:campaignName ?campaign }
  BIND(REPLACE(COALESCE(STR(?campaign), ""), "^.*?([0-9]{4}).*$", "$1") AS ?date)
  BIND(CONCAT("campaign: ", COALESCE(STR(?campaign), "?")) AS ?context)
}"""),
    "officials-offices": (["officials/persons.trig"], """
SELECT ?node ?method ?person ?name ?context ?date WHERE {
  ?node a org:Membership ; org:member ?person ; ltlod:matchMethod ?method ; org:role ?role ;
        org:memberDuring/time:hasBeginning/time:inXSDDate ?date .
  BIND("" AS ?name)
  BIND(CONCAT("office from Wikidata/EP: ", REPLACE(STR(?role), "^.*/position-types/([^/]+)/#this$", "$1")) AS ?context)
}"""),
}
PERSON_FILES = ["seimas/persons.trig", "officials/persons.trig"]
NAMES_QUERY = PREFIXES + "SELECT ?person ?name WHERE { ?person a foaf:Person ; foaf:name ?name }"
COLUMNS = ["link_type", "node", "method", "source_name", "source_context", "date", "person",
           "person_name", "offices_around_date", "auto_check", "verdict", "note"]


def load(paths: list[str], base: str) -> Dataset:
    ds = Dataset(default_union=True)
    for path in paths:
        ds.parse(path, format="trig", publicID=base)
    return ds


def as_date(value: str) -> date | None:
    """An xsd:date, or a bare year (taken as its mid-year)."""
    value = (value or "").strip()
    if len(value) == 4 and value.isdigit():
        return date(int(value), 7, 1)
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def sample(args: argparse.Namespace) -> None:
    os.makedirs(args.out, exist_ok=True)
    persons = load([os.path.join(args.datasets, f) for f in PERSON_FILES], args.base)
    names = {relative(str(r.person), args.base): str(r.name) for r in persons.query(NAMES_QUERY)}
    offices: dict[str, list[tuple[str, str, date, date]]] = defaultdict(list)
    for r in persons.query(OFFICES_QUERY):
        org = relative(str(r.org), args.base)
        kind = office_kind(org)
        if kind:
            end = date.fromisoformat(str(r.end)) if r.end else date.max
            offices[relative(str(r.person), args.base)].append(
                (kind, org.rstrip("/").rsplit("/", 1)[-1] if kind == "mayor" else "", date.fromisoformat(str(r.start)), end))
    rng = random.Random(args.seed)
    totals = Counter()
    for link, (files, query) in LINKS.items():
        paths = [os.path.join(args.datasets, f) for f in files]
        if not all(os.path.exists(p) for p in paths):
            print(f"{link}: skipped, missing {[p for p in paths if not os.path.exists(p)]}", file=sys.stderr)
            continue
        out = os.path.join(args.out, f"{link}.csv")
        if os.path.exists(out) and not args.force:
            with open(out, newline="", encoding="utf-8") as f:
                if any(row.get("verdict") for row in csv.DictReader(f)):
                    print(f"{link}: {out} holds verdicts, kept (--force to resample)", file=sys.stderr)
                    continue
        ds = load(paths, args.base)
        rows = []
        for r in ds.query(PREFIXES + query):
            person = relative(str(r.person), args.base)
            method = str(r.method).rstrip("/").rsplit("/", 2)[-2]
            rows.append({"node": relative(str(r.node), args.base), "method": method, "person": person,
                         "source_name": str(r.name or ""), "source_context": str(r.context or "").strip(" |"),
                         "date": str(r.date or "")})
        if not rows:
            print(f"{link}: no name-based links (yet), no review file", file=sys.stderr)
            continue
        strata: dict[str, list[dict]] = defaultdict(list)
        for row in sorted(rows, key=lambda x: x["node"]):  # deterministic order before sampling
            strata[row["method"]].append(row)
        picked = []
        for method, group in sorted(strata.items()):
            totals[(link, method)] = len(group)
            picked += group if len(group) <= args.per_stratum else rng.sample(group, args.per_stratum)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, COLUMNS)
            w.writeheader()
            for row in sorted(picked, key=lambda x: (x["method"], x["node"])):
                day = as_date(row["date"])
                # one span per office (kind, place) overlapping [date - 400 d, date + 60 d]: a
                # Seimas member also belongs to groups and committees, which add nothing here
                spans: dict[tuple[str, str], list[date]] = {}
                for kind, where, start, end in offices.get(row["person"], []):
                    if day and start <= day + timedelta(days=60) and end >= day - timedelta(days=400):
                        s = spans.setdefault((kind, where), [start, end])
                        s[0], s[1] = min(s[0], start), max(s[1], end)
                near = [f"{kind}{'(' + where + ')' if where else ''} {s}–{'' if e == date.max else e}"
                        for (kind, where), (s, e) in sorted(spans.items(), key=lambda x: x[1][0])]
                auto = {"name-and-office": "name and an office held then agree",
                        "alias": "curated alias", "exact-name": "name only: context does not confirm"}[row["method"]]
                w.writerow({**row, "link_type": link, "person_name": names.get(row["person"], "?"),
                            "offices_around_date": "; ".join(near) or "none on record",
                            "auto_check": auto, "verdict": "", "note": ""})
        print(f"{link}: {len(picked)} of {len(rows)} sampled -> {out}", file=sys.stderr)
    with open(os.path.join(args.out, "population.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["link_type", "method", "links"])
        for (link, method), n in sorted(totals.items()):
            w.writerow([link, method, n])


def wilson(ok: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = ok / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def score(args: argparse.Namespace) -> None:
    counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for path in sorted(glob.glob(os.path.join(args.reviews, "*.csv"))):
        if path.endswith("population.csv"):
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                verdict = (row.get("verdict") or "").strip().lower() or "unreviewed"
                if verdict not in ("ok", "wrong", "unsure", "unreviewed"):
                    sys.exit(f"{path}: unknown verdict {verdict!r} (ok / wrong / unsure)")
                counts[(row["link_type"], row["method"])][verdict] += 1
    population = {}
    pop_path = os.path.join(args.reviews, "population.csv")
    if os.path.exists(pop_path):
        with open(pop_path, newline="", encoding="utf-8") as f:
            population = {(r["link_type"], r["method"]): int(r["links"]) for r in csv.DictReader(f)}
    print("| link type | method | links | reviewed | wrong | unsure | precision | 95 % interval |")
    print("|---|---|---:|---:|---:|---:|---:|---|")
    for (link, method), c in sorted(counts.items()):
        judged = c["ok"] + c["wrong"]
        lo, hi = wilson(c["ok"], judged)
        precision = f"{c['ok'] / judged:.1%}" if judged else "—"
        interval = f"{lo:.1%} – {hi:.1%}" if judged else "—"
        print(f"| {link} | {method} | {population.get((link, method), '?')} | {judged + c['unsure']} | "
              f"{c['wrong']} | {c['unsure']} | {precision} | {interval} |")
    unreviewed = sum(c["unreviewed"] for c in counts.values())
    if unreviewed:
        print(f"\n{unreviewed} sampled links not reviewed yet.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample", help="draw the review sample")
    s.add_argument("--datasets", required=True)
    s.add_argument("--base", required=True)
    s.add_argument("--per-stratum", type=int, default=50)
    s.add_argument("--seed", type=int, default=2026)
    s.add_argument("--out", required=True)
    s.add_argument("--force", action="store_true")
    r = sub.add_parser("score", help="precision from the filled review CSVs")
    r.add_argument("--reviews", required=True)
    args = ap.parse_args()
    sample(args) if args.command == "sample" else score(args)


if __name__ == "__main__":
    main()
