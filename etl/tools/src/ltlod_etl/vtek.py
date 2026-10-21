"""Normalize the VTEK harvests (etl/vtek/harvest-*.js) to CSV for CSV2RDF + mappings/*.rq.

Two registers of the Chief Official Ethics Commission, harvested in a real browser (both
sit behind a Cloudflare challenge; see .claude/skills/harvest-vtek/SKILL.md):

- SKAIDRIS (``--skaidris``): registered lobbyists, lobbyists' transparency declarations
  and officials' declarations of experienced lobbying influence;
- PINREG (``--pinreg``): public private-interest declarations of politicians. The harvest
  already keeps only the declarant's OWN ties (no spouse/partner, personal code or birth
  date), and this step emits nothing else.

Reconciliation is exact and never fuzzy:

- persons (PINREG declarants, natural-person lobbyists, lobbied officials) resolve to
  ``persons/{slug}/`` by normalized full name when exactly one person in ``--persons``
  (one or more TriG files: Seimas persons, officials) carries it; the curated
  ``--aliases`` CSV of the declarations domain (VMI-style name -> asmens_id) applies
  first. Anything else keeps its name as text: no person is minted here;
- lobbied institutions (free text) resolve through the curated ``--institution-aliases``
  CSV (name -> base-relative target IRI, for abbreviations and typos), else to
  ``legal-entities/{jar}/`` by normalized legal name (``--institutions``), else to a
  Seimas committee/commission by its label (``--seimas-units``);
- draft acts cited in a declaration's legislation name or description resolve to the
  Seimas bill by registration number (``XIVP-3879``), minted from the bare key.

Vocabulary codes (lobbying areas, interest roles) resolve via the static taxonomy CSVs;
an unknown label aborts (the source added one: add a row there).

Usage:
    ltlod-vtek --skaidris data/skaidris.json --pinreg data/pinreg.json \
        --persons persons.trig [more.trig ...] --aliases ../declarations/data/aliases.csv \
        --institutions institutions.trig --seimas-units org-units.trig \
        --institution-aliases data/institution-aliases.csv \
        --areas ../taxonomies/data/lobbying-areas.csv --roles ../taxonomies/data/interest-roles.csv \
        --base https://linkeddata.lt/ --out cache/
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from rdflib import Dataset

from ltlod_etl.declarations import DEATHS_QUERY, norm

VILNIUS = ZoneInfo("Europe/Vilnius")
WORKPLACE_ROLE = "darboviete"
# Seimas bill registration numbers: term prefix (XIIP … XVP) + number; a revision
# suffix "(2)" is not part of the key
BILL = re.compile(r"\b((?:XV|XIV|XIII|XII)P-\d+)")
JAR = re.compile(r"^\d{7,9}$")
EMAIL = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+")

PERSONS_QUERY = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?person ?name WHERE { ?person a foaf:Person ; foaf:name ?name }
"""

OFFICES_QUERY = """
PREFIX org:  <http://www.w3.org/ns/org#>
PREFIX time: <http://www.w3.org/2006/time#>
SELECT ?person ?org ?start ?end WHERE {
    ?membership a org:Membership ; org:member ?person ; org:organization ?org ; org:memberDuring ?interval .
    ?interval time:hasBeginning/time:inXSDDate ?start .
    OPTIONAL { ?interval time:hasEnd/time:inXSDDate ?end }
}
"""
# base-relative organization IRI prefix of a membership -> office kind
OFFICE_ORGS = (
    ("organizations/lietuvos-respublikos-seimas/", "seimas"),
    ("organizations/lietuvos-respublikos-vyriausybe/", "government"),
    ("organizations/lietuvos-respublikos-prezidentas/", "president"),
    ("organizations/europos-parlamentas/", "mep"),
    ("admin-units/", "mayor"),
)
# office kinds named in a source's occupation/institution text (ASCII-folded, lower case)
OFFICE_CONTEXT = (
    ("seimas", re.compile(r"\bseim|\blrs\b|\bkomitet|\bfrakcij")),
    ("government", re.compile(r"\bministr|\bministerij|\bvyriausyb")),
    ("president", re.compile(r"\bprezident")),
    ("mep", re.compile(r"\beuropos parlament|\bep narys|\bep nare\b")),
    ("mayor", re.compile(r"\bmer(as|e|o|ui)\b|\bsavivaldyb")),
)
# someone working FOR an office holder or an institution, not holding the office: a name
# match to an office holder would be a namesake (checked before the office kinds)
STAFF = re.compile(r"\bpatarej|\bpadejej|\bspecialist|\bkanceliarij|\bskyriaus|\bdepartament|"
                   r"\bvedej|\breferent|\bkonsultant|\bviceministr|\bkancler|\bsekretor|\bdarbuotoj")

INSTITUTIONS_QUERY = """
PREFIX rov: <http://www.w3.org/ns/regorg#>
SELECT DISTINCT ?org ?name WHERE { ?org rov:legalName ?name }
"""

UNITS_QUERY = """
PREFIX org:  <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?org ?name WHERE { ?org a org:OrganizationalUnit ; skos:prefLabel ?name }
"""
# "Lietuvos Respublikos Seimo Ekonomikos komitetas", "LRS Ekonomikos komitetas", "Seimo …"
SEIMAS_PREFIX = re.compile(r"^(?:lietuvos respublikos seimo|lietuvos respublikos seimas|lrs|seimo) ")


def slug(text: str) -> str:
    """ASCII slug of a Lithuanian label ("Kaimo reikalai ir žemės ūkis" -> kaimo-reikalai-ir-zemes-ukis)."""
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.casefold()).strip("-")


def org_norm(name: str) -> str:
    """Normalize an institution name: case, punctuation, the "LR" abbreviation."""
    n = re.sub(r"[\s.,;:„“\"]+", " ", name).strip().casefold()
    return re.sub(r"\blr\b", "lietuvos respublikos", n)


def vilnius_date(value) -> str:
    """ISO UTC timestamp or epoch milliseconds -> the Europe/Vilnius calendar date.

    SKAIDRIS stores a date picked in the UI as local midnight in UTC
    ("2026-10-23T21:00:00.000Z" is 24 October in Vilnius)."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.date().isoformat()  # PINREG timestamps are local already
    return dt.astimezone(VILNIUS).date().isoformat()


def person_name(given: str, family: str) -> str:
    return " ".join(p.strip().title() for p in (given, family) if p and p.strip())


def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def relative(uri: str, base: str) -> str:
    return uri[len(base):] if uri.startswith(base) else uri


def office_kind(org: str) -> str:
    """The kind of public office an org:Membership's organization stands for ("" if none)."""
    for prefix, kind in OFFICE_ORGS:
        if org.startswith(prefix):
            return kind
    return ""


def context_kinds(text: str) -> set[str] | None:
    """The office kinds a source's free-text occupation/institution points to. None: no text,
    so no context. An empty set: the text describes someone who holds none of these offices
    (staff, advisers, vice-ministers, or an institution that is not an office at all), so a
    name match to an office holder would be a namesake — investigative use prefers a missed
    link to a wrong one."""
    t = slug(text).replace("-", " ")
    if not t:
        return None
    if STAFF.search(t):
        return set()
    return {kind for kind, pattern in OFFICE_CONTEXT if pattern.search(t)}


class Persons:
    """Name resolver to persons/{slug}/#this (base-relative paths), recording how each link
    was made (the match-methods taxonomy):

    - alias: the curated --aliases CSV (VMI-style name -> asmens_id) applies first;
    - name-and-office: the name matches AND the occupation/institution the source gives
      agrees with an office the person held around the source's date — confirmed; among
      namesakes, the one in office wins;
    - exact-name: the name belongs to exactly one person, but the source's context does not
      confirm it (none given, or no matching office on record). Still linked — the office
      data is incomplete (officials come from Wikidata) and people change roles (a former
      minister lobbied as an adviser) — but marked weaker and listed for review.

    Several namesakes that the office cannot tell apart stay unlinked; nothing is guessed.
    A person with a schema:deathDate (Wikidata P570, from alignments.trig) before the
    source's date is no candidate at all — the lifetime guard.
    report() writes every unconfirmed or unlinked match with its reason."""

    def __init__(self, paths: list[str], base: str, aliases_path: str | None):
        by_name: dict[str, set[str]] = defaultdict(set)
        offices: dict[str, list[tuple[str, date, date]]] = defaultdict(list)
        deaths: dict[str, date] = {}
        for path in paths:
            ds = Dataset(default_union=True)
            ds.parse(path, format="trig", publicID=base)
            for row in ds.query(PERSONS_QUERY):
                uri = relative(str(row.person), base)
                if re.fullmatch(r"persons/[^/]+/#this", uri):
                    by_name[norm(str(row.name))].add(uri)
            for row in ds.query(DEATHS_QUERY):
                uri = relative(str(row.person), base)
                died = date.fromisoformat(str(row.death)[:10])
                deaths[uri] = min(deaths.get(uri, date.max), died)
            for row in ds.query(OFFICES_QUERY):
                kind = office_kind(relative(str(row.org), base))
                if kind:
                    end = date.fromisoformat(str(row.end)) if row.end else date.max
                    offices[relative(str(row.person), base)].append((kind, date.fromisoformat(str(row.start)), end))
        self.by_name = by_name
        self.offices = offices
        self.deaths = deaths
        self.aliases: dict[str, str] = {}
        if aliases_path:
            with open(aliases_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.aliases[norm(row["vmi_name"])] = f"persons/{row['asmens_id']}/#this"
        self.unmatched: list[list[str]] = []

    def held(self, person: str, kinds: set[str], on: date, before: int, after: int) -> bool:
        """Did the person hold an office of one of the kinds within [on - before, on + after] days?"""
        lo, hi = on - timedelta(days=before), on + timedelta(days=after)
        return any(k in kinds and start <= hi and end >= lo for k, start, end in self.offices.get(person, ()))

    def resolve(self, name: str, source: str, context: str = "", on: str = "",
                before: int = 60, after: int = 60) -> tuple[str, str]:
        """-> (person path, match-method notation), ("", "") when unresolved."""
        n = norm(name)
        if not n:
            return "", ""
        if n in self.aliases:
            return self.aliases[n], "alias"
        cands = self.by_name.get(n, set())
        if not cands:
            return "", ""  # not a known person at all: nothing to report
        if on:
            living = {c for c in cands if self.deaths.get(c, date.max) >= date.fromisoformat(on)}
            if not living:
                self.unmatched.append([source, name, context, on, "every namesake had died by then",
                                       "unlinked", " ".join(sorted(cands))])
                return "", ""
            cands = living
        kinds = context_kinds(context)
        if kinds is None or not on:
            reason = "no office context"
        else:
            day = date.fromisoformat(on)
            fits = [c for c in sorted(cands) if self.held(c, kinds, day, before, after)]
            if len(fits) == 1:
                return fits[0], "name-and-office"
            reason = ("context names no office held" if not kinds else
                      "no matching office on record then" if not fits else "several namesakes in office")
        linked = len(cands) == 1 and reason != "several namesakes in office"
        if kinds is not None or not linked:  # no context at all is the normal case, not a finding
            self.unmatched.append([source, name, context, on, reason,
                                   "linked (exact-name)" if linked else "unlinked", " ".join(sorted(cands))])
        return (next(iter(cands)), "exact-name") if linked else ("", "")

    def report(self, path: str) -> None:
        """Name matches the source's context did not confirm (linked as exact-name) or that
        stayed unlinked (namesakes), with the reason: the review list, and a to-do list of
        gaps in the office data."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["source", "name", "context", "date", "reason", "outcome", "candidates"])
            w.writerows(self.unmatched)


def names_index(paths: list[str], base: str, query: str) -> dict[str, set[str]]:
    by_name: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        ds = Dataset(default_union=True)
        ds.parse(path, format="trig", publicID=base)
        for row in ds.query(query):
            by_name[org_norm(str(row.name))].add(relative(str(row.org), base))
    return by_name


class Institutions:
    """Free-text institution -> curated alias, else a unique exact (normalized) name:
    legal-entities/{jar}/#this by legal name, then a Seimas committee/commission
    (organizations/lietuvos-respublikos-seimas/org-units/{id}/#this) by label."""

    def __init__(self, paths: list[str], units: list[str], base: str, aliases_path: str):
        self.by_name = names_index(paths, base, INSTITUTIONS_QUERY)
        self.units = names_index(units, base, UNITS_QUERY)
        with open(aliases_path, newline="", encoding="utf-8") as f:
            self.aliases = {org_norm(r["name"]): r["target"] for r in csv.DictReader(f)}

    def resolve(self, name: str) -> str:
        if not name:
            return ""
        n = org_norm(name)
        if n in self.aliases:
            return self.aliases[n]
        for index, key in ((self.by_name, n), (self.by_name, "lietuvos respublikos " + n),
                           (self.units, SEIMAS_PREFIX.sub("", n))):
            cands = index.get(key, set())
            if len(cands) == 1:
                return next(iter(cands))
        return ""


def load_codes(path: str) -> dict[str, str]:
    """label_lt -> notation of a static taxonomy CSV."""
    with open(path, newline="", encoding="utf-8") as f:
        return {row["label_lt"]: row["notation"] for row in csv.DictReader(f)}


def write(path: str, header: list[str], rows) -> None:
    """Write a CSV and, beside it, ``.count``: the number of distinct documents (first column),
    the graph count validate.sh expects (quoted multi-line fields defeat counting lines)."""
    docs = set()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            # free text from the source: drop e-mail addresses (officials paste them into
            # occupation/institution fields), collapse whitespace (line breaks included)
            w.writerow(["" if v is None else " ".join(EMAIL.sub("", str(v)).split()).strip(" ,;") for v in row])
            docs.add(row[0])
    with open(path[: -len(".csv")] + ".count", "w", encoding="utf-8") as f:
        f.write(f"{len(docs)}\n")


def lobbying(skaidris: dict, persons: Persons, institutions: Institutions, areas: dict[str, str], out: str) -> None:
    docs = [("transparency", d) for d in skaidris["transparency"]] + [("influence", d) for d in skaidris["influence"]]
    unknown = sorted({d["fields"]["areaName"] for _, d in docs if d["fields"].get("areaName")} - areas.keys())
    if unknown:
        sys.exit(f"unknown SKAIDRIS lobbying areas (add them to the lobbying-areas CSV): {unknown}")

    # lobbyists: the current register, plus stubs for numbers that only declarations cite
    # (entries since removed from the register); natural persons resolve to persons/ by name
    lobbyists: dict[str, list] = {}
    for l in skaidris["lobbyists"]:
        legal = bool(l.get("legal"))
        code = (l.get("legalCode") or "").strip()
        given, family = ("", "") if legal else (l.get("name") or "", l.get("surname") or "")
        name = (l.get("fullName") or l.get("name") or "").strip() if legal else person_name(given, family)
        person, method = ("", "") if legal else persons.resolve(name, f"lobbyist {l['number']}")
        lobbyists[l["number"]] = [
            l["number"], "legal" if legal else "natural", name,
            given.strip().title(), family.strip().title(),
            code if legal and JAR.match(code) else "",
            person, method,
            vilnius_date(l.get("decisionDate")), l.get("decisionNumber") or "",
            l.get("resourceStatusEnum") or "",
        ]
    for _, d in docs:
        lob = d["fields"]["lobbyist"]
        number = lob["number"]
        if number not in lobbyists:
            legal = number.startswith("LOB-JA")
            name = (lob.get("fullName") or "").strip()
            name = name if legal else name.title()
            person, method = ("", "") if legal else persons.resolve(name, f"lobbyist {number}")
            lobbyists[number] = [number, "legal" if legal else "natural", name, "", "", "",
                                 person, method, "", "", "UNLISTED"]

    ids = {d["id"]: d["name"] for _, d in docs}
    decl_rows, act_rows, contact_rows = [], [], []
    stats = Counter()
    for kind, d in docs:
        f = d["fields"]
        stats[kind] += 1
        legislation = " ".join((f.get("legislationName") or "").split())
        description = " ".join((f.get("legislationDescription") or "").split())
        decl_rows.append([
            d["name"], kind, f["lobbyist"]["number"],
            (f.get("client") or "").strip(), (f.get("beneficiary") or "").strip(),
            areas.get(f.get("areaName") or "", ""), legislation, description,
            vilnius_date(f.get("submissionDate")), vilnius_date(f.get("executionDate")),
        ])
        for bill in sorted(set(BILL.findall(legislation + " " + description))):
            act_rows.append([d["name"], bill])
        for n, c in enumerate(as_list(f.get("influencedPerson")), 1):
            if not isinstance(c, dict):
                continue
            name = " ".join((c.get("fullName") or "").split())
            name = name.title() if name.isupper() else name
            institution = " ".join((c.get("institutionName") or c.get("groupName") or "").split())
            occupation = " ".join((c.get("occupation") or "").split())
            person, method = persons.resolve(
                name, f"contact {d['name']}#{n}", f"{occupation} {institution}",
                vilnius_date(f.get("executionDate")) or vilnius_date(f.get("submissionDate")))
            target = institutions.resolve(institution)
            stats["contacts"] += 1
            stats["contacts-person"] += bool(person)
            stats[f"contacts-{method}"] += bool(person)
            stats["contacts-institution"] += bool(target)
            contact_rows.append([
                d["name"], n, name, occupation, institution, target, person, method,
                c.get("lobbyistInfluenceType") or f.get("lobbyistInfluenceType") or "",
                ids.get(c.get("declarationUuid") or "", ""),
            ])

    write(f"{out}/lobbyists.csv",
          ["number", "kind", "name", "given_name", "family_name", "jar", "person", "person_method",
           "decision_date", "decision_number", "status"],
          sorted(lobbyists.values()))
    write(f"{out}/lobbying.csv",
          ["declaration", "kind", "lobbyist", "client", "beneficiary", "area", "legislation", "description", "issued", "activity_date"],
          decl_rows)
    write(f"{out}/lobbying-acts.csv", ["declaration", "bill"], act_rows)
    write(f"{out}/lobbying-contacts.csv",
          ["declaration", "n", "name", "occupation", "institution", "target", "person", "person_method",
           "influence_type", "counterpart"],
          contact_rows)
    kinds = Counter(r[1] for r in lobbyists.values())
    print(f"lobbyists: {len(lobbyists)} ({kinds['legal']} legal, {kinds['natural']} natural; "
          f"{sum(1 for r in lobbyists.values() if r[5])} with JAR, "
          f"{sum(1 for r in lobbyists.values() if r[6])} natural matched to persons/, "
          f"{sum(1 for r in lobbyists.values() if r[10] == 'UNLISTED')} unlisted)", file=sys.stderr)
    by_method = ", ".join(f"{m} {stats['contacts-' + m]}" for m in ("name-and-office", "exact-name", "alias"))
    print(f"declarations: {stats['transparency']} transparency + {stats['influence']} influence; "
          f"{len({r[0] for r in act_rows})} cite {len({r[1] for r in act_rows})} Seimas bills; "
          f"contacts: {stats['contacts']} ({stats['contacts-person']} -> persons/, "
          f"{stats['contacts-institution']} -> institution; persons by {by_method})", file=sys.stderr)


def interests(pinreg: dict, persons: Persons, roles: dict[str, str], out: str) -> None:
    natures = {t["nature"] for d in pinreg["declarations"] for t in d["legalEntityTies"]}
    unknown = sorted(natures - roles.keys())
    if unknown:
        sys.exit(f"unknown PINREG tie natures (add them to the interest-roles CSV): {unknown}")

    decl_rows, tie_rows = [], []
    matched = 0
    for d in pinreg["declarations"]:
        if d.get("type") != "VIESA" or not d.get("latest", True):
            continue
        given, family = d["declarant"]["givenName"], d["declarant"]["familyName"]
        name = person_name(given, family)
        person, method = persons.resolve(name, f"pinreg {d['accessUuid']}", d.get("listedPosition") or "",
                                         d["submitted"][:10], before=400, after=60)
        matched += bool(person)
        decl_rows.append([d["accessUuid"], name, given.strip().title(), family.strip().title(), person, method,
                          d["submitted"][:10], d.get("listedPosition") or "", d.get("listedWorkplace") or ""])
        seen: Counter = Counter()

        def key(base_key: str) -> str:
            seen[base_key] += 1
            return base_key if seen[base_key] == 1 else f"{base_key}-{seen[base_key]}"

        for w in d["workplaces"]:
            jar = (w.get("jaKodas") or "").strip()
            positions = "; ".join(p["pareigos"].strip() for p in w.get("position") or [] if p.get("pareigos"))
            tie_rows.append([d["accessUuid"], key(f"work-{jar or slug(w['name'])}"), WORKPLACE_ROLE,
                             jar if JAR.match(jar) else "", w["name"].strip(), "", w.get("since") or "", "",
                             "", "", positions, person])
        for t in d["legalEntityTies"]:
            jar = (t.get("jaKodas") or "").strip()
            role = roles[t["nature"]]
            tie_rows.append([d["accessUuid"], key(f"tie-{jar or slug(t['name'])}-{role}"), role,
                             jar if JAR.match(jar) and t.get("registeredInLithuania", True) else "",
                             t["name"].strip(), t.get("legalFormCode") or "", t.get("since") or "", t.get("until") or "",
                             "true" if t.get("inPublicProcurement") else "false",
                             # the declarant's free-text note (pastabos) is not emitted: it
                             # often describes relatives ("the owner is my father")
                             (t.get("procurementInfo") or "").strip(), "", person])

    write(f"{out}/interests.csv",
          ["declaration", "name", "given_name", "family_name", "person", "person_method", "issued", "position", "workplace"],
          decl_rows)
    write(f"{out}/interest-ties.csv",
          ["declaration", "tie", "role", "jar", "org_name", "legal_form", "since", "until", "procurement",
           "procurement_info", "position_title", "person"],
          tie_rows)
    status = "complete" if pinreg.get("complete", True) else f"PARTIAL, {len(pinreg.get('pending', []))} pending"
    print(f"interest declarations: {len(decl_rows)} ({matched} declarants -> persons/; harvest {status}); "
          f"ties: {len(tie_rows)} ({sum(1 for r in tie_rows if r[2] != WORKPLACE_ROLE)} legal-entity ties, "
          f"{sum(1 for r in tie_rows if r[3])} with JAR)", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--skaidris", required=True)
    ap.add_argument("--pinreg", required=True)
    ap.add_argument("--persons", required=True, nargs="+")
    ap.add_argument("--aliases")
    ap.add_argument("--institutions", required=True, nargs="+")
    ap.add_argument("--seimas-units", required=True, nargs="+")
    ap.add_argument("--institution-aliases", required=True)
    ap.add_argument("--areas", required=True)
    ap.add_argument("--roles", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    persons = Persons(args.persons, args.base, args.aliases)
    institutions = Institutions(args.institutions, args.seimas_units, args.base, args.institution_aliases)
    with open(args.skaidris, encoding="utf-8") as f:
        skaidris = json.load(f)
    with open(args.pinreg, encoding="utf-8") as f:
        pinreg = json.load(f)
    for name, data, keys in (("skaidris", skaidris, ("lobbyists", "transparency", "influence")),
                             ("pinreg", pinreg, ("declarations",))):
        empty = [k for k in keys if not data.get(k)]
        if empty:
            sys.exit(f"{name}: empty harvest {empty}")
    lobbying(skaidris, persons, institutions, load_codes(args.areas), args.out)
    interests(pinreg, persons, load_codes(args.roles), args.out)
    persons.report(f"{args.out}/person-matches-to-review.csv")
    outcomes = Counter(f"{r[5]}: {r[4]}" for r in persons.unmatched)
    print(f"person matches to review (cache/person-matches-to-review.csv): {len(persons.unmatched)} "
          f"({'; '.join(f'{k} {v}' for k, v in outcomes.most_common())})", file=sys.stderr)


if __name__ == "__main__":
    main()
