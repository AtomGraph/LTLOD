# SPARQL užklausų pavyzdžiai

Užklausos vykdomos visus `datasets/current/` rinkinius užkrovus į atmintį (Jena, ~1 mln. ketvertų):

```shell
./run.sh <užklausa.rq>     # viena užklausa
./run.sh --all             # visos iš eilės
```

Kiekvienas objektas yra atskirame named graph'e (dokumente), todėl užklausos kiekvieno dokumento trafaretus rašo atskirame `GRAPH ?g { … }` bloke, o tarp dokumentų jungia per bendrus kintamuosius — tai standartinis SPARQL 1.1, veikiantis bet kurioje ketvertų (quad) saugykloje. Vieno dokumento viduje yra ir jo `#fragmentai` (pvz., asmens narystės, jų intervalai ir momentai), todėl jie rašomi tame pačiame bloke. `alignments.trig` ir `photos.trig` naudoja tuos pačius grafų vardus kaip pagrindiniai rinkiniai, todėl užkrovus susilieja su objektų grafais.

Šis failas sugeneruotas `python3 render-examples.py` — perleidus ETL, lenteles galima atnaujinti ta pačia komanda.


## Įstaigos ir paveldas savivaldybėse

**Į kokį klausimą atsako:** kiek savivaldybėje veikiančių švietimo įstaigų, licencijuotų sveikatos priežiūros įstaigų ir kultūros vertybių?

**Kaip veikia:** kiekvienos įstaigos ar vertybės adresas (`locn:Address`) nurodo savivaldybę pagal Adresų registro kodą (`locn:adminUnit`). Trys atskiros agregacijos (kad skaičiai nesidaugintų) sujungiamos su savivaldybėmis iš `admin-units`; veikiančios švietimo įstaigos — tos, kurių buvimo registre intervalas neturi pabaigos.

```sparql
# Cross-domain: facilities × admin-units. A municipality profile of the three facility
# registers — active educational institutions (ŠVIS), licensed health-care
# institutions with an activity address there (VASPVT) and immovable cultural
# heritage objects (KVR) — next to the number of settlements, so the counts can be
# read per place. Each facility's address is a #fragment of its own document and
# points at the municipality by AR code (locn:adminUnit); the municipality is another
# document, hence one GRAPH block per document, joined on ?m. The three counts are
# separate subqueries so they don't multiply each other.
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX org:      <http://www.w3.org/ns/org#>
PREFIX locn:     <http://www.w3.org/ns/locn#>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX time:     <http://www.w3.org/2006/time#>
PREFIX schema:   <https://schema.org/>
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality ?education ?healthCare ?heritage
WHERE
{
    VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
    GRAPH ?municipalityGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality .
        FILTER(LANG(?municipality) = "lt")
    }
    {
        SELECT ?m (COUNT(DISTINCT ?school) AS ?education)
        WHERE
        {
            GRAPH ?schoolGraph
            {
                ?school a schema:EducationalOrganization ;
                    locn:address/locn:adminUnit ?m ;
                    time:hasTime ?registration .
                FILTER NOT EXISTS { ?registration time:hasEnd ?end }
            }
        }
        GROUP BY ?m
    }
    OPTIONAL
    {
        SELECT ?m (COUNT(DISTINCT ?provider) AS ?healthCare)
        WHERE
        {
            GRAPH ?providerGraph
            {
                ?provider a schema:MedicalOrganization ;
                    org:hasSite/org:siteAddress/locn:adminUnit ?m .
            }
        }
        GROUP BY ?m
    }
    OPTIONAL
    {
        SELECT ?m (COUNT(DISTINCT ?object) AS ?heritage)
        WHERE
        {
            GRAPH ?objectGraph
            {
                ?object a schema:LandmarksOrHistoricalBuildings ;
                    locn:address/locn:adminUnit ?m .
            }
        }
        GROUP BY ?m
    }
}
ORDER BY DESC(?heritage)
LIMIT 20
```

Rezultatai:

| municipality | education | healthCare | heritage |
|---|---|---|---|
| Vilniaus miesto savivaldybė | 1623 | 1284 | 3249 |
| Kauno miesto savivaldybė | 619 | 887 | 1691 |
| Kretingos rajono savivaldybė | 53 | 47 | 755 |
| Klaipėdos rajono savivaldybė | 162 | 57 | 752 |
| Šiaulių rajono savivaldybė | 57 | 28 | 628 |
| Anykščių rajono savivaldybė | 51 | 38 | 607 |
| Vilniaus rajono savivaldybė | 197 | 66 | 592 |
| Molėtų rajono savivaldybė | 41 | 27 | 549 |
| Kėdainių rajono savivaldybė | 91 | 72 | 547 |
| Švenčionių rajono savivaldybė | 24 | 26 | 545 |
| Kelmės rajono savivaldybė | 45 | 28 | 536 |
| Telšių rajono savivaldybė | 69 | 60 | 509 |
| Šilutės rajono savivaldybė | 72 | 62 | 507 |
| Pakruojo rajono savivaldybė | 25 | 16 | 490 |
| Varėnos rajono savivaldybė | 38 | 28 | 483 |
| Klaipėdos miesto savivaldybė | 404 | 422 | 471 |
| Panevėžio rajono savivaldybė | 63 | 8 | 470 |
| Ukmergės rajono savivaldybė | 66 | 45 | 464 |
| Plungės rajono savivaldybė | 56 | 46 | 462 |
| Utenos rajono savivaldybė | 60 | 84 | 462 |


## Mokyklų tinklo mažėjimas

**Į kokį klausimą atsako:** kuriose savivaldybėse nuo 2010 m. uždaryta didžiausia dalis bendrojo ugdymo mokyklų?

**Kaip veikia:** mokyklos atrenkamos pagal ŠVIS tipą (`dct:type`), išregistravimas — buvimo registre intervalo pabaigos momentas (`time:hasEnd`), tas pats, kuris susietas su kalendoriaus diena. Skaičiuojama, kiek mokyklų tebeveikia ir kiek išregistruota nuo 2010 m.

```sparql
# Cross-domain: facilities × admin-units × calendar. The school-network reform in
# numbers: per municipality, how many general-education schools (primary, basic,
# secondary, gymnasium, progymnasium, special — by ŠVIS education type) are still on
# the register and how many were deregistered since 2010, and the deregistered share.
# The deregistration is the end instant of the institution's register period
# (time:hasTime/time:hasEnd), the same instant that links the calendar day.
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX locn:     <http://www.w3.org/ns/locn#>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX time:     <http://www.w3.org/2006/time#>
PREFIX schema:   <https://schema.org/>
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality (SUM(?active) AS ?open) (SUM(?closed) AS ?closedSince2010)
    (ROUND(100 * SUM(?closed) / (SUM(?active) + SUM(?closed))) AS ?closedPercent)
WHERE
{
    VALUES ?typeSlug { "pradine-mokykla" "pagrindine-mokykla" "vidurine-mokykla" "gimnazija"
                       "progimnazija" "specialioji-mokykla" }
    BIND(IRI(CONCAT("https://linkeddata.lt/taxonomies/education-types/", ?typeSlug, "/#this")) AS ?type)
    GRAPH ?schoolGraph
    {
        ?school a schema:EducationalOrganization ;
            dct:type ?type ;
            locn:address/locn:adminUnit ?m ;
            time:hasTime ?registration .
        OPTIONAL { ?registration time:hasEnd/time:inXSDDate ?end }
    }
    FILTER(!BOUND(?end) || ?end >= "2010-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
    BIND(IF(BOUND(?end), 0, 1) AS ?active)
    BIND(IF(BOUND(?end), 1, 0) AS ?closed)
    GRAPH ?municipalityGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality .
        VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
        FILTER(LANG(?municipality) = "lt")
    }
}
GROUP BY ?municipality
ORDER BY DESC(?closedPercent)
LIMIT 20
```

Rezultatai:

| municipality | open | closedSince2010 | closedPercent |
|---|---|---|---|
| Pagėgių savivaldybė | 2 | 9 | 82.0 |
| Švenčionių rajono savivaldybė | 4 | 16 | 80.0 |
| Skuodo rajono savivaldybė | 5 | 20 | 80.0 |
| Ignalinos rajono savivaldybė | 4 | 10 | 71.0 |
| Kalvarijos savivaldybė | 4 | 10 | 71.0 |
| Širvintų rajono savivaldybė | 7 | 16 | 70.0 |
| Alytaus rajono savivaldybė | 9 | 20 | 69.0 |
| Anykščių rajono savivaldybė | 8 | 17 | 68.0 |
| Molėtų rajono savivaldybė | 8 | 17 | 68.0 |
| Varėnos rajono savivaldybė | 8 | 17 | 68.0 |
| Zarasų rajono savivaldybė | 8 | 17 | 68.0 |
| Kelmės rajono savivaldybė | 15 | 30 | 67.0 |
| Pakruojo rajono savivaldybė | 9 | 18 | 67.0 |
| Joniškio rajono savivaldybė | 12 | 23 | 66.0 |
| Tauragės rajono savivaldybė | 14 | 27 | 66.0 |
| Plungės rajono savivaldybė | 14 | 26 | 65.0 |
| Vilkaviškio rajono savivaldybė | 17 | 32 | 65.0 |
| Šilalės rajono savivaldybė | 9 | 17 | 65.0 |
| Šakių rajono savivaldybė | 14 | 25 | 64.0 |
| Kupiškio rajono savivaldybė | 10 | 17 | 63.0 |


## Biudžetinės įstaigos su sveikatos priežiūros licencija

**Į kokį klausimą atsako:** kurios valstybės ir savivaldybių biudžetinės įstaigos teikia asmens sveikatos priežiūros paslaugas ir kiek veiklos vietų turi?

**Kaip veikia:** sveikatos priežiūros įstaiga su juridiniu asmeniu susieta pagal įmonės kodą (`ltlod:legalEntity`), todėl jungimas tarp `facilities` ir `legal-entities` — paprastas URI sutapimas; registruota buveinė ir teisinė forma imamos iš JAR, veiklos vietos — iš VASPVT licencijų registro.

```sparql
# Cross-domain: facilities × legal-entities × admin-units. Which state and municipal
# budget institutions (the JAR subset in legal-entities/) hold a personal health-care
# licence, where their registered office is, and in how many places they provide
# care. The health-care institution links its legal entity by JAR code
# (ltlod:legalEntity, minted from the bare company code), so the join is a plain IRI
# match across the two documents; the activity sites are #fragments of the
# health-care document.
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX rov:    <http://www.w3.org/ns/regorg#>
PREFIX locn:   <http://www.w3.org/ns/locn#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?institution ?legalForm ?registeredIn (COUNT(DISTINCT ?site) AS ?sites)
WHERE
{
    GRAPH ?providerGraph
    {
        ?provider a schema:MedicalOrganization ;
            ltlod:legalEntity ?entity ;
            org:hasSite ?site .
    }
    GRAPH ?entityGraph
    {
        ?entity a rov:RegisteredOrganization ;
            rov:legalName ?institution ;
            rov:companyType ?form ;
            org:hasRegisteredSite/org:siteAddress/locn:adminUnit ?m .
    }
    GRAPH ?formGraph { ?form skos:prefLabel ?legalForm }
    GRAPH ?municipalityGraph { ?m skos:prefLabel ?registeredIn }
    FILTER(LANG(?registeredIn) = "lt" && LANG(?legalForm) = "lt")
}
GROUP BY ?institution ?legalForm ?registeredIn
ORDER BY DESC(?sites) ?institution
LIMIT 20
```

Rezultatai:

| institution | legalForm | registeredIn | sites |
|---|---|---|---|
| Lietuvos kariuomenė | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 26 |
| Respublikinis priklausomybės ligų centras | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 13 |
| Valstybinė teismo medicinos tarnyba | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 12 |
| Lietuvos kalėjimų tarnyba | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 11 |
| Valstybinė teismo psichiatrijos tarnyba prie Sveikatos apsaugos ministerijos | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 11 |
| Lietuvos sporto centras | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 8 |
| Biudžetinė įstaiga Valakampių socialinių paslaugų namai | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 6 |
| Nacionalinė visuomenės sveikatos priežiūros laboratorija | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 5 |
| Panevėžio apskrities vyriausiasis policijos komisariatas | Biudžetinė įstaiga | Panevėžio miesto savivaldybė | 5 |
| Adakavo socialinių paslaugų namai | Biudžetinė įstaiga | Tauragės rajono savivaldybė | 4 |
| Biudžetinė įstaiga Socialinių paslaugų centras "Klaipėdos lakštutė" | Biudžetinė įstaiga | Klaipėdos miesto savivaldybė | 4 |
| Marijampolės specialieji socialinės globos namai | Biudžetinė įstaiga | Marijampolės savivaldybė | 4 |
| Vilniaus apskrities vyriausiasis policijos komisariatas | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 4 |
| Aknystos socialinės globos namai | Biudžetinė įstaiga | Anykščių rajono savivaldybė | 3 |
| Anykščių socialinės globos namai | Biudžetinė įstaiga | Anykščių rajono savivaldybė | 3 |
| Biudžetinė įstaiga Liolių socialinės globos namai | Biudžetinė įstaiga | Kelmės rajono savivaldybė | 3 |
| Jonavos rajono socialinių paslaugų centras | Biudžetinė įstaiga | Jonavos rajono savivaldybė | 3 |
| Kauno Prano Daunio ugdymo centras | Biudžetinė įstaiga | Kauno miesto savivaldybė | 3 |
| Lietuvos Respublikos vidaus reikalų ministerijos Medicinos centras | Biudžetinė įstaiga | Vilniaus miesto savivaldybė | 3 |
| Linkuvos socialinių paslaugų centras | Biudžetinė įstaiga | Pakruojo rajono savivaldybė | 3 |


## Savivaldybių apžvalga

**Į kokį klausimą atsako:** kokios Lietuvos savivaldybės turi daugiausia gyvenamųjų vietovių, kokiai apskričiai jos priklauso ir kaip atrodo jų herbai?

**Kaip veikia:** iš `admin-units` rinkinio atrenkami objektai, kurių lygmuo — miesto, rajono arba paprasta savivaldybė (ES ATU-type klasifikatoriaus konceptai `LTU_MSV`/`LTU_RSV`/`LTU_SV`). Per `dct:isPartOf` ryšį randama kiekvienos savivaldybės apskritis ir jos pavadinimas. Dvi vidinės agregacijos suskaičiuoja pavaldžius objektus: seniūnijas (tiesioginis `dct:isPartOf`) ir gyvenamąsias vietoves — vietovė gali priklausyti seniūnijai arba tiesiogiai savivaldybei, todėl tarpinis šuolis per seniūniją yra neprivalomas (`OPTIONAL` + `COALESCE`). Galiausiai iš Wikidata susiejimų (`alignments.trig`) pridedamas QID ir herbo paveikslėlis. Rikiuojama pagal vietovių skaičių — viršuje atsiduria didieji rajonai.

```sparql
# Cross-domain: admin-units hierarchy × Wikidata alignments.
# Municipalities with their county, subordinate eldership/settlement counts,
# Wikidata QID and coat of arms (alignments.trig merges into the entity
# graphs on load, since it reuses the same graph names).
#
# Every admin unit is its own named graph (document), so each hop across the
# hierarchy (municipality -> county, eldership -> municipality, settlement ->
# eldership) is a separate GRAPH block joined on the unit IRI.
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX foaf:     <http://xmlns.com/foaf/0.1/>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX owl:      <http://www.w3.org/2002/07/owl#>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality ?county ?elderships ?settlements ?wikidata ?coatOfArms
WHERE
{
    VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
    GRAPH ?mGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality ;
            dct:isPartOf ?c .
        # alignments.trig reuses the unit's graph name
        OPTIONAL { ?m owl:sameAs ?wikidata }
    }
    GRAPH ?cGraph { ?c skos:prefLabel ?county }

    # The coat of arms (Wikidata P94) is foaf:img; a scenic photo (P18) is a plain
    # foaf:depiction. Collapse to one image per municipality so the row is not
    # multiplied: the coat of arms, else any depiction.
    OPTIONAL { SELECT ?m (SAMPLE(?i) AS ?coa)
               WHERE { GRAPH ?imgGraph { ?m foaf:img ?i } }
               GROUP BY ?m }
    OPTIONAL { SELECT ?m (SAMPLE(?d) AS ?anyDepiction)
               WHERE { GRAPH ?depictionGraph { ?m foaf:depiction ?d } }
               GROUP BY ?m }
    BIND(COALESCE(?coa, ?anyDepiction) AS ?coatOfArms)

    { SELECT ?m (COUNT(DISTINCT ?e) AS ?elderships)
      WHERE { GRAPH ?eGraph { ?e cv:level atu-type:LTU_SEN ; dct:isPartOf ?m } }
      GROUP BY ?m }

    { SELECT ?m (COUNT(DISTINCT ?s) AS ?settlements)
      WHERE { GRAPH ?sGraph
              { ?s cv:level <https://linkeddata.lt/taxonomies/admin-unit-levels/gyvenamoji-vietove/#this> ;
                   dct:isPartOf ?p . }
              # a settlement belongs to an eldership or directly to a municipality
              OPTIONAL { GRAPH ?pGraph { ?p cv:level atu-type:LTU_SEN ; dct:isPartOf ?pm } }
              BIND(COALESCE(?pm, ?p) AS ?m) }
      GROUP BY ?m }
}
ORDER BY DESC(?settlements)
LIMIT 15
```

Rezultatai:

| municipality | county | elderships | settlements | wikidata | coatOfArms |
|---|---|---|---|---|---|
| Vilniaus rajono savivaldybė | Vilniaus apskritis | 24 | 1292 | http://www.wikidata.org/entity/Q118903 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Vilnius%20district%20COA.svg?width=120" width="60" alt=""/> |
| Rokiškio rajono savivaldybė | Panevėžio apskritis | 10 | 1105 | http://www.wikidata.org/entity/Q766969 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Roki%C5%A1kis%20COA.svg?width=120" width="60" alt=""/> |
| Zarasų rajono savivaldybė | Utenos apskritis | 10 | 1075 | http://www.wikidata.org/entity/Q664415 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Zarasai.svg?width=120" width="60" alt=""/> |
| Molėtų rajono savivaldybė | Utenos apskritis | 11 | 1047 | http://www.wikidata.org/entity/Q2089785 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Moletai%20%28Lithuania%29.svg?width=120" width="60" alt=""/> |
| Anykščių rajono savivaldybė | Utenos apskritis | 10 | 982 | http://www.wikidata.org/entity/Q2089772 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Anyk%C5%A1%C4%8Diai%20COA%20great.svg?width=120" width="60" alt=""/> |
| Kelmės rajono savivaldybė | Šiaulių apskritis | 11 | 950 | http://www.wikidata.org/entity/Q1387044 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Kelmes-herbas.svg?width=120" width="60" alt=""/> |
| Panevėžio rajono savivaldybė | Panevėžio apskritis | 12 | 934 | http://www.wikidata.org/entity/Q1351758 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Panev%C4%97%C5%BEys%20District%20COA.svg?width=120" width="60" alt=""/> |
| Ignalinos rajono savivaldybė | Utenos apskritis | 12 | 819 | http://www.wikidata.org/entity/Q2069330 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Ignalina%20%28Lithuania%29.svg?width=120" width="60" alt=""/> |
| Švenčionių rajono savivaldybė | Vilniaus apskritis | 14 | 792 | http://www.wikidata.org/entity/Q1813849 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/%C5%A0ven%C4%8Dionys%20COA.svg?width=120" width="60" alt=""/> |
| Raseinių rajono savivaldybė | Kauno apskritis | 12 | 735 | http://www.wikidata.org/entity/Q2069355 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Raseiniai%20COA.svg?width=120" width="60" alt=""/> |
| Biržų rajono savivaldybė | Panevėžio apskritis | 8 | 712 | http://www.wikidata.org/entity/Q763504 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Bir%C5%BEai%20COA.svg?width=120" width="60" alt=""/> |
| Ukmergės rajono savivaldybė | Vilniaus apskritis | 12 | 703 | http://www.wikidata.org/entity/Q68929 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Ukmerg%C4%97%20COA.svg?width=120" width="60" alt=""/> |
| Utenos rajono savivaldybė | Utenos apskritis | 10 | 669 | http://www.wikidata.org/entity/Q2089798 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Utena%20%28Lithuania%29.svg?width=120" width="60" alt=""/> |
| Šiaulių rajono savivaldybė | Šiaulių apskritis | 11 | 642 | http://www.wikidata.org/entity/Q1417346 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Siauliai%20district%20COA.gif?width=120" width="60" alt=""/> |
| Šakių rajono savivaldybė | Marijampolės apskritis | 16 | 625 | http://www.wikidata.org/entity/Q2021307 | <img src="https://commons.wikimedia.org/wiki/Special:FilePath/Sakiai%20COA.gif?width=120" width="60" alt=""/> |


## Teritorinė grandinė

**Į kokį klausimą atsako:** kur tiksliai yra gatvė — kokioje vietovėje, savivaldybėje ir apskrityje?

**Kaip veikia:** pradedama nuo gatvių (`dct:Location` klasės objektų `streets` rinkinyje) ir `dct:isPartOf` ryšiais lipama aukštyn per administracinę hierarchiją: gatvė → gyvenamoji vietovė → (galbūt seniūnija) → savivaldybė → apskritis. Kiekvienas šuolis kerta atskirą named graph'ą, todėl kiekvienas dokumentas aprašomas savu `GRAPH` bloku, o blokai sujungiami per bendrus kintamuosius. Pavyzdžiui atrinktos tik Vilniaus miesto gatvės; pakeitus filtrą veiktų bet kuriai savivaldybei.

```sparql
# Cross-domain: streets × admin-units (settlements, elderships, municipalities,
# counties) — the full territorial chain for a sample of Vilnius streets,
# walking dct:isPartOf across four entity graphs, one GRAPH block per document.
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?street ?settlement ?municipality ?county
WHERE
{
    GRAPH ?stGraph
    {
        ?st a dct:Location ;
            skos:prefLabel ?street ;
            dct:isPartOf ?s .
    }
    GRAPH ?sGraph
    {
        ?s skos:prefLabel ?settlement ;
            dct:isPartOf ?p .
    }
    # the settlement's parent is an eldership or, directly, the municipality
    OPTIONAL { GRAPH ?pGraph { ?p cv:level atu-type:LTU_SEN ; dct:isPartOf ?pm } }
    BIND(COALESCE(?pm, ?p) AS ?m)
    GRAPH ?mGraph
    {
        ?m skos:prefLabel ?municipality ;
            dct:isPartOf ?c .
    }
    GRAPH ?cGraph { ?c skos:prefLabel ?county }
    FILTER(CONTAINS(STR(?municipality), "Vilniaus miesto"))
}
LIMIT 15
```

Rezultatai:

| street | settlement | municipality | county |
|---|---|---|---|
| Kelmijos Sodų 85-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Rodūnios Sodų 8-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Zavadskių g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Pagubės Sodų 22-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Birelių Sodų 19-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Rožių al. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Vismaliukų Sodų 1-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Pavilnio Sodų 16-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Eišiškių Sodų 3-ioji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Raguvos g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Stumbrų g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Raitininkų g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Sakalaičių Sodų 2-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Vijoklių g. | Grigiškės | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Juodvarnių Sodų 15-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |


## Seimo narių frakcijos

**Į kokį klausimą atsako:** kas šiuo metu priklauso kuriai Seimo frakcijai, kuri partija juos iškėlė ir kaip jie atrodo?

**Kaip veikia:** narystės modeliuojamos kaip atskiri `org:Membership` objektai su galiojimo intervalais, todėl „dabartinė” narystė = narystė, kurios intervalas neturi pabaigos datos (`FILTER NOT EXISTS { ... time:hasEnd ... }`). Iš tokių narysčių atrenkamos tos, kurių organizacija yra frakcija (pagal `org-unit-types` taksonomijos konceptą). Prie kiekvieno nario pridedama: iškėlusi partija (`ltlod:nominatedBy` ryšys į `parties` rinkinį), Wikidata QID (iš `alignments.trig`) ir oficialus lrs.lt portretas (`photos.trig`). Nuotrauka apribojama iki lrs.lt portreto, kad kiekvienas narys lentelėje būtų vieną kartą — susietieji nariai papildomai turi ir Wikidata P18 nuotrauką, kuri kitaip padvigubintų eilutę.

```sparql
# Cross-domain: seimas persons × org-units × parties × taxonomies × alignments.
# Current faction composition: members whose faction membership has no end
# date, with their nominating party, Wikidata QID and official lrs.lt portrait
# (photos.trig). The depiction is filtered to the lrs.lt portrait so each member
# yields a single row — reconciled members also carry a Wikidata P18 depiction
# (alignments.trig), which would otherwise multiply the row per image.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?faction ?member ?party ?wikidata ?photo
WHERE
{
    # the membership and its interval are #fragments of the person's document;
    # alignments.trig and photos.trig reuse the person's graph name
    GRAPH ?personGraph
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?org ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
        ?person foaf:name ?member .
        OPTIONAL { ?person owl:sameAs ?wikidata }
        OPTIONAL { ?person foaf:depiction ?photo . FILTER(CONTAINS(STR(?photo), "lrs.lt")) }
    }

    GRAPH ?orgGraph
    {
        ?org dct:type <https://linkeddata.lt/taxonomies/org-unit-types/frakcija/#this> ;
            skos:prefLabel ?faction .
    }
    # the party that nominated them for the current seat (a person nominated by
    # different parties in different terms carries every one on foaf:Person)
    OPTIONAL {
        GRAPH ?tenureGraph
        {
            ?tenure org:member ?person ;
                ltlod:nominatedBy ?partyEntity ;
                org:memberDuring ?tenureInterval .
            FILTER NOT EXISTS { ?tenureInterval time:hasEnd ?tenureEnd }
        }
        GRAPH ?partyGraph { ?partyEntity skos:prefLabel ?party }
    }
}
ORDER BY ?faction ?member
LIMIT 25
```

Rezultatai:

| faction | member | party | wikidata | photo |
|---|---|---|---|---|
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Jakavičiutė-Miliauskienė | Demokratų sąjunga „Vardan Lietuvos“ |  | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/agne_jakaviciute_miliauskiene.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Širinskienė | Politinė partija „Nemuno Aušra“ | http://www.wikidata.org/entity/Q28933945 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/agne_sirinskiene.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Algirdas Butkevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q394006 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/algirdas_butkevicius.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Dainius Varnas | Politinė partija „Nemuno Aušra“ | http://www.wikidata.org/entity/Q130712526 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/dainius_varnas.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Domas Griškevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q123688288 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/domas_griskevicius.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Jekaterina Rojaka | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q60627846 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/jekaterina_rojaka.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Kęstutis Mažeika | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q28371741 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/kestutis_mazeika.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Linas Kukuraitis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27977694 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/linas_kukuraitis.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Lukas Savickas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q102735741 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/lukas_savickas.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Rima Baškienė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q541371 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/rima_baskiene.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Rūta Miliūtė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27652365 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/ruta_miliute.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Tomas Tomilinas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q28376223 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/tomas_tomilinas.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Zigmantas Balčytis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q117150 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/zigmantas_balcytis.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Andrius Bagdonas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q12648381 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/andrius_bagdonas.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Arminas Lydeka | Liberalų sąjūdis | http://www.wikidata.org/entity/Q9160077 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/arminas_lydeka.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Edita Rudelienė | Liberalų sąjūdis | http://www.wikidata.org/entity/Q12653719 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/edita_rudeliene.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Eugenijus Gentvilas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q204847 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/eugenijus_gentvilas.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Ričardas Juška | Liberalų sąjūdis | http://www.wikidata.org/entity/Q6335993 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/ricardas_juska.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Simonas Gentvilas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q27577960 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/simonas_gentvilas.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Simonas Kairys | Liberalų sąjūdis | http://www.wikidata.org/entity/Q16472414 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/simonas_kairys.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Viktoras Pranckietis | Liberalų sąjūdis | http://www.wikidata.org/entity/Q27537241 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/viktoras_pranckietis.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Viktorija Čmilytė-Nielsen | Liberalų sąjūdis | http://www.wikidata.org/entity/Q270330 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/viktorija_cmilyte_nielsen.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Virgilijus Alekna | Liberalų sąjūdis | http://www.wikidata.org/entity/Q211408 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/virgilijus_alekna.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Vitalijus Gailius | Liberalų sąjūdis | http://www.wikidata.org/entity/Q1304328 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/vitalijus_gailius.jpg" width="60" alt=""/> |
| Liberalų frakcija | Andrius Bagdonas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q12648381 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/andrius_bagdonas.jpg" width="60" alt=""/> |


## Komitetų ir komisijų pirmininkai

**Į kokį klausimą atsako:** kas šiuo metu vadovauja Seimo komitetams, komisijoms ir frakcijoms ir nuo kada?

**Kaip veikia:** vėl naudojamas „narystė be pabaigos datos” požymis, bet šįkart filtruojama pagal pareigų konceptą iš `position-types` taksonomijos: imamos pareigos, kurių lietuviška etiketė turi „pirminink” arba „seniūn” (frakcijų vadovai vadinami seniūnais), atmetant pavaduotojus. Prie vadovo pridedama jį iškėlusi partija ir oficialus portretas — užklausa kerta šešis failus: asmenis, padalinius, pareigų taksonomiją, partijas, nuotraukas ir Wikidata susiejimus. Pradžios data paimama iš narystės galiojimo intervalo (`time:hasBeginning`). Atkreipkite dėmesį, kad pareigų konceptai išlaiko šaltinio giminines formas („pirmininkas”/„pirmininkė”).

```sparql
# Cross-domain: seimas persons × org-units × position-types taxonomy × parties
# × photos. Who currently chairs Seimas committees, commissions and factions —
# role concepts matched by their Lithuanian label ("pirmininkas"/"seniūnas") —
# with their nominating party and official portrait.
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX time:  <http://www.w3.org/2006/time#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?unit ?chair ?party ?since ?photo
WHERE
{
    # memberships, intervals and instants are #fragments of the person's document
    GRAPH ?personGraph
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?org ;
            org:role ?roleConcept ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
        OPTIONAL { ?interval time:hasBeginning/time:inXSDDate ?since }
        ?person foaf:name ?chair .
        # photos.trig reuses the person's graph name
        OPTIONAL { ?person foaf:depiction ?photo . FILTER(CONTAINS(STR(?photo), "lrs.lt")) }
    }

    GRAPH ?roleGraph
    {
        ?roleConcept skos:prefLabel ?role .
        FILTER(LANG(?role) = "lt" &&
               (CONTAINS(LCASE(STR(?role)), "pirminink") || CONTAINS(LCASE(STR(?role)), "seniūn")))
        FILTER(!CONTAINS(LCASE(STR(?role)), "pavaduotoj"))   # skip deputies
    }

    GRAPH ?orgGraph { ?org skos:prefLabel ?unit }
    # the party that nominated them for the current seat (a person nominated by
    # different parties in different terms carries every one on foaf:Person)
    OPTIONAL {
        GRAPH ?tenureGraph
        {
            ?tenure org:member ?person ;
                ltlod:nominatedBy ?partyEntity ;
                org:memberDuring ?tenureInterval .
            FILTER NOT EXISTS { ?tenureInterval time:hasEnd ?tenureEnd }
        }
        GRAPH ?partyGraph { ?partyEntity skos:prefLabel ?party }
    }
}
ORDER BY ?unit
```

Rezultatai:

| unit | chair | party | since | photo |
|---|---|---|---|---|
| Antikorupcijos komisija | Arvydas Anušauskas | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-12-05 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/arvydas_anusauskas.jpg" width="60" alt=""/> |
| Aplinkos apsaugos komitetas | Linas Jonauskas | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/linas_jonauskas.jpg" width="60" alt=""/> |
| Asmenų su negalia teisių komisija | Indrė Kižienė | Lietuvos socialdemokratų partija | 2025-04-10 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/indre_kiziene.jpg" width="60" alt=""/> |
| Ateities komitetas | Vytautas Grubliauskas | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/vytautas_grubliauskas.jpg" width="60" alt=""/> |
| Audito komitetas | Artūras Zuokas | Partija „Laisvė ir teisingumas“ | 2026-07-15 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/arturas_zuokas.jpg" width="60" alt=""/> |
| Biudžeto ir finansų komitetas | Algirdas Sysas | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/algirdas_sysas.jpg" width="60" alt=""/> |
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Širinskienė | Politinė partija „Nemuno Aušra“ | 2026-07-14 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/agne_sirinskiene.jpg" width="60" alt=""/> |
| Ekonomikos ir inovacijų komitetas | Jekaterina Rojaka | Demokratų sąjunga „Vardan Lietuvos“ | 2026-07-07 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/jekaterina_rojaka.jpg" width="60" alt=""/> |
| Ekonomikos komitetas | Jekaterina Rojaka | Demokratų sąjunga „Vardan Lietuvos“ | 2026-07-07 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/jekaterina_rojaka.jpg" width="60" alt=""/> |
| Ekonominių nusikaltimų tyrimo komisija | Arvydas Anušauskas | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-12-05 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/arvydas_anusauskas.jpg" width="60" alt=""/> |
| Energetikos ir darnios plėtros komitetas | Algirdas Butkevičius | Demokratų sąjunga „Vardan Lietuvos“ | 2026-07-07 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/algirdas_butkevicius.jpg" width="60" alt=""/> |
| Etikos ir procedūrų komisija | Viktoras Fiodorovas | Išsikėlė pats | 2025-11-14 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/viktoras_fiodorovas.jpg" width="60" alt=""/> |
| Europos reikalų komitetas | Rasa Budbergytė | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/rasa_budbergyte.jpg" width="60" alt=""/> |
| Gamtos apsaugos komitetas | Linas Jonauskas | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/linas_jonauskas.jpg" width="60" alt=""/> |
| Jaunimo ir sporto reikalų komisija | Algimantas Radvila | Lietuvos socialdemokratų partija | 2026-07-15 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/algimantas_radvila.jpg" width="60" alt=""/> |
| Jungtinė ir Liberalų frakcija | Viktorija Čmilytė-Nielsen | Liberalų sąjūdis | 2024-11-14 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/viktorija_cmilyte_nielsen.jpg" width="60" alt=""/> |
| Jūrinių reikalų komisija | Alvydas Mockus | Lietuvos socialdemokratų partija | 2025-11-20 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/alvydas_mockus.jpg" width="60" alt=""/> |
| Kaimo reikalų komitetas | Bronis Ropė | Lietuvos valstiečių ir žaliųjų sąjunga | 2025-10-15 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/bronis_rope.jpg" width="60" alt=""/> |
| Kriminalinės žvalgybos parlamentinės kontrolės komisija | Dainius Gaižauskas | Lietuvos valstiečių ir žaliųjų sąjunga | 2025-11-11 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/dainius_gaizauskas.jpg" width="60" alt=""/> |
| Kultūros komitetas | Vaida Aleknavičienė | Lietuvos socialdemokratų partija | 2026-09-17 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/vaida_aleknaviciene.jpg" width="60" alt=""/> |
| Laikinoji Ateities grupė | Tadas Prajara | Lietuvos socialdemokratų partija | 2026-08-25 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/tadas_prajara.jpg" width="60" alt=""/> |
| Laikinoji Bendradarbiavimo su Lietuvos jaunimo organizacijų taryba grupė | Tomas Martinaitis | Lietuvos socialdemokratų partija | 2025-03-20 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/tomas_martinaitis.jpg" width="60" alt=""/> |
| Laikinoji Dzūkijos bičiulių grupė | Jurgita Šukevičienė | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/jurgita_sukeviciene.jpg" width="60" alt=""/> |
| Laikinoji Kauno krašto grupė | Robertas Kaunas | Lietuvos socialdemokratų partija | 2024-11-21 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/robertas_kaunas.jpg" width="60" alt=""/> |
| Laikinoji Klaipėdos krašto bičiulių grupė | Ligita Girskienė | Lietuvos valstiečių ir žaliųjų sąjunga | 2025-05-13 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/ligita_girskiene.jpg" width="60" alt=""/> |
| Laikinoji Kultūros asamblėjos draugų grupė | Vytautas Juozapaitis | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2025-12-15 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/vytautas_juozapaitis.jpg" width="60" alt=""/> |
| Laikinoji Lietuvos kariuomenės ir Lietuvos šaulių sąjungos draugų grupė | Audrius Radvilavičius | Lietuvos socialdemokratų partija | 2025-03-28 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/audrius_radvilavicius.jpg" width="60" alt=""/> |
| Laikinoji Maldos grupė | Valdas Rakutis | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2025-10-16 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/valdas_rakutis.jpg" width="60" alt=""/> |
| Laikinoji Neringos bičiulių grupė | Andrius Bagdonas | Liberalų sąjūdis | 2024-12-03 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/andrius_bagdonas.jpg" width="60" alt=""/> |
| Laikinoji Panevėžio krašto bičiulių grupė | Modesta Petrauskaitė | Lietuvos socialdemokratų partija | 2024-12-03 | <img src="https://www.lrs.lt/SIPIS/sn_foto/2024/modesta_petrauskaite.jpg" width="60" alt=""/> |
| … | &nbsp; |&nbsp; |&nbsp; |&nbsp; |


## Įstaigos pagal teisinę formą ir statusą

**Į kokį klausimą atsako:** kiek valstybės ir savivaldybių biudžetinių įstaigų yra registruota, kokios jų teisinės formos ir kiek jų jau išregistruota ar reorganizuojama?

**Kaip veikia:** iš `legal-entities` rinkinio imami visi `rov:RegisteredOrganization` objektai ir per `rov:companyType` bei `rov:orgStatus` ryšius pasiekiamos jų formų ir statusų etiketės — tai SKOS konceptai, sugeneruoti tiesiai iš JAR klasifikatorių (`taxonomies/legal-forms`, `taxonomies/legal-statuses`). Rezultatas grupuojamas ir skaičiuojamas. Lentelėje matyti įdomi detalė: senosios formos „Valstybės biudžetinė įstaiga” (580) ir „Savivaldybės biudžetinė įst.” (680) yra vien istorinės — visos tokios įstaigos išregistruotos, o veikiančios dabar registruojamos bendra forma „Biudžetinė įstaiga” (950).

```sparql
# Cross-domain: legal-entities × taxonomies (JAR classifiers).
# Registered vs dissolved budget institutions per legal form and status.
PREFIX rov:  <http://www.w3.org/ns/regorg#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?legalForm ?status (COUNT(DISTINCT ?e) AS ?entities)
WHERE
{
    GRAPH ?entityGraph
    {
        ?e a rov:RegisteredOrganization ;
            rov:companyType ?form ;
            rov:orgStatus ?statusConcept .
    }
    # budget-institution forms only (580 state, 680 municipal, 950 generic) — the
    # bulk entities.trig holds the rest of the register under the same class
    FILTER(REPLACE(STR(?form), "^.*/legal-forms/([^/]+)/#this$", "$1") IN ("580", "680", "950"))
    # the classifier concepts live in their taxonomy documents
    GRAPH ?formGraph { ?form skos:prefLabel ?legalForm }
    GRAPH ?statusGraph { ?statusConcept skos:prefLabel ?status }
    FILTER(LANG(?legalForm) = "lt" && LANG(?status) = "en")
}
GROUP BY ?legalForm ?status
ORDER BY DESC(?entities)
LIMIT 20
```

Rezultatai:

| legalForm | status | entities |
|---|---|---|
| Biudžetinė įstaiga | No legal proceedings | 2495 |
| Biudžetinė įstaiga | Removed | 1521 |
| Savivaldybės biudžetinė įst. | Removed | 1431 |
| Valstybės biudžetinė įstaiga | Removed | 520 |
| Biudžetinė įstaiga | Under Reorganization | 34 |
| Biudžetinė įstaiga | Participating in Reorganization | 24 |
| Biudžetinė įstaiga | Liquidation being initiated | 1 |
| Biudžetinė įstaiga | Under Liquidation | 1 |
| Biudžetinė įstaiga | Under Reformation | 1 |


## Wikidata susiejimų aprėptis

**Į kokį klausimą atsako:** kokia dalis mūsų duomenų jau susieta su Wikidata ir kiek objektų turi atvaizdus?

**Kaip veikia:** pereinama per visus dokumentus (kiekvienas named graph'as per `foaf:primaryTopic` nurodo savo pagrindinį objektą), objektai sugrupuojami pagal RDF klasę ir suskaičiuojama, kiek jų turi `owl:sameAs` nuorodą į Wikidata ir kiek — `foaf:depiction` atvaizdą (herbą ar nuotrauką). Tai savotiška kokybės suvestinė: matyti, kad su Wikidata susieta 733 iš 831 visų kadencijų Seimo narių, o nuotraukas turi 290 (oficialūs lrs.lt portretai — tik dabartinės kadencijos nariams), administracinių vienetų susieta 642, o gatvės ir įstaigos su Wikidata dar nesiejamos.

```sparql
# Cross-domain: everything × alignments — Wikidata reconciliation and image
# coverage per RDF class across all datasets. Documents point at their main
# entity via foaf:primaryTopic; the entity, its type and its alignments
# (alignments.trig reuses the entity's graph name) are in the same document.
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT ?type (COUNT(DISTINCT ?e) AS ?entities)
       (COUNT(DISTINCT ?aligned) AS ?withWikidata)
       (COUNT(DISTINCT ?depicted) AS ?withImage)
WHERE
{
    GRAPH ?doc
    {
        ?doc foaf:primaryTopic ?e .
        ?e a ?type .
        OPTIONAL { ?e owl:sameAs ?qid . BIND(?e AS ?aligned) }
        # coat of arms is foaf:img, photos foaf:depiction (see CLAUDE.md); a variable
        # predicate + IN, not an alternative path, inside a GRAPH block
        OPTIONAL { ?e ?imgProperty ?img .
                   FILTER(?imgProperty IN (foaf:img, foaf:depiction))
                   BIND(?e AS ?depicted) }
    }
}
GROUP BY ?type
ORDER BY DESC(?entities)
```

Rezultatai:

| type | entities | withWikidata | withImage |
|---|---|---|---|
| http://www.w3.org/ns/org#FormalOrganization | 547448 | 0 | 0 |
| http://www.w3.org/ns/regorg#RegisteredOrganization | 547382 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#Vote | 75761 | 0 | 0 |
| http://purl.org/dc/terms/Location | 61149 | 0 | 0 |
| http://data.europa.eu/a4g/ontology#Contract | 55663 | 0 | 0 |
| http://data.europa.eu/m8g/AdminUnit | 26883 | 642 | 456 |
| http://purl.org/dc/terms/PeriodOfTime | 19290 | 0 | 0 |
| http://www.w3.org/2006/time#DateTimeInterval | 19290 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#Activity | 4902 | 0 | 0 |
| https://schema.org/Event | 4776 | 0 | 0 |
| http://linkeddata.lt/ns#AssetDeclaration | 1953 | 0 | 0 |
| http://linkeddata.lt/ns#CampaignParticipant | 1883 | 0 | 0 |
| http://xmlns.com/foaf/0.1/Person | 831 | 738 | 293 |
| http://linkeddata.lt/ns#ElectoralDistrict | 771 | 0 | 0 |
| http://www.w3.org/ns/org#OrganizationalUnit | 394 | 0 | 0 |
| http://www.w3.org/2004/02/skos/core#Concept | 378 | 0 | 0 |
| http://linkeddata.lt/ns#ConstituencyContest | 142 | 0 | 0 |
| https://schema.org/EventSeries | 131 | 0 | 0 |
| https://schema.org/PoliticalParty | 66 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#ActivityType | 13 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#ParliamentaryTerm | 10 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#DecisionMethod | 5 | 0 | 0 |
| http://linkeddata.lt/ns#Election | 5 | 0 | 0 |


## CONSTRUCT: frakcijų seniūnų profiliai

**Ką daro:** vietoj rezultatų lentelės ši užklausa **sukuria naują RDF grafą** — kompaktiškus frakcijų vadovų profilius schema.org žodynu, tinkamus, pvz., perduoti į kitą sistemą ar įterpti į tinklalapį.

**Kaip veikia:** `WHERE` dalis suranda galiojančias narystes, kurių pareigos — „Frakcijos seniūnas/seniūnė” (be pavaduotojų), ir surenka vardą, frakciją, oficialią lrs.lt nuotrauką bei Wikidata QID iš keturių skirtingų rinkinių. `CONSTRUCT` šablonas iš šių duomenų sudeda naujus trejetus: asmuo tampa `schema:Person` su `schema:name`, `schema:memberOf`, `schema:image` ir `schema:sameAs`, frakcija — `schema:Organization`. Žemiau rezultatas parodytas kaip subjekto–predikato–objekto (S/P/O) trejetų lentelė.

```sparql
# Cross-domain CONSTRUCT: build compact schema.org profiles of current faction
# leaders by joining persons × org-units × parties × position-types × images.
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

CONSTRUCT
{
    ?person a schema:Person ;
        schema:name ?name ;
        schema:memberOf ?faction ;
        schema:image ?photo ;
        schema:sameAs ?qid .
    ?faction a schema:Organization ;
        schema:name ?factionName .
}
WHERE
{
    # the membership, its interval and the person's own triples (photos.trig and
    # alignments.trig reuse the person's graph name) all live in the person's document
    GRAPH ?personGraph
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?faction ;
            org:role ?role ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
        ?person foaf:name ?name .
        OPTIONAL { ?person foaf:depiction ?photo . FILTER(CONTAINS(STR(?photo), "lrs.lt")) }
        OPTIONAL { ?person owl:sameAs ?qid }
    }

    GRAPH ?roleGraph
    {
        ?role skos:prefLabel ?roleLabel .
        FILTER(LANG(?roleLabel) = "lt" && STRSTARTS(STR(?roleLabel), "Frakcijos seniūn"))
        FILTER(!CONTAINS(STR(?roleLabel), "pavaduotoj"))
    }

    GRAPH ?factionGraph { ?faction skos:prefLabel ?factionName }
}
```

Rezultatai:

| subjektas (S) | predikatas (P) | objektas (O) |
|---|---|---|
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1022/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1022/#this> | <https://schema.org/name> | "Tėvynės sąjungos-Lietuvos krikščionių demokratų frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1070/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1070/#this> | <https://schema.org/name> | "Lietuvos valstiečių ir žaliųjų sąjungos frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1070/#this> | <https://schema.org/name> | "Lietuvos valstiečių, žaliųjų ir Krikščioniškų šeimų sąjungos frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1322/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1322/#this> | <https://schema.org/name> | "Demokratų frakcija „Vardan Lietuvos“"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1430/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1430/#this> | <https://schema.org/name> | "„Nemuno aušros“ frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/47/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/47/#this> | <https://schema.org/name> | "Mišri Seimo narių grupė"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/793/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/793/#this> | <https://schema.org/name> | "Lietuvos socialdemokratų darbo frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/793/#this> | <https://schema.org/name> | "Lietuvos socialdemokratų partijos frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/793/#this> | <https://schema.org/name> | "Socialdemokratinės koalicijos (LDDP-LSDP-LRS) frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/870/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/870/#this> | <https://schema.org/name> | "Jungtinė ir Liberalų frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/870/#this> | <https://schema.org/name> | "Liberalų frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/870/#this> | <https://schema.org/name> | "Liberalų ir centro frakcija"@lt |
| <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/870/#this> | <https://schema.org/name> | "Liberalų sąjūdžio frakcija"@lt |
| <https://linkeddata.lt/persons/15266/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/orinta_leipute.jpg> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/memberOf> | <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/793/#this> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/name> | "Orinta Leiputė" |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/sameAs> | <http://www.wikidata.org/entity/Q1750302> |
| <https://linkeddata.lt/persons/64701/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/laurynas_kasciunas.jpg> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/memberOf> | <https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/org-units/1022/#this> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/name> | "Laurynas Kasčiūnas" |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/sameAs> | <http://www.wikidata.org/entity/Q28735068> |
| … | &nbsp; |&nbsp; |


## Įstaigos pagal savivaldybę

**Į kokį klausimą atsako:** kiek biudžetinių įstaigų registruota kiekvienoje savivaldybėje?

**Kaip veikia:** juridinio asmens registruota buveinė susiejama su administraciniu vienetu SEMIC grandine `org:hasRegisteredSite → org:Site → org:siteAddress → locn:Address → locn:adminUnit`. Buveinės savivaldybė gaunama determinuotai iš JAR `Buveine` (ja_kodas → aob_kodas) ir AR `Pastatas` (aob_kodas → savivaldybės kodas) sujungimo. Atrenkamos tik savivaldybės (ATU-type `LTU_MSV`/`LTU_RSV`/`LTU_SV`) ir suskaičiuojamos jose registruotos įstaigos. Užklausa kerta `legal-entities` ir `admin-units` rinkinius: įstaigos (su jos buveine ir adresu) ir savivaldybės trafaretai yra atskiruose `GRAPH` blokuose, sujungtuose per savivaldybės URI.

```sparql
# Cross-domain: legal-entities × admin-units (registered office).
# Budget institutions registered in each municipality, following the SEMIC
# chain org:hasRegisteredSite -> org:Site -> org:siteAddress -> locn:Address
# -> locn:adminUnit into the admin-units hierarchy. The site and address are
# #fragments of the institution's own document; the municipality is another
# document, hence a second GRAPH block joined on ?m.
PREFIX rov:      <http://www.w3.org/ns/regorg#>
PREFIX org:      <http://www.w3.org/ns/org#>
PREFIX locn:     <http://www.w3.org/ns/locn#>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality (COUNT(DISTINCT ?e) AS ?institutions)
WHERE
{
    VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
    GRAPH ?entityGraph
    {
        ?e a rov:RegisteredOrganization ;
            rov:companyType ?form ;
            org:hasRegisteredSite/org:siteAddress/locn:adminUnit ?m .
    }
    # budget-institution forms only (580 state, 680 municipal, 950 generic) — the
    # bulk entities.trig holds the rest of the register under the same class
    FILTER(REPLACE(STR(?form), "^.*/legal-forms/([^/]+)/#this$", "$1") IN ("580", "680", "950"))
    GRAPH ?municipalityGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality .
    }
    FILTER(LANG(?municipality) = "lt")
}
GROUP BY ?municipality
ORDER BY DESC(?institutions)
LIMIT 20
```

Rezultatai:

| municipality | institutions |
|---|---|
| Vilniaus miesto savivaldybė | 501 |
| Kauno miesto savivaldybė | 200 |
| Klaipėdos miesto savivaldybė | 126 |
| Šiaulių miesto savivaldybė | 95 |
| Panevėžio miesto savivaldybė | 88 |
| Vilniaus rajono savivaldybė | 76 |
| Kauno rajono savivaldybė | 67 |
| Mažeikių rajono savivaldybė | 56 |
| Kėdainių rajono savivaldybė | 45 |
| Šalčininkų rajono savivaldybė | 44 |
| Klaipėdos rajono savivaldybė | 42 |
| Telšių rajono savivaldybė | 42 |
| Šilutės rajono savivaldybė | 42 |
| Alytaus miesto savivaldybė | 41 |
| Trakų rajono savivaldybė | 41 |
| Kaišiadorių rajono savivaldybė | 37 |
| Radviliškio rajono savivaldybė | 35 |
| Jonavos rajono savivaldybė | 33 |
| Plungės rajono savivaldybė | 33 |
| Ukmergės rajono savivaldybė | 33 |


## Juridiniai asmenys pagal savivaldybę ir teisinę formą

**Į kokį klausimą atsako:** kiek juridinių asmenų registruota kiekvienoje savivaldybėje, kokių teisinių formų jų daugiausia ir kur labiausiai paplitusios mažosios bendrijos (teisinė forma, atsiradusi 2012 m.)?

**Kaip veikia:** naudojamas visas Juridinių asmenų registras (`make -C etl/legal-entities entities`). Registruota buveinė per SEMIC grandinę `org:hasRegisteredSite → org:Site → org:siteAddress → locn:Address → locn:adminUnit` nurodo ir savivaldybę, ir gyvenamąją vietovę; ATU-type lygis palieka savivaldybę. Teisinė forma atpažįstama iš JAR kodo taksonomijos URI gale (310 — UAB, 960 — mažoji bendrija, 810 — individuali įmonė, 630 — asociacija, 570 — viešoji įstaiga). Skaičiuojami tik juridiniai asmenys su registruota buveine — išregistruoti jos nebeturi.

```sparql
# Cross-domain: legal-entities (full JAR, incl. the bulk entities.trig) × admin-units
# × taxonomies. Registered legal entities per municipality, split by the most common
# legal forms, with the share of small partnerships (mažosios bendrijos, a form that
# exists since 2012) — where the newest, smallest businesses register.
# Only entities with a registered office count: Buveine lists registered entities
# only, so struck-off ones have no municipality. The office's address points at both
# its municipality and settlement (locn:adminUnit); the cv:level filter keeps the
# municipality. Forms are matched by their JAR code (the taxonomy IRI's last segment).
PREFIX rov:      <http://www.w3.org/ns/regorg#>
PREFIX org:      <http://www.w3.org/ns/org#>
PREFIX locn:     <http://www.w3.org/ns/locn#>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality (COUNT(?e) AS ?entities)
    (SUM(IF(?code = "310", 1, 0)) AS ?uab)
    (SUM(IF(?code = "960", 1, 0)) AS ?mb)
    (SUM(IF(?code = "810", 1, 0)) AS ?ii)
    (SUM(IF(?code = "630", 1, 0)) AS ?asociacijos)
    (SUM(IF(?code = "570", 1, 0)) AS ?vsi)
    (ROUND(1000 * SUM(IF(?code = "960", 1, 0)) / COUNT(?e)) / 10 AS ?mbPercent)
WHERE
{
    VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
    GRAPH ?entityGraph
    {
        ?e a rov:RegisteredOrganization ;
            rov:companyType ?form ;
            org:hasRegisteredSite/org:siteAddress/locn:adminUnit ?m .
    }
    GRAPH ?municipalityGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality .
    }
    FILTER(LANG(?municipality) = "lt")
    BIND(REPLACE(STR(?form), "^.*/legal-forms/([^/]+)/#this$", "$1") AS ?code)
}
GROUP BY ?municipality
ORDER BY DESC(?entities)
LIMIT 20
```

Rezultatai:

| municipality | entities | uab | mb | ii | asociacijos | vsi | mbPercent |
|---|---|---|---|---|---|---|---|
| Vilniaus miesto savivaldybė | 80869 | 41806 | 22461 | 4270 | 2704 | 4317 | 27.8 |
| Kauno miesto savivaldybė | 29188 | 13359 | 9002 | 2159 | 1187 | 1284 | 30.8 |
| Klaipėdos miesto savivaldybė | 12044 | 5766 | 3109 | 1050 | 520 | 562 | 25.8 |
| Kauno rajono savivaldybė | 7219 | 2848 | 2865 | 419 | 297 | 306 | 39.7 |
| Vilniaus rajono savivaldybė | 6810 | 3178 | 2333 | 277 | 313 | 318 | 34.3 |
| Šiaulių miesto savivaldybė | 6549 | 2753 | 1539 | 667 | 418 | 225 | 23.5 |
| Panevėžio miesto savivaldybė | 5635 | 2199 | 938 | 896 | 319 | 197 | 16.6 |
| Klaipėdos rajono savivaldybė | 4856 | 2022 | 1745 | 278 | 232 | 206 | 35.9 |
| Alytaus miesto savivaldybė | 3206 | 1209 | 669 | 319 | 209 | 153 | 20.9 |
| Marijampolės savivaldybė | 2972 | 1173 | 749 | 317 | 241 | 130 | 25.2 |
| Mažeikių rajono savivaldybė | 2511 | 1199 | 546 | 262 | 173 | 71 | 21.7 |
| Kėdainių rajono savivaldybė | 2112 | 638 | 556 | 241 | 212 | 65 | 26.3 |
| Telšių rajono savivaldybė | 2075 | 679 | 616 | 262 | 203 | 87 | 29.7 |
| Šiaulių rajono savivaldybė | 2075 | 810 | 574 | 243 | 229 | 65 | 27.7 |
| Palangos miesto savivaldybė | 2032 | 830 | 570 | 247 | 77 | 84 | 28.1 |
| Kretingos rajono savivaldybė | 2023 | 693 | 654 | 270 | 135 | 68 | 32.3 |
| Šilutės rajono savivaldybė | 1874 | 754 | 479 | 215 | 158 | 57 | 25.6 |
| Tauragės rajono savivaldybė | 1872 | 825 | 411 | 263 | 192 | 61 | 22.0 |
| Panevėžio rajono savivaldybė | 1857 | 741 | 491 | 244 | 131 | 82 | 26.4 |
| Trakų rajono savivaldybė | 1778 | 678 | 524 | 143 | 154 | 108 | 29.5 |


## Juridinių asmenų registracijos švenčių dienomis

**Į kokį klausimą atsako:** ar registras dirba švenčių dienomis — kiek juridinių asmenų įregistruota dieną, kuri tuo metu buvo valstybinė šventė?

**Kaip veikia:** juridinio asmens įregistravimo momentas (`time:hasTime → time:Interval → time:hasBeginning → time:Instant`) susietas su kalendoriaus diena (`dct:temporal`), o švenčių dienos kalendoriuje pažymėtos `dct:type` ryšiu į švenčių klasifikatorių — tik tais metais, kai įstatymas tą dieną laikė švente. Todėl tą pačią kalendorinę datą užklausa skaičiuoja tik tais metais, kai ji buvo šventė. Užklausa kerta `legal-entities`, `calendar` ir `taxonomies` rinkinius.

```sparql
# Cross-domain: legal-entities (full JAR) × calendar × taxonomies (public holidays).
# How many legal entities were registered on a day that was a public holiday? Each
# entity's registration instant links to its calendar day (dct:temporal); a day that
# was a public holiday carries dct:type -> its holiday concept, valid only from the
# date the law made it one — so the same calendar date counts only in the years it
# was a holiday. The register mostly rests on holidays; the exceptions are worth a look.
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX time: <http://www.w3.org/2006/time#>

SELECT ?holiday (COUNT(DISTINCT ?e) AS ?registrations)
    (MIN(?date) AS ?earliest) (MAX(?date) AS ?latest)
WHERE
{
    GRAPH ?entityGraph
    {
        ?e time:hasTime ?interval .
        ?interval time:hasBeginning ?start .
        ?start time:inXSDDate ?date ;
            dct:temporal ?day .
    }
    GRAPH ?dayGraph { ?day dct:type ?h }
    GRAPH ?holidayGraph { ?h skos:prefLabel ?holiday }
    FILTER(LANG(?holiday) = "lt")
}
GROUP BY ?holiday
ORDER BY DESC(?registrations)
```

Rezultatai:

| holiday | registrations | earliest | latest |
|---|---|---|---|
| Naujųjų metų diena | 59 | 1990-01-01 | 2025-01-01 |
| Antroji Kalėdų diena | 44 | 1990-12-26 | 1994-12-26 |
| Lietuvos valstybės atkūrimo diena | 21 | 1991-02-16 | 2022-02-16 |
| Kalėdos | 13 | 1990-12-25 | 1996-12-25 |
| Motinos diena | 10 | 1991-05-05 | 1999-05-02 |
| Visų Šventųjų diena | 9 | 1990-11-01 | 2001-11-01 |
| Antroji Velykų diena | 9 | 1991-04-01 | 1996-04-08 |
| Valstybės (Lietuvos karaliaus Mindaugo karūnavimo) ir Tautiškos giesmės diena | 5 | 1991-07-06 | 1998-07-06 |
| Velykos | 5 | 1992-04-19 | 2002-03-31 |
| Tarptautinė darbo diena | 1 | 1996-05-01 | 1996-05-01 |
| Lietuvos nepriklausomybės atkūrimo diena | 1 | 2004-03-11 | 2004-03-11 |
| Tėvo diena | 1 | 2020-06-07 | 2020-06-07 |


## Gatvės, kuriose registruota daugiausia juridinių asmenų

**Į kokį klausimą atsako:** kuriose gatvėse registruota daugiausia juridinių asmenų — verslo centrų, buhalterinių ir „virtualių biurų” adresai?

**Kaip veikia:** registruotos buveinės adresas per `dct:spatial` nurodo gatvę (`streets/{gat_kodas}/`), kuri per `dct:isPartOf` priklauso gyvenamajai vietovei. Gatvės kodas gaunamas iš Adresų registro: JAR `Buveine` → adreso objektas (`aob_kodas`) → pastatas (`Pastatas`) arba patalpa ir jos pastatas (`Patalpa`). Paužklausa pirmiausia suranda 20 gatvių su daugiausia buveinių, tada prijungia jų ir vietovių pavadinimus. Reikia visų trijų didelių sluoksnių — juridinių asmenų, gatvių ir gyvenamųjų vietovių.

```sparql
# Cross-domain: legal-entities (full JAR) × streets × settlements (all bulk layers).
# The streets where most legal entities have their registered office — the country's
# business-registration hot spots (office centres, accountancy and virtual-office
# addresses). The office address links to its street (dct:spatial); the street is a
# separate document (streets/{gat_kodas}/) and its settlement another one.
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX org:  <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?street ?settlement (COUNT(?e) AS ?entities)
WHERE
{
    {
        SELECT ?s (COUNT(?e0) AS ?n)
        WHERE
        {
            GRAPH ?entityGraph { ?e0 org:hasRegisteredSite/org:siteAddress/dct:spatial ?s }
        }
        GROUP BY ?s
        ORDER BY DESC(?n)
        LIMIT 20
    }
    GRAPH ?entityGraph { ?e org:hasRegisteredSite/org:siteAddress/dct:spatial ?s }
    GRAPH ?streetGraph
    {
        ?s skos:prefLabel ?street ;
            dct:isPartOf ?place .
    }
    GRAPH ?settlementGraph { ?place skos:prefLabel ?settlement }
    FILTER(LANG(?street) = "lt" && LANG(?settlement) = "lt")
}
GROUP BY ?street ?settlement
ORDER BY DESC(?entities)
```

Rezultatai:

| street | settlement | entities |
|---|---|---|
| V. Nagevičiaus g. | Vilnius | 3853 |
| Perkūnkiemio g. | Vilnius | 3193 |
| Laisvės pr. | Vilnius | 2413 |
| Partizanų g. | Kaunas | 2215 |
| Girulių g. | Vilnius | 2147 |
| Architektų g. | Vilnius | 1805 |
| Kalvarijų g. | Vilnius | 1669 |
| Žirmūnų g. | Vilnius | 1214 |
| Chemijos g. | Kaunas | 1209 |
| Europos pr. | Kaunas | 1199 |
| J. Savickio g. | Vilnius | 1156 |
| Konstitucijos pr. | Vilnius | 1145 |
| Draugystės g. | Kaunas | 1099 |
| Savanorių pr. | Vilnius | 1097 |
| Švitrigailos g. | Vilnius | 1045 |
| Gedimino pr. | Vilnius | 1011 |
| Eduardo Andrė g. | Vilnius | 953 |
| Lvivo g. | Vilnius | 927 |
| Taikos pr. | Klaipėda | 889 |
| Savanorių pr. | Kaunas | 888 |


## Seimo nariai pagal apygardą

**Į kokį klausimą atsako:** kurie Seimo nariai išrinkti kurioje vienmandatėje rinkimų apygardoje?

**Kaip veikia:** vienmandatės vietos narystė (`org:Membership`) turi `ltlod:electoralDistrict` ryšį į `constituencies` rinkinį; apygardos pavadinimas paimamas iš jos `skos:prefLabel`. Apygardų ribos ir numeracija keičiasi kiekvienuose rinkimuose, todėl apygarda priklauso kadencijai (`constituencies/{kadencija}-{nr}/`), o lentelėje pirmiausia rodoma dabartinė kadencija. Apygardos išanalizuojamos iš narių srauto lauko `išrinkimo_būdas` — rinkimų apygarda nėra administracinis vienetas, todėl turi atskirą `constituencies/` konteinerį. Pagal daugiamandatį sąrašą („Pagal sąrašą”) išrinkti nariai apygardos neturi ir lentelėje nerodomi.

```sparql
# Cross-domain: persons × constituencies (single-member seats).
# Seimas members elected in each electoral district (apygarda). The single-member
# seat (org:Membership tenure) carries ltlod:electoralDistrict -> constituencies/.
# Party-list members ("Pagal sąrašą") have no district and do not appear.
# Districts are redrawn every election, so each is term-scoped; the current
# term's districts come first.
PREFIX epvoc: <https://data.europarl.europa.eu/def/epvoc#>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?term ?district ?member
WHERE
{
    GRAPH ?personGraph
    {
        ?membership org:member ?person ;
            ltlod:electoralDistrict ?d ;
            epvoc:memberDuringParliamentaryTerm ?t .
        ?person foaf:name ?member .
    }
    GRAPH ?termGraph { ?t skos:prefLabel ?term }
    GRAPH ?districtGraph { ?d skos:prefLabel ?district }
}
ORDER BY DESC(?term) ?district
LIMIT 20
```

Rezultatai:

| term | district | member |
|---|---|---|
| 2024–2028 metų kadencija | Aleksoto–Vilijampolės | Robertas Kaunas |
| 2024–2028 metų kadencija | Alytaus | Jurgita Šukevičienė |
| 2024–2028 metų kadencija | Antakalnio | Ingrida Šimonytė |
| 2024–2028 metų kadencija | Aukštaitijos | Modesta Petrauskaitė |
| 2024–2028 metų kadencija | Aušros | Roma Janušonienė |
| 2024–2028 metų kadencija | Baltijos | Vytautas Grubliauskas |
| 2024–2028 metų kadencija | Centro–Žaliakalnio | Simonas Kairys |
| 2024–2028 metų kadencija | Dainavos | Jūratė Zailskienė |
| 2024–2028 metų kadencija | Danės | Audrius Petrošius |
| 2024–2028 metų kadencija | Deltuvos pietinė | Indrė Kižienė |
| 2024–2028 metų kadencija | Deltuvos šiaurinė | Arūnas Dudėnas |
| 2024–2028 metų kadencija | Dzūkijos | Martynas Katelynas |
| 2024–2028 metų kadencija | Fabijoniškių | Remigijus Motuzas |
| 2024–2028 metų kadencija | Gargždų | Alvydas Mockus |
| 2024–2028 metų kadencija | Garliavos | Šarūnas Šukevičius |
| 2024–2028 metų kadencija | Jonavos | Eugenijus Sabutis |
| 2024–2028 metų kadencija | Jotvingių | Linas Urmanavičius |
| 2024–2028 metų kadencija | Justiniškių–Viršuliškių | Linas Kukuraitis |
| 2024–2028 metų kadencija | Kaišiadorių–Elektrėnų | Algimantas Radvila |
| 2024–2028 metų kadencija | Kalniečių | Arvydas Anušauskas |


## Seimo posėdžiai pagal kadenciją

**Į kokį klausimą atsako:** kiek sesijų ir plenarinių posėdžių surengė kiekvienos kadencijos Seimas nuo 1990 m., kada vyko pirmasis ir paskutinis posėdis ir kiek posėdžių turi stenogramą?

**Kaip veikia:** kadencijos, sesijos ir posėdžiai modeliuojami ES ELI-DL ontologija: kadencija — `eli-dl:ParliamentaryTerm`, sesijos ir posėdžiai — `eli-dl:Activity`. Posėdis per `eli-dl:forms_part_of` priklauso sesijai, o abu per `eli-dl:parliamentary_term` nurodo kadenciją. Posėdžio diena — `eli-dl:activity_date`; pirmoji ir paskutinė diena skaičiuojamos atskiroje paužklausoje tik iš datuotų posėdžių (keli suplanuoti posėdžiai datos dar neturi). Stenograma — e-seimo dokumentas, susietas per `eli-dl:recorded_in_a_realization_of` ir pažymėtas pavadinimu „Stenograma”.

```sparql
# Seimas calendar: terms × sessions × plenary sittings (ELI-DL).
# Per term: how many sessions and plenary sittings it held, the first and last
# sitting day, and how many sittings have a stenogram in e-seimas. Sessions and
# sittings are eli-dl:Activity; a sitting forms part of its session
# (eli-dl:forms_part_of) and both point at the term (eli-dl:parliamentary_term).
# The date span comes from a subquery over dated sittings only: a few scheduled
# sittings have no eli-dl:activity_date, and an unbound value in the group would
# blank the whole MIN/MAX.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <https://schema.org/>
PREFIX eli-dl: <http://data.europa.eu/eli/eli-draft-legislation-ontology#>

SELECT ?term (COUNT(DISTINCT ?session) AS ?sessions) (COUNT(DISTINCT ?sitting) AS ?sittings)
       ?first ?last (COUNT(DISTINCT ?transcribed) AS ?withStenogram)
WHERE
{
    GRAPH ?termGraph
    {
        ?t a eli-dl:ParliamentaryTerm ;
            skos:prefLabel ?term .
    }
    GRAPH ?sittingGraph
    {
        ?sitting a schema:Event ;
            eli-dl:parliamentary_term ?t ;
            eli-dl:forms_part_of ?session .
    }
    {
        SELECT ?t (MIN(?date) AS ?first) (MAX(?date) AS ?last)
        WHERE
        {
            GRAPH ?datedGraph
            {
                ?dated eli-dl:parliamentary_term ?t ;
                    eli-dl:activity_date ?date .
            }
        }
        GROUP BY ?t
    }
    OPTIONAL
    {
        # the e-seimas record is described in the sitting's own document
        GRAPH ?sittingGraph
        {
            ?sitting eli-dl:recorded_in_a_realization_of ?record .
            ?record dct:title "Stenograma"@lt .
        }
        BIND(?sitting AS ?transcribed)
    }
}
GROUP BY ?term ?first ?last
ORDER BY ?term
```

Rezultatai:

| term | sessions | sittings | first | last | withStenogram |
|---|---|---|---|---|---|
| 1990–1992 metų kadencija | 9 | 601 | 1990-03-10 | 1992-11-19 | 599 |
| 1992–1996 metų kadencija | 13 | 634 | 1992-11-25 | 1996-11-19 | 634 |
| 1996–2000 metų kadencija | 17 | 528 | 1996-11-25 | 2000-10-18 | 528 |
| 2000–2004 metų kadencija | 18 | 573 | 2000-10-19 | 2004-11-11 | 571 |
| 2004–2008 metų kadencija | 11 | 471 | 2004-11-15 | 2008-11-14 | 471 |
| 2008–2012 metų kadencija | 15 | 489 | 2008-11-17 | 2012-11-14 | 489 |
| 2012–2016 metų kadencija | 11 | 394 | 2012-11-16 | 2016-11-10 | 394 |
| 2016–2020 metų kadencija | 13 | 455 | 2016-11-14 | 2020-11-10 | 455 |
| 2020–2024 metų kadencija | 17 | 431 | 2020-11-13 | 2024-11-12 | 431 |
| 2024–2028 metų kadencija | 7 | 195 | 2024-11-14 | 2026-10-15 | 192 |


## Seimo narių dalyvavimas balsavimuose

**Į kokį klausimą atsako:** kurie dabartiniai Seimo nariai rečiausiai dalyvauja atviruose plenarinių posėdžių balsavimuose ir kaip jie balsuoja?

**Kaip veikia:** balsavimai modeliuojami ES ELI-DL ontologija (`eli-dl:Vote`); kiekvieno nario pasirinkimas — atskiras ryšys `eli-dl:had_voter_favor` / `_against` / `_abstention` į asmenį. Vardiniai balsai yra tik atviruose balsavimuose (balsavimo būdas `atviras`; sprendimai bendru sutarimu, alternatyvūs ir slapti balsavimai jų neturi), todėl vardiklis — atviri balsavimai nuo nario mandato pradžios (tenure intervalas be pabaigos), o skaitiklis — jo balsai už, prieš ir susilaikius. Duomenų rinkinys pasirinktinis: `make -C etl/seimas votes`.

```sparql
# Seimas plenary votes: how often each sitting member takes part in roll calls.
# Per member of the current term who still holds the seat (tenure interval
# without time:hasEnd): the open votes (decision method "atviras") held since
# their seat began, how many of them they voted in favor / against / abstained
# in (eli-dl:had_voter_*), and the resulting participation share — lowest first.
# Consensus and alternative votes carry no for/against choices (see
# etl/seimas/mappings/votes.rq), so only open votes count.
# Needs the opt-in votes dataset: make -C etl/seimas votes
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX epvoc:  <https://data.europarl.europa.eu/def/epvoc#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>
PREFIX eli-dl: <http://data.europa.eu/eli/eli-draft-legislation-ontology#>

SELECT ?member ?party ?since ?openVotes ?favor ?against ?abstention
       (ROUND(1000 * (?favor + ?against + ?abstention) / ?openVotes) / 10 AS ?participationPct)
WHERE
{
    {
        # sitting members of the term that has votes, with their open votes since the seat began
        SELECT ?person ?term ?since ?partyEntity (COUNT(DISTINCT ?vote) AS ?openVotes)
        WHERE
        {
            GRAPH ?methodGraph { ?method skos:notation "atviras" }
            GRAPH ?voteGraph
            {
                ?vote eli-dl:decision_method ?method ;
                    eli-dl:parliamentary_term ?term ;
                    eli-dl:activity_date ?date .
            }
            # the seat, its interval and instants are #fragments of the person's document
            GRAPH ?personGraph
            {
                ?tenure epvoc:memberDuringParliamentaryTerm ?term ;
                    org:member ?person ;
                    ltlod:nominatedBy ?partyEntity ;
                    org:memberDuring ?interval .
                ?interval time:hasBeginning/time:inXSDDate ?since .
                FILTER NOT EXISTS { ?interval time:hasEnd ?end }
            }
            FILTER (?date >= ?since)
        }
        GROUP BY ?person ?term ?since ?partyEntity
    }
    {
        # their choices in the same term (a vote's choices are all in the vote's document)
        SELECT ?person ?term (SUM(?f) AS ?favor) (SUM(?a) AS ?against) (SUM(?s) AS ?abstention)
        WHERE
        {
            GRAPH ?voteGraph
            {
                ?vote eli-dl:parliamentary_term ?term .
                { ?vote eli-dl:had_voter_favor ?person BIND(1 AS ?f) BIND(0 AS ?a) BIND(0 AS ?s) }
                UNION
                { ?vote eli-dl:had_voter_against ?person BIND(0 AS ?f) BIND(1 AS ?a) BIND(0 AS ?s) }
                UNION
                { ?vote eli-dl:had_voter_abstention ?person BIND(0 AS ?f) BIND(0 AS ?a) BIND(1 AS ?s) }
            }
        }
        GROUP BY ?person ?term
    }
    GRAPH ?personGraph
    {
        ?person foaf:givenName ?given ;
            foaf:familyName ?family .
    }
    GRAPH ?partyGraph { ?partyEntity skos:prefLabel ?party }
    BIND(CONCAT(?given, " ", ?family) AS ?member)
}
ORDER BY ?participationPct ?member
LIMIT 15
```

Rezultatai:

| member | party | since | openVotes | favor | against | abstention | participationPct |
|---|---|---|---|---|---|---|---|
| Inga Ruginienė | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 420 | 91 | 25 | 14.7 |
| Rūta Miliūtė | Demokratų sąjunga „Vardan Lietuvos“ | 2024-11-19 | 3650 | 591 | 25 | 93 | 19.4 |
| Raminta Popovienė | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 590 | 102 | 53 | 20.4 |
| Emanuelis Zingeris | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-11-14 | 3653 | 626 | 103 | 85 | 22.3 |
| Dovilė Šakalienė | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 951 | 138 | 45 | 31.0 |
| Laurynas Kasčiūnas | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-11-14 | 3653 | 900 | 193 | 141 | 33.8 |
| Dainius Kreivys | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-11-14 | 3653 | 932 | 217 | 178 | 36.3 |
| Kęstutis Mažeika | Demokratų sąjunga „Vardan Lietuvos“ | 2024-11-14 | 3653 | 1159 | 78 | 234 | 40.3 |
| Vaida Aleknavičienė | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 1209 | 185 | 125 | 41.6 |
| Saulius Skvernelis | Demokratų sąjunga „Vardan Lietuvos“ | 2024-11-14 | 3653 | 1146 | 113 | 266 | 41.7 |
| Viktoras Pranckietis | Liberalų sąjūdis | 2024-11-14 | 3653 | 1184 | 158 | 193 | 42.0 |
| Gintautas Paluckas | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 1222 | 308 | 51 | 43.3 |
| Robertas Kaunas | Lietuvos socialdemokratų partija | 2024-11-14 | 3653 | 1340 | 206 | 99 | 45.0 |
| Žygimantas Pavilionis | Tėvynės sąjunga-Lietuvos krikščionys demokratai | 2024-11-14 | 3653 | 1139 | 272 | 234 | 45.0 |
| Rita Tamašunienė | Lietuvos lenkų rinkimų akcija-Krikščioniškų šeimų sąjunga | 2024-11-14 | 3653 | 1264 | 182 | 227 | 45.8 |


## Seimo narių inicijuoti projektai

**Į kokį klausimą atsako:** kurie dabartiniai Seimo nariai inicijuoja daugiausia teisės aktų projektų ir kokia jų dalis apskritai pasiekia plenarinį posėdį ir priėmimo stadiją?

**Kaip veikia:** projektai modeliuojami ES ELI-DL ontologija (`eli-dl:DraftLegislationWork`); kiekvienas iniciatorius ar bendraautoris — ryšys `eli-dl:legislative_process_work_creator` į asmenį. Posėdžiuose svarstyti klausimai (`eli-dl:Activity`) per `eli-dl:involved_work` nurodo svarstytą projektą, o per `eli-dl:occured_at_stage` — stadiją (pateikimas, svarstymas, priėmimas). Projektas „pasiekė priėmimą“, jei bent vienas jo klausimas svarstytas priėmimo stadijoje — tai apytikslis sėkmės rodiklis, nes šaltinis galutinio projekto likimo nepateikia. Rinkinys pasirinktinis: `make -C etl/seimas bills`.

```sparql
# Seimas bills: which members initiate the most bills, and how far those bills get.
# Per member of the current term: the bills they initiated or co-initiated
# (eli-dl:legislative_process_work_creator, bills.trig), how many of them reached a
# plenary sitting at all (an agenda item with eli-dl:involved_work -> the bill,
# agenda-items.trig) and how many reached the adoption stage ("Priėmimas", stage
# notation "priemimas") — the share of the latter is a proxy for a member's
# legislative success (the feeds carry no final outcome per bill).
# Needs the opt-in bills dataset: make -C etl/seimas bills
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX epvoc:  <https://data.europarl.europa.eu/def/epvoc#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>
PREFIX eli-dl: <http://data.europa.eu/eli/eli-draft-legislation-ontology#>

SELECT ?member ?party ?bills ?inPlenary ?atAdoption
       (ROUND(1000 * ?atAdoption / ?bills) / 10 AS ?adoptionStagePct)
WHERE
{
    {
        SELECT ?person (COUNT(DISTINCT ?bill) AS ?bills)
               (COUNT(DISTINCT ?considered) AS ?inPlenary) (COUNT(DISTINCT ?adopted) AS ?atAdoption)
        WHERE
        {
            GRAPH ?billGraph { ?bill eli-dl:legislative_process_work_creator ?person }
            # triple patterns only inside the OPTIONALs, the BINDs after them (CLAUDE.md gotcha)
            OPTIONAL
            {
                GRAPH ?itemGraph
                {
                    ?item eli-dl:involved_work ?bill ;
                        eli-dl:occured_at_stage ?stage .
                }
                OPTIONAL { GRAPH ?stageGraph { ?stage skos:notation ?stageNotation } }
            }
            BIND(IF(BOUND(?item), ?bill, ?undef) AS ?considered)
            BIND(IF(COALESCE(?stageNotation = "priemimas", false), ?bill, ?undef) AS ?adopted)
        }
        GROUP BY ?person
    }
    # members of the current term (tenure without an end) and the party that nominated them
    GRAPH ?personGraph
    {
        ?tenure org:member ?person ;
            epvoc:memberDuringParliamentaryTerm ?term ;
            ltlod:nominatedBy ?partyEntity ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
        ?person foaf:givenName ?given ;
            foaf:familyName ?family .
    }
    GRAPH ?partyGraph { ?partyEntity skos:prefLabel ?party }
    BIND(CONCAT(?given, " ", ?family) AS ?member)
}
ORDER BY DESC(?bills) ?member
LIMIT 20
```

Rezultatai:

| member | party | bills | inPlenary | atAdoption | adoptionStagePct |
|---|---|---|---|---|---|
| Karolis Neimantas | Politinė partija „Nemuno Aušra“ | 115 | 58 | 20 | 17.4 |
| Martynas Gedvilas | Politinė partija „Nemuno Aušra“ | 115 | 69 | 21 | 18.3 |
| Andrius Busila | Lietuvos socialdemokratų partija | 103 | 75 | 31 | 30.1 |
| Orinta Leiputė | Lietuvos socialdemokratų partija | 94 | 74 | 23 | 24.5 |
| Jurgita Šukevičienė | Lietuvos socialdemokratų partija | 93 | 75 | 35 | 37.6 |
| Linas Urmanavičius | Demokratų sąjunga „Vardan Lietuvos“ | 91 | 56 | 12 | 13.2 |
| Audrius Radvilavičius | Lietuvos socialdemokratų partija | 89 | 73 | 30 | 33.7 |
| Ligita Girskienė | Lietuvos valstiečių ir žaliųjų sąjunga | 89 | 62 | 9 | 10.1 |
| Vytautas Grubliauskas | Lietuvos socialdemokratų partija | 89 | 67 | 22 | 24.7 |
| Rima Baškienė | Demokratų sąjunga „Vardan Lietuvos“ | 86 | 58 | 9 | 10.5 |
| Indrė Kižienė | Lietuvos socialdemokratų partija | 84 | 71 | 31 | 36.9 |
| Algimantas Radvila | Lietuvos socialdemokratų partija | 83 | 62 | 19 | 22.9 |
| Vitalijus Šeršniovas | Išsikėlė pats | 83 | 45 | 11 | 13.3 |
| Karolis Podolskis | Lietuvos socialdemokratų partija | 82 | 69 | 29 | 35.4 |
| Linas Jonauskas | Lietuvos socialdemokratų partija | 81 | 61 | 24 | 29.6 |
| Kęstutis Mažeika | Demokratų sąjunga „Vardan Lietuvos“ | 79 | 57 | 15 | 19.0 |
| Roma Janušonienė | Lietuvos socialdemokratų partija | 78 | 64 | 27 | 34.6 |
| Dainius Varnas | Politinė partija „Nemuno Aušra“ | 77 | 48 | 12 | 15.6 |
| Kęstutis Vilkauskas | Lietuvos socialdemokratų partija | 75 | 56 | 21 | 28.0 |
| Laurynas Šedvydis | Lietuvos socialdemokratų partija | 75 | 60 | 28 | 37.3 |


## Balsavo prieš savo projektą

**Į kokį klausimą atsako:** kurie Seimo nariai balsavo prieš ar susilaikė dėl projekto, kurį patys inicijavo ar pasirašė kaip bendraautoriai?

**Kaip veikia:** sujungiami trys rinkiniai: projekto iniciatoriai (`bills.trig`), klausimai, kuriais tas projektas svarstytas (`agenda-items.trig`, `eli-dl:involved_work`), ir tų klausimų balsavimai (`votes.trig`, balsavimas → klausimas per `schema:superEvent`) su nario paties pasirinkimu (`eli-dl:had_voter_against` / `_abstention`). Dalis atvejų — procedūriniai balsavimai (pvz., dėl atidėjimo) ar pataisos, todėl kiekviena eilutė nurodo balsavimą patikrinti. Reikia abiejų pasirinktinių rinkinių: `make -C etl/seimas bills votes`.

```sparql
# Seimas bills x votes: members who voted against or abstained on a bill they
# themselves initiated. Joins the initiators of a bill (bills.trig) with the open
# votes held on its agenda items (vote -> schema:superEvent -> agenda item ->
# eli-dl:involved_work -> bill; agenda-items.trig, votes.trig) and the member's own
# choice in each vote. Typical causes: a co-signed bill amended beyond what the
# initiator supports, a procedural vote (e.g. on postponing), or a party line
# overriding the signature — each row links to the vote to check which.
# Needs the opt-in bills and votes datasets: make -C etl/seimas bills votes
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX schema: <https://schema.org/>
PREFIX eli-dl: <http://data.europa.eu/eli/eli-draft-legislation-ontology#>

SELECT ?member ?billNo ?date ?choice ?vote
WHERE
{
    GRAPH ?billGraph
    {
        ?bill eli-dl:legislative_process_work_creator ?person ;
            dct:identifier ?billNo .
    }
    GRAPH ?itemGraph { ?item eli-dl:involved_work ?bill }
    GRAPH ?voteGraph
    {
        ?vote schema:superEvent ?item ;
            eli-dl:activity_date ?date .
        { ?vote eli-dl:had_voter_against ?person BIND("prieš" AS ?choice) }
        UNION
        { ?vote eli-dl:had_voter_abstention ?person BIND("susilaikė" AS ?choice) }
    }
    GRAPH ?personGraph
    {
        ?person foaf:givenName ?given ;
            foaf:familyName ?family .
    }
    BIND(CONCAT(?given, " ", ?family) AS ?member)
}
ORDER BY DESC(?date) ?member
LIMIT 25
```

Rezultatai:

| member | billNo | date | choice | vote |
|---|---|---|---|---|
| Kęstutis Mažeika | XVP-1242 | 2026-10-13 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60320/#this |
| Orinta Leiputė | XVP-1701 | 2026-10-13 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60342/#this |
| Violeta Turauskaitė | XVP-1678 | 2026-10-13 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60318/#this |
| Bronis Ropė | XVP-1667 | 2026-10-08 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60293/#this |
| Dainius Gaižauskas | XVP-1667 | 2026-10-08 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60293/#this |
| Eimantas Kirkutis | XVP-1667 | 2026-10-08 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60293/#this |
| Valius Ąžuolas | XVP-1667 | 2026-10-08 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60293/#this |
| Artūras Zuokas | XVP-104 | 2026-10-06 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60213/#this |
| Jaroslaw Narkiewicz | XVP-1729 | 2026-10-06 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60208/#this |
| Linas Urmanavičius | XVP-1729 | 2026-10-06 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60208/#this |
| Vitalijus Šeršniovas | XVP-104 | 2026-10-06 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60213/#this |
| Algirdas Sysas | XVP-1803 | 2026-09-22 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Angelė Jakavonytė | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Arūnas Dudėnas | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Audrius Radvilavičius | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Bronis Ropė | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Bronis Ropė | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60147/#this |
| Daiva Ulbinaitė | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Darius Jakavičius | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Ignas Vėgėlė | XVP-1246 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60116/#this |
| Ignas Vėgėlė | XVP-1246 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60117/#this |
| Ingrida Braziulienė | XVP-1803 | 2026-09-22 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Jaroslaw Narkiewicz | XVP-1729 | 2026-09-22 | susilaikė | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60100/#this |
| Jurgis Razma | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |
| Jurgita Sejonienė | XVP-1803 | 2026-09-22 | prieš | https://linkeddata.lt/organizations/lietuvos-respublikos-seimas/votes/-60146/#this |

## Ką deklaruoja dabartinis Seimas

**Į kokį klausimą atsako:** kokį turtą deklaruoja dabartiniai Seimo nariai — kiek jų turi butų, žemės, akcijų, pinigų užsienyje ar skolų, ir kokios tai sumos?

**Kaip veikia:** kiekviena VMI turto deklaracija — atskiras dokumentas (`declarations/{asmens_id}-{metai}/`), o kiekviena nenulinė suma — jo fragmentas (`schema:MonetaryAmount`) su turto rūšimi (`dct:type` → `asset-categories` klasifikatorius). Užklausa ima 2024 ataskaitinių metų deklaracijas (`dct:temporal` → kalendoriaus metai) tų asmenų, kurių Seimo mandatas dar galioja, ir sugrupuoja sumas pagal rūšį. Rūšis, kurią VMI skaido į „Lietuvoje” ir „užsienyje”, per `skos:broader` parodoma po bendresne rūšimi. „Pasiskolintos lėšos” — įsipareigojimas, ne turtas. Partijų, kadencijos pokyčių, turto užsienyje ir balsavimų pjūviai — duomenų istorijoje „Seimo turtas 2024” (`app/stories/seimo-turtas-2024.ttl`).

```sparql
# Declarations × asset-categories taxonomy × Seimas: what the current Seimas declares.
# For reporting year 2024, per asset category: how many sitting members declared it,
# the total and the largest amount. Each amount is a #fragment of its declaration's
# document (one GRAPH block); the category concept and its skos:broader parent (the
# undivided category its Lithuania/abroad split belongs to) live in the taxonomy docs.
# "Pasiskolintos lėšos" is a liability (skos:scopeNote), not an asset.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX schema: <https://schema.org/>
PREFIX epvoc:  <https://data.europarl.europa.eu/def/epvoc#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?group ?category (COUNT(DISTINCT ?person) AS ?members) (SUM(?value) AS ?total) (MAX(?value) AS ?largest)
WHERE
{
    # the reporting year: a calendar year document (dct:identifier "2024")
    GRAPH ?yearGraph { ?year dct:identifier "2024" ; a time:DateTimeInterval }
    GRAPH ?declarationGraph
    {
        ?declaration ltlod:declarant ?person ;
            dct:temporal ?year ;
            ltlod:declaredValue ?amount .
        ?amount dct:type ?concept ;
            schema:value ?value .
    }
    # sitting members: a Seimas seat whose interval has no end (the seat, interval and
    # instants are #fragments of the person's document)
    GRAPH ?personGraph
    {
        ?tenure org:member ?person ;
            epvoc:memberDuringParliamentaryTerm ?term ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
    }
    GRAPH ?conceptGraph
    {
        ?concept skos:prefLabel ?category .
        FILTER (LANG(?category) = "lt")
    }
    # the broader (undivided) category, if the concept is a Lithuania/abroad split; the hop
    # and its label share one OPTIONAL so ?broader is bound before its label is looked up
    OPTIONAL
    {
        GRAPH ?conceptGraph { ?concept skos:broader ?broader }
        GRAPH ?broaderGraph { ?broader skos:prefLabel ?broaderLabel . FILTER (LANG(?broaderLabel) = "lt") }
    }
    BIND (COALESCE(?broaderLabel, ?category) AS ?group)
}
GROUP BY ?group ?category
ORDER BY ?group DESC(?total)
```

Rezultatai:

| group | category | members | total | largest |
|---|---|---|---|---|
| Akcijų vertė | Akcijų vertė | 22 | 5303463.0 | 1750000.0 |
| Dalių ir / ar pajų vertė | Dalių ir / ar pajų vertė | 2 | 2043.0 | 2000.0 |
| Kelių transporto priemonių vertė | Kelių transporto priemonių vertė | 96 | 1892390.0 | 132000.0 |
| Kitų registruotinų daiktų, meno kūrinių ir juvelyrinių dirbinių vertė | Kitų registruotinų daiktų, meno kūrinių ir juvelyrinių dirbinių vertė | 41 | 899171.0 | 282894.0 |
| Kitų vertybinių popierių vertė | Kitų vertybinių popierių vertė | 11 | 215593.0 | 95237.0 |
| Kredito įstaigose ir ne jose turimų piniginių lėšų suma | Kredito įstaigose ir ne jose turimų piniginių lėšų, esančių Lietuvos Respublikoje, suma | 131 | 6489809.0 | 707678.0 |
| Kredito įstaigose ir ne jose turimų piniginių lėšų suma | Kredito įstaigose ir ne jose turimų piniginių lėšų, esančių užsienio valstybėje, suma | 11 | 275980.0 | 93543.0 |
| Nekilnojamojo turto registre registruotinų patalpų, inžinerinių ir kitų statinių vertė | Butų daugiabučiuose namuose, esančių Lietuvos Respublikoje, vertė | 70 | 9816356.0 | 1138250.0 |
| Nekilnojamojo turto registre registruotinų patalpų, inžinerinių ir kitų statinių vertė | Gyvenamųjų namų (namo dalių), esančių Lietuvos Respublikoje, vertė | 78 | 7117720.0 | 1240000.0 |
| Nekilnojamojo turto registre registruotinų patalpų, inžinerinių ir kitų statinių vertė | Kitų statinių (sodo namelių, garažų, inžinerinių statinių), esančių Lietuvos Respublikoje… | 61 | 2178443.0 | 552020.0 |
| Nekilnojamojo turto registre registruotinų patalpų, inžinerinių ir kitų statinių vertė | Butų daugiabučiuose namuose, esančių užsienio valstybėje, vertė | 5 | 588490.0 | 150000.0 |
| Nekilnojamojo turto registre registruotinų patalpų, inžinerinių ir kitų statinių vertė | Nebaigtų statyti statinių, esančių Lietuvos Respublikoje, vertė | 6 | 341026.0 | 196000.0 |
| Pasiskolintų ir negrąžintų lėšų suma | Pasiskolintų ir negrąžintų lėšų suma | 64 | 4435111.0 | 417353.0 |
| Paskolintų ir nesusigrąžintų lėšų suma | Paskolintų ir nesusigrąžintų lėšų suma | 13 | 2273497.0 | 1324901.0 |
| Vyriausybės vertybinių popierių vertė | Vyriausybės vertybinių popierių vertė | 6 | 59555.0 | 33968.0 |
| Žemės sklypų vertė | Žemės sklypų Lietuvos Respublikoje vertė | 88 | 3346795.0 | 433682.0 |
| Žemės sklypų vertė | Žemės sklypų užsienio valstybėje vertė | 1 | 180000.0 | 180000.0 |


## Vieno politiko deklaracijos per metus

**Į kokį klausimą atsako:** kaip kito vieno politiko deklaruotas grynasis turtas per visus metus, kokias pareigas jis ėjo teikdamas deklaraciją ir kada ją pateikė?

**Kaip veikia:** asmuo randamas pagal vardą, jo deklaracijos — per `ltlod:declarant`. Grynasis turtas = visos sumos atėmus pasiskolintas lėšas. Sumos saugomos tokios, kokias paskelbė VMI, todėl valiuta keičiasi su euro įvedimu: iki 2014 ataskaitinių metų — litai (`LTL`), nuo 2015 — eurai (1 EUR = 3,4528 LTL); palyginimui per šią ribą sumas reikia perskaičiuoti. Pareigybių grupė (`dct:type` → `declarant-groups`) rodo pareigas deklaracijos pateikimo metu (`dct:issued` — kitų metų pavasaris).

```sparql
# Declarations over time: one person's declared net assets per reporting year — every
# declaration is its own document, the amounts its #fragments. Net = all amounts minus
# borrowed funds (the liability category). Amounts are as published, so the currency
# changes with the euro: litas for reporting years up to 2014, euro since (1 EUR =
# 3.4528 LTL). The VMI position group shows the office held when the declaration was
# filed (dct:issued, the spring after the reporting year).
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?year ?office ?filed (COUNT(?amount) AS ?categories) ?currency
       (SUM(IF(?notation = "pasiskolintos-lesos", -?value, ?value)) AS ?net)
WHERE
{
    GRAPH ?personGraph { ?person foaf:name "Agnė Bilotaitė" }
    GRAPH ?declarationGraph
    {
        ?declaration ltlod:declarant ?person ;
            dct:temporal ?yearEntity ;
            dct:type ?group ;
            dct:issued ?filed .
        OPTIONAL
        {
            ?declaration ltlod:declaredValue ?amount .
            ?amount dct:type ?concept ;
                schema:value ?value ;
                schema:currency ?currency .
        }
    }
    GRAPH ?yearGraph { ?yearEntity dct:identifier ?year }
    GRAPH ?groupGraph { ?group skos:prefLabel ?office . FILTER (LANG(?office) = "lt") }
    OPTIONAL { GRAPH ?conceptGraph { ?concept skos:notation ?notation } }
}
GROUP BY ?year ?office ?filed ?currency
ORDER BY ?year
```

Rezultatai:

| year | office | filed | categories | currency | net |
|---|---|---|---|---|---|
| 2013 | Lietuvos Respublikos Seimo nariai | 2014-02-20 | 4 | LTL | 283420.0 |
| 2014 | Lietuvos Respublikos Seimo nariai | 2015-05-02 | 4 | LTL | 283420.0 |
| 2015 | Lietuvos Respublikos Seimo nariai | 2016-05-01 | 4 | EUR | 94856.0 |
| 2016 | Lietuvos Respublikos Seimo nariai | 2017-05-01 | 4 | EUR | 41070.0 |
| 2017 | Lietuvos Respublikos Seimo nariai | 2018-04-30 | 4 | EUR | 63255.0 |
| 2018 | Lietuvos Respublikos Seimo nariai | 2019-05-01 | 1 | EUR | 37360.0 |
| 2019 | Lietuvos Respublikos Seimo nariai | 2020-05-02 | 1 | EUR | 37360.0 |
| 2020 | Ministras Pirmininkas ir ministrai | 2021-05-02 | 1 | EUR | 49360.0 |
| 2021 | Ministras Pirmininkas ir ministrai | 2022-05-01 | 1 | EUR | 37360.0 |
| 2022 | Ministras Pirmininkas ir ministrai | 2023-04-30 | 1 | EUR | 37360.0 |
| 2023 | Ministras Pirmininkas ir ministrai | 2024-03-28 | 1 | EUR | 37360.0 |
| 2024 | Lietuvos Respublikos Seimo nariai | 2025-05-01 | 1 | EUR | 37360.0 |
| 2025 | Lietuvos Respublikos Seimo nariai | 2026-05-03 | 1 | EUR | 30000.0 |


## Karjeros tarp pareigų

**Į kokį klausimą atsako:** kurie politikai ėjo daugiausia skirtingų viešųjų pareigų — Seimo nario, ministro, EP nario, mero — ir kokia tvarka?

**Kaip veikia:** VMI kiekvienų metų deklaraciją priskiria vienai pareigybių grupei — pareigoms, eitoms ją teikiant. Užklausa kiekvienam asmeniui ir grupei randa pirmus ir paskutinius tokių deklaracijų metus ir sujungia juos į kelią, atrikiuotą pagal pradžią. Rodomi asmenys, ėję bent trejas skirtingas pareigas.

```sparql
# Declarations × declarant-groups taxonomy: careers across public offices. VMI files each
# person-year under the one position group held when filing (Seimas member, minister,
# MEP, mayor, …), so a declarant's groups over the years trace their path between the
# Seimas, the Government, the European Parliament and the municipalities.
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?member (COUNT(DISTINCT ?group) AS ?offices) (GROUP_CONCAT(?step; separator=" → ") AS ?path)
WHERE
{
    {
        # one step per office: the first and last reporting year declared under it
        SELECT ?person ?group (CONCAT(MIN(?year), IF(MIN(?year) = MAX(?year), "", CONCAT("–", MAX(?year))), " ", SAMPLE(?label)) AS ?step)
        WHERE
        {
            GRAPH ?declarationGraph
            {
                ?declaration ltlod:declarant ?person ;
                    dct:type ?group ;
                    dct:temporal ?yearEntity .
            }
            GRAPH ?yearGraph { ?yearEntity dct:identifier ?year }
            GRAPH ?groupGraph { ?group skos:prefLabel ?label . FILTER (LANG(?label) = "lt") }
        }
        GROUP BY ?person ?group
        ORDER BY ?person MIN(?year)
    }
    GRAPH ?personGraph { ?person foaf:name ?member }
}
GROUP BY ?member
HAVING (COUNT(DISTINCT ?group) > 2)
ORDER BY DESC(?offices) ?member
```

Rezultatai:

| member | offices | path |
|---|---|---|
| Aurelijus Veryga | 3 | 2016–2019 Ministras Pirmininkas ir ministrai → 2020–2023 Lietuvos Respublikos Seimo naria… |
| Bronius Markauskas | 3 | 2016–2017 Ministras Pirmininkas ir ministrai → 2018 Lietuvos Respublikos Seimo nariai → 2… |
| Gabrielius Landsbergis | 3 | 2014–2015 Europos Parlamento nariai, išrinkti nuo Lietuvos Respublikos → 2016–2019 Lietuv… |
| Giedrius Surplys | 3 | 2017 Viceministrai → 2018 Ministras Pirmininkas ir ministrai → 2020–2023 Lietuvos Respubl… |
| Juozas Olekas | 3 | 2012–2025 Lietuvos Respublikos Seimo nariai → 2013 Ministras Pirmininkas ir ministrai → 2… |
| Virginijus Sinkevičius | 3 | 2016 Lietuvos Respublikos Seimo nariai → 2017–2018 Ministras Pirmininkas ir ministrai → 2… |

## Merų turtas pagal savivaldybę

**Į kokį klausimą atsako:** kiek turto deklaravo kiekvienos savivaldybės meras (-ai), ėję pareigas 2024 metais?

**Kaip veikia:** mero pareigos yra narystė (`org:Membership`) savivaldybėje — `admin-units` objekte (`officials` rinkinys, iš Wikidata). Narystė susieja savivaldybę su asmeniu, o asmuo — su jo 2024 m. VMI turto deklaracija. Sumuojamos visos deklaruotos turto kategorijos, išskyrus pasiskolintas lėšas (tai įsipareigojimas, ne turtas).

```sparql
# Officials × admin-units × declarations × asset-categories: what mayors declare, per
# municipality. A mayor's office is an org:Membership in their municipality (the
# cv:AdminUnit, etl/officials/), so the office links the municipality to the person,
# and the person to their VMI property declaration for reporting year 2024 (filed under
# the mayors' group, or any other group they belonged to that year). Assets are summed
# per declaration; "Pasiskolintos lėšos" is a liability, not an asset, so it is left out.
# The office, its interval and instants are #fragments of the person's document.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?municipality ?mayor (SUM(?value) AS ?assets) ?currency
WHERE
{
    GRAPH ?roleGraph { ?role skos:notation "meras" }
    # mayors in office at some point in 2024
    GRAPH ?personGraph
    {
        ?office org:member ?person ;
            org:role ?role ;
            org:organization ?unit ;
            org:memberDuring ?interval .
        ?interval time:hasBeginning/time:inXSDDate ?from .
        OPTIONAL { ?interval time:hasEnd/time:inXSDDate ?to }
        ?person foaf:name ?mayor .
    }
    FILTER (?from <= "2024-12-31"^^xsd:date && (!BOUND(?to) || ?to >= "2024-01-01"^^xsd:date))
    GRAPH ?unitGraph { ?unit skos:prefLabel ?municipality }
    GRAPH ?yearGraph { ?year dct:identifier "2024" ; a time:DateTimeInterval }
    GRAPH ?declarationGraph
    {
        ?declaration ltlod:declarant ?person ;
            dct:temporal ?year ;
            ltlod:declaredValue ?amount .
        ?amount dct:type ?concept ;
            schema:value ?value ;
            schema:currency ?currency .
    }
    GRAPH ?conceptGraph { ?concept skos:notation ?notation }
    FILTER (?notation != "pasiskolintos-lesos")
}
GROUP BY ?municipality ?mayor ?currency
ORDER BY DESC(?assets)
```

Rezultatai:

| municipality | mayor | assets | currency |
|---|---|---|---|
| Kauno miesto savivaldybė | Visvaldas Matijošaitis | 129551624.0 | EUR |
| Druskininkų savivaldybė | Ričardas Malinauskas | 1573066.0 | EUR |
| Palangos miesto savivaldybė | Šarūnas Vaitkus | 1389462.0 | EUR |
| Prienų rajono savivaldybė | Alvydas Vaicekauskas | 1199598.0 | EUR |
| Zarasų rajono savivaldybė | Nijolė Guobienė | 1189062.0 | EUR |
| Klaipėdos rajono savivaldybė | Bronius Markauskas | 819473.0 | EUR |
| Kelmės rajono savivaldybė | Ildefonsas Petkevičius | 716133.0 | EUR |
| Kazlų Rūdos savivaldybė | Mantas Varaška | 566000.0 | EUR |
| Radviliškio rajono savivaldybė | Kazimieras Račkauskis | 552459.0 | EUR |
| Širvintų rajono savivaldybė | Živilė Pinskuvienė | 531497.0 | EUR |
| Švenčionių rajono savivaldybė | Rimantas Klipčius | 523641.0 | EUR |
| Alytaus miesto savivaldybė | Nerijus Cesiulis | 455500.0 | EUR |
| Klaipėdos miesto savivaldybė | Arvydas Vaitkus | 379016.0 | EUR |
| Alytaus rajono savivaldybė | Rasa Vitkauskienė | 292948.0 | EUR |
| Visagino savivaldybė | Erlandas Galaguz | 271567.0 | EUR |
| Kauno rajono savivaldybė | Valerijus Makūnas | 258590.0 | EUR |
| Šalčininkų rajono savivaldybė | Zdzislav Palevič | 253620.0 | EUR |
| Šiaulių miesto savivaldybė | Artūras Visockas | 253070.0 | EUR |
| Plungės rajono savivaldybė | Audrius Klišonis | 252836.0 | EUR |
| Vilkaviškio rajono savivaldybė | Algirdas Neiberka | 249392.0 | EUR |
| Neringos savivaldybė | Darius Jasaitis | 235405.0 | EUR |
| Vilniaus miesto savivaldybė | Valdas Benkunskas | 233000.0 | EUR |
| Utenos rajono savivaldybė | Marijus Kaukėnas | 224724.0 | EUR |
| Rietavo savivaldybė | Antanas Černeckis | 220187.0 | EUR |
| Pakruojo rajono savivaldybė | Saulius Margis | 208228.0 | EUR |
| Lazdijų rajono savivaldybė | Ausma Miškinienė | 202820.0 | EUR |
| Kupiškio rajono savivaldybė | Algirdas Raslanas | 200025.0 | EUR |
| Telšių rajono savivaldybė | Tomas Katkus | 182500.0 | EUR |
| Kretingos rajono savivaldybė | Antanas Kalnius | 175510.0 | EUR |
| Anykščių rajono savivaldybė | Kęstutis Tubis | 171063.0 | EUR |
| … | &nbsp; |&nbsp; |&nbsp; |


## Vyriausybės nariai, kartu buvę Seimo nariais

**Į kokį klausimą atsako:** kiek Vyriausybės narių (ministrų ir Ministro Pirmininko) kiekvienos Seimo kadencijos metu tuo pat metu turėjo ir Seimo nario mandatą?

**Kaip veikia:** ministro pareigos (`officials` rinkinys, iš Wikidata) ir Seimo nario mandatas yra to paties asmens narystės tame pačiame dokumente, todėl jų laikotarpių persidengimas tikrinamas viename asmens dokumente. Pareigos priskiriamos kadencijai, jei jų laikotarpis persidengia su kadencijos laikotarpiu. Ministrų sąrašas toks išsamus, kiek juos aprašo Wikidata.

```sparql
# Officials × Seimas terms × Seimas seats: how many Government members also sat in the
# Seimas while in office, per term. A minister's (or the Prime Minister's) office and a
# Seimas seat are both org:Memberships of the same person — in ONE document, since a
# minister who held a seat keeps their persons/{asmens_id}/ graph — so the overlap of
# the two intervals is a join inside that document. Counts only reach as far as
# Wikidata's coverage of Lithuanian ministers (etl/officials/), which is incomplete.
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX org:    <http://www.w3.org/ns/org#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX eli-dl: <http://data.europa.eu/eli/eli-draft-legislation-ontology#>
PREFIX epvoc:  <https://data.europarl.europa.eu/def/epvoc#>

SELECT ?kadencija (COUNT(DISTINCT ?person) AS ?vyriausybes_nariai) (COUNT(DISTINCT ?mp) AS ?kartu_seimo_nariai)
WHERE
{
    GRAPH ?termGraph
    {
        ?term a eli-dl:ParliamentaryTerm ;
            skos:prefLabel ?label ;
            time:hasTime ?termInterval .
        ?termInterval time:hasBeginning/time:inXSDDate ?termStart .
        OPTIONAL { ?termInterval time:hasEnd/time:inXSDDate ?termEnd }
    }
    # Government offices held during the term
    GRAPH ?personGraph
    {
        ?office org:member ?person ;
            org:organization ?government ;
            org:memberDuring ?officeInterval .
        ?officeInterval time:hasBeginning/time:inXSDDate ?officeStart .
        OPTIONAL { ?officeInterval time:hasEnd/time:inXSDDate ?officeEnd }
    }
    # the Government document is app/ scaffolding (not in datasets/current), so the
    # organization is recognised by its (host-agnostic) path
    FILTER (STRENDS(STR(?government), "/organizations/lietuvos-respublikos-vyriausybe/#this"))
    FILTER (?officeStart < COALESCE(?termEnd, "9999-12-31"^^xsd:date)
        && COALESCE(?officeEnd, "9999-12-31"^^xsd:date) > ?termStart)
    # ... by someone holding a seat of that term at the same time
    OPTIONAL
    {
        GRAPH ?personGraph
        {
            ?tenure org:member ?mp ;
                epvoc:memberDuringParliamentaryTerm ?term ;
                org:memberDuring ?seatInterval .
            ?seatInterval time:hasBeginning/time:inXSDDate ?seatStart .
            OPTIONAL { ?seatInterval time:hasEnd/time:inXSDDate ?seatEnd }
        }
        FILTER (?mp = ?person
            && ?seatStart < COALESCE(?officeEnd, "9999-12-31"^^xsd:date)
            && COALESCE(?seatEnd, "9999-12-31"^^xsd:date) > ?officeStart)
    }
    BIND (REPLACE(STR(?label), " metų kadencija", "") AS ?kadencija)
}
GROUP BY ?termStart ?kadencija
ORDER BY ?termStart
```

Rezultatai:

| kadencija | vyriausybes_nariai | kartu_seimo_nariai |
|---|---|---|
| 1990–1992 | 21 | 6 |
| 1992–1996 | 38 | 6 |
| 1996–2000 | 41 | 16 |
| 2000–2004 | 42 | 15 |
| 2004–2008 | 32 | 18 |
| 2008–2012 | 36 | 15 |
| 2012–2016 | 40 | 19 |
| 2016–2020 | 36 | 13 |
| 2020–2024 | 36 | 20 |
| 2024–2028 | 37 | 20 |
## Asmeninis balsas vienmandatėse apygardose

**Į kokį klausimą atsako:** kurie 2024 m. vienmandatėse apygardose išrinkti Seimo nariai surinko gerokai daugiau balsų nei juos iškėlusi partija toje pačioje apygardoje — t. y. laimėjo asmeniniu populiarumu, ne partijos vardu?

**Kaip veikia:** viename apygardos rezultatų dokumente (`election-results`) yra ir kandidatų rezultatai, ir toje apygardoje už partijų sąrašus atiduoti balsai. Užklausa randa laimėtoją (`ltlod:elected true`), jo I turo balsų dalį ir jį iškėlusios partijos (`ltlod:nominatedBy`) sąrašo balsų dalį tame pačiame ture (`ltlod:party`) — abu skaičiuoti tame pačiame balsavime. Skirtumas procentiniais punktais = asmeninis balsas. Vardas imamas iš `persons`, partijos pavadinimas — iš `parties` dokumento. Išsikėlę patys laimėtojai sąrašo neturi ir nerodomi.

```sparql
# Cross-domain: election-results × persons × parties.
# The personal vote of the 2024 single-member winners: the candidate's round-one share
# minus their nominating party's list share in the same constituency (both counted on
# the same ballots that day). A large positive gap is a candidate who out-polls the
# party brand; a negative one rode the party. Self-nominated winners have no list to
# compare against and drop out.
#
# One contest document holds the contest, its rounds, every candidate result and the
# constituency's party-list results, so the comparison is one GRAPH block; the person's
# and party's names come from their own documents.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?member ?party ?constituency ?candidateShare ?listShare ?personalVote
WHERE
{
    GRAPH ?contestGraph
    {
        ?contest a ltlod:ConstituencyContest ;
            dct:identifier ?id ;
            dct:title ?title .
        # the winner, in whichever round decided the contest
        ?win ltlod:elected true ;
            ltlod:candidate ?person ;
            ltlod:nominatedBy ?p .
        # the same person's result in round one, on the day of the list vote
        ?first ltlod:candidate ?person ;
            ltlod:contestRound ?round1 ;
            ltlod:voteShare ?candidateShare .
        ?list ltlod:contestRound ?round1 ;
            ltlod:party ?p ;
            ltlod:voteShare ?listShare .
        ?round1 ltlod:contest ?contest .
    }
    FILTER(STRSTARTS(?id, "seimas-2024-") && STRENDS(STR(?round1), "#round-1"))
    GRAPH ?personGraph { ?person foaf:name ?member }
    GRAPH ?partyGraph { ?p skos:prefLabel ?party }
    BIND(STRBEFORE(STR(?title), " apygarda") AS ?constituency)
    BIND(?candidateShare - ?listShare AS ?personalVote)
}
ORDER BY DESC(?personalVote)
LIMIT 20
```

Rezultatai:

| member | party | constituency | candidateShare | listShare | personalVote |
|---|---|---|---|---|---|
| Viktorija Čmilytė-Nielsen | Liberalų sąjūdis | Senamiesčio–Žvėryno | 44.9 | 13.37 | 31.53 |
| Algirdas Butkevičius | Demokratų sąjunga „Vardan Lietuvos“ | Vilkaviškio | 39.3 | 17.53 | 21.77 |
| Eugenijus Sabutis | Lietuvos socialdemokratų partija | Jonavos | 54.39 | 33.71 | 20.68 |
| Ingrida Šimonytė | Tėvynės sąjunga-Lietuvos krikščionys demokratai | Antakalnio | 53.55 | 35.95 | 17.6 |
| Ligita Girskienė | Lietuvos valstiečių ir žaliųjų sąjunga | Marių | 24.35 | 9.04 | 15.31 |
| Ričardas Juška | Liberalų sąjūdis | Karšuvos | 24.46 | 10.21 | 14.25 |
| Arvydas Anušauskas | Tėvynės sąjunga-Lietuvos krikščionys demokratai | Kalniečių | 34.61 | 22.5 | 12.11 |
| Linas Urmanavičius | Demokratų sąjunga „Vardan Lietuvos“ | Jotvingių | 31.14 | 19.31 | 11.83 |
| Jevgenij Šuklin | Liberalų sąjūdis | Nalšios šiaurinė | 20.34 | 8.89 | 11.45 |
| Kęstutis Vilkauskas | Lietuvos socialdemokratų partija | Trakų–Vievio | 31.72 | 20.32 | 11.4 |
| Artūras Zuokas | Partija „Laisvė ir teisingumas“ | Naujininkų–Rasų | 14.38 | 3.2 | 11.18 |
| Vaida Aleknavičienė | Lietuvos socialdemokratų partija | Žiemgalos vakarinė | 39.55 | 28.4 | 11.15 |
| Kęstutis Mažeika | Demokratų sąjunga „Vardan Lietuvos“ | Sūduvos pietinė | 28.08 | 17.32 | 10.76 |
| Remigijus Žemaitaitis | Politinė partija „Nemuno Aušra“ | Kelmės–Šilalės | 46.44 | 37.54 | 8.9 |
| Laurynas Kasčiūnas | Tėvynės sąjunga-Lietuvos krikščionys demokratai | Lazdynų | 34.34 | 25.96 | 8.38 |
| Vytautas Sinica | Nacionalinis susivienijimas | Pilaitės–Karoliniškių | 13.11 | 5.04 | 8.07 |
| Audrius Petrošius | Tėvynės sąjunga-Lietuvos krikščionys demokratai | Danės | 31.06 | 23.33 | 7.73 |
| Alvydas Mockus | Lietuvos socialdemokratų partija | Gargždų | 27.68 | 20.14 | 7.54 |
| Matas Skamarakas | Lietuvos socialdemokratų partija | Raseinių–Josvainių | 38.03 | 31.37 | 6.66 |
| Domas Griškevičius | Demokratų sąjunga „Vardan Lietuvos“ | Saulės | 17.24 | 11.28 | 5.96 |


## Pralaimėję apygardoje, bet Seime pagal sąrašą

**Į kokį klausimą atsako:** kas 2024 m. pralaimėjo vienmandatėje apygardoje, bet vis tiek tapo Seimo nariu — pagal partijos sąrašą?

**Kaip veikia:** iš `elections` imama 2024 m. rinkimų išrinkta kadencija (`ltlod:electedTerm`). Apygardos rezultatų dokumente randami su asmenimis susieti kandidatai (`ltlod:candidate`), kurie toje apygardoje nebuvo išrinkti; asmens dokumente — jų Seimo nario vieta toje kadencijoje be rinkimų apygardos (`ltlod:electoralDistrict` neturi tik pagal sąrašą išrinktųjų vietos). Rodoma geriausia kandidato balsų dalis ir vieta abiejuose turuose.

```sparql
# Cross-domain: election-results × elections × persons (Seimas seats).
# Who lost their single-member race in 2024 yet sits in the Seimas anyway — through the
# party list? A candidate result resolved to a person (ltlod:candidate) with no elected
# result in that contest, joined to the person's seat in the term that election elected
# where the seat carries no ltlod:electoralDistrict (a list seat). Their best share in
# the race shows how far from the district win they were.
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX epvoc: <https://data.europarl.europa.eu/def/epvoc#>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?member ?constituency (MAX(?share) AS ?bestShare) (MIN(?rank) AS ?bestRank)
WHERE
{
    GRAPH ?electionGraph
    {
        ?election dct:identifier "seimas-2024" ;
            ltlod:electedTerm ?term .
    }
    GRAPH ?contestGraph
    {
        ?contest ltlod:election ?election ;
            dct:title ?title .
        ?result ltlod:candidate ?person ;
            ltlod:voteShare ?share ;
            ltlod:rank ?rank .
        FILTER NOT EXISTS { ?won ltlod:candidate ?person ; ltlod:elected true }
    }
    GRAPH ?personGraph
    {
        ?seat org:member ?person ;
            epvoc:memberDuringParliamentaryTerm ?term .
        ?person foaf:name ?member .
        FILTER NOT EXISTS { ?seat ltlod:electoralDistrict ?district }
    }
    BIND(STRBEFORE(STR(?title), " apygarda") AS ?constituency)
}
GROUP BY ?member ?constituency
ORDER BY DESC(?bestShare)
LIMIT 25
```

Rezultatai:

| member | constituency | bestShare | bestRank |
|---|---|---|---|
| Aistė Gedvilienė | Fabijoniškių | 47.99 | 1 |
| Radvilė Morkūnaitė-Mikulėnienė | Pilaitės–Karoliniškių | 47.45 | 1 |
| Zigmantas Balčytis | Šilutės | 46.38 | 2 |
| Gintarė Skaistė | Panemunės | 45.86 | 1 |
| Jurgis Razma | Plungės–Rietavo | 45.84 | 1 |
| Valius Ąžuolas | Žemaitijos šiaurinė | 45.66 | 1 |
| Rasa Budbergytė | Šeškinės–Šnipiškių | 44.96 | 2 |
| Saulius Skvernelis | Lazdynų | 44.3 | 2 |
| Vytautas Kernagis | Pašilaičių | 44.24 | 1 |
| Agnė Bilotaitė | Vilniaus pietinė | 43.99 | 1 |
| Arūnas Valinskas | Pajūrio | 43.77 | 1 |
| Lina Šukytė-Korsakė | Baltijos | 43.71 | 1 |
| Kazys Starkevičius | Petrašiūnų–Gričiupio | 43.52 | 1 |
| Tadas Prajara | Sūduvos pietinė | 42.76 | 2 |
| Viktoras Pranckietis | Raudondvario | 42.14 | 2 |
| Tomas Tomilinas | Deltuvos šiaurinė | 41.95 | 2 |
| Dainius Gaižauskas | Marijampolės | 40.65 | 2 |
| Algirdas Sysas | Verkių | 40.58 | 2 |
| Aidas Gedvilas | Aušros | 38.21 | 1 |
| Liudas Mažylis | Savanorių | 38.18 | 1 |
| Matas Maldeikis | Justiniškių–Viršuliškių | 37.41 | 1 |
| Edita Rudelienė | Trakų–Vievio | 30.89 | 2 |
| Gintautas Paluckas | Utenos | 19.24 | 3 |
| Aušrinė Norkienė | Tauragės | 18.04 | 4 |
| Vytautas Juozapaitis | Senamiesčio–Žvėryno | 17.49 | 2 |

## Didžiausi juridinių asmenų įnašai partijoms

**Į kokį klausimą atsako:** kurios įmonės daugiausia aukojo kiekvienos partijos ir jos kandidatų Seimo rinkimų kampanijoms?

**Kaip veikia:** politinės kampanijos dalyvio dokumente (`campaign-finance`) yra jo juridinių asmenų įnašai (`ltlod:CampaignDonation`). Atrenkami lėšų šaltinio „JAA — juridinio asmens auka“ įnašai (be partijos pervedimų ir valstybės biudžeto lėšų), o partija nustatoma pagal dalyvį: partijos kampanija (`ltlod:campaignOf`) arba kandidatą iškėlusi partija (`ltlod:nominatedBy`). Aukotojas — kaip paskelbta, su nuoroda į juridinį asmenį pagal JAR kodą. Beveik visi tokie įnašai — 2008 m. kampanijos.

```sparql
# Cross-domain: campaign-finance × parties (× legal-entities).
# The largest corporate donors of Seimas election campaigns, per party: legal-person
# donations (funding source JAA — "juridinio asmens auka"; party transfers, state budget
# allocations and refunded unacceptable donations are other sources and excluded), to the
# party's own campaign or to the campaigns of the candidates it nominated. In the data,
# 676 of the 735 such donations are from the 2008 campaign and only a handful come after
# 2011, so the ranking is effectively the 2008 one.
# The donor is the published name; its legal-entities/{jar}/ link resolves with the full
# JAR register.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?party ?donorName ?donor (COUNT(?donation) AS ?donations) (SUM(?value) AS ?eur)
WHERE
{
    GRAPH ?participantGraph
    {
        ?donation ltlod:recipient ?participant ;
            dct:type ?source ;
            ltlod:donorName ?donorName ;
            schema:value ?value .
        OPTIONAL { ?donation ltlod:donor ?donor }
        { ?participant ltlod:campaignOf ?p } UNION { ?participant ltlod:nominatedBy ?p }
    }
    FILTER(STRENDS(STR(?source), "/taxonomies/campaign-funding-sources/jaa/#this"))
    GRAPH ?partyGraph { ?p skos:prefLabel ?party }
}
GROUP BY ?party ?donorName ?donor
ORDER BY DESC(?eur)
LIMIT 20
```

Rezultatai:

| party | donorName | donor | donations | eur |
|---|---|---|---|---|
| Lietuvos Respublikos liberalų sąjūdis | Viešoji įstaiga "TAIKOMOSIOS POLITIKOS INSTITUTAS" | https://linkeddata.lt/legal-entities/302481795/#this | 1 | 45336.86 |
| Tėvynės sąjunga-Lietuvos krikščionys demokratai | Tėvynės sąjunga-Lietuvos krikščionys demokratai | https://linkeddata.lt/legal-entities/301753623/#this | 14 | 26426.37 |
| Liberalų ir centro sąjunga | Uždaroji akcinė bendrovė "DANGAUS ŽYDRYNĖ" | https://linkeddata.lt/legal-entities/224501370/#this | 7 | 23169.6 |
| Tėvynės sąjunga-Lietuvos krikščionys demokratai | UAB koncernas "ACHEMOS GRUPĖ" | https://linkeddata.lt/legal-entities/156673480/#this | 3 | 20273.4 |
| Lietuvos socialdemokratų partija | UAB koncernas "ACHEMOS GRUPĖ" | https://linkeddata.lt/legal-entities/156673480/#this | 2 | 18535.68 |
| Lietuvos Respublikos liberalų sąjūdis | UAB "POSŪKIS" | https://linkeddata.lt/legal-entities/122570783/#this | 3 | 11584.8 |
| Lietuvos Respublikos liberalų sąjūdis | Uždaroji akcinė bendrovė "MERKO STATYBA" | https://linkeddata.lt/legal-entities/111610080/#this | 1 | 11295.18 |
| Tėvynės sąjunga-Lietuvos krikščionys demokratai | Uždaroji akcinė bendrovė "MERKO STATYBA" | https://linkeddata.lt/legal-entities/111610080/#this | 1 | 11295.18 |
| Lietuvos socialdemokratų partija | UAB "POSŪKIS" | https://linkeddata.lt/legal-entities/122570783/#this | 1 | 11295.18 |
| Tėvynės sąjunga-Lietuvos krikščionys demokratai | Uždaroji akcinė bendrovė "JURGENA" | https://linkeddata.lt/legal-entities/122769753/#this | 1 | 11295.18 |
| Lietuvos socialdemokratų partija | Akcinė bendrovė "KLAIPĖDOS JŪRŲ KROVINIŲ KOMPANIJA" | https://linkeddata.lt/legal-entities/140346267/#this | 1 | 11295.18 |
| Lietuvos valstiečių liaudininkų sąjunga | Uždaroji akcinė bendrovė "METALOIDAS" | https://linkeddata.lt/legal-entities/145376111/#this | 1 | 11295.18 |
| Lietuvos socialdemokratų partija | UAB "Ūrus" ir Ko | https://linkeddata.lt/legal-entities/145496114/#this | 1 | 11295.18 |
| Naujoji sąjunga (socialliberalai) | D. Petraitienės firma "Akvija" | https://linkeddata.lt/legal-entities/147685829/#this | 1 | 11295.18 |
| Lietuvos socialdemokratų partija | Akcinė bendrovė "Achema" | https://linkeddata.lt/legal-entities/156667399/#this | 1 | 11295.18 |
| Lietuvos valstiečių liaudininkų sąjunga | UAB koncernas "ACHEMOS GRUPĖ" | https://linkeddata.lt/legal-entities/156673480/#this | 1 | 11295.18 |
| Naujoji sąjunga (socialliberalai) | UAB koncernas "ACHEMOS GRUPĖ" | https://linkeddata.lt/legal-entities/156673480/#this | 1 | 11295.18 |
| Lietuvos valstiečių ir žaliųjų sąjunga | Žemės ūkio bendrovė "Draugas" | https://linkeddata.lt/legal-entities/171295543/#this | 1 | 11295.18 |
| Liberalų ir centro sąjunga | Uždaroji akcinė bendrovė "IZOBARA" | https://linkeddata.lt/legal-entities/183114189/#this | 1 | 11295.18 |
| Lietuvos socialdemokratų partija | UAB "E.L.L. NEKILNOJAMAS TURTAS" | https://linkeddata.lt/legal-entities/211659210/#this | 1 | 11295.18 |


## Kampanijų aukotojai — viešųjų pirkimų tiekėjai

**Į kokį klausimą atsako:** kurios įmonės aukojo Seimo rinkimų kampanijoms ir taip pat laimėjo viešųjų pirkimų sutarčių?

**Kaip veikia:** aukotojas (`ltlod:donor`) ir sutarties tiekėjas (`epo:bindsContractor → epo:playedBy`) — tas pats juridinio asmens IRI, abiejų rinkinių sukonstruotas iš JAR kodo (`legal-entities/{ja_kodas}/#this`), todėl jie sujungiami neįkėlus JAR registro. Dvi vidinės agregacijos susumuoja įmonės „JAA” įnašus ir jos sutarčių vertę. Reikia įkelto `procurement` rinkinio (be jo rezultatas tuščias). Atkreipkite dėmesį į laikotarpius: įmonių įnašai beveik visi iš 2008 m. kampanijos, o pirkimai — naujausios sutartys, todėl sutapimas rodo tą pačią įmonę abiejose pusėse, o ne mainus. Užklausa kerta `elections` ir `procurement` rinkinius.

```sparql
# Cross-domain: campaign-finance × procurement (via the JAR code).
# Companies that funded a Seimas election campaign AND won public procurement contracts:
# the donor and the contractor are the same legal-entities/{jar}/#this IRI, minted from
# the bare JAR code by both pipelines, so they join without either dataset loading the
# JAR register. Donations are legal-person ones of source JAA ("juridinio asmens auka");
# contract values are EUR (epo:hasContractValue). Needs the procurement domain loaded
# (PR #65, gitignored bulk output); without it the query returns nothing. Mind the
# periods: corporate donations are almost all from the 2008 campaign, while procurement
# is windowed to recent contracts, so a match shows the same company on both sides,
# not a quid pro quo.
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX epo:    <http://data.europa.eu/a4g/ontology#>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?company ?donorName ?donated_eur ?contracts ?contracts_eur
WHERE
{
    {
        SELECT ?company ?donorName (SUM(?value) AS ?donated_eur)
        WHERE
        {
            GRAPH ?participantGraph
            {
                ?donation ltlod:donor ?company ;
                    ltlod:donorName ?donorName ;
                    dct:type ?source ;
                    schema:value ?value .
            }
            FILTER(STRENDS(STR(?source), "/taxonomies/campaign-funding-sources/jaa/#this"))
        }
        GROUP BY ?company ?donorName
    }
    {
        SELECT ?company (COUNT(DISTINCT ?contract) AS ?contracts) (SUM(?amount) AS ?contracts_eur)
        WHERE
        {
            GRAPH ?contractGraph
            {
                ?contract epo:bindsContractor/epo:playedBy ?company ;
                    epo:hasContractValue/epo:hasAmountValue ?amount .
            }
        }
        GROUP BY ?company
    }
}
ORDER BY DESC(?contracts_eur)
LIMIT 20
```

Rezultatai:

| company | donorName | donated_eur | contracts | contracts_eur |
|---|---|---|---|---|
| https://linkeddata.lt/legal-entities/133556411/#this | Akcinė bendrovė "YIT KAUSTA" | 4344.3 | 32 | 101275748.76 |
| https://linkeddata.lt/legal-entities/121477326/#this | TILTŲ STATYBOS UŽDAROJI AKCINĖ BENDROVĖ "TILSTA" | 1737.72 | 5 | 92163879.73 |
| https://linkeddata.lt/legal-entities/122211549/#this | UAB "Stebulė" | 868.86 | 15 | 74397105.61 |
| https://linkeddata.lt/legal-entities/110801759/#this | Uždaroji akcinė bendrovė "Fegda" | 5792.4 | 44 | 53017058.71 |
| https://linkeddata.lt/legal-entities/249672710/#this | Uždaroji akcinė bendrovė "Alkesta" | 1448.1 | 54 | 49169657.65 |
| https://linkeddata.lt/legal-entities/165108836/#this | Uždaroji akcinė bendrovė "Parama" | 8196.25 | 37 | 30179399.91 |
| https://linkeddata.lt/legal-entities/147710353/#this | Akcinė bendrovė "PANEVĖŽIO KELIAI" | 2896.2 | 34 | 28232733.23 |
| https://linkeddata.lt/legal-entities/183615620/#this | Uždaroji akcinė bendrovė "Alauša" | 724.05 | 32 | 23126729.01 |
| https://linkeddata.lt/legal-entities/125759732/#this | UAB "EIGESA" | 1448.1 | 23 | 19946695.12 |
| https://linkeddata.lt/legal-entities/180240752/#this | Akcinė bendrovė "ŽEMAITIJOS PIENAS" | 7935.59 | 608 | 17575338.41 |
| https://linkeddata.lt/legal-entities/132439736/#this | Uždaroji akcinė bendrovė "Elektromontuotojas" | 2250.35 | 20 | 15288462.25 |
| https://linkeddata.lt/legal-entities/122755433/#this | Uždaroji akcinė bendrovė "EKSKOMISARŲ BIURAS" | 2461.77 | 64 | 14047632.2 |
| https://linkeddata.lt/legal-entities/169700486/#this | Uždaroji akcinė bendrovė „VVARFF“ | 1158.48 | 19 | 12250661.33 |
| https://linkeddata.lt/legal-entities/134906131/#this | Virginijaus ir Romaldo Rabačių tikroji ūkinė bendrija "Virmalda" | 10136.7 | 17 | 11347716.32 |
| https://linkeddata.lt/legal-entities/135915083/#this | UAB "Vitafarma" | 8138.32 | 20 | 9574284.39 |
| https://linkeddata.lt/legal-entities/147732969/#this | Akcinė bendrovė "PANEVĖŽIO STATYBOS TRESTAS" | 4344.3 | 3 | 8968392.95 |
| https://linkeddata.lt/legal-entities/184263588/#this | Uždaroji akcinė bendrovė "Dauniškis" ir KO | 1158.48 | 8 | 7821221.85 |
| https://linkeddata.lt/legal-entities/167900844/#this | Akcinė bendrovė "Dolomitas" | 2896.2 | 18 | 7249529.87 |
| https://linkeddata.lt/legal-entities/121289694/#this | Uždaroji akcinė bendrovė "FIMA" | 17377.2 | 44 | 6839637.95 |
| https://linkeddata.lt/legal-entities/158102142/#this | A. Žilinskio ir ko UAB | 2896.2 | 5 | 6485380.98 |


## Kiek kainavo balsas

**Į kokį klausimą atsako:** kiek eurų 2024 m. vienmandatėse apygardose išrinkti Seimo nariai išleido kampanijai vienam I turo balsui?

**Kaip veikia:** kandidato kampanijos dalyvis susietas su jo rezultatu apygardoje (`ltlod:candidacy`) per VRK kandidato ID. Susumuojamos dalyvio išlaidos — juridinių asmenų paslaugos (`campaign-expenses.trig`) ir fizinių asmenų paslaugų sumos — ir padalinamos iš I turo balsų. Partijos išlaidos kandidatui neįskaičiuotos.

```sparql
# Cross-domain: campaign-finance × election-results × persons.
# What a vote cost the 2024 single-member winners: the campaign's itemised spending
# (payments to legal persons, #expense-…, plus the natural-person totals) divided by
# the candidate's round-one votes. The campaign participant links to its ArcGIS
# candidate result by the VRK candidate id (ltlod:candidacy), and the result's contest
# says whether that candidate won. Spending on a candidate by their party's own campaign
# is not included.
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX schema: <https://schema.org/>
PREFIX ltlod:  <http://linkeddata.lt/ns#>

SELECT ?member ?spent_eur ?votes (ROUND(?spent_eur / ?votes * 100) / 100 AS ?eur_per_vote)
WHERE
{
    {
        SELECT ?participant ?candidacy ?person (SUM(?value) AS ?spent_eur)
        WHERE
        {
            GRAPH ?participantGraph
            {
                ?participant ltlod:candidacy ?candidacy ;
                    ltlod:campaignOf ?person .
                ?expense ltlod:payer ?participant ;
                    schema:value ?value .
            }
        }
        GROUP BY ?participant ?candidacy ?person
    }
    GRAPH ?contestGraph
    {
        ?candidacy ltlod:votes ?votes ;
            ltlod:candidate ?person .
        ?winner ltlod:candidate ?person ;
            ltlod:elected true .
    }
    FILTER(CONTAINS(STR(?candidacy), "/election-results/seimas-2024-"))
    GRAPH ?personGraph { ?person foaf:name ?member }
}
ORDER BY DESC(?eur_per_vote)
LIMIT 20
```

Rezultatai:

| member | spent_eur | votes | eur_per_vote |
|---|---|---|---|
| Roma Janušonienė | 42536.8 | 3184 | 13.36 |
| Robertas Kaunas | 22384.11 | 2530 | 8.85 |
| Karolis Podolskis | 30356.19 | 4001 | 7.59 |
| Žygimantas Pavilionis | 33013.43 | 4377 | 7.54 |
| Audrius Petrošius | 30586.99 | 5115 | 5.98 |
| Martynas Katelynas | 23564.0 | 3938 | 5.98 |
| Algimantas Radvila | 21595.66 | 3865 | 5.59 |
| Arūnas Dudėnas | 17470.45 | 3153 | 5.54 |
| Remigijus Motuzas | 12300.0 | 2252 | 5.46 |
| Šarūnas Šukevičius | 21095.66 | 4185 | 5.04 |
| Šarūnas Birutis | 17785.78 | 3621 | 4.91 |
| Indrė Kižienė | 11713.85 | 2736 | 4.28 |
| Raminta Popovienė | 20747.86 | 5704 | 3.64 |
| Laurynas Šedvydis | 9589.52 | 2741 | 3.5 |
| Dainius Kreivys | 23276.83 | 6661 | 3.49 |
| Lilija Vaitiekūnienė | 13090.86 | 3869 | 3.38 |
| Orinta Leiputė | 11824.77 | 3522 | 3.36 |
| Ingrida Braziulienė | 10829.45 | 3412 | 3.17 |
| Jūratė Zailskienė | 13026.34 | 4163 | 3.13 |
| Liutauras Kazlavickas | 11935.8 | 3852 | 3.1 |
## Viešieji pirkimai pagal perkančiosios organizacijos savivaldybę

**Į kokį klausimą atsako:** kurių savivaldybių įstaigos per paskutinius 12 mėnesių sudarė didžiausios vertės viešųjų pirkimų sutarčių?

**Kaip veikia:** sutartis (ES ePO) per `epo:bindsBuyer` ir `epo:playedBy` susieta su perkančiąja organizacija pagal jos JAR kodą, o ši — per registruotos buveinės grandinę (`org:hasRegisteredSite → org:Site → org:siteAddress → locn:Address → locn:adminUnit`) — su savivaldybe. Sutarčių vertės pirmiausia sumuojamos kiekvienai perkančiajai organizacijai, tada — savivaldybei. Užklausa kerta tris rinkinius: `procurement`, `legal-entities` ir `admin-units`. Perkančiosios organizacijos, kurių nėra `legal-entities` (pvz., valstybės įmonės, kol neįkeltas pilnas JAR), į sumą nepatenka.

```sparql
# Cross-domain: procurement × legal-entities × admin-units.
# Public procurement spend by the municipality where the BUYER is registered:
# contract -> epo:bindsBuyer -> role -> epo:playedBy -> the buyer (a JAR legal entity),
# whose registered office resolves to a municipality (org:hasRegisteredSite ->
# org:Site -> org:siteAddress -> locn:Address -> locn:adminUnit). One GRAPH block per
# document: the contract (with its role and value fragments), the buyer, the municipality.
# Contracts are summed per buyer first, so the institution and municipality joins run
# once per buyer, not once per contract.
# Buyers outside legal-entities/ (state enterprises etc. until the full JAR register is
# loaded) have no registered office here and drop out.
PREFIX epo:      <http://data.europa.eu/a4g/ontology#>
PREFIX org:      <http://www.w3.org/ns/org#>
PREFIX locn:     <http://www.w3.org/ns/locn#>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality (SUM(?n) AS ?contracts) (COUNT(?buyer) AS ?buyers)
    (ROUND(SUM(?total) / 10000) / 100 AS ?mln_eur)
WHERE
{
    {
        SELECT ?buyer (COUNT(?contract) AS ?n) (SUM(?amount) AS ?total)
        WHERE
        {
            GRAPH ?contractGraph
            {
                ?contract epo:bindsBuyer/epo:playedBy ?buyer ;
                    epo:hasContractValue/epo:hasAmountValue ?amount .
            }
        }
        GROUP BY ?buyer
    }
    VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
    GRAPH ?buyerGraph
    {
        ?buyer org:hasRegisteredSite/org:siteAddress/locn:adminUnit ?m .
    }
    GRAPH ?municipalityGraph
    {
        ?m cv:level ?level ;
            skos:prefLabel ?municipality .
    }
    FILTER(LANG(?municipality) = "lt")
}
GROUP BY ?municipality
ORDER BY DESC(?mln_eur)
LIMIT 20
```

Rezultatai:

| municipality | contracts | buyers | mln_eur |
|---|---|---|---|
| Vilniaus miesto savivaldybė | 7328 | 401 | 1729.14 |
| Kauno miesto savivaldybė | 2360 | 187 | 846.03 |
| Palangos miesto savivaldybė | 282 | 21 | 552.43 |
| Klaipėdos miesto savivaldybė | 949 | 109 | 156.57 |
| Panevėžio miesto savivaldybė | 617 | 70 | 111.22 |
| Šiaulių miesto savivaldybė | 984 | 81 | 103.33 |
| Alytaus miesto savivaldybė | 487 | 23 | 83.66 |
| Švenčionių rajono savivaldybė | 244 | 10 | 56.74 |
| Marijampolės savivaldybė | 418 | 27 | 54.21 |
| Telšių rajono savivaldybė | 338 | 32 | 52.95 |
| Kelmės rajono savivaldybė | 284 | 20 | 47.41 |
| Klaipėdos rajono savivaldybė | 555 | 38 | 39.76 |
| Akmenės rajono savivaldybė | 205 | 18 | 38.44 |
| Trakų rajono savivaldybė | 302 | 21 | 34.8 |
| Šilutės rajono savivaldybė | 365 | 33 | 30.24 |
| Mažeikių rajono savivaldybė | 399 | 41 | 29.05 |
| Jonavos rajono savivaldybė | 277 | 27 | 28.95 |
| Tauragės rajono savivaldybė | 306 | 26 | 27.53 |
| Kupiškio rajono savivaldybė | 134 | 15 | 27.25 |
| Utenos rajono savivaldybė | 322 | 28 | 27.1 |


## Didžiausi viešojo sektoriaus tiekėjai

**Į kokį klausimą atsako:** kurie tiekėjai per paskutinius 12 mėnesių gavo didžiausios vertės viešųjų pirkimų sutarčių ir kiek skirtingų perkančiųjų organizacijų iš jų perka?

**Kaip veikia:** kiekvienos sutarties tiekėjo vaidmuo (`epo:bindsContractor → epo:Contractor → epo:playedBy`) nurodo juridinį asmenį pagal jo JAR kodą — nuoroda sukonstruojama iš kodo, nežiūrint į kitą rinkinį. Sumuojama tiekėjo sutarčių vertė ir skaičiuojami skirtingi pirkėjai (vienas dominuojantis pirkėjas ar plati klientų bazė). Pavadinimas paimamas iš tiekėjo `legal-entities` dokumento, jei jis įkeltas (pilnas JAR), kitaip rodomas JAR kodas.

```sparql
# Cross-domain: procurement × legal-entities.
# The largest suppliers of the public sector: total contract value per contractor, with
# the number of contracts and of distinct buyers it sells to (one dominant buyer vs a
# broad client base).
# The contractor is a bare JAR link (legal-entities/{code}/#this, minted from the code);
# its name comes from its legal-entities/ document when that is loaded (the full JAR
# register), else the JAR code is shown.
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX epo:  <http://data.europa.eu/a4g/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?supplier ?name ?contracts ?buyers ?mln_eur
WHERE
{
    {
        SELECT ?supplier (COUNT(DISTINCT ?contract) AS ?contracts) (COUNT(DISTINCT ?buyer) AS ?buyers)
            (ROUND(SUM(?amount) / 10000) / 100 AS ?mln_eur)
        WHERE
        {
            GRAPH ?contractGraph
            {
                ?contract epo:bindsContractor/epo:playedBy ?supplier ;
                    epo:bindsBuyer/epo:playedBy ?buyer ;
                    epo:hasContractValue/epo:hasAmountValue ?amount .
            }
        }
        GROUP BY ?supplier
        ORDER BY DESC(?mln_eur)
        LIMIT 20
    }
    OPTIONAL { GRAPH ?supplierGraph { ?supplier skos:prefLabel ?label } }
    BIND(COALESCE(?label, STRBEFORE(STRAFTER(STR(?supplier), "/legal-entities/"), "/")) AS ?name)
}
ORDER BY DESC(?mln_eur)
```

Rezultatai:

| supplier | name | contracts | buyers | mln_eur |
|---|---|---|---|---|
| https://linkeddata.lt/legal-entities/133729589/#this | 133729589 | 33 | 9 | 392.01 |
| https://linkeddata.lt/legal-entities/135007799/#this | 135007799 | 87 | 12 | 387.34 |
| https://linkeddata.lt/legal-entities/135640993/#this | 135640993 | 33 | 9 | 261.17 |
| https://linkeddata.lt/legal-entities/303383884/#this | 303383884 | 297 | 252 | 211.6 |
| https://linkeddata.lt/legal-entities/124644360/#this | 124644360 | 145 | 138 | 189.55 |
| https://linkeddata.lt/legal-entities/121949798/#this | 121949798 | 72 | 7 | 160.82 |
| https://linkeddata.lt/legal-entities/120750163/#this | 120750163 | 2 | 2 | 126.99 |
| https://linkeddata.lt/legal-entities/133630961/#this | 133630961 | 70 | 34 | 119.65 |
| https://linkeddata.lt/legal-entities/302947360/#this | 302947360 | 16 | 9 | 118.19 |
| https://linkeddata.lt/legal-entities/122635779/#this | 122635779 | 8 | 3 | 106.56 |
| https://linkeddata.lt/legal-entities/234522530/#this | 234522530 | 23 | 14 | 102.84 |
| https://linkeddata.lt/legal-entities/133556411/#this | 133556411 | 32 | 7 | 101.28 |
| https://linkeddata.lt/legal-entities/121477326/#this | 121477326 | 5 | 4 | 92.16 |
| https://linkeddata.lt/legal-entities/166451720/#this | 166451720 | 13 | 10 | 87.52 |
| https://linkeddata.lt/legal-entities/305202934/#this | 305202934 | 34 | 5 | 85.41 |
| https://linkeddata.lt/legal-entities/178715423/#this | 178715423 | 411 | 340 | 79.23 |
| https://linkeddata.lt/legal-entities/303528358/#this | 303528358 | 20 | 6 | 78.38 |
| https://linkeddata.lt/legal-entities/122211549/#this | 122211549 | 15 | 6 | 74.4 |
| https://linkeddata.lt/legal-entities/125956142/#this | 125956142 | 4 | 3 | 72.83 |
| https://linkeddata.lt/legal-entities/304915315/#this | 304915315 | 38 | 3 | 70.93 |


## Sutartys, sudarytos savaitgaliais ir per šventes

**Į kokį klausimą atsako:** kiek viešųjų pirkimų sutarčių sudaryta ne darbo dieną — savaitgalį ar per valstybinę šventę?

**Kaip veikia:** kiekvienos sutarties sudarymo data susieta su kalendoriaus diena (`dct:temporal`), o dienos dokumentas žino savaitės dieną (`time:dayOfWeek`) ir, jei tą dieną buvo valstybinė šventė, — šventės konceptą (`dct:type`). Sutartys suskirstomos pagal dienos rūšį. Didelė ne darbo dienų dalis — ženklas, kad sutartys registruojamos atgaline data ar paketais, ne tik darbo įpročių rodiklis.

```sparql
# Cross-domain: procurement × calendar (× taxonomies/holidays).
# Contracts concluded on a public holiday or a weekend. Every contract links its
# conclusion date to the calendar day (dct:temporal); the day document knows its
# weekday (time:dayOfWeek) and, when it was a public holiday, carries dct:type -> the
# holiday concept. Counted per kind of day, so the share of signings outside working
# days is visible at a glance — a data-quality signal (back-dated or batch-registered
# contracts) as much as a working-habits one.
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX epo:  <http://data.europa.eu/a4g/ontology#>
PREFIX time: <http://www.w3.org/2006/time#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?kind (COUNT(?contract) AS ?contracts) (ROUND(SUM(?amount) / 10000) / 100 AS ?mln_eur)
WHERE
{
    GRAPH ?contractGraph
    {
        ?contract a epo:Contract ;
            dct:temporal ?day ;
            epo:hasContractValue/epo:hasAmountValue ?amount .
    }
    GRAPH ?dayGraph
    {
        ?day time:hasDateTimeDescription/time:dayOfWeek ?weekday .
    }
    # the holiday and its label in ONE optional, joined on the already-bound ?day (a
    # separate OPTIONAL on an unbound ?holiday would match every prefLabel)
    OPTIONAL
    {
        GRAPH ?holidayDayGraph { ?day dct:type ?holiday }
        GRAPH ?holidayGraph { ?holiday skos:prefLabel ?holidayLabel }
        FILTER(LANG(?holidayLabel) = "lt")
    }
    BIND(IF(BOUND(?holidayLabel), CONCAT("šventė: ", STR(?holidayLabel)),
         IF(?weekday IN (time:Saturday, time:Sunday), "savaitgalis", "darbo diena")) AS ?kind)
}
GROUP BY ?kind
ORDER BY DESC(?contracts)
```

Rezultatai:

| kind | contracts | mln_eur |
|---|---|---|
| darbo diena | 54808 | 14709.49 |
| savaitgalis | 713 | 104.82 |
| šventė: Naujųjų metų diena | 36 | 12.41 |
| šventė: Tarptautinė darbo diena | 21 | 0.52 |
| šventė: Visų Šventųjų diena | 20 | 4.42 |
| šventė: Valstybės (Lietuvos karaliaus Mindaugo karūnavimo) ir Tautiškos giesmės diena | 14 | 0.75 |
| šventė: Lietuvos valstybės atkūrimo diena | 9 | 1.11 |
| šventė: Lietuvos nepriklausomybės atkūrimo diena | 9 | 1.78 |
| šventė: Tėvo diena | 8 | 1.07 |
| šventė: Rasos ir Joninių diena | 7 | 0.44 |
| šventė: Antroji Velykų diena | 6 | 0.51 |
| šventė: Motinos diena | 4 | 0.13 |
| šventė: Antroji Kalėdų diena | 2 | 0.02 |
| šventė: Kūčios | 2 | 0.03 |
| šventė: Velykos | 1 | 0.01 |
| šventė: Kalėdos | 1 | 0.01 |
| šventė: Mirusiųjų atminimo (Vėlinių) diena | 1 | 0.02 |
| šventė: Žolinė (Švč. Mergelės Marijos ėmimo į dangų diena) | 1 | 0.05 |
## Privatūs interesai ir lobizmas

**Į kokį klausimą atsako:** kurie politikai deklaravo ryšį (narystę, valdymo organą, akcijas) su juridiniu asmeniu, kuris pats įrašytas į lobistų sąrašą — ir kiek lobistinės veiklos deklaracijų tas juridinis asmuo pateikė, kiek jų nurodo patį politiką?

**Kaip veikia:** PINREG ryšys yra `org:Membership` su `ltlod:interestOrganization` į `legal-entities/{JAR kodas}/`; SKAIDRIS lobistas — juridinis asmuo — turi `ltlod:agent` į tą patį URI, nes abu rinkiniai jį sukuria iš to paties JAR kodo. Taip sujungiami du skirtingų registrų įrašai be jokių paieškų pagal pavadinimą. Lobistinės deklaracijos, kuriose paveiktas asmuo — pats politikas, skaičiuojamos atskirai.

```sparql
# VTEK private interests × lobbying register: conflicts of interest. An official who
# declared a tie (membership, board seat, shares…) to a legal entity that is itself a
# registered lobbyist (ltlod:agent -> the same legal-entities/{jar}/#this), with how many
# lobbying declarations the entity filed and how many of them named this official.
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX time:  <http://www.w3.org/2006/time#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?official ?entity ?tie_role (COUNT(DISTINCT ?declaration) AS ?lobbying_declarations)
    (COUNT(DISTINCT ?lobbiedSelf) AS ?naming_the_official) (IF(BOUND(?ended), "baigėsi", "dabartinis") AS ?tie_status)
WHERE
{
    GRAPH ?interestGraph
    {
        ?tie ltlod:interestOrganization ?org ;
            org:member ?person ;
            org:role ?role ;
            ltlod:organizationName ?entity .
        OPTIONAL { ?tie org:memberDuring ?interval . ?interval time:hasEnd ?ended }
    }
    GRAPH ?lobbyistGraph { ?lobbyist ltlod:agent ?org }
    GRAPH ?declarationGraph { ?declaration ltlod:lobbyist ?lobbyist }
    # only triple patterns inside OPTIONAL (a BIND there could not see ?declaration)
    OPTIONAL
    {
        GRAPH ?declarationGraph
        {
            ?declaration ltlod:contact ?selfContact .
            ?selfContact ltlod:influencedPerson ?person .
        }
    }
    BIND(IF(BOUND(?selfContact), ?declaration, ?undef) AS ?lobbiedSelf)
    GRAPH ?personGraph { ?person foaf:name ?official }
    GRAPH ?roleGraph { ?role skos:prefLabel ?tie_role FILTER(LANG(?tie_role) = "lt") }
}
GROUP BY ?official ?entity ?tie_role ?ended
ORDER BY DESC(?naming_the_official) DESC(?lobbying_declarations) ?official
```

Rezultatai:

| official | entity | tie_role | lobbying_declarations | naming_the_official | tie_status |
|---|---|---|---|---|---|
| Kęstutis Tubis | Lietuvos miško ir žemės savininkų asociacija | Kolegialaus valdymo organo narys | 72 | 0 | dabartinis |
| Simonas Gentvilas | Lietuvos miško ir žemės savininkų asociacija | Narys | 72 | 0 | dabartinis |


## Dažniausiai lobistų veikti pareigūnai

**Į kokį klausimą atsako:** kuriuos Seimo narius (ir kitus pareigūnus, esančius `persons/`) lobistai nurodo dažniausiai, kiek skirtingų lobistų juos veikė ir kokiose srityse?

**Kaip veikia:** kiekviena lobistinės veiklos deklaracija turi paveiktų asmenų fragmentus (`ltlod:contact`); tie, kurių vardas ir pavardė vienareikšmiškai sutampa su asmeniu, susieti `ltlod:influencedPerson`. Sritys (`dct:subject`) surenkamos atskira agregacija, nes pačių pareigūnų deklaracijos sritį nurodo retai.

```sparql
# VTEK lobbying × Seimas persons: the officials most often named in lobbying declarations
# (lobbyists' transparency declarations and their own experienced-influence declarations),
# with the number of distinct lobbyists and the areas they lobbied on.
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?official (COUNT(DISTINCT ?declaration) AS ?declarations) (COUNT(DISTINCT ?lobbyist) AS ?lobbyists) ?areas
WHERE
{
    GRAPH ?declarationGraph
    {
        ?declaration ltlod:contact ?contact ;
            ltlod:lobbyist ?lobbyist .
        ?contact ltlod:influencedPerson ?person .
    }
    # areas in a subquery: officials' own declarations mostly carry no area, and an
    # unbound value inside GROUP_CONCAT would blank the whole aggregate
    OPTIONAL
    {
        SELECT ?person (GROUP_CONCAT(DISTINCT ?label; separator=", ") AS ?areas)
        WHERE
        {
            GRAPH ?g
            {
                ?d ltlod:contact ?c ;
                    dct:subject ?area .
                ?c ltlod:influencedPerson ?person .
            }
            GRAPH ?areaGraph { ?area skos:prefLabel ?label FILTER(LANG(?label) = "lt") }
        }
        GROUP BY ?person
    }
    GRAPH ?personGraph { ?person foaf:name ?official }
}
GROUP BY ?official ?areas
ORDER BY DESC(?declarations)
LIMIT 20
```

Rezultatai:

| official | declarations | lobbyists | areas |
|---|---|---|---|
| Lukas Savickas | 40 | 17 | Finansai ir bankininkystė, Energetika, Socialinė apsauga ir darbas, Ekonomika ir inovacij… |
| Simonas Gentvilas | 36 | 19 | Teisė ir teisėtvarka, Aplinkosauga, Energetika, Kaimo reikalai ir žemės ūkis, Statybos, T… |
| Tomas Tomilinas | 26 | 14 | Aplinkosauga, Azartiniai lošimai ir loterijos, Energetika, Transportas ir susisiekimas, S… |
| Andrius Bagdonas | 25 | 13 | Ekonomika ir inovacijos, Transportas ir susisiekimas, Tabako ir alkoholio kontrolė, Teisė… |
| Linas Jonauskas | 24 | 12 | Miškų ūkis, Ekonomika ir inovacijos, Aplinkosauga, Energetika, Kaimo reikalai ir žemės ūk… |
| Audrius Radvilavičius | 22 | 8 | Energetika, Aplinkosauga, Ekonomika ir inovacijos |
| Mindaugas Lingė | 22 | 9 | Azartiniai lošimai ir loterijos, Socialinė apsauga ir darbas, Tabako ir alkoholio kontrol… |
| Ieva Pakarklytė | 21 | 8 | Aplinkosauga, Finansai ir bankininkystė, Energetika, Nacionalinis saugumas ir gynyba, Eko… |
| Saulius Bucevičius | 21 | 9 | Užsienio reikalai, Energetika, Ekonomika ir inovacijos, Transportas ir susisiekimas, Teis… |
| Kasparas Adomaitis | 19 | 8 | Kaimo reikalai ir žemės ūkis, Transportas ir susisiekimas, Aplinkosauga, Energetika, Stat… |
| Gintautas Paluckas | 18 | 10 | Teisė ir teisėtvarka, Finansai ir bankininkystė, Aplinkosauga, Socialinė apsauga ir darba… |
| Algirdas Sysas | 17 | 12 | Azartiniai lošimai ir loterijos, Švietimas ir mokslas, Finansai ir bankininkystė, Transpo… |
| Viktoras Fiodorovas | 16 | 10 | Teisė ir teisėtvarka, Energetika, Socialinė apsauga ir darbas, Ekonomika ir inovacijos, F… |
| Vytautas Mitalas | 16 | 9 | Azartiniai lošimai ir loterijos, Tabako ir alkoholio kontrolė, Ekonomika ir inovacijos, N… |
| Algirdas Butkevičius | 13 | 10 | Energetika, Kaimo reikalai ir žemės ūkis, Finansai ir bankininkystė, Teisė ir teisėtvarka… |
| Aistė Gedvilienė | 13 | 6 | Statybos, Aplinkosauga, Energetika, Užsienio reikalai |
| Valius Ąžuolas | 13 | 7 | Transportas ir susisiekimas, Energetika, Aplinkosauga, Nacionalinis saugumas ir gynyba, E… |
| Juozas Olekas | 13 | 8 | Tabako ir alkoholio kontrolė, Sveikatos apsauga, Nacionalinis saugumas ir gynyba, Azartin… |
| Inga Ruginienė | 12 | 7 | Ekonomika ir inovacijos, Azartiniai lošimai ir loterijos, Sveikatos apsauga, Socialinė ap… |
| Linas Kukuraitis | 11 | 5 | Socialinė apsauga ir darbas, Sveikatos apsauga, Azartiniai lošimai ir loterijos, Finansai… |


## Privatūs interesai ir viešieji pirkimai

**Į kokį klausimą atsako:** kurių politikų deklaruoti juridiniai asmenys (akcijos, valdymo organai, narystė) laimi viešuosius pirkimus, kiek sutarčių ir už kokią sumą — ir ar pats politikas deklaravo, kad juridinis asmuo dalyvauja pirkimuose?

**Kaip veikia:** ryšys ir pirkimo sutarties tiekėjo vaidmuo (`epo:playedBy`) rodo į tą patį `legal-entities/{JAR kodas}/` URI. Darbovietės neįtraukiamos. Reikia įkelto viešųjų pirkimų rinkinio (`etl/procurement`); be jo rezultatas tuščias.

```sparql
# VTEK private interests × public procurement (etl/procurement, CVP IS contracts): officials
# whose declared tie is to a legal entity that won public contracts, joined by the bare JAR
# code both pipelines mint (legal-entities/{jar}/#this) — no lookup in either direction.
# The declarant's own "takes part in public procurement" flag is shown beside the facts.
# Needs the procurement dataset loaded (an empty result without it).
PREFIX foaf:  <http://xmlns.com/foaf/0.1/>
PREFIX org:   <http://www.w3.org/ns/org#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX epo:   <http://data.europa.eu/a4g/ontology#>
PREFIX ltlod: <http://linkeddata.lt/ns#>

SELECT ?official ?entity ?tie_role ?declared_procurement
    (COUNT(DISTINCT ?contract) AS ?contracts) (SUM(?amount) AS ?total_eur)
WHERE
{
    GRAPH ?interestGraph
    {
        ?tie ltlod:interestOrganization ?org ;
            org:member ?person ;
            org:role ?role ;
            ltlod:organizationName ?entity .
        OPTIONAL { ?tie ltlod:inPublicProcurement ?declared_procurement }
    }
    # ties only: a declared workplace (an official employed by a contracting university or
    # municipal administration) is not a private interest in the contractor
    FILTER(!STRENDS(STR(?role), "/interest-roles/darboviete/#this"))
    GRAPH ?contractGraph
    {
        ?contract a epo:Contract ;
            epo:bindsContractor ?contractor ;
            epo:hasContractValue ?value .
        ?contractor epo:playedBy ?org .
        ?value epo:hasAmountValue ?amount .
    }
    GRAPH ?personGraph { ?person foaf:name ?official }
    GRAPH ?roleGraph { ?role skos:prefLabel ?tie_role FILTER(LANG(?tie_role) = "lt") }
}
GROUP BY ?official ?entity ?tie_role ?declared_procurement
ORDER BY DESC(?total_eur)
```

Rezultatai:

| official | entity | tie_role | declared_procurement | contracts | total_eur |
|---|---|---|---|---|---|
