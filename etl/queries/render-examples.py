#!/usr/bin/env python3
"""Sugeneruoja EXAMPLES.md: kiekvienai .rq užklausai — aprašymas, SPARQL tekstas
ir rezultatų lentelė (SELECT — kintamųjų lentelė; CONSTRUCT — S/P/O trejetai).

Naudojimas:  python3 render-examples.py
"""

from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path

DIR = Path(__file__).parent
RUN = DIR / "run.sh"
OUT = DIR / "EXAMPLES.md"
MAX_CELL = 90
MAX_ROWS = 30

QUERIES = [
    ("municipality-overview.rq",
     "Savivaldybių apžvalga",
     "**Į kokį klausimą atsako:** kokios Lietuvos savivaldybės turi daugiausia gyvenamųjų "
     "vietovių, kokiai apskričiai jos priklauso ir kaip atrodo jų herbai?\n\n"
     "**Kaip veikia:** iš `admin-units` rinkinio atrenkami objektai, kurių lygmuo — miesto, "
     "rajono arba paprasta savivaldybė (ES ATU-type klasifikatoriaus konceptai "
     "`LTU_MSV`/`LTU_RSV`/`LTU_SV`). Per `dct:isPartOf` ryšį randama kiekvienos savivaldybės "
     "apskritis ir jos pavadinimas. Dvi vidinės agregacijos suskaičiuoja pavaldžius objektus: "
     "seniūnijas (tiesioginis `dct:isPartOf`) ir gyvenamąsias vietoves — vietovė gali "
     "priklausyti seniūnijai arba tiesiogiai savivaldybei, todėl tarpinis šuolis per seniūniją "
     "yra neprivalomas (`OPTIONAL` + `COALESCE`). Galiausiai iš Wikidata susiejimų "
     "(`alignments.trig`) pridedamas QID ir herbo paveikslėlis. Rikiuojama pagal vietovių "
     "skaičių — viršuje atsiduria didieji rajonai."),
    ("territorial-chain.rq",
     "Teritorinė grandinė",
     "**Į kokį klausimą atsako:** kur tiksliai yra gatvė — kokioje vietovėje, savivaldybėje "
     "ir apskrityje?\n\n"
     "**Kaip veikia:** pradedama nuo gatvių (`dct:Location` klasės objektų `streets` "
     "rinkinyje) ir `dct:isPartOf` ryšiais lipama aukštyn per administracinę hierarchiją: "
     "gatvė → gyvenamoji vietovė → (galbūt seniūnija) → savivaldybė → apskritis. Kiekvienas "
     "šuolis kerta atskirą named graph'ą — būtent tam naudojamas `<urn:x-arq:UnionGraph>`. "
     "Pavyzdžiui atrinktos tik Vilniaus miesto gatvės; pakeitus filtrą veiktų bet kuriai "
     "savivaldybei."),
    ("mps-current-factions.rq",
     "Seimo narių frakcijos",
     "**Į kokį klausimą atsako:** kas šiuo metu priklauso kuriai Seimo frakcijai, kuri "
     "partija juos iškėlė ir kaip jie atrodo?\n\n"
     "**Kaip veikia:** narystės modeliuojamos kaip atskiri `org:Membership` objektai su "
     "galiojimo intervalais, todėl „dabartinė” narystė = narystė, kurios intervalas neturi "
     "pabaigos datos (`FILTER NOT EXISTS { ... time:hasEnd ... }`). Iš tokių narysčių "
     "atrenkamos tos, kurių organizacija yra frakcija (pagal `org-unit-types` taksonomijos "
     "konceptą). Prie kiekvieno nario pridedama: iškėlusi partija (`ltlod:nominatedBy` ryšys "
     "į `parties` rinkinį), Wikidata QID (iš `alignments.trig`) ir nuotrauka — oficialus "
     "lrs.lt portretas iš `photos.trig` ir/arba Wikidata nuotrauka, todėl kai kurie nariai "
     "lentelėje matomi du kartus su skirtingomis nuotraukomis."),
    ("committee-chairs.rq",
     "Komitetų ir komisijų pirmininkai",
     "**Į kokį klausimą atsako:** kas šiuo metu vadovauja Seimo komitetams, komisijoms ir "
     "frakcijoms ir nuo kada?\n\n"
     "**Kaip veikia:** vėl naudojamas „narystė be pabaigos datos” požymis, bet šįkart "
     "filtruojama pagal pareigų konceptą iš `position-types` taksonomijos: imamos pareigos, "
     "kurių lietuviška etiketė turi „pirminink” arba „seniūn” (frakcijų vadovai vadinami "
     "seniūnais), atmetant pavaduotojus. Prie vadovo pridedama jį iškėlusi partija ir oficialus portretas — užklausa kerta šešis failus: asmenis, padalinius, pareigų taksonomiją, partijas, nuotraukas ir Wikidata susiejimus. Pradžios data paimama iš narystės galiojimo "
     "intervalo (`time:hasBeginning`). Atkreipkite dėmesį, kad pareigų konceptai išlaiko "
     "šaltinio giminines formas („pirmininkas”/„pirmininkė”)."),
    ("institutions-by-legal-form.rq",
     "Įstaigos pagal teisinę formą ir statusą",
     "**Į kokį klausimą atsako:** kiek valstybės ir savivaldybių biudžetinių įstaigų yra "
     "registruota, kokios jų teisinės formos ir kiek jų jau išregistruota ar "
     "reorganizuojama?\n\n"
     "**Kaip veikia:** iš `legal-entities` rinkinio imami visi `rov:RegisteredOrganization` "
     "objektai ir per `rov:companyType` bei `rov:orgStatus` ryšius pasiekiamos jų formų ir "
     "statusų etiketės — tai SKOS konceptai, sugeneruoti tiesiai iš JAR klasifikatorių "
     "(`taxonomies/legal-forms`, `taxonomies/legal-statuses`). Rezultatas grupuojamas ir "
     "skaičiuojamas. Lentelėje matyti įdomi detalė: senosios formos „Valstybės biudžetinė "
     "įstaiga” (580) ir „Savivaldybės biudžetinė įst.” (680) yra vien istorinės — visos "
     "tokios įstaigos išregistruotos, o veikiančios dabar registruojamos bendra forma "
     "„Biudžetinė įstaiga” (950)."),
    ("wikidata-coverage.rq",
     "Wikidata susiejimų aprėptis",
     "**Į kokį klausimą atsako:** kokia dalis mūsų duomenų jau susieta su Wikidata ir kiek "
     "objektų turi atvaizdus?\n\n"
     "**Kaip veikia:** pereinama per visus dokumentus (kiekvienas named graph'as per "
     "`foaf:primaryTopic` nurodo savo pagrindinį objektą), objektai sugrupuojami pagal RDF "
     "klasę ir suskaičiuojama, kiek jų turi `owl:sameAs` nuorodą į Wikidata ir kiek — "
     "`foaf:depiction` atvaizdą (herbą ar nuotrauką). Tai savotiška kokybės suvestinė: "
     "matyti, kad susieti visi Seimo nariai turi nuotraukas (148/148), administracinių "
     "vienetų susieta 642, o gatvės ir įstaigos su Wikidata dar nesiejamos."),
    ("construct-faction-leaders.rq",
     "CONSTRUCT: frakcijų seniūnų profiliai",
     "**Ką daro:** vietoj rezultatų lentelės ši užklausa **sukuria naują RDF grafą** — "
     "kompaktiškus frakcijų vadovų profilius schema.org žodynu, tinkamus, pvz., perduoti į "
     "kitą sistemą ar įterpti į tinklalapį.\n\n"
     "**Kaip veikia:** `WHERE` dalis suranda galiojančias narystes, kurių pareigos — "
     "„Frakcijos seniūnas/seniūnė” (be pavaduotojų), ir surenka vardą, frakciją, oficialią "
     "lrs.lt nuotrauką bei Wikidata QID iš keturių skirtingų rinkinių. `CONSTRUCT` šablonas "
     "iš šių duomenų sudeda naujus trejetus: asmuo tampa `schema:Person` su `schema:name`, "
     "`schema:memberOf`, `schema:image` ir `schema:sameAs`, frakcija — `schema:Organization`. "
     "Žemiau rezultatas parodytas kaip subjekto–predikato–objekto (S/P/O) trejetų lentelė."),
]


def is_image(value: str) -> bool:
    return value.startswith(("http://", "https://")) and \
        (value.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".svg"))
         or "Special:FilePath" in value)


def clip(value: str) -> str:
    value = value.replace("|", "\\|").replace("\n", " ")
    if is_image(value):
        # render images inline; Commons Special:FilePath scales via ?width=
        # (also rasterizes SVG coats of arms)
        src = value + "?width=120" if "Special:FilePath" in value else value
        return f'<img src="{src}" width="60" alt=""/>'
    return value if len(value) <= MAX_CELL else value[:MAX_CELL - 1] + "…"


def md_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for row in rows[:MAX_ROWS]:
        lines.append("| " + " | ".join(clip(c) for c in row) + " |")
    if len(rows) > MAX_ROWS:
        lines.append(f"| … | {'&nbsp; |' * (len(header) - 1)}".rstrip("|") + "|")
    return "\n".join(lines)


def run_select(query: Path) -> str:
    out = subprocess.run([str(RUN), str(query), "--results=csv"],
                         check=True, capture_output=True, text=True).stdout
    reader = csv.reader(io.StringIO(out))
    header, *rows = list(reader)
    return md_table(header, rows)


def run_construct(query: Path) -> str:
    import os
    turtle = subprocess.run([str(RUN), str(query)],
                            check=True, capture_output=True, text=True).stdout
    jena_bin = os.environ.get("JENA_HOME", "/Users/martynas/WebRoot/apache-jena-6.1.0") + "/bin"
    riot = subprocess.run([f"{jena_bin}/riot", "--syntax=turtle", "--output=ntriples"],
                          input=turtle, check=True, capture_output=True, text=True).stdout
    rows = []
    for line in sorted(riot.splitlines()):
        s, p, rest = line.split(" ", 2)
        rows.append([s, p, rest.rstrip(" .")])
    return md_table(["subjektas (S)", "predikatas (P)", "objektas (O)"], rows)


def main() -> None:
    parts = [
        "# SPARQL užklausų pavyzdžiai\n",
        "Užklausos vykdomos visus `datasets/current/` rinkinius užkrovus į atmintį "
        "(Jena, ~1 mln. ketvertų):\n",
        "```shell\n./run.sh <užklausa.rq>     # viena užklausa\n"
        "./run.sh --all             # visos iš eilės\n```\n",
        "Kadangi kiekvienas objektas yra atskirame named graph'e, kiekviena užklausa "
        "deklaruoja `FROM <urn:x-arq:UnionGraph>` — Jena sintetinį grafą, kuris yra visų "
        "named graph'ų sąjunga. Ji tampa užklausos default grafu, todėl trafaretai ir "
        "property path'ai veikia tarp objektų grafų be `GRAPH` apvalkalų. `alignments.trig` "
        "ir `photos.trig` naudoja tuos pačius grafų vardus kaip pagrindiniai rinkiniai, "
        "todėl užkrovus susilieja su objektų grafais.\n",
        "Šis failas sugeneruotas `python3 render-examples.py` — perleidus ETL, "
        "lenteles galima atnaujinti ta pačia komanda.\n",
    ]

    for filename, title, description in QUERIES:
        query = DIR / filename
        print(f"vykdoma: {filename}", flush=True)
        table = run_construct(query) if filename.startswith("construct") else run_select(query)
        parts += [f"\n## {title}\n",
                  f"{description}\n",
                  f"```sparql\n{query.read_text().strip()}\n```\n",
                  f"Rezultatai:\n\n{table}\n"]

    OUT.write_text("\n".join(parts))
    print(f"įrašyta: {OUT}")


if __name__ == "__main__":
    main()
