"""Aggregate public-sector invoices (get.data.gov.lt, nbfc/viesojo_sektoriaus_saskaitos) into
buyer-supplier-year totals for CSV2RDF:

  aggregates.csv  buyer_code,supplier_code,year,invoices,total_eur,net_eur

The source is huge — ~14.4M invoices (Saskaitos) and ~32M invoice-party rows (SaskaituSalys) —
and the party rows cannot be windowed by invoice year (their `data` is a 2020-era registration
date, unrelated to the invoice date), so the whole party table must be read to attribute each
invoice to its buyer and supplier. Both feeds are therefore streamed, keyset-paginated on _id,
into a temporary on-disk SQLite database and joined/aggregated there (low memory for tens of
millions of rows).

Join (verified 2026-10-25): SaskaituSalys.sf_id = Saskaitos.sf_id normalized to an "LT" prefix
(the source spells it inconsistently); tipas "Pirkėjas" is the buyer, "Tiekėjas" the supplier,
each identified by validus_jar_kodas (a JAR code). Party names (pavadinimas) are pseudonymised
in the source, so names are not taken from here — they come from legal-entities/ by the code.
Rows without a JAR code (natural persons, pseudonymised; foreign parties) are dropped. One
output row per (buyer JAR, supplier JAR, invoice year): the invoice count, the total billed
(bendra_sf_suma, incl. VAT) and the net total (suma_be_pvm).
"""

import argparse
import csv
import io
import os
import sqlite3
import sys
import tempfile
import time

import httpx

API = "https://get.data.gov.lt/datasets/gov/nbfc/viesojo_sektoriaus_saskaitos"
PAGE = 50000


def norm_sf(sf: str) -> str:
    sf = (sf or "").strip()
    return sf[2:] if sf.startswith("LT") else sf


def stream(client: httpx.Client, model: str, select: str, handle) -> int:
    """Keyset-paginate a model on _id, passing each page's rows to `handle`. Lossless even if a
    page is truncated by the export size cap (the next page resumes after the last _id)."""
    rows = 0
    last = ""
    while True:
        q = f"select(_id,{select})&sort(_id)&limit({PAGE})"
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
                print(f"WARN {model}: HTTP {r.status_code}", file=sys.stderr)
            except httpx.HTTPError as e:
                print(f"WARN {model}: {e}", file=sys.stderr)
            time.sleep(5 * 2 ** attempt)
        else:
            sys.exit(f"ERROR: {model} kept failing: {url[:160]}")
        if not page:
            break
        handle(page)
        rows += len(page)
        last = page[-1]["_id"]
        if rows % 500000 < PAGE:
            print(f"  {model}: {rows} rows", file=sys.stderr)
    if not rows:
        sys.exit(f"ERROR: {model} returned no rows")
    print(f"  {model}: {rows} rows total", file=sys.stderr)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", required=True, help="output: one row per buyer-supplier-year")
    ap.add_argument("--db", help="SQLite work file (default: a temp file, removed after)")
    ap.add_argument("--min-total", type=float, default=1000.0,
                    help="only publish a (buyer, supplier, year) whose billed total (incl. VAT) "
                         "reaches this many EUR (default 1000; drops the ~63%% of zero-total "
                         "credit-note/VAT pairs and the long tail of trivial flows)")
    ap.add_argument("--reaggregate", action="store_true",
                    help="skip the fetch and re-aggregate an existing --db (e.g. a new --min-total)")
    args = ap.parse_args()

    db_path = args.db or tempfile.mktemp(suffix=".sqlite", prefix="pubspend-")
    con = sqlite3.connect(db_path)
    if not args.reaggregate:
        con.executescript("""
            PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
            DROP TABLE IF EXISTS party; DROP TABLE IF EXISTS invoice;
            CREATE TABLE party (sf TEXT, tipas TEXT, jar TEXT, PRIMARY KEY (sf, tipas)) WITHOUT ROWID;
            CREATE TABLE invoice (sf TEXT, year TEXT, gross REAL, net REAL);
        """)

    def put_parties(page):
        batch = []
        for r in page:
            jar = (r.get("validus_jar_kodas") or "").strip()
            tipas = (r.get("tipas") or "").strip()
            if not jar or tipas not in ("Pirkėjas", "Tiekėjas"):
                continue
            batch.append((norm_sf(r.get("sf_id", "")), tipas, jar))
        # first party per (sf, tipas) wins (an invoice has one buyer and one supplier)
        con.executemany("INSERT OR IGNORE INTO party VALUES (?,?,?)", batch)

    def put_invoices(page):
        batch = []
        for r in page:
            d = (r.get("israsymo_data") or "").strip()
            if len(d) < 4:
                continue
            def num(v):
                v = (v or "").strip()
                try:
                    return float(v)
                except ValueError:
                    return 0.0
            batch.append((norm_sf(r.get("sf_id", "")), d[:4],
                          num(r.get("bendra_sf_suma")), num(r.get("suma_be_pvm"))))
        con.executemany("INSERT INTO invoice VALUES (?,?,?,?)", batch)

    if not args.reaggregate:
        with httpx.Client(timeout=600, follow_redirects=True) as client:
            print("streaming invoice parties (SaskaituSalys, ~32M)…", file=sys.stderr)
            stream(client, "SaskaituSalys", "sf_id,tipas,validus_jar_kodas", put_parties)
            con.commit()
            print("streaming invoices (Saskaitos, ~14.4M)…", file=sys.stderr)
            stream(client, "Saskaitos", "sf_id,israsymo_data,bendra_sf_suma,suma_be_pvm", put_invoices)
            con.commit()

    print("indexing + aggregating…", file=sys.stderr)
    con.execute("CREATE INDEX IF NOT EXISTS i_inv_sf ON invoice (sf)")
    cur = con.execute("""
        SELECT b.jar, s.jar, i.year, COUNT(*), ROUND(SUM(i.gross), 2), ROUND(SUM(i.net), 2)
        FROM invoice i
        JOIN party b ON b.sf = i.sf AND b.tipas = 'Pirkėjas'
        JOIN party s ON s.sf = i.sf AND s.tipas = 'Tiekėjas'
        -- only years the calendar covers (1977-2027); drops malformed/implausible invoice dates
        WHERE i.year >= '1977' AND i.year <= '2027'
        GROUP BY b.jar, s.jar, i.year
        HAVING ROUND(SUM(i.gross), 2) >= ?
    """, (args.min_total,))
    n = 0
    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["buyer_code", "supplier_code", "year", "invoices", "total_eur", "net_eur"])
        for buyer, supplier, year, invoices, gross, net in cur:
            w.writerow([buyer, supplier, year, invoices, gross, net])
            n += 1
    con.close()
    if not args.db:
        os.unlink(db_path)
    print(f"aggregates: {n} (buyer, supplier, year) rows (>= {args.min_total:g} EUR)", file=sys.stderr)


if __name__ == "__main__":
    main()
