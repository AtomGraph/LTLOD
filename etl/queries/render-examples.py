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
     "Savivaldybės su apskritimi, seniūnijų ir gyvenamųjų vietovių skaičiais, "
     "Wikidata QID ir herbu — sujungia `admin-units` hierarchiją su `alignments.trig` "
     "(Wikidata susiejimais)."),
    ("territorial-chain.rq",
     "Teritorinė grandinė",
     "Pilna teritorinė grandinė gatvė → gyvenamoji vietovė → savivaldybė → apskritis, "
     "einant `dct:isPartOf` ryšiais per keturis skirtingus named graph'us."),
    ("mps-current-factions.rq",
     "Seimo narių frakcijos",
     "Dabartinė frakcijų sudėtis (narystės be pabaigos datos) su iškėlusia partija, "
     "Wikidata QID ir nuotrauka — sujungia `seimas`, `parties`, `taxonomies` ir "
     "`alignments`/`photos` rinkinius."),
    ("committee-chairs.rq",
     "Komitetų ir komisijų pirmininkai",
     "Kas šiuo metu vadovauja Seimo komitetams, komisijoms ir frakcijoms — pareigų "
     "konceptai atrenkami pagal lietuviškas etiketes iš `position-types` taksonomijos."),
    ("institutions-by-legal-form.rq",
     "Įstaigos pagal teisinę formą ir statusą",
     "Biudžetinių įstaigų skaičiai pagal teisinę formą ir statusą — sujungia "
     "`legal-entities` su JAR klasifikatorių taksonomijomis."),
    ("wikidata-coverage.rq",
     "Wikidata susiejimų aprėptis",
     "Kiek kiekvienos RDF klasės objektų turi Wikidata `owl:sameAs` nuorodą ir "
     "atvaizdą (`foaf:depiction`) — visų rinkinių suvestinė."),
    ("construct-faction-leaders.rq",
     "CONSTRUCT: frakcijų seniūnų profiliai",
     "Iš kelių rinkinių sukonstruojami kompaktiški schema.org profiliai — rezultatas "
     "yra RDF grafas, žemiau pateikiamas kaip S/P/O trejetų lentelė."),
]


def clip(value: str) -> str:
    value = value.replace("|", "\\|").replace("\n", " ")
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
    jena_bin = os.environ.get("JENA_HOME", "/Users/martynas/WebRoot/apache-jena-5.6.0") + "/bin"
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
        "Kadangi kiekvienas objektas yra atskirame named graph'e, kryžminės užklausos "
        "naudoja Jena sintetinį `<urn:x-arq:UnionGraph>` — visų named graph'ų sąjungą, "
        "kurioje property path'ai veikia tarp objektų grafų. `alignments.trig` ir "
        "`photos.trig` naudoja tuos pačius grafų vardus kaip pagrindiniai rinkiniai, "
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
