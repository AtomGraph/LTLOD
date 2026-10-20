"""Fetch public procurement contracts (VPT CVP IS contract subsystem, published by
the State Data Agency on get.data.gov.lt as datasets/gov/lsd/vpt/cvpp) and flatten
them to two CSVs for CSV2RDF:

  contracts.csv  dok_id,title,number,cpv,nature,value,date
  parties.csv    dok_id,role,n,kind,code,name

The source has two tables joined on the document id: Sutartis (one row per
contract) and Salis (one row per contract party; ar_salis_tiekejas tells the
supplier from the buyer). Salis has no date column and ~12M rows, so instead of
dumping it the parties of the windowed contracts are fetched in batches of
dok_id="…"|dok_id="…" filters.

Party kinds:
  jar     Lithuanian legal entity (9-digit JAR code) -> legal-entities/{code}/#this
  org     other legal entity (foreign or non-JAR code) -> name + identifier kept
  person  natural person — the source already pseudonymises them (hashed code and
          name, salies_asmens_rusis "Nežinomas"); code and name are dropped here.
"""

import argparse
import csv
import io
import re
import sys
import time
from datetime import date

import httpx

API = "https://get.data.gov.lt/datasets/gov/lsd/vpt/cvpp"
CONTRACT_COLUMNS = (
    "dok_id,cpv_codes,dok_sut_numeris,dok_sut_obj_rusis,dok_sut_obj_pav,"
    "dok_sut_verte,dok_sudarymo_data"
)
PARTY_COLUMNS = "dok_id,salies_kodas,salies_asmens_rusis,salies_pavadinimas,salies_eil_nr,ar_salis_tiekejas"
# dok_sut_obj_rusis -> EU contract-nature authority table code
NATURE = {"1": "supplies", "2": "services", "3": "works"}
CPV = re.compile(r"^(\d{8})(-\d)?$")
JAR = re.compile(r"^\d{9}$")


def fetch_csv(client: httpx.Client, model: str, query: str) -> list[dict]:
    url = f"{API}/{model}/:format/csv?{query}"
    for attempt in range(5):
        try:
            r = client.get(url)
            if r.status_code == 200 and r.text.startswith(("dok_id", "_type")):
                return list(csv.DictReader(io.StringIO(r.text)))
            # the portal's WAF answers with an HTML block page, not an HTTP error
            print(f"WARN {model}: HTTP {r.status_code} {r.text[:120]!r}", file=sys.stderr)
        except httpx.HTTPError as e:
            print(f"WARN {model}: {e}", file=sys.stderr)
        time.sleep(5 * 2**attempt)
    sys.exit(f"ERROR: {model} kept failing: {url[:200]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", required=True, help="first conclusion date (YYYY-MM-DD)")
    ap.add_argument("--until", default=date.today().isoformat(),
                    help="last conclusion date (default today; the source has typos like 2525-…)")
    ap.add_argument("--min-value", default="10000",
                    help="minimum contract value in EUR (CVP IS publishes contracts >= 10 000 EUR)")
    ap.add_argument("--batch", type=int, default=150, help="dok_ids per Salis request")
    ap.add_argument("--contracts", required=True)
    ap.add_argument("--parties", required=True)
    args = ap.parse_args()

    client = httpx.Client(timeout=600, headers={"User-Agent": "LTLOD ETL (linkeddata.lt)"})
    # dok_formos_tipas 2 = a contract AMENDMENT (susitarimas dėl sutarties pakeitimo): it
    # restates the whole contract value under the original contract number, once per
    # amendment (one road contract has 25 in a year), so counting it would multiply the
    # spend (~70% of the windowed value). Only the contracts themselves (form 1) are kept.
    window = (f'dok_sudarymo_data>="{args.since}"&dok_sudarymo_data<="{args.until}"'
              f"&dok_sut_verte>={args.min_value}&dok_formos_tipas=\"1\"")
    rows = fetch_csv(client, "Sutartis", f"select({CONTRACT_COLUMNS})&{window}&sort(dok_id)")
    if not rows:
        sys.exit("ERROR: no contracts in the window")

    contracts = {}
    skipped = 0
    for r in rows:
        dok_id = r["dok_id"].strip()
        title = " ".join(r["dok_sut_obj_pav"].split())
        cpv = CPV.match(r["cpv_codes"].strip())
        try:
            day = date.fromisoformat(r["dok_sudarymo_data"][:10]).isoformat()
            value = f"{float(r['dok_sut_verte']):.2f}"
        except ValueError:
            skipped += 1
            continue
        if not dok_id.isdigit() or dok_id in contracts:
            skipped += 1
            continue
        contracts[dok_id] = {
            "dok_id": dok_id,
            "title": title,
            "number": " ".join(r["dok_sut_numeris"].split()),
            "cpv": cpv.group(1) if cpv else "",
            "nature": NATURE.get(r["dok_sut_obj_rusis"].strip(), ""),
            "value": value,
            "date": day,
        }
    print(f"contracts: {len(rows)} rows -> {len(contracts)} kept ({skipped} malformed)", file=sys.stderr)

    ids = list(contracts)
    parties = []
    started = time.time()
    for i in range(0, len(ids), args.batch):
        chunk = ids[i:i + args.batch]
        flt = "|".join(f'dok_id="{d}"' for d in chunk)
        parties += fetch_csv(client, "Salis", f"select({PARTY_COLUMNS})&{flt}")
        done = i + len(chunk)
        if done % (args.batch * 40) < args.batch or done == len(ids):
            print(f"parties: {done}/{len(ids)} contracts, {time.time() - started:.0f}s", file=sys.stderr)

    out_parties = []
    seen = set()
    with_buyer, with_contractor = set(), set()
    for p in parties:
        dok_id = p["dok_id"].strip()
        if dok_id not in contracts:
            continue
        role = "contractor" if p["ar_salis_tiekejas"] == "True" else "buyer"
        n = p["salies_eil_nr"].strip() or "1"
        key = (dok_id, role, n)
        if key in seen:
            continue
        seen.add(key)
        code = p["salies_kodas"].strip()
        legal = p["salies_asmens_rusis"].strip() == "Juridinis"
        if legal and JAR.match(code):
            kind, name = "jar", ""
        elif legal:
            kind, name = "org", " ".join(p["salies_pavadinimas"].split())
        else:
            kind, code, name = "person", "", ""
        out_parties.append({"dok_id": dok_id, "role": role, "n": n, "kind": kind, "code": code, "name": name})
        (with_buyer if role == "buyer" else with_contractor).add(dok_id)

    print(f"parties: {len(out_parties)}; contracts with a buyer {len(with_buyer)}, "
          f"with a contractor {len(with_contractor)} of {len(contracts)}", file=sys.stderr)
    # a failing join (schema drift, WAF) must not silently produce party-less contracts
    if len(with_buyer) < 0.9 * len(contracts):
        sys.exit("ERROR: fewer than 90% of contracts resolved a buyer")

    with open(args.contracts, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dok_id", "title", "number", "cpv", "nature", "value", "date"])
        w.writeheader()
        w.writerows(contracts.values())
    with open(args.parties, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dok_id", "role", "n", "kind", "code", "name"])
        w.writeheader()
        w.writerows(out_parties)


if __name__ == "__main__":
    main()
