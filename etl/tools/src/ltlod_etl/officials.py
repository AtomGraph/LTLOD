"""Public officials beyond the Seimas: the President, the Government, mayors, MEPs.

Two subcommands, the fetch and normalize stages of etl/officials/:

``fetch`` pulls the raw sources into a cache directory:

- Wikidata (WDQS, CC0): position-held (P39) statements, with start/end qualifiers, of
  the President of Lithuania, the Prime Minister and the ministers (every position
  that is a subclass of minister Q83307 for Lithuania — each must be listed in the
  curated ``--positions`` CSV, an unknown one aborts) and the mayors of the 60
  municipalities (positions that are a subclass of mayor Q30185 whose P1001 is one
  of the municipalities aligned in admin-units/alignments.trig);
- the European Parliament open data API (CC BY 4.0): every MEP elected in Lithuania
  with their mandates (``MEMBER_PARLIAMENT`` memberships representing LTU), and the
  Wikidata items carrying their EP id (P1186), which unify them with the rest.

``normalize`` resolves everyone to ONE person document:

- a person aligned to Wikidata in seimas/alignments.trig (owl:sameAs) keeps their
  Seimas document ``persons/{asmens_id}/`` — the office memberships are written into
  that same named graph and merge with it on load (like alignments.trig);
- anyone else gets ``persons/{QID}/`` (a Wikidata id; ``Q`` keeps it disjoint from the
  numeric asmens_id), or ``persons/ep-{id}/`` for an MEP without a Wikidata item.

and writes three CSVs for CSV2RDF + mappings/officials.rq / position-types.rq:
one row per person document, one per office held, one per position concept.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time

import httpx
from rdflib import Dataset

from ltlod_etl.wikidata import USER_AGENT, sparql

EP_API = "https://data.europarl.europa.eu/api/v2/meps"
WD = "http://www.wikidata.org/entity/"
MAYOR_QID = "Q30185"
SINCE = "1990-03-11"  # Act of the Re-Establishment of the State of Lithuania
MEP_QID = "Q27169"
GENDERS = {WD + "Q6581097": "male", WD + "Q6581072": "female",
           "http://publications.europa.eu/resource/authority/human-sex/MALE": "male",
           "http://publications.europa.eu/resource/authority/human-sex/FEMALE": "female"}

# organization documents (app/organizations/*.ttl scaffolding) per office kind;
# a mayor's organization is their municipality (admin-units/{sav_kodas}/)
ORGANIZATIONS = {
    "president": "organizations/lietuvos-respublikos-prezidentas/",
    "government": "organizations/lietuvos-respublikos-vyriausybe/",
    "mep": "organizations/europos-parlamentas/",
}
# position concepts that are not read from --positions
FIXED_ROLES = [
    {"wikidata": MAYOR_QID, "kind": "mayor", "slug": "meras", "label_lt": "Meras", "label_en": "Mayor"},
    {"wikidata": MEP_QID, "kind": "mep", "slug": "europos-parlamento-narys",
     "label_lt": "Europos Parlamento narys", "label_en": "Member of the European Parliament"},
]

POSITIONS_QUERY = """
SELECT DISTINCT ?pos WHERE {
  ?pos wdt:P279* wd:Q83307 .
  { ?pos wdt:P1001 wd:Q37 } UNION { ?pos wdt:P17 wd:Q37 }
  ?person p:P39/ps:P39 ?pos .
}
"""

OFFICES_QUERY = """
SELECT ?person ?pos ?muni ?start ?end ?lt ?en ?gender WHERE {
  { VALUES ?pos { %(positions)s } }
  UNION
  { VALUES ?muni { %(municipalities)s } ?pos wdt:P279 wd:%(mayor)s ; wdt:P1001 ?muni . }
  ?person p:P39 ?st . ?st ps:P39 ?pos ; wikibase:rank ?rank .
  FILTER (?rank != wikibase:DeprecatedRank)
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?person rdfs:label ?lt FILTER (LANG(?lt) = "lt") }
  OPTIONAL { ?person rdfs:label ?en FILTER (LANG(?en) = "en") }
  OPTIONAL { ?person wdt:P21 ?gender }
}
"""

EP_IDS_QUERY = """
SELECT ?person ?ep WHERE { VALUES ?ep { %s } ?person wdt:P1186 ?ep . }
"""


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def municipality_qids(municipalities: str, alignments: str, base: str) -> dict[str, str]:
    """Wikidata QID -> sav_kodas of the municipalities (cv:AdminUnit in municipalities.trig)."""
    ds = Dataset(default_union=True)
    ds.parse(municipalities, format="trig", publicID=base)
    ds.parse(alignments, format="trig", publicID=base)
    q = """PREFIX owl: <http://www.w3.org/2002/07/owl#> PREFIX cv: <http://data.europa.eu/m8g/>
           SELECT ?unit ?wd WHERE { ?unit a cv:AdminUnit ; owl:sameAs ?wd }"""
    out = {}
    for row in ds.query(q):
        m = re.search(r"/admin-units/([0-9]+)/#this$", str(row.unit))
        if m and str(row.wd).startswith(WD):
            out[str(row.wd)[len(WD):]] = m.group(1)
    if len(out) != 60:
        sys.exit(f"expected 60 municipalities aligned to Wikidata, got {len(out)}")
    return out


def fetch(args: argparse.Namespace) -> None:
    os.makedirs(args.out_dir, exist_ok=True)
    positions = {r["wikidata"] for r in read_csv(args.positions)}

    found = {r["pos"][len(WD):] for r in sparql(POSITIONS_QUERY)}
    unknown = sorted(found - positions)
    if unknown:
        sys.exit(f"unknown Wikidata minister positions (add them to {args.positions}): {unknown}")

    munis = municipality_qids(args.municipalities, args.alignments, args.base)
    rows = sparql(OFFICES_QUERY % {
        "positions": " ".join(f"wd:{q}" for q in sorted(positions)),
        "municipalities": " ".join(f"wd:{q}" for q in sorted(munis)),
        "mayor": MAYOR_QID,
    })
    if not rows:
        sys.exit("WDQS returned no office holders")
    with open(os.path.join(args.out_dir, "wikidata-offices.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)

    client = httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "application/ld+json"},
                          timeout=60, follow_redirects=True)

    def get(url: str, params: dict) -> dict:
        for attempt in range(4):
            try:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        return {}

    fmt = {"format": "application/ld+json"}
    meps = get(EP_API, {"country-of-representation": "LT", "offset": 0, "limit": 1000, **fmt})["data"]
    if not meps:
        sys.exit("EP API returned no Lithuanian MEPs")
    details = []
    for mep in meps:
        details.extend(get(f"{EP_API}/{mep['identifier']}", fmt)["data"])
        time.sleep(0.2)
    with open(os.path.join(args.out_dir, "ep-meps.json"), "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=0)

    ids = " ".join(f'"{m["identifier"]}"' for m in meps)
    with open(os.path.join(args.out_dir, "wikidata-ep-ids.json"), "w", encoding="utf-8") as f:
        json.dump(sparql(EP_IDS_QUERY % ids), f, ensure_ascii=False, indent=0)
    print(f"{len(rows)} Wikidata office statements, {len(details)} MEPs", file=sys.stderr)


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace(".", " ")).strip().casefold()


def name_keys(name: str) -> tuple[str, str]:
    """(full name, first given name + family name), normalized: LRS often spells a middle
    name Wikidata leaves out ("Algirdas Mykolas Brazauskas" / "Algirdas Brazauskas")."""
    tokens = norm(name).split(" ")
    return " ".join(tokens), f"{tokens[0]} {tokens[-1]}"


def seimas_persons(persons: str, alignments: str, base: str) -> tuple[dict[str, str], dict[str, str], dict[str, set[str]]]:
    """Of the Seimas persons: QID -> asmens_id, asmens_id -> document title, and a name
    index (both name_keys -> asmens_ids; unaligned-only keys prefixed with "u:")."""
    ds = Dataset(default_union=True)
    ds.parse(persons, format="trig", publicID=base)
    ds.parse(alignments, format="trig", publicID=base)
    q = """PREFIX owl: <http://www.w3.org/2002/07/owl#> PREFIX foaf: <http://xmlns.com/foaf/0.1/>
           PREFIX dct: <http://purl.org/dc/terms/>
           SELECT ?doc ?title ?wd WHERE { ?doc foaf:primaryTopic ?p ; dct:title ?title .
                                          ?p a foaf:Person . OPTIONAL { ?p owl:sameAs ?wd } }"""
    by_qid, titles = {}, {}
    for row in ds.query(q):
        m = re.search(r"/persons/([^/]+)/$", str(row.doc))
        if not m:
            continue
        titles[m.group(1)] = str(row.title)
        if row.wd is not None and str(row.wd).startswith(WD):
            by_qid[str(row.wd)[len(WD):]] = m.group(1)
    aligned = set(by_qid.values())
    names: dict[str, set[str]] = {}
    for slug, title in titles.items():
        full, short = name_keys(title)
        names.setdefault(full, set()).add(slug)
        if slug not in aligned:
            names.setdefault("u:" + full, set()).add(slug)
            names.setdefault("u:" + short, set()).add(slug)
    return by_qid, titles, names


def date(value: str | None) -> str:
    # WDQS dateTimes ("1990-03-17T00:00:00Z") and EP dates ("2019-07-02") -> xsd:date
    return value[:10] if value else ""


def split_name(name: str) -> tuple[str, str]:
    # Lithuanian names: the family name is the last token (double-barrelled family
    # names are hyphenated, so they stay one token); everything before is given names
    given, _, family = name.strip().rpartition(" ")
    return given, family


def normalize(args: argparse.Namespace) -> None:
    by_qid, seimas_titles, names = seimas_persons(args.persons, args.seimas_alignments, args.base)
    munis = municipality_qids(args.municipalities, args.alignments, args.base)
    positions = {r["wikidata"]: r for r in read_csv(args.positions)}
    with open(os.path.join(args.cache, "wikidata-offices.json"), encoding="utf-8") as f:
        wd_rows = json.load(f)
    with open(os.path.join(args.cache, "ep-meps.json"), encoding="utf-8") as f:
        meps = json.load(f)
    with open(os.path.join(args.cache, "wikidata-ep-ids.json"), encoding="utf-8") as f:
        ep_qid = {r["ep"]: r["person"][len(WD):] for r in json.load(f)}

    people: dict[str, dict] = {}  # slug -> person row
    name_matched: set[str] = set()  # Seimas persons reused by a unique name, not an aligned QID
    offices: dict[str, dict] = {}  # (slug, fragment) -> office row

    def person(qid: str | None, ep: str | None, name: str, gender: str | None) -> str:
        # Officials the Seimas alignment cannot place reuse a Seimas person by name, only
        # when exactly one matches: one with a Wikidata item is matched against Seimas
        # persons aligned to NO item (full name, else first given + family name — LRS
        # spells middle names Wikidata leaves out); an MEP without a Wikidata item
        # against every Seimas person, by full name. Anyone else is a new person.
        full, short = name_keys(name)
        if qid:
            namesakes = names.get("u:" + full) or names.get("u:" + short) or set()
        else:
            namesakes = names.get(full, set())
        if qid and qid in by_qid:
            slug = by_qid[qid]
        elif len(namesakes) == 1:
            slug = next(iter(namesakes))
            name_matched.add(slug)
        elif qid:
            slug = qid
        else:
            slug = f"ep-{ep}"
        p = people.get(slug)
        if p is None:
            seimas = slug in seimas_titles
            given, family = split_name(name)
            p = people[slug] = {
                "slug": slug, "seimas": "true" if seimas else "false",
                "title": seimas_titles[slug] if seimas else name,
                "given": given, "family": family, "name": name,
                "gender": gender or "", "wikidata": qid or "", "ep": ep or "",
            }
        if ep and not p["ep"]:
            p["ep"] = ep
        if gender and not p["gender"]:
            p["gender"] = gender
        return slug

    def office(slug: str, role: str, org: str, key: str, start: str, end: str) -> None:
        fragment = f"office-{key}-{start.replace('-', '')}"
        # restored independence only (the calendar starts in 1990): Wikidata's
        # Lithuanian positions also hold the interwar Presidents and ministers, and
        # undated statements cannot be placed in time at all
        if not start or (end or "9999") < SINCE:
            return
        offices.setdefault((slug, fragment), {"person": slug, "fragment": fragment, "role": role,
                                              "organization": org, "from": start, "to": end})

    # Wikidata: the President, the Government, mayors
    for r in wd_rows:
        qid = r["person"][len(WD):]
        name = r.get("lt") or r.get("en")
        if not name or not re.fullmatch(r"Q[0-9]+", qid):
            continue
        slug = person(qid, None, name, GENDERS.get(r.get("gender", "")))
        start, end = date(r.get("start")), date(r.get("end"))
        if "muni" in r:
            sav = munis[r["muni"][len(WD):]]
            office(slug, "meras", f"admin-units/{sav}/", f"meras-{sav}", start, end)
        else:
            pos = positions[r["pos"][len(WD):]]
            office(slug, pos["slug"], ORGANIZATIONS[pos["kind"]], pos["slug"], start, end)

    # European Parliament: mandates representing Lithuania
    for m in meps:
        ep = m["identifier"]
        name = f"{m.get('givenName', '')} {m.get('familyName', '')}".strip() or m["label"]
        slug = person(ep_qid.get(ep), ep, name, GENDERS.get(m.get("hasGender", "")))
        for ms in m.get("hasMembership", []):
            if (ms.get("role") == "def/ep-roles/MEMBER_PARLIAMENT"
                    and "http://publications.europa.eu/resource/authority/country/LTU" in ms.get("represents", [])):
                term = ms["organization"].removeprefix("org/")  # ep-9
                period = ms.get("memberDuring", {})
                office(slug, "europos-parlamento-narys", ORGANIZATIONS["mep"], term,
                       date(period.get("startDate")), date(period.get("endDate")))

    # persons whose every office predates 1990 (interwar) or is undated are dropped
    held = {o["person"] for o in offices.values()}
    people = {slug: p for slug, p in people.items() if slug in held}

    with open(args.persons_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["slug", "seimas", "title", "given", "family", "name", "gender", "wikidata", "ep"])
        w.writeheader()
        w.writerows(sorted(people.values(), key=lambda p: p["slug"]))
    # how each office was attributed to an existing Seimas person (taxonomies/match-methods/):
    # exact-name for a reuse by unique name; none for a Wikidata-aligned QID (a code join)
    # or a person this pipeline mints itself
    for o in offices.values():
        o["person_method"] = "exact-name" if o["person"] in name_matched else ""
    with open(args.offices_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["person", "fragment", "role", "organization", "from", "to", "person_method"])
        w.writeheader()
        w.writerows(sorted(offices.values(), key=lambda o: (o["person"], o["fragment"])))
    with open(args.roles_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["wikidata", "slug", "label_lt", "label_en"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(list(positions.values()) + FIXED_ROLES, key=lambda r: (r["slug"], r["wikidata"])))

    reused = sum(p["seimas"] == "true" for p in people.values())
    print(f"{len(people)} persons ({reused} Seimas persons reused, {len(people) - reused} new), "
          f"{len(offices)} offices", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "normalize"):
        p = sub.add_parser(name)
        p.add_argument("--base", required=True)
        p.add_argument("--positions", required=True)
        p.add_argument("--municipalities", required=True, help="admin-units/municipalities.trig")
        p.add_argument("--alignments", required=True, help="admin-units/alignments.trig")
    f = sub.choices["fetch"]
    f.add_argument("--out-dir", required=True)
    n = sub.choices["normalize"]
    n.add_argument("--cache", required=True)
    n.add_argument("--persons", required=True, help="seimas/persons.trig")
    n.add_argument("--seimas-alignments", required=True, help="seimas/alignments.trig")
    n.add_argument("--persons-out", required=True)
    n.add_argument("--offices-out", required=True)
    n.add_argument("--roles-out", required=True)
    args = ap.parse_args()
    {"fetch": fetch, "normalize": normalize}[args.cmd](args)


if __name__ == "__main__":
    main()
