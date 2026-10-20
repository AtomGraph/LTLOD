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
     "šuolis kerta atskirą named graph'ą, todėl kiekvienas dokumentas aprašomas savu "
     "`GRAPH` bloku, o blokai sujungiami per bendrus kintamuosius. "
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
     "į `parties` rinkinį), Wikidata QID (iš `alignments.trig`) ir oficialus lrs.lt portretas "
     "(`photos.trig`). Nuotrauka apribojama iki lrs.lt portreto, kad kiekvienas narys lentelėje "
     "būtų vieną kartą — susietieji nariai papildomai turi ir Wikidata P18 nuotrauką, kuri "
     "kitaip padvigubintų eilutę."),
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
     "matyti, kad su Wikidata susieta 733 iš 831 visų kadencijų Seimo narių, o nuotraukas "
     "turi 290 (oficialūs lrs.lt portretai — tik dabartinės kadencijos nariams), administracinių "
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
    ("institutions-per-municipality.rq",
     "Įstaigos pagal savivaldybę",
     "**Į kokį klausimą atsako:** kiek biudžetinių įstaigų registruota kiekvienoje "
     "savivaldybėje?\n\n"
     "**Kaip veikia:** juridinio asmens registruota buveinė susiejama su administraciniu "
     "vienetu SEMIC grandine `org:hasRegisteredSite → org:Site → org:siteAddress → "
     "locn:Address → locn:adminUnit`. Buveinės savivaldybė gaunama determinuotai iš JAR "
     "`Buveine` (ja_kodas → aob_kodas) ir AR `Pastatas` (aob_kodas → savivaldybės kodas) "
     "sujungimo. Atrenkamos tik savivaldybės (ATU-type `LTU_MSV`/`LTU_RSV`/`LTU_SV`) ir "
     "suskaičiuojamos jose registruotos įstaigos. Užklausa kerta `legal-entities` ir "
     "`admin-units` rinkinius: įstaigos (su jos buveine ir adresu) ir savivaldybės "
     "trafaretai yra atskiruose `GRAPH` blokuose, sujungtuose per savivaldybės URI."),
    ("legal-entities-per-municipality.rq",
     "Juridiniai asmenys pagal savivaldybę ir teisinę formą",
     "**Į kokį klausimą atsako:** kiek juridinių asmenų registruota kiekvienoje savivaldybėje, "
     "kokių teisinių formų jų daugiausia ir kur labiausiai paplitusios mažosios bendrijos "
     "(teisinė forma, atsiradusi 2012 m.)?\n\n"
     "**Kaip veikia:** naudojamas visas Juridinių asmenų registras (`make -C etl/legal-entities "
     "entities`). Registruota buveinė per SEMIC grandinę `org:hasRegisteredSite → org:Site → "
     "org:siteAddress → locn:Address → locn:adminUnit` nurodo ir savivaldybę, ir gyvenamąją "
     "vietovę; ATU-type lygis palieka savivaldybę. Teisinė forma atpažįstama iš JAR kodo "
     "taksonomijos URI gale (310 — UAB, 960 — mažoji bendrija, 810 — individuali įmonė, 630 — "
     "asociacija, 570 — viešoji įstaiga). Skaičiuojami tik juridiniai asmenys su registruota "
     "buveine — išregistruoti jos nebeturi."),
    ("legal-entities-on-holidays.rq",
     "Juridinių asmenų registracijos švenčių dienomis",
     "**Į kokį klausimą atsako:** ar registras dirba švenčių dienomis — kiek juridinių asmenų "
     "įregistruota dieną, kuri tuo metu buvo valstybinė šventė?\n\n"
     "**Kaip veikia:** juridinio asmens įregistravimo momentas (`time:hasTime → time:Interval "
     "→ time:hasBeginning → time:Instant`) susietas su kalendoriaus diena (`dct:temporal`), o "
     "švenčių dienos kalendoriuje pažymėtos `dct:type` ryšiu į švenčių klasifikatorių — tik tais "
     "metais, kai įstatymas tą dieną laikė švente. Todėl tą pačią kalendorinę datą užklausa "
     "skaičiuoja tik tais metais, kai ji buvo šventė. Užklausa kerta `legal-entities`, "
     "`calendar` ir `taxonomies` rinkinius."),
    ("legal-entities-top-streets.rq",
     "Gatvės, kuriose registruota daugiausia juridinių asmenų",
     "**Į kokį klausimą atsako:** kuriose gatvėse registruota daugiausia juridinių asmenų — "
     "verslo centrų, buhalterinių ir „virtualių biurų” adresai?\n\n"
     "**Kaip veikia:** registruotos buveinės adresas per `dct:spatial` nurodo gatvę "
     "(`streets/{gat_kodas}/`), kuri per `dct:isPartOf` priklauso gyvenamajai vietovei. "
     "Gatvės kodas gaunamas iš Adresų registro: JAR `Buveine` → adreso objektas "
     "(`aob_kodas`) → pastatas (`Pastatas`) arba patalpa ir jos pastatas (`Patalpa`). "
     "Paužklausa pirmiausia suranda 20 gatvių su daugiausia buveinių, tada prijungia jų ir "
     "vietovių pavadinimus. Reikia visų trijų didelių sluoksnių — juridinių asmenų, gatvių ir "
     "gyvenamųjų vietovių."),
    ("mps-per-constituency.rq",
     "Seimo nariai pagal apygardą",
     "**Į kokį klausimą atsako:** kurie Seimo nariai išrinkti kurioje vienmandatėje "
     "rinkimų apygardoje?\n\n"
     "**Kaip veikia:** vienmandatės vietos narystė (`org:Membership`) turi "
     "`ltlod:electoralDistrict` ryšį į `constituencies` rinkinį; apygardos pavadinimas "
     "paimamas iš jos `skos:prefLabel`. Apygardų ribos ir numeracija keičiasi kiekvienuose "
     "rinkimuose, todėl apygarda priklauso kadencijai (`constituencies/{kadencija}-{nr}/`), "
     "o lentelėje pirmiausia rodoma dabartinė kadencija. Apygardos išanalizuojamos iš narių srauto lauko "
     "`išrinkimo_būdas` — rinkimų apygarda nėra administracinis vienetas, todėl turi atskirą "
     "`constituencies/` konteinerį. Pagal daugiamandatį sąrašą („Pagal sąrašą”) išrinkti "
     "nariai apygardos neturi ir lentelėje nerodomi."),
    ("sittings-per-term.rq",
     "Seimo posėdžiai pagal kadenciją",
     "**Į kokį klausimą atsako:** kiek sesijų ir plenarinių posėdžių surengė kiekvienos "
     "kadencijos Seimas nuo 1990 m., kada vyko pirmasis ir paskutinis posėdis ir kiek "
     "posėdžių turi stenogramą?\n\n"
     "**Kaip veikia:** kadencijos, sesijos ir posėdžiai modeliuojami ES ELI-DL ontologija: "
     "kadencija — `eli-dl:ParliamentaryTerm`, sesijos ir posėdžiai — `eli-dl:Activity`. "
     "Posėdis per `eli-dl:forms_part_of` priklauso sesijai, o abu per "
     "`eli-dl:parliamentary_term` nurodo kadenciją. Posėdžio diena — "
     "`eli-dl:activity_date`; pirmoji ir paskutinė diena skaičiuojamos atskiroje "
     "paužklausoje tik iš datuotų posėdžių (keli suplanuoti posėdžiai datos dar neturi). "
     "Stenograma — e-seimo dokumentas, susietas per "
     "`eli-dl:recorded_in_a_realization_of` ir pažymėtas pavadinimu „Stenograma”."),
    ("votes-participation.rq",
     "Seimo narių dalyvavimas balsavimuose",
     "**Į kokį klausimą atsako:** kurie dabartiniai Seimo nariai rečiausiai dalyvauja "
     "atviruose plenarinių posėdžių balsavimuose ir kaip jie balsuoja?\n\n"
     "**Kaip veikia:** balsavimai modeliuojami ES ELI-DL ontologija (`eli-dl:Vote`); kiekvieno "
     "nario pasirinkimas — atskiras ryšys `eli-dl:had_voter_favor` / `_against` / "
     "`_abstention` į asmenį. Vardiniai balsai yra tik atviruose balsavimuose (balsavimo "
     "būdas `atviras`; sprendimai bendru sutarimu, alternatyvūs ir slapti balsavimai jų "
     "neturi), todėl vardiklis — atviri balsavimai nuo nario mandato pradžios (tenure "
     "intervalas be pabaigos), o skaitiklis — jo balsai už, prieš ir susilaikius. Duomenų "
     "rinkinys pasirinktinis: `make -C etl/seimas votes`."),
    ("bills-initiators.rq",
     "Seimo narių inicijuoti projektai",
     "**Į kokį klausimą atsako:** kurie dabartiniai Seimo nariai inicijuoja daugiausia teisės "
     "aktų projektų ir kokia jų dalis apskritai pasiekia plenarinį posėdį ir priėmimo stadiją?\n\n"
     "**Kaip veikia:** projektai modeliuojami ES ELI-DL ontologija (`eli-dl:DraftLegislationWork`); "
     "kiekvienas iniciatorius ar bendraautoris — ryšys `eli-dl:legislative_process_work_creator` "
     "į asmenį. Posėdžiuose svarstyti klausimai (`eli-dl:Activity`) per `eli-dl:involved_work` "
     "nurodo svarstytą projektą, o per `eli-dl:occured_at_stage` — stadiją (pateikimas, "
     "svarstymas, priėmimas). Projektas „pasiekė priėmimą“, jei bent vienas jo klausimas svarstytas "
     "priėmimo stadijoje — tai apytikslis sėkmės rodiklis, nes šaltinis galutinio projekto likimo "
     "nepateikia. Rinkinys pasirinktinis: `make -C etl/seimas bills`."),
    ("bills-initiators-vote-against.rq",
     "Balsavo prieš savo projektą",
     "**Į kokį klausimą atsako:** kurie Seimo nariai balsavo prieš ar susilaikė dėl projekto, kurį "
     "patys inicijavo ar pasirašė kaip bendraautoriai?\n\n"
     "**Kaip veikia:** sujungiami trys rinkiniai: projekto iniciatoriai (`bills.trig`), klausimai, "
     "kuriais tas projektas svarstytas (`agenda-items.trig`, `eli-dl:involved_work`), ir tų klausimų "
     "balsavimai (`votes.trig`, balsavimas → klausimas per `schema:superEvent`) su nario paties "
     "pasirinkimu (`eli-dl:had_voter_against` / `_abstention`). Dalis atvejų — procedūriniai "
     "balsavimai (pvz., dėl atidėjimo) ar pataisos, todėl kiekviena eilutė nurodo balsavimą "
     "patikrinti. Reikia abiejų pasirinktinių rinkinių: `make -C etl/seimas bills votes`."),
    ("declarations-by-category.rq",
     "Ką deklaruoja dabartinis Seimas",
     "**Į kokį klausimą atsako:** kokį turtą deklaruoja dabartiniai Seimo nariai — kiek jų "
     "turi butų, žemės, akcijų, pinigų užsienyje ar skolų, ir kokios tai sumos?\n\n"
     "**Kaip veikia:** kiekviena VMI turto deklaracija — atskiras dokumentas "
     "(`declarations/{asmens_id}-{metai}/`), o kiekviena nenulinė suma — jo fragmentas "
     "(`schema:MonetaryAmount`) su turto rūšimi (`dct:type` → `asset-categories` "
     "klasifikatorius). Užklausa ima 2024 ataskaitinių metų deklaracijas (`dct:temporal` → "
     "kalendoriaus metai) tų asmenų, kurių Seimo mandatas dar galioja, ir sugrupuoja sumas "
     "pagal rūšį. Rūšis, kurią VMI skaido į „Lietuvoje” ir „užsienyje”, per `skos:broader` "
     "parodoma po bendresne rūšimi. „Pasiskolintos lėšos” — įsipareigojimas, ne turtas. "
     "Partijų, kadencijos pokyčių, turto užsienyje ir balsavimų pjūviai — duomenų istorijoje "
     "„Seimo turtas 2024” (`app/stories/seimo-turtas-2024.ttl`)."),
    ("declarations-person-history.rq",
     "Vieno politiko deklaracijos per metus",
     "**Į kokį klausimą atsako:** kaip kito vieno politiko deklaruotas grynasis turtas per "
     "visus metus, kokias pareigas jis ėjo teikdamas deklaraciją ir kada ją pateikė?\n\n"
     "**Kaip veikia:** asmuo randamas pagal vardą, jo deklaracijos — per `ltlod:declarant`. "
     "Grynasis turtas = visos sumos atėmus pasiskolintas lėšas. Sumos saugomos tokios, kokias "
     "paskelbė VMI, todėl valiuta keičiasi su euro įvedimu: iki 2014 ataskaitinių metų — "
     "litai (`LTL`), nuo 2015 — eurai (1 EUR = 3,4528 LTL); palyginimui per šią ribą sumas "
     "reikia perskaičiuoti. Pareigybių grupė (`dct:type` → `declarant-groups`) rodo pareigas "
     "deklaracijos pateikimo metu (`dct:issued` — kitų metų pavasaris)."),
    ("declarations-careers.rq",
     "Karjeros tarp pareigų",
     "**Į kokį klausimą atsako:** kurie politikai ėjo daugiausia skirtingų viešųjų pareigų — "
     "Seimo nario, ministro, EP nario, mero — ir kokia tvarka?\n\n"
     "**Kaip veikia:** VMI kiekvienų metų deklaraciją priskiria vienai pareigybių grupei — "
     "pareigoms, eitoms ją teikiant. Užklausa kiekvienam asmeniui ir grupei randa pirmus ir "
     "paskutinius tokių deklaracijų metus ir sujungia juos į kelią, atrikiuotą pagal pradžią. "
     "Rodomi asmenys, ėję bent trejas skirtingas pareigas."),
    ("mayors-declared-assets.rq",
     "Merų turtas pagal savivaldybę",
     "**Į kokį klausimą atsako:** kiek turto deklaravo kiekvienos savivaldybės meras "
     "(-ai), ėję pareigas 2024 metais?\n\n"
     "**Kaip veikia:** mero pareigos yra narystė (`org:Membership`) savivaldybėje — "
     "`admin-units` objekte (`officials` rinkinys, iš Wikidata). Narystė susieja savivaldybę "
     "su asmeniu, o asmuo — su jo 2024 m. VMI turto deklaracija. Sumuojamos visos deklaruotos "
     "turto kategorijos, išskyrus pasiskolintas lėšas (tai įsipareigojimas, ne turtas)."),
    ("ministers-in-seimas.rq",
     "Vyriausybės nariai, kartu buvę Seimo nariais",
     "**Į kokį klausimą atsako:** kiek Vyriausybės narių (ministrų ir Ministro Pirmininko) "
     "kiekvienos Seimo kadencijos metu tuo pat metu turėjo ir Seimo nario mandatą?\n\n"
     "**Kaip veikia:** ministro pareigos (`officials` rinkinys, iš Wikidata) ir Seimo nario "
     "mandatas yra to paties asmens narystės tame pačiame dokumente, todėl jų laikotarpių "
     "persidengimas tikrinamas viename asmens dokumente. Pareigos priskiriamos kadencijai, "
     "jei jų laikotarpis persidengia su kadencijos laikotarpiu. Ministrų sąrašas toks "
     "išsamus, kiek juos aprašo Wikidata."),
]


def is_image(value: str) -> bool:
    return value.startswith(("http://", "https://")) and \
        (value.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".svg"))
         or "Special:FilePath" in value)


def clip(value: str) -> str:
    value = value.replace("|", "\\|").replace("\n", " ")
    if is_image(value):
        # render images inline; Commons Special:FilePath scales via ?width=
        # (also rasterizes SVG coats of arms). Wikidata stores http:// image
        # URIs, but GitHub's Markdown image proxy only renders https:// — upgrade
        # the scheme for display so Commons images don't show up blank.
        if value.startswith("http://"):
            value = "https://" + value[len("http://"):]
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
        "Kiekvienas objektas yra atskirame named graph'e (dokumente), todėl užklausos "
        "kiekvieno dokumento trafaretus rašo atskirame `GRAPH ?g { … }` bloke, o tarp "
        "dokumentų jungia per bendrus kintamuosius — tai standartinis SPARQL 1.1, veikiantis "
        "bet kurioje ketvertų (quad) saugykloje. Vieno dokumento viduje yra ir jo `#fragmentai` "
        "(pvz., asmens narystės, jų intervalai ir momentai), todėl jie rašomi tame pačiame "
        "bloke. `alignments.trig` ir `photos.trig` naudoja tuos pačius grafų vardus kaip "
        "pagrindiniai rinkiniai, todėl užkrovus susilieja su objektų grafais.\n",
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
