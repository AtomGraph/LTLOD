"""Normalize the VMI property-declaration harvest (etl/declarations/harvest.js) to CSV.

The harvest identifies declarants by name and VMI position group only, so this step
resolves each to a person (``persons/{slug}/``) by exact full name:

- group 506 (Seimas members): the name must belong to a person whose Seimas seat
  overlaps the reporting year or the next (extracts are filed in the following spring);
- any other group (ministers, mayors, …): the name must also be a group-506 declarant
  matched above, so a namesake (a mayor sharing an MP's name) is never attached to the
  wrong person; failing that, with ``--officials`` (etl/officials/), the name must
  belong to exactly one person who held that group's office (the President, a
  Government member, a mayor, an MEP) in the reporting year or the next;
- names spelled differently by VMI and LRS resolve only through the curated
  ``--aliases`` CSV (VMI name -> asmens_id), never by fuzzy matching.

Unmatched declarants go to the report, never force-matched. A person listed under
several groups in one year filed ONE declaration; it is emitted once, with every group.

Writes two CSVs for CSV2RDF + mappings/declarations.rq: one row per declaration and
group (``--declarations``) and one per declared amount (``--items``). Category labels
resolve to ``taxonomies/asset-categories/`` notations via its source CSV; an unknown
label aborts (VMI added a category: add a row there).

Usage:
    ltlod-declarations --base https://linkeddata.lt/ --persons persons.trig \
        --categories ../taxonomies/data/asset-categories.csv --input data/vmi-fr0001.json \
        --aliases data/aliases.csv --declarations cache/declarations.csv \
        --items cache/items.csv --report cache/unmatched.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict

from rdflib import Dataset

SEIMAS_GROUP = "506"

TENURES_QUERY = """
PREFIX epvoc: <https://data.europarl.europa.eu/def/epvoc#>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX time:  <http://www.w3.org/2006/time#>
SELECT ?person ?name ?begin ?end
WHERE {
    ?person a foaf:Person ; foaf:name ?name .
    OPTIONAL {
        ?tenure org:member ?person ;
            epvoc:memberDuringParliamentaryTerm ?term ;
            org:memberDuring ?interval .
        ?interval time:hasBeginning/time:inXSDDate ?begin .
        OPTIONAL { ?interval time:hasEnd/time:inXSDDate ?end }
    }
}
"""


# VMI position group -> the office (an org:Membership in officials/persons.trig) that
# puts a declarant in it: by organization, or by role (each mayor's organization is
# their municipality). Group 519 (vice-ministers) has no office data.
GROUP_OFFICES = {
    "502": ("org", "organizations/europos-parlamentas/#this"),
    "505": ("org", "organizations/lietuvos-respublikos-vyriausybe/#this"),
    "510": ("org", "organizations/lietuvos-respublikos-prezidentas/#this"),
    "536": ("role", "taxonomies/position-types/meras/#this"),
}

OFFICES_QUERY = """
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX time:  <http://www.w3.org/2006/time#>
SELECT ?person ?name ?org ?role ?begin ?end
WHERE {
    ?office org:member ?person ;
        org:organization ?org ;
        org:role ?role ;
        org:memberDuring ?interval .
    ?person foaf:name ?name .
    ?interval time:hasBeginning/time:inXSDDate ?begin .
    OPTIONAL { ?interval time:hasEnd/time:inXSDDate ?end }
}
"""


def load_offices(paths: list[str], persons: str, base: str) -> dict[tuple[str, str], list[dict]]:
    """(group, normalized full name) -> the persons who held that group's office, with
    their office years. The Seimas persons file supplies the names of the officials who
    also held a seat (their office memberships merge into the Seimas person graphs)."""
    ds = Dataset(default_union=True)
    ds.parse(persons, format="trig", publicID=base)
    for path in paths:
        ds.parse(path, format="trig", publicID=base)
    found: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in ds.query(OFFICES_QUERY):
        m = re.search(r"/persons/([^/]+)/#this$", str(row.person))
        if not m:
            continue
        for group, (kind, path) in GROUP_OFFICES.items():
            if str(row.org if kind == "org" else row.role) != base + path:
                continue
            p = found[(group, norm(str(row.name)))].setdefault(
                m.group(1), {"id": m.group(1), "name": str(row.name), "years": set()})
            first = int(str(row.begin)[:4])
            last = int(str(row.end)[:4]) if row.end is not None else 9999
            p["years"].update(range(first, min(last, 2100) + 1))
    return {k: list(v.values()) for k, v in found.items()}


def norm(name: str) -> str:
    # stray periods occur in the LRS feed ("Vytautas. Gapšys")
    name = re.sub(r"\s+", " ", name.replace(".", " "))
    return re.sub(r"\s*-\s*", "-", name).strip().casefold()


def load_persons(path: str, base: str) -> dict[str, list[dict]]:
    """Normalized full name -> persons, each with asmens_id and seat years."""
    ds = Dataset(default_union=True)
    ds.parse(path, format="trig", publicID=base)
    persons: dict[str, dict] = {}
    for row in ds.query(TENURES_QUERY):
        uri = str(row.person)
        m = re.search(r"/persons/([^/]+)/#this$", uri)
        if not m:
            continue
        p = persons.setdefault(uri, {"id": m.group(1), "name": str(row.name), "years": set()})
        if row.begin is not None:
            first = int(str(row.begin)[:4])
            last = int(str(row.end)[:4]) if row.end is not None else 9999
            p["years"].update(range(first, min(last, 2100) + 1))
    by_name: dict[str, list[dict]] = defaultdict(list)
    for p in persons.values():
        by_name[norm(p["name"])].append(p)
    return by_name


def load_categories(path: str) -> dict[str, str]:
    """VMI category label -> asset-categories notation."""
    with open(path, newline="", encoding="utf-8") as f:
        return {row["label_lt"]: row["notation"] for row in csv.DictReader(f)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--persons", required=True)
    ap.add_argument("--categories", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--declarations", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--aliases", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--officials", action="append", default=[],
                    help="officials/persons.trig (repeatable): resolves non-Seimas declarants")
    args = ap.parse_args()

    by_name = load_persons(args.persons, args.base)
    offices = load_offices(args.officials, args.persons, args.base) if args.officials else {}
    categories = load_categories(args.categories)
    persons_by_id = {p["id"]: p for ps in by_name.values() for p in ps}
    with open(args.aliases, newline="", encoding="utf-8") as f:
        aliases = {norm(row["vmi_name"]): persons_by_id[row["asmens_id"]] for row in csv.DictReader(f)}
    with open(args.input, encoding="utf-8") as f:
        harvest = json.load(f)
    labels = harvest["labels"]
    unknown = sorted({labels[i] for q in harvest["queries"].values() for p in q["people"]
                      for i, _ in p[5]} - categories.keys())
    if unknown:
        sys.exit(f"unknown VMI asset categories (add them to {args.categories}): {unknown}")

    # flatten, group 506 first so the other groups can require a matched MP namesake
    rows = []
    for key, q in harvest["queries"].items():
        group = key.split("-")[0]
        for name, group_label, year, first_filed, updated, items in q["people"]:
            rows.append({"group": group, "group_label": group_label, "name": name, "year": year,
                         "first_filed": first_filed, "updated": updated, "items": items})
    rows.sort(key=lambda r: r["group"] != SEIMAS_GROUP)

    mp_names: dict[str, dict] = {}  # normalized name -> person, from matched group-506 rows
    declarations: dict[tuple[str, int], dict] = {}
    unmatched = []
    for r in rows:
        n = norm(r["name"])
        person = aliases.get(n)
        if person is not None:
            mp_names.setdefault(n, person)
        elif r["group"] == SEIMAS_GROUP:
            cands = [p for p in by_name.get(n, []) if r["year"] in p["years"] or r["year"] + 1 in p["years"]]
            if len(cands) == 1:
                person = cands[0]
                mp_names.setdefault(n, person)
        elif n in mp_names:
            person = mp_names[n]
        else:
            cands = [p for p in offices.get((r["group"], n), [])
                     if r["year"] in p["years"] or r["year"] + 1 in p["years"]]
            if len(cands) == 1:
                person = cands[0]
        if person is None:
            unmatched.append(r)
            continue
        key = (person["id"], r["year"])
        d = declarations.get(key)
        if d is None or r["updated"] > d["updated"]:
            groups = d["groups"] if d else {}
            d = declarations[key] = dict(r, name=person["name"], groups=groups)
        d["groups"][r["group"]] = r["group_label"]

    with open(args.declarations, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["declaration", "person", "name", "year", "first_filed", "updated", "group"])
        for (person, year), d in sorted(declarations.items()):
            for group in sorted(d["groups"]):
                w.writerow([f"{person}-{year}", person, d["name"], year,
                            d["first_filed"], d["updated"], group])
    with open(args.items, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["declaration", "category", "value"])
        for (person, year), d in sorted(declarations.items()):
            for i, value in d["items"]:
                w.writerow([f"{person}-{year}", categories[labels[i]], value])
    with open(args.report, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group", "year", "name"])
        for r in sorted(unmatched, key=lambda r: (r["group"], r["year"], r["name"])):
            w.writerow([r["group"], r["year"], r["name"]])

    print(f"{len(declarations)} declarations of {len({p for p, _ in declarations})} persons; "
          f"{len(unmatched)} unmatched rows -> {args.report}", file=sys.stderr)


if __name__ == "__main__":
    main()
