"""Fetch VMI legal-entity tax data (get.data.gov.lt) and flatten it to two CSVs for CSV2RDF:

  companies.csv  ja_kodas,name,sav,arrears,overdue,deferred,deferred_overdue,updated
  paid.csv       ja_kodas,year,paid

Two source models, both keyed on the 9-digit JAR code:

  vmi/ja_nepriemokos/NepriemokosSuma  the CURRENT tax-arrears snapshot, one row per
      legal entity that owes tax (ja_kodas, name, the registration municipality's AR
      code sav_kodas.sav_kodas, the arrears amounts, and the snapshot date atnaujinta).
  vmi/ja_mokesciai/Moketojas          taxes PAID, one row per taxpayer per year (menuo
      is always 12 — the year's total). The JAR code is a dereferenced parent key
      mm_kodas.ja_kodas (mm_registras is legal entities only); rows whose taxpayer has
      no JAR code — foreign entities — are dropped. Windowed to --since-year.

companies.csv is the UNION of the two feeds' legal entities (so a company with taxes
paid but no arrears still gets a document); arrears columns are blank when the company
has no arrears row. paid.csv has one row per (company, year).

The plain CSV export truncates unpredictably (a per-request size cap), so every model is
read with keyset pagination on the opaque _id (sort(_id) + _id>'<last>'), which is
lossless. The portal's WAF sometimes answers with an HTML block page instead of an HTTP
error, so a page that does not start with the expected header is retried.
"""

import argparse
import csv
import io
import re
import sys
import time
from datetime import date

import httpx

API = "https://get.data.gov.lt/datasets/gov"
ARREARS = "vmi/ja_nepriemokos/NepriemokosSuma"
PAID = "vmi/ja_mokesciai/Moketojas"
PAGE = 20000
JAR = re.compile(r"^\d{9}$")


def fetch(client: httpx.Client, model: str, select: str, extra: str = "") -> list[dict]:
    """All rows of a model, keyset-paginated on _id (lossless)."""
    rows: list[dict] = []
    last = ""
    while True:
        q = f"select(_id,{select})&sort(_id)&limit({PAGE})"
        if extra:
            q += f"&{extra}"
        if last:
            q += f"&_id>'{last}'"
        url = f"{API}/{model}/:format/csv?{q}"
        page = None
        for attempt in range(5):
            try:
                r = client.get(url)
                if r.status_code == 200 and r.text.startswith("_id"):
                    page = list(csv.DictReader(io.StringIO(r.text)))
                    break
                print(f"WARN {model}: HTTP {r.status_code} {r.text[:120]!r}", file=sys.stderr)
            except httpx.HTTPError as e:
                print(f"WARN {model}: {e}", file=sys.stderr)
            time.sleep(5 * 2**attempt)
        else:
            sys.exit(f"ERROR: {model} kept failing: {url[:200]}")
        if not page:
            break
        rows.extend(page)
        last = page[-1]["_id"]
        print(f"  {model}: {len(rows)} rows", file=sys.stderr)
    if not rows:
        sys.exit(f"ERROR: {model} returned no rows")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since-year", type=int, default=date.today().year - 4,
                    help="earliest reporting year for taxes paid (default: 4 years back)")
    ap.add_argument("--companies", required=True, help="output: one row per legal entity")
    ap.add_argument("--paid", required=True, help="output: one row per (entity, year)")
    args = ap.parse_args()

    with httpx.Client(timeout=600, follow_redirects=True) as client:
        print("fetching tax arrears snapshot…", file=sys.stderr)
        arrears = fetch(
            client, ARREARS,
            "ja_kodas,ja_pavadinimas,sav_kodas.sav_kodas,nepriemoka,"
            "pradelsta_nepriemoka,atideta_nepriemoka,atideta_pradelsta,atnaujinta",
        )
        print(f"fetching taxes paid since {args.since_year}…", file=sys.stderr)
        paid = fetch(client, PAID, "mm_kodas.ja_kodas,pavadinimas,metai,suma",
                     extra=f"metai>={args.since_year}")

    # companies: union of both feeds, keyed by JAR; arrears columns from the arrears feed
    companies: dict[str, dict] = {}
    for r in arrears:
        code = (r.get("ja_kodas") or "").strip()
        if not JAR.match(code):
            continue
        companies[code] = {
            "ja_kodas": code,
            "name": (r.get("ja_pavadinimas") or "").strip(),
            "sav": (r.get("sav_kodas.sav_kodas") or "").strip(),
            "arrears": r.get("nepriemoka", ""),
            "overdue": r.get("pradelsta_nepriemoka", ""),
            "deferred": r.get("atideta_nepriemoka", ""),
            "deferred_overdue": r.get("atideta_pradelsta", ""),
            "updated": (r.get("atnaujinta") or "").strip(),
        }

    paid_rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for r in paid:
        code = (r.get("mm_kodas.ja_kodas") or "").strip()
        year = (r.get("metai") or "").strip()
        suma = (r.get("suma") or "").strip()
        if not JAR.match(code) or not year or not suma:
            continue
        key = (code, year)
        if key in seen:  # the grain is one row per (taxpayer, year); guard anyway
            continue
        seen.add(key)
        paid_rows.append((code, year, suma))
        companies.setdefault(code, {
            "ja_kodas": code, "name": (r.get("pavadinimas") or "").strip(),
            "sav": "", "arrears": "", "overdue": "", "deferred": "",
            "deferred_overdue": "", "updated": "",
        })

    cols = ["ja_kodas", "name", "sav", "arrears", "overdue", "deferred",
            "deferred_overdue", "updated"]
    with open(args.companies, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for code in sorted(companies):
            w.writerow(companies[code])

    with open(args.paid, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ja_kodas", "year", "paid"])
        w.writerows(sorted(paid_rows))

    print(f"companies: {len(companies)} ({len(arrears)} arrears rows), "
          f"paid: {len(paid_rows)} (entity, year) rows", file=sys.stderr)


if __name__ == "__main__":
    main()
