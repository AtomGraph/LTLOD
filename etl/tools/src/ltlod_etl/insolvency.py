"""Fetch AVNT insolvency data (get.data.gov.lt) and flatten it to one CSV for CSV2RDF:

  proceedings.csv  code,name,type,start,end,sav,court,initiator,out_of_court,
                   simplified,intentional,intentional_date,liquidation,deregistration,source

One row per insolvency proceeding (a bankruptcy or a restructuring). Three source models,
all keyed on the legal-entity code imones_kodas:

  avnt/imoniu_bankrotas/BankrotoAtaskaitosDatos        bankruptcy proceedings, 2020+, one
      row per proceeding with the full report fields (court, initiator, the out-of-court /
      simplified / intentional dates, liquidation and deregistration).
  avnt/imoniu_restrukturizavimas/RestrukturizavimoAtaskaitosDatos  restructuring
      proceedings, 2020+.
  avnt/tyciniai_bankrotai/TycinisBankrotas             intentional bankruptcies, 1994-2025
      (fewer fields). It overlaps the Datos table for 2020+ cases (which already carry the
      intentional date inline) and adds the ~630 older intentional bankruptcies as their own
      proceedings.

The proceeding is keyed by (code, start, type); the start date coalesces bankroto_data (the
court declaration) with ne_teismo_tvarka (the out-of-court decision). The Datos table has
leading-zero duplicates of veiklos_kodas (an activity field this pipeline does not use), so
two rows of the same (code, start) collapse to one. A TycinisBankrotas row whose (code,
bankroto_pradzia) matches a bankruptcy enriches it (sets the intentional flag/date);
otherwise it becomes a new, older intentional bankruptcy.

The AVNT territory code (teritorijos_kodas, a 4-digit 26XX statistical code — 7 digits for
the few sub-municipal rows) crosswalks to the AR savivaldybe code by its last two digits
(2611->11 Alytus, 2641->41 Vilnius r.), with one hardcoded exception (2601->13, Vilnius
city) and the defunct 2651 (Marijampole district, abolished 2000) left unmatched. The valid
set is read live from the AR savivaldybe classifier, so a code mapping to no current
municipality gets no refArea link (logged), never a guess.

The `...Finansai` financial tables are deliberately not fetched: their eil_nr key joins to no
company code in the report tables, so the figures cannot be attached to a proceeding.
"""

import argparse
import csv
import io
import sys

import httpx

API = "https://get.data.gov.lt/datasets/gov"
BANKRUPTCY = "avnt/imoniu_bankrotas/BankrotoAtaskaitosDatos"
RESTRUCTURING = "avnt/imoniu_restrukturizavimas/RestrukturizavimoAtaskaitosDatos"
INTENTIONAL = "avnt/tyciniai_bankrotai/TycinisBankrotas"
AR_SAVIVALDYBE = "rc/ar/savivaldybe/Savivaldybe"

# Regional (apygardos) courts -> stable slugs (matching taxonomies/data/courts.csv)
COURTS = {
    "Vilniaus apygardos teismas": "vilniaus",
    "Kauno apygardos teismas": "kauno",
    "Klaipėdos apygardos teismas": "klaipedos",
    "Šiaulių apygardos teismas": "siauliu",
    "Panevėžio apygardos teismas": "panevezio",
}

# Bankruptcy initiators -> stable slugs (matching taxonomies/data/insolvency-initiators.csv)
INITIATORS = {
    "Įmonės vadovas": "imones-vadovas",
    "Valstybinė mokesčių inspekcija": "vmi",
    "Valstybinio socialinio draudimo fondo valdyba": "sodra",
    "Kiti kreditoriai": "kreditoriai",
    "Darbuotojai": "darbuotojai",
    "Savininkas (savininkai)": "savininkas",
    "Įmonės likvidatorius": "likvidatorius",
    "Finansų ministerija": "finansu-ministerija",
}


def fetch_csv(client: httpx.Client, model: str, select: str = "") -> list[dict]:
    """A model's full CSV export. These tables are small (< 6k rows), so the plain export
    is lossless; fail loudly if it comes back empty or as a WAF HTML block."""
    url = f"{API}/{model}/:format/csv"
    if select:
        url += f"?select({select})"
    r = client.get(url)
    r.raise_for_status()
    if not r.text.lstrip().startswith(("_id", "_type", "sav_kodas")):
        sys.exit(f"ERROR: {model} did not return CSV: {r.text[:120]!r}")
    rows = [row for row in csv.DictReader(io.StringIO(r.text))
            # a stray header line is embedded mid-data in one AVNT export
            if (row.get("teritorijos_kodas") or "") != "Teritorijos kodas"]
    if not rows:
        sys.exit(f"ERROR: {model} returned no rows")
    print(f"  {model}: {len(rows)} rows", file=sys.stderr)
    return rows


def municipality_codes(client: httpx.Client) -> set[int]:
    """The current AR savivaldybe codes (the 60 municipalities)."""
    rows = fetch_csv(client, AR_SAVIVALDYBE, "sav_kodas,pavadinimas")
    return {int(r["sav_kodas"]) for r in rows if (r.get("sav_kodas") or "").strip().isdigit()}


def crosswalk_sav(territory: str, valid: set[int]) -> str:
    """AVNT teritorijos_kodas -> AR sav_kodas (as a string), or "" if no current municipality.

    The 4-digit 26XX code's last two digits are the sav_kodas (7-digit sub-municipal codes
    truncate to their 4-digit prefix); 2601 is Vilnius city (sav 13), not 01."""
    code = (territory or "").strip()
    if not code.isdigit():
        return ""
    head = code[:4]
    sav = 13 if head == "2601" else int(head[2:])
    return str(sav) if sav in valid else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", required=True, help="output: one row per proceeding")
    args = ap.parse_args()

    with httpx.Client(timeout=600, follow_redirects=True) as client:
        print("fetching AR municipalities…", file=sys.stderr)
        valid = municipality_codes(client)
        print("fetching bankruptcies…", file=sys.stderr)
        bankruptcies = fetch_csv(client, BANKRUPTCY)
        print("fetching restructurings…", file=sys.stderr)
        restructurings = fetch_csv(client, RESTRUCTURING)
        print("fetching intentional bankruptcies…", file=sys.stderr)
        intentional = fetch_csv(client, INTENTIONAL)

    def clean(row: dict, key: str) -> str:
        return (row.get(key) or "").strip()

    def name_of(row: dict) -> str:
        # The company name, undoing the source's extra CSV-quoting layer: many names come
        # wrapped in a quote pair with the internal quotes doubled, so the real name
        # UAB "EDROMA" arrives as a quoted-and-doubled literal.
        n = clean(row, "imones_pavadinimas")
        if len(n) >= 2 and n.startswith('"') and n.endswith('"'):
            n = n[1:-1].replace('""', '"')
        return n

    # (code, start, type) -> proceeding dict
    proceedings: dict[tuple[str, str, str], dict] = {}
    skipped = {"no_code": 0, "no_start": 0, "no_sav": 0}

    def row(code, name, typ, start, end, sav, court, initiator, out_of_court,
            simplified, intentional_date, liquidation, deregistration, source) -> dict:
        return dict(code=code, name=name, type=typ, start=start, end=end, sav=sav,
                    court=court, initiator=initiator,
                    out_of_court="1" if out_of_court else "",
                    simplified="1" if simplified else "",
                    intentional="1" if intentional_date else "",
                    intentional_date=intentional_date, liquidation=liquidation,
                    deregistration=deregistration, source=source)

    # --- bankruptcies (the richest source) ---
    for r in bankruptcies:
        code = clean(r, "imones_kodas")
        if not code:
            skipped["no_code"] += 1
            continue
        start = clean(r, "bankroto_data") or clean(r, "ne_teismo_tvarka")
        if not start:
            skipped["no_start"] += 1
            continue
        sav = crosswalk_sav(clean(r, "teritorijos_kodas"), valid)
        if clean(r, "teritorijos_kodas") and not sav:
            skipped["no_sav"] += 1
        key = (code, start, "bankrotas")
        # leading-zero veiklos_kodas duplicates collapse here (same key, first wins)
        proceedings.setdefault(key, row(
            code=code, name=name_of(r), typ="bankrotas",
            start=start, end=clean(r, "isregistravimo_data") or clean(r, "nutraukimo_data"),
            sav=sav, court=COURTS.get(clean(r, "apygardos_teismas"), ""),
            initiator=INITIATORS.get(clean(r, "bankroto_iniciatorius"), ""),
            out_of_court=clean(r, "ne_teismo_tvarka"),
            simplified=clean(r, "supaprastintas_bankrotas"),
            intentional_date=clean(r, "tycinis_bankrotas"),
            liquidation=clean(r, "likvidavimo_data"),
            deregistration=clean(r, "isregistravimo_data"), source="bankrotas"))

    # --- restructurings ---
    for r in restructurings:
        code = clean(r, "imones_kodas")
        if not code:
            skipped["no_code"] += 1
            continue
        start = clean(r, "restrukturizavimo_data")
        if not start:
            skipped["no_start"] += 1
            continue
        sav = crosswalk_sav(clean(r, "teritorijos_kodas"), valid)
        if clean(r, "teritorijos_kodas") and not sav:
            skipped["no_sav"] += 1
        key = (code, start, "restrukturizavimas")
        proceedings.setdefault(key, row(
            code=code, name=name_of(r), typ="restrukturizavimas",
            start=start, end=clean(r, "nutraukimo_data"), sav=sav,
            court=COURTS.get(clean(r, "apygardos_teismas"), ""), initiator="",
            out_of_court="", simplified="", intentional_date="", liquidation="",
            deregistration="", source="restrukturizavimas"))

    # --- intentional bankruptcies: enrich a matching bankruptcy, else add an older one ---
    added_intentional = enriched = 0
    for r in intentional:
        code = clean(r, "imones_kodas")
        start = clean(r, "bankroto_pradzia")
        if not code or not start:
            skipped["no_start" if code else "no_code"] += 1
            continue
        tycinis = clean(r, "tycinis_bankrotas")
        key = (code, start, "bankrotas")
        if key in proceedings:
            p = proceedings[key]
            if not p["intentional_date"]:
                p["intentional_date"] = tycinis
                p["intentional"] = "1" if tycinis else p["intentional"]
            enriched += 1
            continue
        proceedings[key] = row(
            code=code, name=name_of(r), typ="bankrotas", start=start,
            end=clean(r, "isregistravimo_data"), sav="",
            court=COURTS.get(clean(r, "apygardos_teismas"), ""), initiator="",
            out_of_court="", simplified="", intentional_date=tycinis,
            liquidation=clean(r, "likvidavimo_data"),
            deregistration=clean(r, "isregistravimo_data"), source="tycinis")
        added_intentional += 1

    cols = ["code", "name", "type", "start", "end", "sav", "court", "initiator",
            "out_of_court", "simplified", "intentional", "intentional_date",
            "liquidation", "deregistration", "source"]
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for key in sorted(proceedings):
            w.writerow(proceedings[key])

    n = len(proceedings)
    types = {t: sum(1 for p in proceedings.values() if p["type"] == t)
             for t in ("bankrotas", "restrukturizavimas")}
    flagged = sum(1 for p in proceedings.values() if p["intentional"])
    print(f"proceedings: {n} ({types['bankrotas']} bankruptcy, "
          f"{types['restrukturizavimas']} restructuring; {flagged} intentional — "
          f"{enriched} enriched, {added_intentional} added pre-2020); "
          f"skipped {skipped}", file=sys.stderr)


if __name__ == "__main__":
    main()
