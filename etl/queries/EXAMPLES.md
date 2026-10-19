# SPARQL užklausų pavyzdžiai

Užklausos vykdomos visus `datasets/current/` rinkinius užkrovus į atmintį (Jena, ~1 mln. ketvertų):

```shell
./run.sh <užklausa.rq>     # viena užklausa
./run.sh --all             # visos iš eilės
```

Kiekvienas objektas yra atskirame named graph'e (dokumente), todėl užklausos kiekvieno dokumento trafaretus rašo atskirame `GRAPH ?g { … }` bloke, o tarp dokumentų jungia per bendrus kintamuosius — tai standartinis SPARQL 1.1, veikiantis bet kurioje ketvertų (quad) saugykloje. Vieno dokumento viduje yra ir jo `#fragmentai` (pvz., asmens narystės, jų intervalai ir momentai), todėl jie rašomi tame pačiame bloke. `alignments.trig` ir `photos.trig` naudoja tuos pačius grafų vardus kaip pagrindiniai rinkiniai, todėl užkrovus susilieja su objektų grafais.

Šis failas sugeneruotas `python3 render-examples.py` — perleidus ETL, lenteles galima atnaujinti ta pačia komanda.


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
| http://data.europa.eu/eli/eli-draft-legislation-ontology#Vote | 75761 | 0 | 0 |
| http://purl.org/dc/terms/Location | 61149 | 0 | 0 |
| http://data.europa.eu/m8g/AdminUnit | 26883 | 642 | 456 |
| http://purl.org/dc/terms/PeriodOfTime | 14373 | 0 | 0 |
| http://www.w3.org/2006/time#DateTimeInterval | 14373 | 0 | 0 |
| http://www.w3.org/ns/org#FormalOrganization | 6094 | 0 | 0 |
| http://www.w3.org/ns/regorg#RegisteredOrganization | 6028 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#Activity | 4902 | 0 | 0 |
| https://schema.org/Event | 4771 | 0 | 0 |
| http://linkeddata.lt/ns#AssetDeclaration | 1953 | 0 | 0 |
| http://xmlns.com/foaf/0.1/Person | 831 | 738 | 293 |
| http://linkeddata.lt/ns#ElectoralDistrict | 771 | 0 | 0 |
| http://www.w3.org/ns/org#OrganizationalUnit | 394 | 0 | 0 |
| http://www.w3.org/2004/02/skos/core#Concept | 341 | 0 | 0 |
| https://schema.org/EventSeries | 131 | 0 | 0 |
| https://schema.org/PoliticalParty | 66 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#ActivityType | 13 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#ParliamentaryTerm | 10 | 0 | 0 |
| http://data.europa.eu/eli/eli-draft-legislation-ontology#DecisionMethod | 5 | 0 | 0 |


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
            org:hasRegisteredSite/org:siteAddress/locn:adminUnit ?m .
    }
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
| Vilniaus miesto savivaldybė | 479 |
| Kauno miesto savivaldybė | 197 |
| Klaipėdos miesto savivaldybė | 119 |
| Šiaulių miesto savivaldybė | 93 |
| Panevėžio miesto savivaldybė | 88 |
| Vilniaus rajono savivaldybė | 75 |
| Kauno rajono savivaldybė | 64 |
| Mažeikių rajono savivaldybė | 56 |
| Kėdainių rajono savivaldybė | 45 |
| Šalčininkų rajono savivaldybė | 44 |
| Telšių rajono savivaldybė | 42 |
| Šilutės rajono savivaldybė | 42 |
| Alytaus miesto savivaldybė | 41 |
| Klaipėdos rajono savivaldybė | 41 |
| Trakų rajono savivaldybė | 40 |
| Kaišiadorių rajono savivaldybė | 36 |
| Radviliškio rajono savivaldybė | 34 |
| Jonavos rajono savivaldybė | 33 |
| Prienų rajono savivaldybė | 32 |
| Ukmergės rajono savivaldybė | 32 |


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
