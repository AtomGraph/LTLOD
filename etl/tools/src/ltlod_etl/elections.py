"""Normalize VRK Seimas election results (etl/elections/fetch-arcgis.sh) to CSV + geo TriG.

The source is the VRK results map's ArcGIS feature layers, one feature per
single-member constituency (apygarda) and layer, in a WIDE shape: candidates as
``CAND{n}_NAME`` / ``_PART_NAME`` / ``_VOTES`` / ``_VOTES_PCT`` / ``_ELECTED`` /
``_PHOTO_URL`` column groups (round 1 and round 2 layers), party lists as
``PART{n}_NAME`` / ``_VOTES`` / ``_VOTES_PCT`` / ``_ELECTIONLIST_NO`` (the party-list
vote counted in that constituency). This step flattens them into one row per result
and resolves the cross-dataset keys:

- constituency: ``constituencies/{term}-{nr}/`` (seimas domain); a district absent
  there is reported and its contest skipped (no dangling links);
- candidate -> ``persons/{asmens_id}/`` by exact full name (``declarations.norm``),
  unique across all persons, or among namesakes the one seated in the elected term;
  never fuzzy. Names VRK spells differently from LRS (Lithuanian vs Polish spelling, a
  dropped double surname) resolve only through the curated ``--person-aliases`` CSV. Unresolved candidates keep only their published name (no person entity
  is minted for private individuals) and go to the report;
- party -> ``parties/{slug}/`` by the seimas domain's slug rule (xslt/nariai.xsl) over a
  normalized name, else the curated ``--party-aliases`` CSV; self-nominated candidates
  ("Išsikėlę patys") and coalitions without a parties/ document keep the name only.

A district decided in round 1 still appears in the round-2 layer, carrying its winner
alone; those rows are dropped (there was no runoff). The candidate key is VRK's own
candidate id, read from the photo URL (``…/photo_{id}.jpeg``), else the result rank.

Every elected candidate must resolve to the person whose seat in that term was won in
that very constituency (persons.trig ``ltlod:electoralDistrict``); a mismatch fails the
run — it means a wrong name match or a wrong district key.

Boundaries (the round-1 layer's polygons, requested in LKS-94 / EPSG:3346) are
simplified by ``--simplify`` metres, reprojected to WGS84 and written as geo:lat/long +
gsp:asWKT into the constituency documents' own graphs (``geo.write_geo``), merged on
load like the admin units' *-geo.trig.

Usage:
    ltlod-elections --base https://linkeddata.lt/ --elections data/elections.csv \
        --years "2020 2024" --cache cache --persons persons.trig --parties parties.trig \
        --constituencies constituencies.trig --party-aliases data/party-aliases.csv \
        --person-aliases data/person-aliases.csv \
        --simplify 100 --geo cache/constituencies-geo.trig --report cache/unmatched.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

from pyproj import Transformer
from rdflib import Dataset
from shapely import to_wkt
from shapely.geometry import LinearRing, MultiPolygon, Polygon
from shapely.ops import transform as shapely_transform

from ltlod_etl.declarations import load_deaths, norm
from ltlod_etl.geo import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, check_bounds, write_geo

PERSONS_QUERY = """
PREFIX epvoc: <https://data.europarl.europa.eu/def/epvoc#>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX ltlod: <http://linkeddata.lt/ns#>
SELECT ?person ?name ?term ?district
WHERE {
    ?person a foaf:Person ; foaf:name ?name .
    OPTIONAL {
        ?tenure org:member ?person ;
            epvoc:memberDuringParliamentaryTerm ?term .
        OPTIONAL { ?tenure ltlod:electoralDistrict ?district }
    }
}
"""

SELF_NOMINATED = "išsikėlę patys"

# m² — Lithuania is ~65 000 km²; a constituency polygon larger than the country is
# not a territorial one
WORLD_AREA = 1e11

# slug rule of etl/seimas/xslt/nariai.xsl (parties/{slug}/): lowercase, Lithuanian
# letters to ASCII, drop „“"()., and join words with "-"
DIACRITICS = str.maketrans("ąčęėįšųūž", "aceeisuuz")
DROPPED = str.maketrans("", "", "„“\"().,")


def clean(name: str) -> str:
    """A published name as emitted: NBSPs and runs of spaces collapsed, nothing else."""
    return re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip()


def party_name(name: str) -> str:
    """A VRK party name normalized for MATCHING only: VRK spells the same party
    "A - B", "A – B" and "A-B" across layers; LRS writes "A-B"."""
    return re.sub(r"\s*[-–]\s*", "-", clean(name))


def slug(name: str) -> str:
    return " ".join(party_name(name).lower().translate(DIACRITICS).translate(DROPPED).split()).replace(" ", "-")


def load_persons(path: str, base: str):
    """name -> [asmens_id], (asmens_id, term id) set, constituency key -> {asmens_id}."""
    ds = Dataset(default_union=True)
    ds.parse(path, format="trig", publicID=base)
    by_name: dict[str, set[str]] = defaultdict(set)
    terms: set[tuple[str, str]] = set()
    elected_in: dict[str, set[str]] = defaultdict(set)
    for row in ds.query(PERSONS_QUERY):
        m = re.search(r"/persons/([^/]+)/#this$", str(row.person))
        if not m:
            continue
        pid = m.group(1)
        by_name[norm(str(row.name))].add(pid)
        t = re.search(r"/terms/([^/]+)/#this$", str(row.term)) if row.term is not None else None
        if t:
            terms.add((pid, t.group(1)))
        if row.district is not None:
            d = re.search(r"/constituencies/([^/]+)/#this$", str(row.district))
            if d:
                elected_in[d.group(1)].add(pid)
    return by_name, terms, elected_in


def graph_keys(path: str, container: str) -> set[str]:
    """{key} of every <{container}{key}/> document graph in a TriG file."""
    with open(path, encoding="utf-8") as f:
        return set(re.findall(rf"^<{re.escape(container)}([^/>]+)/>\s*\{{", f.read(), re.M))


def features(cache: str, year: str, layer: str) -> list[dict]:
    with open(os.path.join(cache, f"{year}-{layer}.json"), encoding="utf-8") as f:
        return json.load(f)["features"]


def groups(attrs: dict, prefix: str) -> list[tuple[int, str]]:
    """(n, column prefix) of every populated {prefix}{n}_NAME group, in n order."""
    found = []
    for key, value in attrs.items():
        m = re.fullmatch(rf"{prefix}(\d+)_NAME", key)
        if m and value and value.strip():
            found.append((int(m.group(1)), f"{prefix}{m.group(1)}_"))
    return sorted(found)


def esri_polygon(rings: list[list[list[float]]]):
    """Esri rings -> shapely (Multi)Polygon: clockwise rings are shells, the
    counter-clockwise ones holes of the shell that contains them."""
    shells, holes = [], []
    for ring in rings:
        lr = LinearRing(ring)
        (holes if lr.is_ccw else shells).append(lr)
    polys = [[s, []] for s in shells]
    for h in holes:
        for p in polys:
            if Polygon(p[0]).contains(Polygon(h)):
                p[1].append(h)
                break
    geoms = [Polygon(s, hs) for s, hs in polys]
    geom = geoms[0] if len(geoms) == 1 else MultiPolygon(geoms)
    return geom if geom.is_valid else geom.buffer(0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--elections", required=True)
    ap.add_argument("--years", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--persons", required=True)
    ap.add_argument("--parties", required=True)
    ap.add_argument("--constituencies", required=True)
    ap.add_argument("--party-aliases", required=True)
    ap.add_argument("--person-aliases", required=True)
    ap.add_argument("--alignments", action="append", default=[],
                    help="alignments.trig (repeatable): schema:deathDate for the lifetime guard")
    ap.add_argument("--simplify", type=float, required=True)
    ap.add_argument("--geo", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    years = args.years.split()
    with open(args.elections, newline="", encoding="utf-8") as f:
        elections = {row["year"]: row for row in csv.DictReader(f) if row["year"] in years}
    missing = set(years) - elections.keys()
    if missing:
        sys.exit(f"no row in {args.elections} for {sorted(missing)}")

    by_name, seated, elected_in = load_persons(args.persons, args.base)
    deaths = load_deaths(args.alignments, args.base)
    party_slugs = graph_keys(args.parties, "parties/")
    districts = graph_keys(args.constituencies, "constituencies/")
    with open(args.party_aliases, newline="", encoding="utf-8") as f:
        aliases = {party_name(row["vrk_name"]): row["slug"] for row in csv.DictReader(f)}
    bad = {s for s in aliases.values() if s and s not in party_slugs}
    if bad:
        sys.exit(f"{args.party_aliases}: no parties/ document for {sorted(bad)}")

    unmatched_parties: set[str] = set()

    def resolve_party(name: str) -> str:
        n = party_name(name)
        if n.lower() == SELF_NOMINATED:
            return ""
        if n in aliases:
            return aliases[n]
        s = slug(n)
        if s in party_slugs:
            return s
        unmatched_parties.add(clean(name))
        return ""

    with open(args.person_aliases, newline="", encoding="utf-8") as f:
        person_aliases = {norm(row["vrk_name"]): row["asmens_id"] for row in csv.DictReader(f)}

    def resolve_person(name: str, term: str, year: int) -> tuple[str, str]:
        """-> (asmens_id, match-method notation): alias; name-and-office when the person was
        seated in the term (the office, so namesakes resolve too); exact-name when the name is
        unique but the candidate was not seated (a losing candidate). A person who had died
        before the election year is no candidate (the lifetime guard)."""
        if norm(name) in person_aliases:
            return person_aliases[norm(name)], "alias"
        ids = {i for i in by_name.get(norm(name), set()) if deaths.get(i, 9999) >= year}
        in_office = {i for i in ids if (i, term) in seated}
        if len(in_office) == 1:
            return next(iter(in_office)), "name-and-office"
        if len(ids) == 1:
            return next(iter(ids)), "exact-name"
        return "", ""

    contests, rounds, candidates, lists, unmatched = [], [], [], [], []
    geo_features, mismatches = [], []
    transformer = Transformer.from_crs("EPSG:3346", "EPSG:4326", always_xy=True)
    for year in years:
        e = elections[year]
        term, election = e["term"], e["election"]
        smd1 = {a["AREA1_NO"]: a for a in (f["attributes"] for f in features(args.cache, year, "smd1"))}
        smd2 = {a["AREA1_NO"]: a for a in (f["attributes"] for f in features(args.cache, year, "smd2"))}
        mmd = {a["AREA1_NO"]: a for a in (f["attributes"] for f in features(args.cache, year, "mmd"))}
        for nr in sorted(smd1, key=int):
            key = f"{term}-{nr}"
            if key not in districts:
                unmatched.append(["constituency", year, key, smd1[nr]["AREA1_NAME"]])
                continue
            contest = f"{election}-{nr}"
            decided = any(smd1[nr].get(f"{p}ELECTED") == 1 for _, p in groups(smd1[nr], "CAND"))
            layers = [("1", smd1[nr])] + ([] if decided or nr not in smd2 else [("2", smd2[nr])])
            contests.append([contest, election, key, smd1[nr]["AREA1_NAME"].strip(), layers[-1][0]])
            for rnd, a in layers:
                rounds.append([contest, rnd, a["VOTERS_TOTAL"], a["VOTERS_TOTAL_PCT"]])
                for rank, (_, p) in enumerate(groups(a, "CAND"), 1):
                    name = " ".join(a[f"{p}NAME"].split())
                    m = re.search(r"photo_(\d+)\.", a.get(f"{p}PHOTO_URL") or "")
                    cand = m.group(1) if m else f"rank-{rank}"
                    nominator = clean(a.get(f"{p}PART_NAME") or "")
                    person, method = resolve_person(name, term, int(year))
                    elected = a.get(f"{p}ELECTED") == 1
                    if not person:
                        unmatched.append(["candidate", year, f"{key} r{rnd}", name])
                    if elected and person not in elected_in.get(key, set()):
                        mismatches.append((key, name, person, sorted(elected_in.get(key, set()))))
                    candidates.append([contest, rnd, cand, name, person, method, nominator, resolve_party(nominator),
                                       a[f"{p}VOTES"], a[f"{p}VOTES_PCT"], "true" if elected else "", rank])
            if nr in mmd:
                a = mmd[nr]
                for n, p in groups(a, "PART"):
                    name = clean(a[f"{p}NAME"])
                    lists.append([contest, a.get(f"{p}ELECTIONLIST_NO") or n, name, resolve_party(name),
                                  a[f"{p}VOTES"], a[f"{p}VOTES_PCT"]])
        for feat in features(args.cache, year, "geo"):
            key = f"{term}-{feat['attributes']['AREA1_NO']}"
            if key not in districts or not feat.get("geometry"):
                continue
            geom = esri_polygon(feat["geometry"]["rings"])
            if geom.area > WORLD_AREA:
                # the diaspora constituency (Pasaulio lietuvių, Nr. 71) is drawn as the
                # rest of the world; it has no place on a map of Lithuania
                unmatched.append(["boundary", year, key, feat["attributes"]["AREA1_NAME"]])
                continue
            pt = geom.representative_point()
            lon, lat = transformer.transform(pt.x, pt.y)
            simp = geom.simplify(args.simplify, preserve_topology=True)
            boundary = to_wkt(shapely_transform(transformer.transform, simp), rounding_precision=6)
            geo_features.append((key, round(lat, 6), round(lon, 6), boundary))

    if mismatches:
        for m in mismatches:
            print(f"ERROR: {m[0]}: elected {m[1]!r} resolved to {m[2] or 'nobody'}, "
                  f"but persons.trig seats {m[3]} for that constituency", file=sys.stderr)
        sys.exit(1)
    out_of_bounds = check_bounds(geo_features)
    if out_of_bounds:
        sys.exit(f"{len(out_of_bounds)} constituency point(s) outside Lithuania "
                 f"(lat {LAT_MIN}–{LAT_MAX}, lon {LON_MIN}–{LON_MAX}): {out_of_bounds[:3]}")

    outdir = args.cache
    for name, header, rows in [
        ("contests", ["contest", "election", "district", "district_name", "deciding_round"], contests),
        ("rounds", ["contest", "round", "ballots", "turnout"], rounds),
        ("candidates", ["contest", "round", "candidate", "name", "person", "person_method", "nominator", "party",
                        "votes", "share", "elected", "rank"], candidates),
        ("lists", ["contest", "list_no", "list_name", "party", "list_votes", "list_share"], lists),
    ]:
        with open(os.path.join(outdir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
    write_geo(geo_features, args.base, "constituencies/", args.geo)
    for p in sorted(unmatched_parties):
        unmatched.append(["party", "", "", p])
    with open(args.report, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "year", "key", "name"])
        w.writerows(unmatched)

    linked = sum(1 for c in candidates if c[4])
    print(f"{len(contests)} contests, {len(rounds)} rounds, {len(candidates)} candidate results "
          f"({linked} linked to persons/), {len(lists)} party-list results, {len(geo_features)} "
          f"boundaries; {len(unmatched)} unmatched -> {args.report}", file=sys.stderr)


if __name__ == "__main__":
    main()
