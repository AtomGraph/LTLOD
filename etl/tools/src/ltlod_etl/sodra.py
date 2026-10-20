"""Normalize Sodra's per-insurer monthly open data (atvira.sodra.lt) to CSV.

Sodra publishes, per insurer (draudėjas) and month, the number of insured persons, their
average wage and the social-insurance contributions, as yearly ``monthly-{yyyy}.csv.zip``
files on https://atvira.sodra.lt/imones/rinkiniai/index.html. The site is behind a
Cloudflare bot challenge, so there is no scripted fetch: the zips are downloaded in a
real browser into ``etl/sodra/data/`` (see .claude/skills/harvest-sodra/SKILL.md).

This step reads every ``*.csv.zip`` / ``*.csv`` in ``--input-dir`` and keeps the latest
``--months`` months present (the window). It always writes ``--summary``: one row per
employer for mappings/employers.rq — the employer's latest month in the window as
published (insured persons, average wage, contributions) plus window aggregates over the
months it reported (their count, mean insured persons, the headcount-weighted mean wage,
total contributions). With ``--cube`` it also writes the monthly cube for
mappings/observations.rq: one CSV per chunk of ``--chunk-size`` employers (rows sorted by
JAR code, so every employer lands in exactly one chunk) — a year is ~1.2M rows, ~14M quads.

- Header columns are recognised by the English keys Sodra puts in parentheses
  (``jarCode``, ``month``, ``numInsured``, ``avgWage``, ``tax``, ``name``,
  ``municipality``) or by their Lithuanian labels; a missing required column aborts with
  the header seen. The "II" variants (a second wage/headcount definition) are ignored.
- Only rows with a 9-digit JAR code are kept: the link target is
  ``legal-entities/{jar}/#this``, and natural-person insurers never get person-level rows.
- Two insurer rows for one JAR code and month (separately registered units) are merged:
  headcounts and contributions summed, the wage averaged weighted by headcount.
- The municipality resolves to an AR ``sav_kodas`` (Sodra uses the AR codes; a name such
  as "Vilniaus m. sav." is matched against the admin-units labels). Unresolved values go
  to ``--report``, never guessed.

Usage:
    ltlod-sodra --input-dir data --months 12 \
        --municipalities ../../datasets/current/admin-units/municipalities.trig \
        --base https://linkeddata.lt/ --summary cache/employers.csv \
        [--cube --chunk-size 10000] --out-dir cache/chunks --report cache/unmatched.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from rdflib import Dataset

MUNICIPALITIES_QUERY = """
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?code ?label WHERE { ?unit dct:identifier ?code ; skos:prefLabel ?label }
"""

# column key -> predicate over the casefolded header cell
COLUMNS = {
    "jar": lambda h: "(jarcode)" in h or h == "jarcode" or "juridinių asmenų registro kodas" in h,
    "name": lambda h: "(name)" in h or h == "name" or h.startswith("pavadinimas"),
    "municipality": lambda h: "(municipality)" in h or h == "municipality" or h.startswith("savivaldyb"),
    "month": lambda h: "(month)" in h or h == "month" or h.startswith("mėnuo"),
    "insured": lambda h: "(numinsured)" in h or h == "numinsured"
                         or (h.startswith("apdraustųjų skaičius") and " ii" not in h),
    "wage": lambda h: "(avgwage)" in h or h == "avgwage"
                      or (h.startswith("vidutinis darbo užmokestis") and " ii" not in h),
    "tax": lambda h: "(tax)" in h or h == "tax" or ("įmokų suma" in h and " ii" not in h),
}
REQUIRED = ("jar", "month", "insured")


def read_tables(input_dir: Path):
    """Yield (source name, text) for every CSV, inside zips or bare."""
    files = sorted(input_dir.glob("*.csv.zip")) + sorted(input_dir.glob("*.csv"))
    if not files:
        sys.exit(f"no *.csv.zip / *.csv in {input_dir} — harvest them first "
                 "(.claude/skills/harvest-sodra/SKILL.md)")
    for f in files:
        if f.suffix == ".zip":
            with zipfile.ZipFile(f) as z:
                for member in z.namelist():
                    if member.lower().endswith(".csv"):
                        yield f"{f.name}:{member}", decode(z.read(member))
        else:
            yield f.name, decode(f.read_bytes())


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1257")


def number(value: str) -> float | None:
    value = value.strip().replace(" ", "").replace(" ", "")
    if not value:
        return None
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    return float(value)


def month_key(value: str) -> str:
    """'202409' / '2024-09' / '2024.09' -> '2024-09'."""
    digits = re.sub(r"\D", "", value)
    if len(digits) < 6:
        raise ValueError(f"unparseable month {value!r}")
    return f"{digits[:4]}-{digits[4:6]}"


def municipality_resolver(path: str, base: str):
    ds = Dataset(default_union=True)
    ds.parse(path, format="trig", publicID=base)
    codes: set[str] = set()
    by_label: dict[str, str] = {}
    for row in ds.query(MUNICIPALITIES_QUERY):
        codes.add(str(row.code))
        by_label[str(row.label).casefold()] = str(row.code)

    def expand(name: str) -> str:
        name = re.sub(r"\bm\.", "miesto", name.casefold())
        name = re.sub(r"\br\.", "rajono", name)
        name = re.sub(r"\bsav\.?$", "savivaldybė", name.strip())
        return re.sub(r"\s+", " ", name).strip()

    def resolve(value: str) -> str | None:
        value = value.strip()
        if not value:
            return None
        if value.isdigit():
            return value if value in codes else None
        return by_label.get(value.casefold()) or by_label.get(expand(value))

    return resolve


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--months", type=int, default=12, help="keep the latest N months (0 = all)")
    ap.add_argument("--chunk-size", type=int, default=10000, help="employers per output CSV")
    ap.add_argument("--municipalities", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--summary", required=True, help="per-employer summary CSV (default output)")
    ap.add_argument("--cube", action="store_true", help="also write the monthly cube chunks")
    ap.add_argument("--out-dir", required=True, type=Path, help="cube chunk CSV directory")
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    resolve = municipality_resolver(args.municipalities, args.base)

    # (jar, month) -> aggregate; jar -> (month, name) of its latest row
    obs: dict[tuple[str, str], dict] = {}
    names: dict[str, tuple[str, str]] = {}
    unmatched: dict[str, int] = defaultdict(int)
    skipped = merged = 0
    for source, text in read_tables(args.input_dir):
        sample = text[:4096]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        header = [h.strip().casefold() for h in next(reader)]
        index = {}
        for key, test in COLUMNS.items():
            hits = [i for i, h in enumerate(header) if test(h)]
            if hits:
                index[key] = hits[0]
        missing = [k for k in REQUIRED if k not in index]
        if missing:
            sys.exit(f"{source}: no {missing} column in header {header} — Sodra changed the format")
        for row in reader:
            if not row:
                continue
            get = lambda k: row[index[k]].strip() if k in index and index[k] < len(row) else ""
            jar = get("jar")
            if not re.fullmatch(r"\d{9}", jar):
                skipped += 1
                continue
            month = month_key(get("month"))
            insured = number(get("insured"))
            wage = number(get("wage"))
            tax = number(get("tax"))
            municipality = resolve(get("municipality")) if "municipality" in index else None
            if "municipality" in index and get("municipality") and municipality is None:
                unmatched[get("municipality")] += 1
            name = get("name")
            if name and (jar not in names or month >= names[jar][0]):
                names[jar] = (month, name)
            o = obs.get((jar, month))
            if o is None:
                obs[(jar, month)] = {"insured": insured, "wage": wage, "tax": tax,
                                     "municipality": municipality}
                continue
            # a second insurer row for the same legal entity and month: merge
            merged += 1
            n1, n2 = o["insured"] or 0, insured or 0
            if o["wage"] is not None and wage is not None and n1 + n2 > 0:
                o["wage"] = (o["wage"] * n1 + wage * n2) / (n1 + n2)
            elif o["wage"] is None:
                o["wage"] = wage
            o["insured"] = None if o["insured"] is None and insured is None else n1 + n2
            o["tax"] = None if o["tax"] is None and tax is None else (o["tax"] or 0) + (tax or 0)
            o["municipality"] = o["municipality"] or municipality

    if not obs:
        sys.exit("no observations with a JAR code — empty or unrecognised input")
    months = sorted({m for _, m in obs})
    keep = set(months[-args.months:]) if args.months > 0 else set(months)
    jars = sorted({j for j, m in obs if m in keep})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for old in args.out_dir.glob("observations-*.csv"):
        old.unlink()
    fmt = lambda v, digits: "" if v is None else (f"{v:.{digits}f}" if digits else str(int(round(v))))

    # the default output: one summary row per employer — its latest month in the window
    # as published, plus window aggregates over the months it reported
    with open(args.summary, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["jar", "name", "month", "municipality", "insured", "avg_wage", "contributions",
                    "months", "mean_insured", "mean_wage", "total_contributions"])
        for jar in jars:
            series = [(m, obs[(jar, m)]) for m in sorted(keep) if (jar, m) in obs]
            month, last = series[-1]
            # the most recent municipality the employer reported in the window
            municipality = next((o["municipality"] for _, o in reversed(series) if o["municipality"]), None)
            insured = [o["insured"] for _, o in series if o["insured"] is not None]
            paid = [(o["wage"], o["insured"]) for _, o in series
                    if o["wage"] is not None and o["insured"]]
            taxes = [o["tax"] for _, o in series if o["tax"] is not None]
            w.writerow([jar, names.get(jar, ("", jar))[1], month, municipality or "",
                        fmt(last["insured"], 0), fmt(last["wage"], 2), fmt(last["tax"], 2),
                        len(series),
                        fmt(sum(insured) / len(insured), 1) if insured else "",
                        fmt(sum(x * n for x, n in paid) / sum(n for _, n in paid), 2) if paid else "",
                        fmt(sum(taxes), 2) if taxes else ""])

    rows = 0
    for c in range(0, len(jars), args.chunk_size) if args.cube else ():
        path = args.out_dir / f"observations-{c // args.chunk_size:03d}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["jar", "name", "month", "municipality", "insured", "avg_wage", "contributions"])
            for jar in jars[c:c + args.chunk_size]:
                name = names.get(jar, ("", jar))[1]
                for month in sorted(m for m in keep if (jar, m) in obs):
                    o = obs[(jar, month)]
                    w.writerow([jar, name, month, o["municipality"] or "", fmt(o["insured"], 0),
                                fmt(o["wage"], 2), fmt(o["tax"], 2)])
                    rows += 1

    with open(args.report, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["municipality", "rows"])
        for value, n in sorted(unmatched.items()):
            w.writerow([value, n])

    print(f"{len(jars)} employers, months {min(keep)}..{max(keep)} ({len(keep)}) -> {args.summary}; "
          f"{rows} monthly cube observations{'' if args.cube else ' (--cube off)'}; {merged} merged duplicate rows, {skipped} rows without a JAR code skipped, "
          f"{sum(unmatched.values())} rows with an unresolved municipality -> {args.report}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
