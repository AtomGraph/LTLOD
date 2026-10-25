"""Fetch 2014-2020 EU structural-funds implementation data (get.data.gov.lt, finmin) and
flatten it to two CSVs for CSV2RDF:

  contracts.csv  id,code,name,beneficiary_code,beneficiary_name,foreign,legal_person_type,
                 sav,started,finished,impl_from,impl_till,state_aid,de_minimis,eu_amount,
                 total_amount,decision_eu_amount
  partners.csv   contract_id,partner_code,partner_name

One row per implementation contract (finmin/sutartys/Contract, ~26k) — a grant agreement
with a beneficiary (executor_code, a JAR code). ~805 carry a formal project code
(finmin/paraiskos/Project, reached via Contract.project) with decision amounts and a full
financing breakdown (ConFinSource); the rest are code-less financial-instrument payouts
(e.g. partial interest compensation to SMEs) with only the beneficiary, dates and aid flags.

Joins (all by the Spinta _id, verified 2026-10-25):
  ConPartner.project._id   = Contract._id   (project partners, also JAR-coded)
  ConFinSource.project._id = Contract._id   (financing sources; the EU and total amounts)
  Contract.project._id     = paraiskos/Project._id   (the code + decision amounts)

The municipality is a free-text field (e.g. "Akmenės raj."), crosswalked to the AR
savivaldybe code by normalizing the abbreviation and matching the registry name; the valid
set is read live, so an unmatched value gets no refArea link (logged), never a guess.

NOT fetched: Repayment (lėšų grąžinimai) and kontroles_veiksmai/Suspicion (pažeidimai) are
keyed by an opaque project_hash / project_hash_id that is a hash of an UNPUBLISHED internal
SFMIS identifier — tested 2026-10-25, it matches no hash (md5/sha*/crc/blake, salted,
prefix/suffix) of any published id (project code, _id, project_id, Contract._id), so the
repayments and irregularities cannot be attributed to a project or beneficiary. Also absent:
the 2021-2027 programme (not on Spinta).
"""

import argparse
import csv
import io
import sys
import time

import httpx

API = "https://get.data.gov.lt/datasets/gov/finmin"
AR_SAVIVALDYBE = "https://get.data.gov.lt/datasets/gov/rc/ar/savivaldybe/Savivaldybe"
PAGE = 20000


def fetch_all(client: httpx.Client, url: str) -> list[dict]:
    """A small model's full CSV export; fail loudly if empty or a WAF block."""
    for attempt in range(5):
        try:
            r = client.get(url)
            if r.status_code == 200 and "," in r.text.splitlines()[0]:
                return list(csv.DictReader(io.StringIO(r.text)))
            print(f"WARN {url[:80]}: HTTP {r.status_code}", file=sys.stderr)
        except (httpx.HTTPError, IndexError) as e:
            print(f"WARN {url[:80]}: {e}", file=sys.stderr)
        time.sleep(5 * 2 ** attempt)
    sys.exit(f"ERROR: kept failing: {url[:120]}")


def fetch_keyset(client: httpx.Client, model: str, select: str) -> list[dict]:
    """A large model, keyset-paginated on _id (lossless; the plain CSV export truncates)."""
    rows: list[dict] = []
    last = ""
    while True:
        q = f"select(_id,{select})&sort(_id)&limit({PAGE})"
        if last:
            q += f"&_id>'{last}'"
        page = fetch_all(client, f"{API}/{model}/:format/csv?{q}")
        if not page:
            break
        rows.extend(page)
        last = page[-1]["_id"]
        print(f"  {model}: {len(rows)} rows", file=sys.stderr)
    if not rows:
        sys.exit(f"ERROR: {model} returned no rows")
    return rows


def municipality_crosswalk(client: httpx.Client) -> dict[str, str]:
    """finmin municipality text (e.g. 'Akmenės raj.', 'Alytaus miesto', 'Birštono') -> AR
    sav_kodas, by normalizing the abbreviation and matching the registry name."""
    ar = fetch_all(client, f"{AR_SAVIVALDYBE}/:format/csv?select(sav_kodas,pavadinimas)")
    by_name = {(r["pavadinimas"] or "").strip(): str(r["sav_kodas"]).strip() for r in ar}
    return by_name


def to_sav(text: str, by_name: dict[str, str]) -> str:
    """Map one finmin municipality text to an AR sav_kodas, or '' if none matches."""
    t = (text or "").strip()
    if not t:
        return ""
    norm = t.replace(" raj.", " rajono")
    # exact ("Alytaus miesto", "Birštono") or prefix ("Akmenės rajono" vs AR "Akmenės rajono")
    for name, code in by_name.items():
        if name == norm or name.startswith(norm + " ") or name == norm + " savivaldybė":
            return code
    for name, code in by_name.items():
        if name.startswith(norm):
            return code
    # fallback for a form the registry spells without the type word (finmin "Visagino
    # miesto" vs AR "Visagino"): the first token, only if it names exactly one municipality.
    # Cities that also have a rajono match exactly above, so this stays unambiguous.
    stem = norm.split()[0]
    hits = [code for name, code in by_name.items() if name.split()[0] == stem]
    return hits[0] if len(hits) == 1 else ""


def flag(v) -> str:
    return "1" if str(v).strip().lower() in ("true", "1", "taip") else ""


def amount(v) -> str:
    v = (str(v) if v is not None else "").strip()
    return v if v not in ("", "None") else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--contracts", required=True)
    ap.add_argument("--partners", required=True)
    args = ap.parse_args()

    with httpx.Client(timeout=600, follow_redirects=True) as client:
        print("fetching municipality crosswalk…", file=sys.stderr)
        by_name = municipality_crosswalk(client)
        print("fetching contracts…", file=sys.stderr)
        contracts = fetch_keyset(
            client, "sutartys/Contract",
            "name,project._id,project.code,project.decision_eu_amount,executor,"
            "executor_code,executor_foreign_person,legal_person_type,municipality,"
            "started,finished,impl_from,impl_till,state_aid,de_minimis_aid")
        print("fetching partners…", file=sys.stderr)
        partners = fetch_all(client, f"{API}/sutartys/ConPartner/:format/csv"
                             "?select(project._id,partner,code)")
        print("fetching financing sources…", file=sys.stderr)
        finsrc = fetch_all(client, f"{API}/sutartys/ConFinSource/:format/csv"
                           "?select(project._id,fin_source,amount)")

    # financing: EU-fund and total amounts per contract (_id)
    eu_amount: dict[str, str] = {}
    total_amount: dict[str, str] = {}
    for r in finsrc:
        cid = (r.get("project._id") or "").strip()
        src = (r.get("fin_source") or "").strip()
        amt = amount(r.get("amount"))
        if not cid or not amt:
            continue
        if src == "ES fondų lėšos":
            eu_amount[cid] = amt
        elif src == "Iš viso":
            total_amount[cid] = amt

    unmatched_sav = set()
    with open(args.contracts, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "code", "name", "beneficiary_code", "beneficiary_name", "foreign",
                    "legal_person_type", "sav", "started", "finished", "impl_from",
                    "impl_till", "state_aid", "de_minimis", "eu_amount", "total_amount",
                    "decision_eu_amount"])
        n = skipped = 0
        for r in contracts:
            cid = (r.get("_id") or "").strip()
            ben = (r.get("executor_code") or "").strip()
            if not cid or not ben:
                # a funding record with no beneficiary code has no JAR link — drop it
                skipped += 1 if cid else 0
                continue
            muni = (r.get("municipality") or "").strip()
            sav = to_sav(muni, by_name)
            if muni and not sav:
                unmatched_sav.add(muni)
            w.writerow([
                cid,
                (r.get("project.code") or "").strip(),
                (r.get("name") or "").strip(),
                (r.get("executor_code") or "").strip(),
                (r.get("executor") or "").strip(),
                flag(r.get("executor_foreign_person")),
                (r.get("legal_person_type") or "").strip(),
                sav,
                (r.get("started") or "").strip(),
                (r.get("finished") or "").strip(),
                (r.get("impl_from") or "").strip(),
                (r.get("impl_till") or "").strip(),
                flag(r.get("state_aid")),
                flag(r.get("de_minimis_aid")),
                eu_amount.get(cid, ""),
                total_amount.get(cid, ""),
                amount(r.get("project.decision_eu_amount")),
            ])
            n += 1

    p = 0
    with open(args.partners, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["contract_id", "partner_code", "partner_name"])
        for r in partners:
            cid = (r.get("project._id") or "").strip()
            code = (r.get("code") or "").strip()
            if not cid or not code:
                continue
            w.writerow([cid, code, (r.get("partner") or "").strip()])
            p += 1

    coded = sum(1 for r in contracts
                if (r.get("project.code") or "").strip() and (r.get("executor_code") or "").strip())
    print(f"contracts: {n} ({coded} with a project code; {skipped} dropped with no beneficiary), "
          f"partners: {p}; EU amounts: {len(eu_amount)}; "
          f"unmatched municipalities: {sorted(unmatched_sav)}", file=sys.stderr)


if __name__ == "__main__":
    main()
