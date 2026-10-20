"""Normalize the NŽT land-acquisition applications (get.data.gov.lt nzt/paraiskos) to CSV.

Applications to acquire agricultural or forest land (the Law on the Acquisition of
Agricultural Land requires the National Land Service's consent). NŽT publishes every
application, but identifies only legal-entity applicants: natural persons' codes and
names are hashed. So this step writes two CSVs for CSV2RDF + mappings/*.rq:

- ``--applications``: one row per legal-entity application (prasytojo_tipas = JA), with
  the applicant's JAR code checked against the Legal Entities Register name
  (``--jar-names``), the municipality resolved to its AR code (``--municipalities``),
  the land purpose and decision as taxonomy notations, and the dates validated;
- ``--totals``: natural-person applications (persons, spouses, foreigners) counted per
  municipality, year and land purpose - never per applicant. A cell of fewer than
  ``--min-cell`` applications is suppressed, so a single purchase cannot be singled out.

The applicant check compares the name NŽT publishes with the JAR name of the code it
publishes, after dropping legal-form words and district qualifiers. There is no shared
key besides the code itself and no name history in the open JAR, so a renamed company
and a mistyped code look alike; the check classifies rather than corrects:

  atitinka          the names agree (similarity >= MATCH)
  neaisku           partly (>= UNCERTAIN): a spelling variant, an abbreviation or a
                    sibling company of the same group
  neatitinka        they do not: very likely the wrong code (e.g. the State Tax
                    Inspectorate's code next to a private company)
  nepatikrinama     the name cannot be compared: hashed by NŽT, or withheld by the JAR
                    (sole proprietorships and partnerships are published as their form)
  nerasta-registre  the code is not in the JAR
  be-kodo           NŽT published no code

Only atitinka, neaisku and nepatikrinama link the application to the legal entity; the
published code and name are kept as literals on every row. The mismatches go to
``--report`` for review.

Usage:
    ltlod-land --input cache/applications.csv --jar-names cache/jar-names.csv \
        --municipalities ../../datasets/current/admin-units/municipalities.trig \
        --base https://linkeddata.lt/ --applications cache/le-applications.csv \
        --totals cache/totals.csv --report cache/name-check.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime
import re
import sys
import unicodedata
from collections import Counter, defaultdict

from rapidfuzz import fuzz
from rdflib import Dataset, Namespace

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

MATCH = 80
UNCERTAIN = 60

PURPOSES = {
    "Įsigyti žemės ūkio paskirties žemę": "zemes-ukio",
    "Įsigyti miškų ūkio paskirties žemę": "misku-ukio",
}
DECISIONS = {
    "Suformuoti sutikimą": "sutikimas",
    "[Sutikimai_ZemesUkioZeme_IsduotiSutikima]": "sutikimas",  # one row carries the raw code
    "Atmesti prašymą": "atmesta",
    "Prašymas atmestas": "atmesta",
}
NATURAL = {"FA", "Sutuoktiniai", "SutuoktiniaiUzsienieciai", "Uzsienietis"}
# the open JAR publishes these legal forms under their form name only
WITHHELD = {"individuali įmonė", "tikroji ūkinė bendrija", "komanditinė ūkinė bendrija"}
# legal-form words, abbreviations and district qualifiers: compared names keep the rest
STOP = set(
    "uab ab zub ziub mb vsi ii kub tub zuk sr uzdaroji akcine bendrove zemes ukio mazoji "
    "bendrija viesoji istaiga individuali imone komanditine tikroji ukine kooperatyvas "
    "kooperatine rajono miesto savivaldybes lt lietuvos".split()
)
HASHED = re.compile(r"[0-9a-f]{15}")
JAR_CODE = re.compile(r"[0-9]{9}")


def tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.findall(r"[a-z0-9]+", s) if t not in STOP]


def similarity(a: str, b: str) -> float:
    ta, tb = " ".join(tokens(a)), " ".join(tokens(b))
    if not ta or not tb:
        return 0.0
    return max(fuzz.token_set_ratio(ta, tb), fuzz.ratio(ta.replace(" ", ""), tb.replace(" ", "")))


def municipality_key(name: str) -> str:
    """'Šiaulių rajono savivaldybė' and NŽT's 'Šiaulių r. sav' both -> 'šiaulių r'."""
    s = name.lower().strip().rstrip(".")
    s = s.replace("miesto savivaldybė", "m").replace("rajono savivaldybė", "r").replace("savivaldybė", "")
    s = re.sub(r"\s+sav$", "", s)
    s = re.sub(r"\s+(r|m)\.?$", r" \1", s)
    return re.sub(r"\s+", " ", s).strip()


def load_municipalities(path: str, base: str) -> dict[str, str]:
    ds = Dataset()
    ds.parse(path, format="trig", publicID=base)
    out = {}
    for s, _, o, _ in ds.quads((None, SKOS.prefLabel, None, None)):
        m = re.search(r"/admin-units/([0-9]+)/#this$", str(s))
        if m and getattr(o, "language", None) == "lt":
            out[municipality_key(str(o))] = m.group(1)
    return out


def valid_date(value: str, last: datetime.date) -> str:
    """ISO date within the calendar's range (1990-01-01 .. end of next year), else ''."""
    try:
        d = datetime.date.fromisoformat((value or "")[:10])
    except ValueError:
        return ""
    return d.isoformat() if datetime.date(1990, 1, 1) <= d <= last else ""


def number(value: str) -> str:
    try:
        return repr(round(float(value), 4)) if value not in ("", None) else ""
    except ValueError:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--jar-names", required=True)
    ap.add_argument("--municipalities", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--applications", required=True)
    ap.add_argument("--totals", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--min-cell", type=int, default=3)
    args = ap.parse_args()

    last = datetime.date(datetime.date.today().year + 1, 12, 31)
    municipalities = load_municipalities(args.municipalities, args.base)
    with open(args.jar_names, newline="", encoding="utf-8") as f:
        jar = {r["ja_kodas"]: r["ja_pavadinimas"] for r in csv.DictReader(f)}
    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("no applications in the input")

    unknown = sorted({r["prasymo_tipas"] for r in rows} - PURPOSES.keys()
                     | {r["sprendimas"] for r in rows if r["sprendimas"]} - DECISIONS.keys()
                     | {r["prasytojo_tipas"] for r in rows} - NATURAL - {"JA"})
    if unknown:
        sys.exit(f"unknown NŽT enumeration values (map them in land_acquisitions.py): {unknown}")
    unresolved = sorted({r["savivaldybe"] for r in rows
                         if r["savivaldybe"] and municipality_key(r["savivaldybe"]) not in municipalities})
    if unresolved:
        sys.exit(f"municipalities that do not resolve to admin-units: {unresolved}")

    stats: Counter = Counter()
    checks: Counter = Counter()
    report = []
    totals: dict[tuple, Counter] = defaultdict(Counter)
    area: dict[tuple, float] = defaultdict(float)
    consented: dict[tuple, float] = defaultdict(float)

    with open(args.applications, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["id", "title", "submitted", "purpose", "representation", "applicant_code",
                      "applicant_name", "check", "entity", "municipality", "decision", "decided",
                      "area", "held", "held_after"])
        for r in rows:
            submitted = valid_date(r["pateikimo_data"], last)
            if r["pateikimo_data"] and not submitted:
                stats["submission dates out of range"] += 1
            decided = valid_date(r["sprendimo_data"], last)
            if r["sprendimo_data"] and not decided:
                stats["decision dates out of range"] += 1
            purpose = PURPOSES[r["prasymo_tipas"]]
            decision = DECISIONS.get(r["sprendimas"], "")
            sav = municipalities.get(municipality_key(r["savivaldybe"]), "") if r["savivaldybe"] else ""

            if r["prasytojo_tipas"] in NATURAL:
                stats["natural-person applications"] += 1
                if not (sav and submitted):
                    stats["natural-person applications without municipality or date"] += 1
                    continue
                key = (sav, submitted[:4], purpose)
                totals[key]["applications"] += 1
                area[key] += float(r["isigyjamas_plotas"] or 0)
                if decision:
                    totals[key][decision] += 1
                if decision == "sutikimas":
                    consented[key] += float(r["isigyjamas_plotas"] or 0)
                continue

            stats["legal-entity applications"] += 1
            code = (r["gavejo_asmens_kodas"] or "").strip()
            name = (r["teikejo_vardas"] or "").strip()
            name = "" if HASHED.fullmatch(name) else name
            if not JAR_CODE.fullmatch(code):
                check, code = "be-kodo", ""
            elif code not in jar:
                check = "nerasta-registre"
            elif not name or jar[code].strip().lower() in WITHHELD:
                check = "nepatikrinama"
            else:
                score = similarity(name, jar[code])
                check = "atitinka" if score >= MATCH else "neaisku" if score >= UNCERTAIN else "neatitinka"
                if check != "atitinka":
                    report.append([r["paraiskos_id"], code, jar[code], name, round(score), check])
            checks[check] += 1
            entity = code if check in ("atitinka", "neaisku", "nepatikrinama") else ""
            label = name or (jar.get(code) if code and jar.get(code, "").strip().lower() not in WITHHELD else "") or code or "Juridinis asmuo"
            what = "žemės ūkio paskirties žemė" if purpose == "zemes-ukio" else "miškų ūkio paskirties žemė"
            title = f"{label}: {what}" + (f", {submitted}" if submitted else "")
            out.writerow([r["paraiskos_id"], title, submitted, purpose, r["atstovavimas"], code, name, check,
                          entity, sav, decision, decided if decision else "", number(r["isigyjamas_plotas"]),
                          number(r["bendras_prasytojo_valdomas_plotas"]), number(r["bendras_plotas_po_isigyjimo"])])

    suppressed = 0
    with open(args.totals, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["municipality", "year", "purpose", "applications", "consents", "refusals",
                      "area", "area_consented"])
        for key in sorted(totals):
            c = totals[key]
            if c["applications"] < args.min_cell:
                suppressed += c["applications"]
                continue
            out.writerow([*key, c["applications"], c["sutikimas"], c["atmesta"],
                          repr(round(area[key], 4)), repr(round(consented[key], 4))])

    with open(args.report, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["paraiskos_id", "code", "jar_name", "nzt_name", "similarity", "check"])
        out.writerows(sorted(report, key=lambda x: x[4]))

    for k, v in sorted(stats.items()):
        print(f"{k}: {v}", file=sys.stderr)
    print("applicant checks: " + ", ".join(f"{k} {v}" for k, v in checks.most_common()), file=sys.stderr)
    print(f"natural-person cells: {sum(1 for k in totals if totals[k]['applications'] >= args.min_cell)}"
          f" kept, {suppressed} applications in cells under {args.min_cell} suppressed", file=sys.stderr)
