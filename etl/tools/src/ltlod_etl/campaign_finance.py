"""Normalize VRK political campaign finance (etl/elections/harvest-vrk.js) to CSV.

Input is the browser harvest of VRK's open-data Spinta models (atviriduomenys.vrk.lt
is behind a Cloudflare challenge, see .claude/skills/harvest-vrk/): campaign income
(``Pajamos``), campaign expenses (``Islaidos``) and the Seimas election candidates
(``Kandidatai``). Each income/expense row belongs to one campaign participant
(``p_kamp_dal_id``: a candidate, party, list, political committee, … in one campaign),
which becomes one document; this step flattens the rows per participant and resolves:

- campaign scope: only campaign types in ``--types`` (``p_kamp_rusis``, default SEI);
- election: a participant of a general Seimas election links to ``elections/{slug}/``
  via the VRK election id (``vrk_id`` column of data/elections.csv); by-election
  participants keep the VRK campaign name only;
- candidate (``dal_tipo_kodas`` K): the VRK candidate (``rink_kandidato_id``) whose
  "FIRST LAST" appears in the participant name, in the same election, narrowed by the
  constituency number when two match. That id is also the key of the ArcGIS candidate
  results (``election-results/…/#round-n-{id}``, ltlod-elections). The candidate's
  person resolves to ``persons/`` as in ltlod-elections (exact name, unique or seated
  in the elected term, curated aliases); never fuzzy. The candidate's nominating
  organisation (``v_org``, else the list's ``d_org``) resolves to ``parties/`` like a party
  participant (below);
- party (``PP``): the participant name minus VRK's status markers, by the seimas slug
  rule (``elections.slug``) or the party aliases;
- legal-person donors and service providers: their JAR code when it is 9 digits
  (``legal-entities/{code}/#this``); foreign/other codes are kept as literals;
- natural persons (donors, service providers) are private: their rows carry no identity
  in the harvest and are AGGREGATED here per participant and funding source / expense
  purpose (count + sum), never emitted one by one.

Amounts are EUR as VRK publishes them (litas-era campaigns were converted by VRK:
11.58 = 40 Lt). Funding sources, expense purposes and participant types become SKOS
concepts keyed by VRK's codes (``codes.csv``).

Usage:
    ltlod-campaign-finance --base https://linkeddata.lt/ --types SEI \
        --income data/vrk-pajamos.csv --expenses data/vrk-islaidos.csv \
        --candidates data/vrk-kandidatai-seimas.csv --elections data/elections.csv \
        --results cache/candidates.csv --persons persons.trig --parties parties.trig \
        --party-aliases data/party-aliases.csv --person-aliases data/person-aliases.csv \
        --out cache/finance --report cache/finance/unmatched.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal

from ltlod_etl.declarations import norm
from ltlod_etl.elections import clean, graph_keys, load_persons, party_name, slug

JAR = re.compile(r"\d{9}")
# VRK appends a status marker to participant names, "(S)" or "(PR)"; lapsed
# participants are prefixed "Praradęs statusą".
MARKER = re.compile(r"\s*\((S|PR)\)\s*$")
LAPSED = re.compile(r"^\s*Praradęs statusą\.?\s*", re.I)
# "MA - Fizinio asmens maža auka" -> ("MA", "Fizinio asmens maža auka")
CODED = re.compile(r"^\s*([A-Z]+)\s*-\s*(.+?)\s*$", re.S)


def is_jar(code: str) -> bool:
    """A 9-digit JAR code, not a placeholder typed into VRK's forms (000000000,
    123456789): those stay literals rather than links."""
    return bool(JAR.fullmatch(code)) and len(set(code)) > 1 and code != "123456789"


def read(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def day(value: str) -> str:
    """'2024-09-10T00:00:00' -> '2024-09-10' (blank stays blank)."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", value or "")
    return m.group(1) if m else ""


def display_name(name: str) -> str:
    return MARKER.sub("", LAPSED.sub("", clean(name))).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("base", "types", "income", "expenses", "candidates", "elections", "results", "persons",
              "parties", "party-aliases", "person-aliases", "out", "report"):
        ap.add_argument(f"--{a}", required=True)
    args = ap.parse_args()
    types = set(args.types.split())
    os.makedirs(args.out, exist_ok=True)

    income = [r for r in read(args.income) if r["p_kamp_rusis"] in types]
    expenses = [r for r in read(args.expenses) if r["p_kamp_rusis"] in types]
    if not income:
        sys.exit(f"no income rows of campaign types {sorted(types)} in {args.income}")
    elections = {r["vrk_id"]: r for r in read(args.elections) if r.get("vrk_id")}
    candidates = defaultdict(list)
    for k in read(args.candidates):
        candidates[k["rinkimu_id"]].append(k)
    result_keys = {(r["contest"], r["candidate"]) for r in read(args.results)}

    by_name, seated, _ = load_persons(args.persons, args.base)
    party_slugs = graph_keys(args.parties, "parties/")
    aliases = {party_name(r["vrk_name"]): r["slug"] for r in read(args.party_aliases)}
    person_aliases = {norm(r["vrk_name"]): r["asmens_id"] for r in read(args.person_aliases)}

    def resolve_person(name: str, term: str) -> tuple[str, str]:
        """-> (asmens_id, match-method notation): alias; name-and-office when the person was
        seated in the term (the office, so namesakes resolve too); exact-name when the name is
        unique but the candidate was not seated (a losing candidate)."""
        if norm(name) in person_aliases:
            return person_aliases[norm(name)], "alias"
        ids = by_name.get(norm(name), set())
        in_office = {i for i in ids if (i, term) in seated}
        if len(in_office) == 1:
            return next(iter(in_office)), "name-and-office"
        if len(ids) == 1:
            return next(iter(ids)), "exact-name"
        return "", ""

    def resolve_party(name: str) -> str:
        n = party_name(name)
        if n in aliases:
            return aliases[n]
        s = slug(n)
        return s if s in party_slugs else ""

    # --- campaign participants (one per p_kamp_dal_id) ---
    participants: dict[str, dict] = {}
    for r in income + expenses:
        pid = r["p_kamp_dal_id"]
        if pid in participants:
            continue
        participants[pid] = {
            "participant": pid, "election_id": r["rinkimu_id"],
            "campaign": clean(r.get("p_kamp_pavad") or ""),
            "type": r["dal_tipo_kodas"], "name": display_name(r["p_kamp_dal_pavad"]),
            "constituency_nr": r["apyg_nr"],
        }
    codes: dict[tuple[str, str], tuple[str, str]] = {}  # (scheme, code) -> (label, latest date)

    def code(scheme: str, notation: str, label: str, when: str) -> None:
        if not notation:
            return
        old = codes.get((scheme, notation))
        if old is None or when > old[1]:
            codes[(scheme, notation)] = (label, when)

    for r in income + expenses:
        code("campaign-participant-types", r["dal_tipo_kodas"], clean(r["dal_tipas"]),
             day(r.get("paj_dok_data") or r.get("dok_data")))

    unmatched = []
    linked = Counter()
    for p in participants.values():
        election = elections.get(p["election_id"])
        p["election"] = election["election"] if election else ""
        p["term"] = election["term"] if election else ""
        p["constituency"] = (f"{p['term']}-{p['constituency_nr']}"
                             if p["term"] and p["constituency_nr"] else "")
        p.update(person="", person_method="", party="", candidate="", candidacy="", nominated_by="")
        if p["type"] == "PP":
            p["party"] = resolve_party(p["name"])
            if not p["party"]:
                unmatched.append(["party", p["participant"], p["name"]])
        elif p["type"] in ("K", "KS"):
            text = " " + " ".join(p["name"].upper().split()) + " "
            found = [k for k in candidates.get(p["election_id"], [])
                     if " " + " ".join(f"{k['vardas']} {k['pavarde']}".upper().split()) + " " in text]
            if len({k["kandidato_id"] for k in found}) > 1 and p["constituency_nr"]:
                found = [k for k in found if k["apyg_nr"] == p["constituency_nr"]] or found
            ids = {k["rink_kandidato_id"] for k in found}
            if len(ids) == 1:
                k = found[0]
                p["candidate"] = k["rink_kandidato_id"]
                # the nominating party (v_org), else the list's (d_org); self-nominated: none
                org = k["v_org_pavad"] or k["d_org_pavad"]
                if org and k["v_ar_pats"] != "T":
                    p["nominated_by"] = resolve_party(org)
                p["person"], p["person_method"] = resolve_person(f"{k['vardas']} {k['pavarde']}", p["term"])
                # the ArcGIS candidate result (round 1) keyed by the same VRK id
                contest = f"{p['election']}-{k['apyg_nr']}" if p["election"] and k["apyg_nr"] else ""
                if (contest, k["rink_kandidato_id"]) in result_keys:
                    p["candidacy"] = f"{contest}/#round-1-{k['rink_kandidato_id']}"
            elif p["election_id"] in candidates:
                unmatched.append(["candidate", p["participant"], p["name"]])
        for key in ("person", "person_method", "party", "candidate", "candidacy", "nominated_by"):
            linked[key] += bool(p[key])

    # --- income: legal-person rows one by one, natural-person rows aggregated ---
    donations, income_totals = [], defaultdict(lambda: [0, Decimal(0)])
    for r in income:
        m = CODED.match(r["lesu_saltinis"] or "")
        source = r["lesu_saltinio_kodas"]
        code("campaign-funding-sources", source, m.group(2) if m else clean(r["lesu_saltinis"]),
             day(r["paj_dok_data"]))
        if r["auk_tipas"] == "J":
            jar = r["auk_ja_kodas"].strip()
            donations.append([r["pajamu_id"], r["p_kamp_dal_id"], jar if is_jar(jar) else "",
                              "" if is_jar(jar) else jar, clean(r["auk_ja_pavad"]), source,
                              clean(r["lesu_forma"]), r["suma"], day(r["paj_dok_data"])])
        else:
            t = income_totals[(r["p_kamp_dal_id"], source)]
            t[0] += 1
            t[1] += Decimal(r["suma"] or "0")

    spending, expense_totals = [], defaultdict(lambda: [0, Decimal(0)])
    for r in expenses:
        m = CODED.match(r["islaidu_paskirtis"] or "")
        purpose = r["islaidu_paskirties_kodas"]
        code("campaign-expense-purposes", purpose, m.group(2) if m else clean(r["islaidu_paskirtis"]),
             day(r["dok_data"]))
        if r["pasl_teikejo_tipas"] == "J":
            jar = r["pasl_teikejo_ja_kodas"].strip()
            spending.append([r["islaidu_id"], r["p_kamp_dal_id"], jar if is_jar(jar) else "",
                             "" if is_jar(jar) else jar, clean(r["pasl_teikejas"]), purpose,
                             r["suma"], day(r["dok_data"])])
        else:
            t = expense_totals[(r["p_kamp_dal_id"], purpose)]
            t[0] += 1
            t[1] += Decimal(r["suma"] or "0")

    def write(name: str, header: list[str], rows) -> None:
        with open(os.path.join(args.out, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    cols = ["participant", "election", "campaign", "type", "name", "constituency", "person", "person_method", "party",
            "candidate", "candidacy", "nominated_by"]
    write("participants", cols, ([p[c] for c in cols] for p in sorted(participants.values(),
                                                                       key=lambda p: int(p["participant"]))))
    write("donations", ["donation", "participant", "jar", "code", "name", "source", "form", "amount", "date"],
          donations)
    write("income-totals", ["participant", "source", "count", "amount"],
          ([p, s, n, f"{a:f}"] for (p, s), (n, a) in sorted(income_totals.items())))
    write("expenses", ["expense", "participant", "jar", "code", "name", "purpose", "amount", "date"], spending)
    write("expense-totals", ["participant", "purpose", "count", "amount"],
          ([p, s, n, f"{a:f}"] for (p, s), (n, a) in sorted(expense_totals.items())))
    write("codes", ["scheme", "notation", "slug", "label"],
          ([s, n, n.lower(), label] for (s, n), (label, _) in sorted(codes.items())))
    with open(args.report, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "participant", "name"])
        w.writerows(unmatched)

    print(f"{len(participants)} participants ({linked['party']} -> parties/, {linked['candidate']} VRK "
          f"candidates, {linked['person']} -> persons/, {linked['candidacy']} -> election-results/, {linked['nominated_by']} nominating parties); "
          f"{len(donations)} legal-person income rows, {len(income_totals)} natural-person income totals "
          f"(of {sum(n for n, _ in income_totals.values())} rows); {len(spending)} legal-person expenses, "
          f"{len(expense_totals)} natural-person expense totals; {len(unmatched)} unmatched -> {args.report}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
