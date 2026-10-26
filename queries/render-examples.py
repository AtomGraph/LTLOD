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
    ("facilities-per-municipality.rq",
     "Įstaigos ir paveldas savivaldybėse",
     "**Į kokį klausimą atsako:** kiek savivaldybėje veikiančių švietimo įstaigų, licencijuotų "
     "sveikatos priežiūros įstaigų ir kultūros vertybių?\n\n"
     "**Kaip veikia:** kiekvienos įstaigos ar vertybės adresas (`locn:Address`) nurodo "
     "savivaldybę pagal Adresų registro kodą (`locn:adminUnit`). Trys atskiros agregacijos "
     "(kad skaičiai nesidaugintų) sujungiamos su savivaldybėmis iš `admin-units`; veikiančios "
     "švietimo įstaigos — tos, kurių buvimo registre intervalas neturi pabaigos."),
    ("school-closures-per-municipality.rq",
     "Mokyklų tinklo mažėjimas",
     "**Į kokį klausimą atsako:** kuriose savivaldybėse nuo 2010 m. uždaryta didžiausia dalis "
     "bendrojo ugdymo mokyklų?\n\n"
     "**Kaip veikia:** mokyklos atrenkamos pagal ŠVIS tipą (`dct:type`), išregistravimas — "
     "buvimo registre intervalo pabaigos momentas (`time:hasEnd`), tas pats, kuris susietas su "
     "kalendoriaus diena. Skaičiuojama, kiek mokyklų tebeveikia ir kiek išregistruota nuo 2010 m."),
    ("health-care-public-institutions.rq",
     "Biudžetinės įstaigos su sveikatos priežiūros licencija",
     "**Į kokį klausimą atsako:** kurios valstybės ir savivaldybių biudžetinės įstaigos teikia "
     "asmens sveikatos priežiūros paslaugas ir kiek veiklos vietų turi?\n\n"
     "**Kaip veikia:** sveikatos priežiūros įstaiga su juridiniu asmeniu susieta pagal įmonės "
     "kodą (`ltlod:legalEntity`), todėl jungimas tarp `facilities` ir `legal-entities` — paprastas "
     "URI sutapimas; registruota buveinė ir teisinė forma imamos iš JAR, veiklos vietos — iš "
     "VASPVT licencijų registro."),
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
    ("elections-personal-vote.rq",
     "Asmeninis balsas vienmandatėse apygardose",
     "**Į kokį klausimą atsako:** kurie 2024 m. vienmandatėse apygardose išrinkti Seimo "
     "nariai surinko gerokai daugiau balsų nei juos iškėlusi partija toje pačioje apygardoje "
     "— t. y. laimėjo asmeniniu populiarumu, ne partijos vardu?\n\n"
     "**Kaip veikia:** viename apygardos rezultatų dokumente (`election-results`) yra ir "
     "kandidatų rezultatai, ir toje apygardoje už partijų sąrašus atiduoti balsai. Užklausa "
     "randa laimėtoją (`ltlod:elected true`), jo I turo balsų dalį ir jį iškėlusios partijos "
     "(`ltlod:nominatedBy`) sąrašo balsų dalį tame pačiame ture (`ltlod:party`) — abu "
     "skaičiuoti tame pačiame balsavime. Skirtumas procentiniais punktais = asmeninis balsas. "
     "Vardas imamas iš `persons`, partijos pavadinimas — iš `parties` dokumento. Išsikėlę "
     "patys laimėtojai sąrašo neturi ir nerodomi."),
    ("elections-list-seats-of-district-losers.rq",
     "Pralaimėję apygardoje, bet Seime pagal sąrašą",
     "**Į kokį klausimą atsako:** kas 2024 m. pralaimėjo vienmandatėje apygardoje, bet vis "
     "tiek tapo Seimo nariu — pagal partijos sąrašą?\n\n"
     "**Kaip veikia:** iš `elections` imama 2024 m. rinkimų išrinkta kadencija "
     "(`ltlod:electedTerm`). Apygardos rezultatų dokumente randami su asmenimis susieti "
     "kandidatai (`ltlod:candidate`), kurie toje apygardoje nebuvo išrinkti; asmens "
     "dokumente — jų Seimo nario vieta toje kadencijoje be rinkimų apygardos "
     "(`ltlod:electoralDistrict` neturi tik pagal sąrašą išrinktųjų vietos). Rodoma geriausia "
     "kandidato balsų dalis ir vieta abiejuose turuose."),
    ("finance-corporate-donors-per-party.rq",
     "Didžiausi juridinių asmenų įnašai partijoms",
     "**Į kokį klausimą atsako:** kurios įmonės daugiausia aukojo kiekvienos partijos ir jos "
     "kandidatų Seimo rinkimų kampanijoms?\n\n"
     "**Kaip veikia:** politinės kampanijos dalyvio dokumente (`campaign-finance`) yra jo "
     "juridinių asmenų įnašai (`ltlod:CampaignDonation`). Atrenkami lėšų šaltinio „JAA — "
     "juridinio asmens auka“ įnašai (be partijos pervedimų ir valstybės biudžeto lėšų), o "
     "partija nustatoma pagal dalyvį: partijos kampanija (`ltlod:campaignOf`) arba kandidatą "
     "iškėlusi partija (`ltlod:nominatedBy`). Aukotojas — kaip paskelbta, su nuoroda į "
     "juridinį asmenį pagal JAR kodą. Beveik visi tokie įnašai — 2008 m. kampanijos."),
    ("finance-donors-procurement.rq",
     "Kampanijų aukotojai — viešųjų pirkimų tiekėjai",
     "**Į kokį klausimą atsako:** kurios įmonės aukojo Seimo rinkimų kampanijoms ir taip pat "
     "laimėjo viešųjų pirkimų sutarčių?\n\n"
     "**Kaip veikia:** aukotojas (`ltlod:donor`) ir sutarties tiekėjas (`epo:bindsContractor → "
     "epo:playedBy`) — tas pats juridinio asmens IRI, abiejų rinkinių sukonstruotas iš JAR "
     "kodo (`legal-entities/{ja_kodas}/#this`), todėl jie sujungiami neįkėlus JAR registro. "
     "Dvi vidinės agregacijos susumuoja įmonės „JAA” įnašus ir jos sutarčių vertę. Reikia "
     "įkelto `procurement` rinkinio (be jo rezultatas tuščias). Atkreipkite dėmesį į "
     "laikotarpius: įmonių įnašai beveik visi iš 2008 m. kampanijos, o pirkimai — naujausios "
     "sutartys, todėl sutapimas rodo tą pačią įmonę abiejose pusėse, o ne mainus. Užklausa "
     "kerta `elections` ir `procurement` rinkinius."),
    ("finance-spend-per-vote.rq",
     "Kiek kainavo balsas",
     "**Į kokį klausimą atsako:** kiek eurų 2024 m. vienmandatėse apygardose išrinkti Seimo "
     "nariai išleido kampanijai vienam I turo balsui?\n\n"
     "**Kaip veikia:** kandidato kampanijos dalyvis susietas su jo rezultatu apygardoje "
     "(`ltlod:candidacy`) per VRK kandidato ID. Susumuojamos dalyvio išlaidos — juridinių "
     "asmenų paslaugos (`campaign-expenses.trig`) ir fizinių asmenų paslaugų sumos — ir "
     "padalinamos iš I turo balsų. Partijos išlaidos kandidatui neįskaičiuotos."),
    ("procurement-by-municipality.rq",
     "Viešieji pirkimai pagal perkančiosios organizacijos savivaldybę",
     "**Į kokį klausimą atsako:** kurių savivaldybių įstaigos per paskutinius 12 mėnesių "
     "sudarė didžiausios vertės viešųjų pirkimų sutarčių?\n\n"
     "**Kaip veikia:** sutartis (ES ePO) per `epo:bindsBuyer` ir `epo:playedBy` susieta su "
     "perkančiąja organizacija pagal jos JAR kodą, o ši — per registruotos buveinės grandinę "
     "(`org:hasRegisteredSite → org:Site → org:siteAddress → locn:Address → locn:adminUnit`) — "
     "su savivaldybe. Sutarčių vertės pirmiausia sumuojamos kiekvienai perkančiajai "
     "organizacijai, tada — savivaldybei. Užklausa kerta tris rinkinius: `procurement`, "
     "`legal-entities` ir `admin-units`. Perkančiosios organizacijos, kurių nėra "
     "`legal-entities` (pvz., valstybės įmonės, kol neįkeltas pilnas JAR), į sumą nepatenka."),
    ("procurement-top-suppliers.rq",
     "Didžiausi viešojo sektoriaus tiekėjai",
     "**Į kokį klausimą atsako:** kurie tiekėjai per paskutinius 12 mėnesių gavo didžiausios "
     "vertės viešųjų pirkimų sutarčių ir kiek skirtingų perkančiųjų organizacijų iš jų perka?\n\n"
     "**Kaip veikia:** kiekvienos sutarties tiekėjo vaidmuo (`epo:bindsContractor → "
     "epo:Contractor → epo:playedBy`) nurodo juridinį asmenį pagal jo JAR kodą — nuoroda "
     "sukonstruojama iš kodo, nežiūrint į kitą rinkinį. Sumuojama tiekėjo sutarčių vertė ir "
     "skaičiuojami skirtingi pirkėjai (vienas dominuojantis pirkėjas ar plati klientų bazė). "
     "Pavadinimas paimamas iš tiekėjo `legal-entities` dokumento, jei jis įkeltas (pilnas "
     "JAR), kitaip rodomas JAR kodas."),
    ("procurement-on-holidays.rq",
     "Sutartys, sudarytos savaitgaliais ir per šventes",
     "**Į kokį klausimą atsako:** kiek viešųjų pirkimų sutarčių sudaryta ne darbo dieną — "
     "savaitgalį ar per valstybinę šventę?\n\n"
     "**Kaip veikia:** kiekvienos sutarties sudarymo data susieta su kalendoriaus diena "
     "(`dct:temporal`), o dienos dokumentas žino savaitės dieną (`time:dayOfWeek`) ir, jei tą "
     "dieną buvo valstybinė šventė, — šventės konceptą (`dct:type`). Sutartys suskirstomos "
     "pagal dienos rūšį. Didelė ne darbo dienų dalis — ženklas, kad sutartys registruojamos "
     "atgaline data ar paketais, ne tik darbo įpročių rodiklis."),
    ("vtek-interest-lobbying.rq",
     "Privatūs interesai ir lobizmas",
     "**Į kokį klausimą atsako:** kurie politikai deklaravo ryšį (narystę, valdymo organą, "
     "akcijas) su juridiniu asmeniu, kuris pats įrašytas į lobistų sąrašą — ir kiek lobistinės "
     "veiklos deklaracijų tas juridinis asmuo pateikė, kiek jų nurodo patį politiką?\n\n"
     "**Kaip veikia:** PINREG ryšys yra `org:Membership` su `ltlod:interestOrganization` į "
     "`legal-entities/{JAR kodas}/`; SKAIDRIS lobistas — juridinis asmuo — turi `ltlod:agent` "
     "į tą patį URI, nes abu rinkiniai jį sukuria iš to paties JAR kodo. Taip sujungiami du "
     "skirtingų registrų įrašai be jokių paieškų pagal pavadinimą. Lobistinės deklaracijos, "
     "kuriose paveiktas asmuo — pats politikas, skaičiuojamos atskirai."),
    ("vtek-lobbied-officials.rq",
     "Dažniausiai lobistų veikti pareigūnai",
     "**Į kokį klausimą atsako:** kuriuos Seimo narius (ir kitus pareigūnus, esančius "
     "`persons/`) lobistai nurodo dažniausiai, kiek skirtingų lobistų juos veikė ir kokiose "
     "srityse?\n\n"
     "**Kaip veikia:** kiekviena lobistinės veiklos deklaracija turi paveiktų asmenų "
     "fragmentus (`ltlod:contact`); tie, kurių vardas ir pavardė vienareikšmiškai sutampa su "
     "asmeniu, susieti `ltlod:influencedPerson`. Sritys (`dct:subject`) surenkamos atskira "
     "agregacija, nes pačių pareigūnų deklaracijos sritį nurodo retai."),
    ("vtek-interest-procurement.rq",
     "Privatūs interesai ir viešieji pirkimai",
     "**Į kokį klausimą atsako:** kurių politikų valdomos privataus sektoriaus įmonės (akcijos, "
     "pajai, vadovavimas, valdybos ar kitas kolegialus valdymo organas) laimi viešuosius pirkimus, kiek "
     "sutarčių ir už kokią sumą — ir ar pats politikas deklaravo, kad juridinis asmuo dalyvauja "
     "pirkimuose?\n\n"
     "**Kaip veikia:** ryšys ir pirkimo sutarties tiekėjo vaidmuo (`epo:playedBy`) rodo į tą "
     "patį `legal-entities/{JAR kodas}/` URI. Įtraukiami tik nuosavybės ir valdymo ryšiai: "
     "darbovietės, darbas, eilinė ar garbės narystė (pvz., masinėje organizacijoje) ir „kiti "
     "ryšiai” nėra dalis juridinio asmens ir neįtraukiami. Įmonės sektorius imamas iš jos "
     "JAR teisinės formos (`skos:scopeNote` „Privatus”): vietos asociacijų, viešųjų įstaigų ar "
     "universitetų valdymo organuose politikai dažniausiai dalyvauja eidami pareigas, todėl "
     "jie neįtraukiami. Sutapimas reiškia, kad politiko "
     "deklaruotas juridinis asmuo laimėjo sutarčių, o ne kad politikas jas lėmė. Reikia įkelto "
     "viešųjų pirkimų rinkinio (`etl/procurement`) ir pilno JAR (`entities.trig`); be jų "
     "rezultatas tuščias."),
    ("employment-wage-by-municipality.rq",
     "Vidutinis darbo užmokestis pagal savivaldybes",
     "**Į kokį klausimą atsako:** kokiose savivaldybėse paskutinį Sodros mėnesį mokamas "
     "didžiausias vidutinis darbo užmokestis, kiek jose yra draudėjų ir apdraustųjų, ir "
     "koks vidurkis per 12 mėnesių?\n\n"
     "**Kaip veikia:** kiekvienas draudėjas (darbdavys) — atskiras dokumentas su vienu "
     "suvestiniu RDF Data Cube stebiniu (`qb:Observation`): paskutinio mėnesio apdraustųjų "
     "skaičius ir vidutinis užmokestis bei 12 mėnesių lango vidurkiai. Mėnuo per "
     "`dct:temporal` susietas su kalendoriaus mėnesio dokumentu, vieta "
     "(`sdmx-dimension:refArea`) — su savivaldybe `admin-units` rinkinyje, o per jos "
     "`dct:isPartOf` randama apskritis. Vidurkis sveriamas apdraustųjų skaičiumi. Vieta — "
     "draudėjo registracijos savivaldybė, ne darbuotojų gyvenamoji vieta. Užklausa kerta "
     "`employment`, `admin-units` ir `calendar` rinkinius."),
    ("employment-institutions-by-form.rq",
     "Darbdaviai pagal teisinę formą",
     "**Į kokį klausimą atsako:** kiek kiekvienos teisinės formos juridinių asmenų paskutinį "
     "Sodros mėnesį turėjo apdraustųjų, kiek žmonių juose dirba ir koks jų vidutinis darbo "
     "užmokestis?\n\n"
     "**Kaip veikia:** Sodros stebinio darbdavys (`ltlod:employer`) yra juridinio asmens IRI, "
     "sukonstruotas iš JAR kodo (`legal-entities/{ja_kodas}/#this`), todėl jungiamas su JAR "
     "dokumentu be jokios sąsajų lentelės. Iš JAR dokumento imama teisinė forma "
     "(`rov:companyType` → `legal-forms` klasifikatorius). Be pilno JAR registro "
     "(`entities.trig`) įkeltos tik biudžetinės įstaigos, todėl lentelėje — viena eilutė: "
     "valstybės (580) ir savivaldybių (680) biudžetinių įstaigų formos nebenaudojamos, visos "
     "tokios įstaigos išregistruotos, o veikiančios turi bendrą formą „Biudžetinė įstaiga” "
     "(950). Įkėlus pilną registrą atsiranda visos formos. Užklausa kerta `employment`, "
     "`legal-entities` ir `taxonomies` rinkinius."),
    ("land-public-buyers.rq",
     "Biudžetinės įstaigos, prašančios leisti įsigyti žemės",
     "**Į kokį klausimą atsako:** kurios valstybės ir savivaldybių įstaigos prašė "
     "Nacionalinės žemės tarnybos sutikimo įsigyti žemės ūkio ar miškų ūkio paskirties "
     "žemės, kiek kartų, kiek hektarų ir kur?\n\n"
     "**Kaip veikia:** `land-acquisitions` rinkinio prašymas su juridiniu asmeniu susietas "
     "(`ltlod:applicant`) tik tada, kai NŽT nurodytas pavadinimas atitinka JAR kodą arba jo "
     "palyginti negalima. Įstaigos pavadinimas ir teisinė forma imami iš jos pačios "
     "`legal-entities` dokumento (biudžetinių įstaigų formos 580, 680, 950), savivaldybė — "
     "iš `admin-units` (`schema:location`). Dažniausiai tai savivaldybių administracijos, "
     "įsigyjančios žemę viešiesiems poreikiams."),
    ("land-companies-vs-persons.rq",
     "Žemės ūkio paskirties žemė: įmonės ir gyventojai pagal apskritį",
     "**Į kokį klausimą atsako:** kiek žemės ūkio paskirties žemės NŽT leido įsigyti "
     "juridiniams asmenims, o kiek — gyventojams, ir kokia įmonių dalis kiekvienoje "
     "apskrityje?\n\n"
     "**Kaip veikia:** juridinių asmenų prašymai skaičiuojami po vieną (tik gavę sutikimą — "
     "`ltlod:decision` → `sutikimas`), fizinių asmenų — iš paskelbtų suvestinių "
     "(`qb:Observation`, `ltlod:consentedArea`), nes pavieniai jų prašymai neskelbiami; "
     "mažiau nei 3 prašymų langeliai praleisti, todėl gyventojų plotas šiek tiek "
     "nepakankamas. Savivaldybė priskiriama apskričiai per `dct:isPartOf` (`admin-units`)."),
    ("procurement-small-suppliers.rq",
     "Milijoninės sutartys tiekėjams be darbuotojų",
     "**Į kokį klausimą atsako:** kurie tiekėjai per paskutinius 12 mėnesių laimėjo bent "
     "1 mln. Eur viešųjų pirkimų sutarčių, nors Sodrai paskutinį mėnesį deklaravo ne daugiau "
     "kaip tris apdraustuosius?\n\n"
     "**Kaip veikia:** tiekėjo vaidmuo sutartyje (`epo:bindsContractor → epo:playedBy`), Sodros "
     "darbdavio stebinys (`ltlod:employer`) ir JAR dokumentas — tas pats "
     "`legal-entities/{JAR kodas}/#this` URI, todėl trys registrai sujungiami be sąsajų lentelių. "
     "Tai signalas, o ne išvada: viešojo ir privataus sektorių partnerystės projektų bendrovės, "
     "kontroliuojančiosios bendrovės ar perpardavėjai teisėtai turi mažai darbuotojų, o Sodra "
     "skaičiuoja tik pačios bendrovės apdraustuosius (ne subrangovus ar užsienio darbuotojus). "
     "Užklausa kerta `procurement`, `employment` ir `legal-entities` rinkinius."),
    ("procurement-buyer-concentration.rq",
     "Vienas pirkėjas — vienas tiekėjas",
     "**Į kokį klausimą atsako:** kurios perkančiosios organizacijos per paskutinius 12 mėnesių "
     "bent 80 % savo pirkimų (iš ne mažiau kaip 2 mln. Eur) skyrė vienam privataus sektoriaus "
     "tiekėjui?\n\n"
     "**Kaip veikia:** dvi vidinės agregacijos suskaičiuoja kiekvieno pirkėjo visas sutartis ir "
     "jo sutartis su kiekvienu tiekėju; paliekamos poros, kur vienas tiekėjas gauna ≥ 80 %. "
     "Tiekėjo sektorius imamas iš JAR teisinės formos (`skos:scopeNote` „Privatus”), todėl "
     "valstybės ir savivaldybių įmonės bei biudžetinės įstaigos neįtraukiamos; valstybei ar "
     "savivaldybei priklausanti UAB vis tiek laikoma privačia, nes atvirame JAR savininkų nėra. "
     "Didelė koncentracija gali būti visiškai teisėta (vienas didelis darbų pirkimas, vienintelis "
     "licencijuotas tiekėjas, preliminarioji sutartis), bet būtent čia verta patikrinti "
     "konkurenciją. Užklausa kerta `procurement`, `legal-entities` ir `taxonomies` rinkinius."),
    ("procurement-dissolved-suppliers.rq",
     "Sutartys su jau išregistruotomis įmonėmis",
     "**Į kokį klausimą atsako:** kurios viešųjų pirkimų sutartys sudarytos su tiekėju, kuris "
     "pagal JAR kodą sutarties dieną jau buvo išregistruotas?\n\n"
     "**Kaip veikia:** sutarties sudarymo data (`epo:hasContractConclusionDate`) palyginama su "
     "tiekėjo išregistravimo data JAR dokumente (`schema:dissolutionDate`). Dažniausiai tai "
     "duomenų kokybės signalas — klaidingai įvestas ar pasenęs kodas pirkimų sistemoje, filialo "
     "kodas vietoj juridinio asmens — bet sutartis su nebeegzistuojančia įmone verta paaiškinimo "
     "bet kuriuo atveju. Užklausa kerta `procurement` ir `legal-entities` rinkinius."),
    ("taxes-contractors-with-arrears.rq",
     "Viešųjų pirkimų tiekėjai su pradelsta mokestine nepriemoka",
     "**Į kokį klausimą atsako:** kurie viešųjų pirkimų tiekėjai šiuo metu turi pradelstą "
     "mokestinę nepriemoką, ir kokia jų laimėtų sutarčių vertė?\n\n"
     "**Kaip veikia:** tiekėjas (`epo:playedBy`) ir mokesčių mokėtojas (`ltlod:taxpayer`) — tas "
     "pats `legal-entities/{jar}/#this` IRI, abiejų pipeline'ų nukaltas iš JAR kodo, todėl jungimas "
     "nereikalauja JAR registro. Viešųjų pirkimų įstatymas draudžia sudaryti sutartį su tiekėju, "
     "turinčiu pradelstą įsiskolinimą valstybės biudžetui ar Sodrai, tad tiekėjas su nepriemoka "
     "vertas dėmesio — tačiau nepriemoka yra dabartinė, ne sutarties dienos būsena. Užklausa kerta "
     "`procurement` ir `taxes` rinkinius."),
    ("taxes-contract-value-vs-paid.rq",
     "Sutarčių vertė palyginti su sumokamais mokesčiais",
     "**Į kokį klausimą atsako:** kurių viešųjų pirkimų tiekėjų laimėtų sutarčių vertė labiausiai "
     "viršija jų per tuos pačius metus sumokėtus mokesčius?\n\n"
     "**Kaip veikia:** kiekvienam tiekėjui susumuojama laimėtų sutarčių vertė "
     "(`epo:hasContractValue`) ir per langą sumokėti mokesčiai (`ltlod:taxesPaid`), sujungiant per "
     "JAR kodą. Didelis santykis — signalas patikrinti (marža, ar pajamos nukreiptos kitur), ne "
     "išvada: sutartys gali būti daugiametės, o mokesčiai pateikti atėmus grąžinimus. Užklausa "
     "kerta `procurement` ir `taxes` rinkinius."),
    ("contractors-in-insolvency.rq",
     "Viešųjų pirkimų tiekėjai nemokumo registre",
     "**Į kokį klausimą atsako:** kurie viešųjų pirkimų tiekėjai yra ar buvo nemokūs (bankrotas ar "
     "restruktūrizavimas)?\n\n"
     "**Kaip veikia:** tiekėjas (`epo:playedBy`) ir nemoki įmonė (`ltlod:insolvent`) — tas pats "
     "`legal-entities/{jar}/#this` IRI, nukaltas iš JAR kodo. Įmonė, laiminti viešuosius pirkimus ir "
     "kartu einanti per bankrotą ar restruktūrizavimą (ar netrukus po jų), verta dėmesio. Rodoma "
     "bylos pradžios data, kad matytųsi laikas sutarties atžvilgiu: viešųjų pirkimų duomenys apima tik "
     "pastaruosius 12 mėn., tad dauguma bylų čia yra ankstesnės (tebeveikianti restruktūrizuojama įmonė, "
     "arba bankrotas įmonės, kurios ankstesnės sutartys nepatenka į langą). Užklausa kerta `procurement` "
     "ir `insolvency` rinkinius."),
    ("donors-later-insolvent.rq",
     "Politinių kampanijų rėmėjai, vėliau tapę nemokūs",
     "**Į kokį klausimą atsako:** kurie juridiniai asmenys parėmė politinę kampaniją ir vėliau "
     "tapo nemokūs?\n\n"
     "**Kaip veikia:** rėmėjas (`ltlod:donor`) ir nemoki įmonė (`ltlod:insolvent`) — tas pats "
     "`legal-entities/{jar}/#this` IRI. Skaičiuojamos tik bylos, prasidėjusios po aukos. Įmonė, "
     "finansavusi kampaniją ir netrukus bankrutavusi, verta dėmesio — auka galėjo nualinti jau "
     "smunkančią įmonę, arba politinis ryšys turi reikšmės tolesniems įvykiams. Užklausa kerta "
     "`elections` ir `insolvency` rinkinius."),
    ("pinreg-ties-eu-funds.rq",
     "Politikų įmonės ir ES fondų parama",
     "**Į kokį klausimą atsako:** kurių politikų deklaruoti juridiniai asmenys gavo 2014–2020 m. "
     "ES struktūrinių fondų paramą?\n\n"
     "**Kaip veikia:** privataus intereso ryšio įmonė (`ltlod:interestOrganization`) ir paramos "
     "gavėjas (`ltlod:beneficiary`) — tas pats `legal-entities/{jar}/#this` IRI. Imami tik "
     "nuosavybės ar valdymo ryšiai (akcininkas, vadovas, valdybos narys ir pan.). ES lėšos "
     "susumuojamos ten, kur jos nurodytos (tik ~685 koduotų projektų; finansinių priemonių "
     "išmokos sumų neturi). Politiko ryšys su ES lėšų gavusia įmone — signalas patikrinti, ne "
     "išvada. Užklausa kerta `vtek` ir `eu-funds` rinkinius."),
    ("eu-funds-and-procurement.rq",
     "Įmonės, gavusios ir ES fondų, ir viešųjų pirkimų",
     "**Į kokį klausimą atsako:** kurios įmonės gavo ir ES struktūrinių fondų paramą, ir laimėjo "
     "viešųjų pirkimų sutarčių — du viešųjų pinigų srautai tai pačiai įmonei?\n\n"
     "**Kaip veikia:** paramos gavėjas (`ltlod:beneficiary`) ir pirkimų tiekėjas (`epo:playedBy`) "
     "— tas pats `legal-entities/{jar}/#this` IRI, nukaltas iš JAR kodo. Platus viešųjų pinigų "
     "pėdsakas savaime nėra pažeidimas, bet derinį verta žemėlapyje matyti. Užklausa kerta "
     "`eu-funds` ir `procurement` rinkinius."),
    ("suppliers-under-threshold.rq",
     "Tiekėjai, apmokami smulkiomis sąskaitomis be pirkimo",
     "**Į kokį klausimą atsako:** kuriems tiekėjams viešasis sektorius per metus sumoka daug "
     "smulkių (žemiau pirkimų ribos) sąskaitų, nors viešųjų pirkimų registre jie neturi "
     "sutarties?\n\n"
     "**Kaip veikia:** sąskaitų tiekėjas (`ltlod:spendingSupplier`) ir pirkimų tiekėjas "
     "(`epo:playedBy`) — tas pats `legal-entities/{jar}/#this` IRI. Atrenkamos poros, kuriose per "
     "metus ≥ 30 000 EUR per ≥ 10 sąskaitų, kurių vidurkis < 10 000 EUR, ir patikrinama, ar nėra "
     "pirkimo sutarties. Pirkimo skaidymas į mažas sąskaitas išvengia pirkimų registro — tad tai "
     "signalas tikrinti (nors taip atsiskaitoma ir pagal preliminariąsias sutartis, ir už "
     "komunalines paslaugas). Užklausa kerta `public-spending` ir `procurement` rinkinius."),
    ("pinreg-ties-public-spending.rq",
     "Politikų įmonės, apmokamos viešojo sektoriaus",
     "**Į kokį klausimą atsako:** kurių politikų deklaruoti juridiniai asmenys gauna pinigų iš "
     "viešojo sektoriaus pagal sąskaitas faktūras?\n\n"
     "**Kaip veikia:** privataus intereso ryšio įmonė (`ltlod:interestOrganization`) ir sąskaitų "
     "tiekėjas (`ltlod:spendingSupplier`) — tas pats `legal-entities/{jar}/#this` IRI. Imami tik "
     "nuosavybės ar valdymo ryšiai; sąskaitų sumos ir skaičiai susumuojami. Užklausa kerta `vtek` "
     "ir `public-spending` rinkinius."),
    ("land-new-companies.rq",
     "Naujos įmonės be darbuotojų, siekiančios įsigyti žemės",
     "**Į kokį klausimą atsako:** kurios nuo 2020 m. įregistruotos bendrovės, neturinčios "
     "apdraustųjų darbuotojų, prašė leidimo įsigyti daugiausia žemės ūkio ar miško paskirties "
     "žemės?\n\n"
     "**Kaip veikia:** NŽT prašymai (`ltlod:LandAcquisitionApplication`) susumuojami pagal "
     "pareiškėją (`ltlod:applicant` → JAR kodas); prie jų pridedama įregistravimo data iš JAR ir "
     "apdraustųjų skaičius iš Sodros (tuščia — bendrovė Sodrai apdraustųjų nedeklaruoja). "
     "Plotas — prašytas, ne leistas įsigyti. Kas stovi už tokių bendrovių, iš atvirų duomenų "
     "nematyti (JAR akcininkų neskelbia) — tam reikia žurnalistinio darbo. Užklausa kerta "
     "`land-acquisitions`, `legal-entities` ir `employment` rinkinius."),
    ("declarations-wealth-growth.rq",
     "Deklaruoto turto pokytis per dešimtmetį",
     "**Į kokį klausimą atsako:** kurių politikų deklaruotas grynasis turtas labiausiai išaugo "
     "nuo pirmos iki paskutinės deklaracijos eurais?\n\n"
     "**Kaip veikia:** kiekvienos deklaracijos grynasis turtas = visos deklaruotos sumos atėmus "
     "pasiskolintas lėšas; imami tik ataskaitiniai metai nuo 2015 (eurais, kad nesimaišytų su "
     "litais) ir tik asmenys, turintys bent penkias tokias deklaracijas. Sumos — paties "
     "deklaruotojo nurodytos vertės (dažnai įsigijimo kaina, ne rinkos vertė), o šuolis gali "
     "būti paveldėjimas, sutuoktinio turtas, perkainojimas ar neišsami pirmoji deklaracija — "
     "tai klausimas, ne atsakymas. Užklausa kerta `declarations`, `seimas`/`officials` asmenis "
     "ir `calendar`."),
    ("lobbying-then-vote.rq",
     "Lobistų kalbinti Seimo nariai ir jų balsavimas",
     "**Į kokį klausimą atsako:** kuriuos Seimo narius lobistai deklaravo kalbinę dėl konkretaus "
     "įstatymo projekto ir kaip jie vėliau dėl to projekto balsavo?\n\n"
     "**Kaip veikia:** lobisto skaidrumo deklaracija nurodo projektą (`ltlod:draftAct`) ir "
     "paveiktą asmenį (`ltlod:influencedPerson`); balsavimas susietas su svarstomu klausimu "
     "(`schema:superEvent`), o šis — su projektu (`eli-dl:involved_work`). Skaičiuojami visi "
     "balsavimai dėl projekto (straipsnių, pataisų) nuo lobistinio kontakto dienos. Lobizmas "
     "teisėtas ir deklaruotas; klausimas tik, ar kalbintų narių balsai sutampa su lobisto "
     "siekiu, kurį aprašo deklaracija. Reikia įkeltų balsavimų ir projektų (`make -C etl/seimas "
     "votes bills`). Užklausa kerta `vtek` ir `seimas` rinkinius."),
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
