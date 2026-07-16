# SPARQL užklausų pavyzdžiai

Užklausos vykdomos visus `datasets/current/` rinkinius užkrovus į atmintį (Jena, ~1 mln. ketvertų):

```shell
./run.sh <užklausa.rq>     # viena užklausa
./run.sh --all             # visos iš eilės
```

Kadangi kiekvienas objektas yra atskirame named graph'e, kryžminės užklausos naudoja Jena sintetinį `<urn:x-arq:UnionGraph>` — visų named graph'ų sąjungą, kurioje property path'ai veikia tarp objektų grafų. `alignments.trig` ir `photos.trig` naudoja tuos pačius grafų vardus kaip pagrindiniai rinkiniai, todėl užkrovus susilieja su objektų grafais.

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
# All queries here use Jena's synthetic <urn:x-arq:UnionGraph>, which exposes
# the union of all named graphs — property paths can then cross entity graphs.
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX foaf:     <http://xmlns.com/foaf/0.1/>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX owl:      <http://www.w3.org/2002/07/owl#>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?municipality ?county ?elderships ?settlements ?wikidata ?coatOfArms
WHERE
{
    GRAPH <urn:x-arq:UnionGraph>
    {
        VALUES ?level { atu-type:LTU_MSV atu-type:LTU_RSV atu-type:LTU_SV }
        ?m cv:level ?level ;
            skos:prefLabel ?municipality ;
            dct:isPartOf/skos:prefLabel ?county .
        OPTIONAL { ?m owl:sameAs ?wikidata }
        OPTIONAL { ?m foaf:depiction ?coatOfArms }

        { SELECT ?m (COUNT(DISTINCT ?e) AS ?elderships)
          WHERE { ?e cv:level atu-type:LTU_SEN ; dct:isPartOf ?m }
          GROUP BY ?m }

        { SELECT ?m (COUNT(DISTINCT ?s) AS ?settlements)
          WHERE { ?s cv:level <https://linkeddata.lt/taxonomies/admin-unit-levels/gyvenamoji-vietove/#this> ;
                     dct:isPartOf ?p .
                  OPTIONAL { ?p cv:level atu-type:LTU_SEN ; dct:isPartOf ?pm }
                  BIND(COALESCE(?pm, ?p) AS ?m) }
          GROUP BY ?m }
    }
}
ORDER BY DESC(?settlements)
LIMIT 15
```

Rezultatai:

| municipality | county | elderships | settlements | wikidata | coatOfArms |
|---|---|---|---|---|---|
| Vilniaus rajono savivaldybė | Vilniaus apskritis | 24 | 1292 | http://www.wikidata.org/entity/Q118903 | http://commons.wikimedia.org/wiki/Special:FilePath/Karmazinu%20takas3.JPG |
| Vilniaus rajono savivaldybė | Vilniaus apskritis | 24 | 1292 | http://www.wikidata.org/entity/Q118903 | http://commons.wikimedia.org/wiki/Special:FilePath/Vilnius%20district%20COA.svg |
| Rokiškio rajono savivaldybė | Panevėžio apskritis | 10 | 1105 | http://www.wikidata.org/entity/Q766969 | http://commons.wikimedia.org/wiki/Special:FilePath/Roki%C5%A1kis%20COA.svg |
| Zarasų rajono savivaldybė | Utenos apskritis | 10 | 1075 | http://www.wikidata.org/entity/Q664415 | http://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Zarasai.svg |
| Zarasų rajono savivaldybė | Utenos apskritis | 10 | 1075 | http://www.wikidata.org/entity/Q664415 | http://commons.wikimedia.org/wiki/Special:FilePath/Veselava002.JPG |
| Molėtų rajono savivaldybė | Utenos apskritis | 11 | 1047 | http://www.wikidata.org/entity/Q2089785 | http://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Moletai%20%28L… |
| Anykščių rajono savivaldybė | Utenos apskritis | 10 | 982 | http://www.wikidata.org/entity/Q2089772 | http://commons.wikimedia.org/wiki/Special:FilePath/Anyk%C5%A1%C4%8Diai%20COA%20great.svg |
| Anykščių rajono savivaldybė | Utenos apskritis | 10 | 982 | http://www.wikidata.org/entity/Q2089772 | http://commons.wikimedia.org/wiki/Special:FilePath/Church%20of%20St.%20Matthew%20and%20th… |
| Kelmės rajono savivaldybė | Šiaulių apskritis | 11 | 950 | http://www.wikidata.org/entity/Q1387044 | http://commons.wikimedia.org/wiki/Special:FilePath/Kelmes-herbas.svg |
| Panevėžio rajono savivaldybė | Panevėžio apskritis | 12 | 934 | http://www.wikidata.org/entity/Q1351758 | http://commons.wikimedia.org/wiki/Special:FilePath/Panev%C4%97%C5%BEys%20District%20COA.s… |
| Ignalinos rajono savivaldybė | Utenos apskritis | 12 | 819 | http://www.wikidata.org/entity/Q2069330 | http://commons.wikimedia.org/wiki/Special:FilePath/Coat%20of%20arms%20of%20Ignalina%20%28… |
| Švenčionių rajono savivaldybė | Vilniaus apskritis | 14 | 792 | http://www.wikidata.org/entity/Q1813849 | http://commons.wikimedia.org/wiki/Special:FilePath/%C5%A0ven%C4%8Dionys%20COA.svg |
| Raseinių rajono savivaldybė | Kauno apskritis | 12 | 735 | http://www.wikidata.org/entity/Q2069355 | http://commons.wikimedia.org/wiki/Special:FilePath/Raseiniai%20COA.svg |
| Raseinių rajono savivaldybė | Kauno apskritis | 12 | 735 | http://www.wikidata.org/entity/Q2069355 | http://commons.wikimedia.org/wiki/Special:FilePath/Raseiniu%20tvankinys%202010.jpg |
| Biržų rajono savivaldybė | Panevėžio apskritis | 8 | 712 | http://www.wikidata.org/entity/Q763504 | http://commons.wikimedia.org/wiki/Special:FilePath/Bir%C5%BEai%20COA.svg |


## Teritorinė grandinė

**Į kokį klausimą atsako:** kur tiksliai yra gatvė — kokioje vietovėje, savivaldybėje ir apskrityje?

**Kaip veikia:** pradedama nuo gatvių (`dct:Location` klasės objektų `streets` rinkinyje) ir `dct:isPartOf` ryšiais lipama aukštyn per administracinę hierarchiją: gatvė → gyvenamoji vietovė → (galbūt seniūnija) → savivaldybė → apskritis. Kiekvienas šuolis kerta atskirą named graph'ą — būtent tam naudojamas `<urn:x-arq:UnionGraph>`. Pavyzdžiui atrinktos tik Vilniaus miesto gatvės; pakeitus filtrą veiktų bet kuriai savivaldybei.

```sparql
# Cross-domain: streets × admin-units (settlements, elderships, municipalities,
# counties) — the full territorial chain for a sample of Vilnius streets,
# walking dct:isPartOf across four entity graphs.
PREFIX cv:       <http://data.europa.eu/m8g/>
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
PREFIX atu-type: <http://publications.europa.eu/resource/authority/atu-type/>

SELECT ?street ?settlement ?municipality ?county
WHERE
{
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?st a dct:Location ;
            skos:prefLabel ?street ;
            dct:isPartOf ?s .
        ?s skos:prefLabel ?settlement ;
            dct:isPartOf ?p .
        OPTIONAL { ?p cv:level atu-type:LTU_SEN ; dct:isPartOf ?pm }
        BIND(COALESCE(?pm, ?p) AS ?m)
        ?m skos:prefLabel ?municipality ;
            dct:isPartOf/skos:prefLabel ?county .
        FILTER(CONTAINS(STR(?municipality), "Vilniaus miesto"))
    }
}
LIMIT 15
```

Rezultatai:

| street | settlement | municipality | county |
|---|---|---|---|
| Karolio Sipavičiaus g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Skydo g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Merkinės g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Rudnios g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Žiedų g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Nendrių g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Medeinos g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Stefanijos Ladigienės g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Brastos g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Andriaus Vasilos g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Juodvarnių Sodų 1-oji g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Amatų g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Šermukšnių g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Pagirio g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |
| Taboro g. | Vilnius | Vilniaus miesto savivaldybė | Vilniaus apskritis |


## Seimo narių frakcijos

**Į kokį klausimą atsako:** kas šiuo metu priklauso kuriai Seimo frakcijai, kuri partija juos iškėlė ir kaip jie atrodo?

**Kaip veikia:** narystės modeliuojamos kaip atskiri `org:Membership` objektai su galiojimo intervalais, todėl „dabartinė” narystė = narystė, kurios intervalas neturi pabaigos datos (`FILTER NOT EXISTS { ... time:hasEnd ... }`). Iš tokių narysčių atrenkamos tos, kurių organizacija yra frakcija (pagal `org-unit-types` taksonomijos konceptą). Prie kiekvieno nario pridedama: iškėlusi partija (`ltlod:nominatedBy` ryšys į `parties` rinkinį), Wikidata QID (iš `alignments.trig`) ir nuotrauka — oficialus lrs.lt portretas iš `photos.trig` ir/arba Wikidata nuotrauka, todėl kai kurie nariai lentelėje matomi du kartus su skirtingomis nuotraukomis.

```sparql
# Cross-domain: seimas persons × org-units × parties × taxonomies × alignments.
# Current faction composition: members whose faction membership has no end
# date, with their nominating party, Wikidata QID and photo (official lrs.lt
# portrait from photos.trig and/or Wikidata P18 from alignments.trig).
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
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?org ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }

        ?org dct:type <https://linkeddata.lt/taxonomies/org-unit-types/frakcija/#this> ;
            skos:prefLabel ?faction .
        ?person foaf:name ?member .
        OPTIONAL { ?person ltlod:nominatedBy/skos:prefLabel ?party }
        OPTIONAL { ?person owl:sameAs ?wikidata }
        OPTIONAL { ?person foaf:depiction ?photo }
    }
}
ORDER BY ?faction ?member
LIMIT 25
```

Rezultatai:

| faction | member | party | wikidata | photo |
|---|---|---|---|---|
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Jakavičiutė-Miliauskienė | Demokratų sąjunga „Vardan Lietuvos“ |  | https://www.lrs.lt/SIPIS/sn_foto/2024/agne_jakaviciute_miliauskiene.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Širinskienė | Politinė partija „Nemuno Aušra“ | http://www.wikidata.org/entity/Q28933945 | http://commons.wikimedia.org/wiki/Special:FilePath/Agne%20Sirinskiene%20by%20Augustas%20D… |
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Širinskienė | Politinė partija „Nemuno Aušra“ | http://www.wikidata.org/entity/Q28933945 | https://www.lrs.lt/SIPIS/sn_foto/2024/agne_sirinskiene.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Algirdas Butkevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q394006 | http://commons.wikimedia.org/wiki/Special:FilePath/Algirdas%20Butkevi%C4%8Dius%202015.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Algirdas Butkevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q394006 | https://www.lrs.lt/SIPIS/sn_foto/2024/algirdas_butkevicius.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Dainius Varnas | Politinė partija „Nemuno Aušra“ | http://www.wikidata.org/entity/Q130712526 | https://www.lrs.lt/SIPIS/sn_foto/2024/dainius_varnas.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Domas Griškevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q123688288 | http://commons.wikimedia.org/wiki/Special:FilePath/Domas%20Gri%C5%A1kevi%C4%8Dius.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Domas Griškevičius | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q123688288 | https://www.lrs.lt/SIPIS/sn_foto/2024/domas_griskevicius.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Jekaterina Rojaka | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q60627846 | http://commons.wikimedia.org/wiki/Special:FilePath/Jekaterina%20Rojaka%20by%20Augustas%20… |
| Demokratų frakcija „Vardan Lietuvos“ | Jekaterina Rojaka | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q60627846 | https://www.lrs.lt/SIPIS/sn_foto/2024/jekaterina_rojaka.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Kęstutis Mažeika | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q28371741 | https://www.lrs.lt/SIPIS/sn_foto/2024/kestutis_mazeika.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Linas Kukuraitis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27977694 | http://commons.wikimedia.org/wiki/Special:FilePath/Linas%20Kukuraitis%20by%20Augustas%20D… |
| Demokratų frakcija „Vardan Lietuvos“ | Linas Kukuraitis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27977694 | https://www.lrs.lt/SIPIS/sn_foto/2024/linas_kukuraitis.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Lukas Savickas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q102735741 | http://commons.wikimedia.org/wiki/Special:FilePath/Lukas%20Savickas.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Lukas Savickas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q102735741 | https://www.lrs.lt/SIPIS/sn_foto/2024/lukas_savickas.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Rima Baškienė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q541371 | http://commons.wikimedia.org/wiki/Special:FilePath/Rima%20Baskiene%20by%20Augustas%20Didz… |
| Demokratų frakcija „Vardan Lietuvos“ | Rima Baškienė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q541371 | https://www.lrs.lt/SIPIS/sn_foto/2024/rima_baskiene.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Rūta Miliūtė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27652365 | http://commons.wikimedia.org/wiki/Special:FilePath/Ruta%20Miliute%20by%20Augustas%20Didzg… |
| Demokratų frakcija „Vardan Lietuvos“ | Rūta Miliūtė | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q27652365 | https://www.lrs.lt/SIPIS/sn_foto/2024/ruta_miliute.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Tomas Tomilinas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q28376223 | http://commons.wikimedia.org/wiki/Special:FilePath/Tomas%20Tomilinas%20by%20Augustas%20Di… |
| Demokratų frakcija „Vardan Lietuvos“ | Tomas Tomilinas | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q28376223 | https://www.lrs.lt/SIPIS/sn_foto/2024/tomas_tomilinas.jpg |
| Demokratų frakcija „Vardan Lietuvos“ | Zigmantas Balčytis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q117150 | http://commons.wikimedia.org/wiki/Special:FilePath/Zigmantas%20Balcytis%20by%20Augustas%2… |
| Demokratų frakcija „Vardan Lietuvos“ | Zigmantas Balčytis | Demokratų sąjunga „Vardan Lietuvos“ | http://www.wikidata.org/entity/Q117150 | https://www.lrs.lt/SIPIS/sn_foto/2024/zigmantas_balcytis.jpg |
| Liberalų sąjūdžio frakcija | Andrius Bagdonas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q12648381 | http://commons.wikimedia.org/wiki/Special:FilePath/Andrius%20Bagdonas%20by%20Augustas%20D… |
| Liberalų sąjūdžio frakcija | Andrius Bagdonas | Liberalų sąjūdis | http://www.wikidata.org/entity/Q12648381 | https://www.lrs.lt/SIPIS/sn_foto/2024/andrius_bagdonas.jpg |


## Komitetų ir komisijų pirmininkai

**Į kokį klausimą atsako:** kas šiuo metu vadovauja Seimo komitetams, komisijoms ir frakcijoms ir nuo kada?

**Kaip veikia:** vėl naudojamas „narystė be pabaigos datos” požymis, bet šįkart filtruojama pagal pareigų konceptą iš `position-types` taksonomijos: imamos pareigos, kurių lietuviška etiketė turi „pirminink” arba „seniūn” (frakcijų vadovai vadinami seniūnais), atmetant pavaduotojus. Pradžios data paimama iš narystės galiojimo intervalo (`time:hasBeginning`). Atkreipkite dėmesį, kad pareigų konceptai išlaiko šaltinio giminines formas („pirmininkas”/„pirmininkė”).

```sparql
# Cross-domain: seimas persons × org-units × position-types taxonomy.
# Who currently chairs Seimas committees, commissions and factions — role
# concepts are matched by their Lithuanian label ("pirmininkas"/"seniūnas").
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX org:  <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX time: <http://www.w3.org/2006/time#>

SELECT ?unit ?chair ?role ?since
WHERE
{
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?org ;
            org:role ?roleConcept ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }
        OPTIONAL { ?interval time:hasBeginning/time:inXSDDate ?since }

        ?roleConcept skos:prefLabel ?role .
        FILTER(LANG(?role) = "lt" &&
               (CONTAINS(LCASE(STR(?role)), "pirminink") || CONTAINS(LCASE(STR(?role)), "seniūn")))
        FILTER(!CONTAINS(LCASE(STR(?role)), "pavaduotoj"))   # skip deputies

        ?org skos:prefLabel ?unit .
        ?person foaf:name ?chair .
    }
}
ORDER BY ?unit
```

Rezultatai:

| unit | chair | role | since |
|---|---|---|---|
| Antikorupcijos komisija | Arvydas Anušauskas | Komisijos pirmininkas | 2024-12-05 |
| Aplinkos apsaugos komitetas | Linas Jonauskas | Komiteto pirmininkas | 2024-11-21 |
| Asmenų su negalia teisių komisija | Indrė Kižienė | Komisijos pirmininkė | 2025-04-10 |
| Ateities komitetas | Vytautas Grubliauskas | Komiteto pirmininkas | 2024-11-21 |
| Audito komitetas | Artūras Zuokas | Komiteto pirmininkas | 2026-07-15 |
| Biudžeto ir finansų komitetas | Algirdas Sysas | Komiteto pirmininkas | 2024-11-21 |
| Demokratų frakcija „Vardan Lietuvos“ | Agnė Širinskienė | Frakcijos seniūnė | 2026-07-14 |
| Ekonomikos ir inovacijų komitetas | Jekaterina Rojaka | Komiteto pirmininkė | 2026-07-07 |
| Ekonomikos komitetas | Jekaterina Rojaka | Komiteto pirmininkė | 2026-07-07 |
| Energetikos ir darnios plėtros komitetas | Algirdas Butkevičius | Komiteto pirmininkas | 2026-07-07 |
| Etikos ir procedūrų komisija | Viktoras Fiodorovas | Komisijos pirmininkas | 2025-11-14 |
| Europos reikalų komitetas | Rasa Budbergytė | Komiteto pirmininkė | 2024-11-21 |
| Jaunimo ir sporto reikalų komisija | Algimantas Radvila | Komisijos pirmininkas | 2026-07-15 |
| Jūrinių reikalų komisija | Alvydas Mockus | Komisijos pirmininkas | 2025-11-20 |
| Kaimo reikalų komitetas | Bronis Ropė | Komiteto pirmininkas | 2025-10-15 |
| Kriminalinės žvalgybos parlamentinės kontrolės komisija | Dainius Gaižauskas | Komisijos pirmininkas | 2025-11-11 |
| Kultūros komitetas | Kęstutis Vilkauskas | Komiteto pirmininkas | 2024-11-21 |
| Laikinoji Bendradarbiavimo su Lietuvos jaunimo organizacijų taryba grupė | Tomas Martinaitis | Pirmininkas | 2025-03-20 |
| Laikinoji Dzūkijos bičiulių grupė | Jurgita Šukevičienė | Pirmininkė | 2024-11-21 |
| Laikinoji Kauno krašto grupė | Robertas Kaunas | Pirmininkas | 2024-11-21 |
| Laikinoji Klaipėdos krašto bičiulių grupė | Ligita Girskienė | Pirmininkė | 2025-05-13 |
| Laikinoji Kultūros asamblėjos draugų grupė | Vytautas Juozapaitis | Pirmininkas | 2025-12-15 |
| Laikinoji Lietuvos kariuomenės ir Lietuvos šaulių sąjungos draugų grupė | Audrius Radvilavičius | Pirmininkas | 2025-03-28 |
| Laikinoji Maldos grupė | Valdas Rakutis | Pirmininkas | 2025-10-16 |
| Laikinoji Moterų grupė | Agnė Bilotaitė | Pirmininkė | 2024-12-12 |
| Laikinoji Neringos bičiulių grupė | Andrius Bagdonas | Pirmininkas | 2024-12-03 |
| Laikinoji Panevėžio krašto bičiulių grupė | Modesta Petrauskaitė | Pirmininkė | 2024-12-03 |
| Laikinoji Seimo ir akademinės bendruomenės bendradarbiavimo grupė | Vilija Targamadzė | Pirmininkė | 2026-06-18 |
| Laikinoji Seimo narių grupė Lietuvos Respublikos Konstitucinio Teismo įstatymui tobulinti | Audronius Ažubalis | Pirmininkas | 2025-09-16 |
| Laikinoji Seimo narių ryšių su Ekonominio bendradarbiavimo ir plėtros organizacija (EBPO)… | Giedrė Balčytytė | Pirmininkė | 2024-11-21 |
| … | &nbsp; |&nbsp; |&nbsp; |


## Įstaigos pagal teisinę formą ir statusą

**Į kokį klausimą atsako:** kiek valstybės ir savivaldybių biudžetinių įstaigų yra registruota, kokios jų teisinės formos ir kiek jų jau išregistruota ar reorganizuojama?

**Kaip veikia:** iš `legal-entities` rinkinio imami visi `rov:RegisteredOrganization` objektai ir per `rov:companyType` bei `rov:orgStatus` ryšius pasiekiamos jų formų ir statusų etiketės — tai SKOS konceptai, sugeneruoti tiesiai iš JAR klasifikatorių (`taxonomies/legal-forms`, `taxonomies/legal-statuses`). Rezultatas grupuojamas ir skaičiuojamas. Lentelėje matyti įdomi detalė: senosios formos „Valstybės biudžetinė įstaiga” (580) ir „Savivaldybės biudžetinė įst.” (680) yra vien istorinės — visos tokios įstaigos išregistruotos, o veikiančios dabar registruojamos bendra forma „Biudžetinė įstaiga” (950).

```sparql
# Cross-domain: legal-entities × taxonomies (JAR classifiers).
# Registered vs dissolved budget institutions per legal form and status.
PREFIX rov:    <http://www.w3.org/ns/regorg#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <https://schema.org/>

SELECT ?legalForm ?status (COUNT(DISTINCT ?e) AS ?entities)
WHERE
{
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?e a rov:RegisteredOrganization ;
            rov:companyType/skos:prefLabel ?legalForm ;
            rov:orgStatus/skos:prefLabel ?status .
        FILTER(LANG(?legalForm) = "lt" && LANG(?status) = "en")
    }
}
GROUP BY ?legalForm ?status
ORDER BY DESC(?entities)
LIMIT 20
```

Rezultatai:

| legalForm | status | entities |
|---|---|---|
| Biudžetinė įstaiga | No legal proceedings | 2536 |
| Biudžetinė įstaiga | Removed | 1507 |
| Savivaldybės biudžetinė įst. | Removed | 1431 |
| Valstybės biudžetinė įstaiga | Removed | 520 |
| Biudžetinė įstaiga | Under Reorganization | 24 |
| Biudžetinė įstaiga | Participating in Reorganization | 6 |
| Biudžetinė įstaiga | Under Reformation | 1 |


## Wikidata susiejimų aprėptis

**Į kokį klausimą atsako:** kokia dalis mūsų duomenų jau susieta su Wikidata ir kiek objektų turi atvaizdus?

**Kaip veikia:** pereinama per visus dokumentus (kiekvienas named graph'as per `foaf:primaryTopic` nurodo savo pagrindinį objektą), objektai sugrupuojami pagal RDF klasę ir suskaičiuojama, kiek jų turi `owl:sameAs` nuorodą į Wikidata ir kiek — `foaf:depiction` atvaizdą (herbą ar nuotrauką). Tai savotiška kokybės suvestinė: matyti, kad susieti visi Seimo nariai turi nuotraukas (148/148), administracinių vienetų susieta 642, o gatvės ir įstaigos su Wikidata dar nesiejamos.

```sparql
# Cross-domain: everything × alignments — Wikidata reconciliation and image
# coverage per RDF class across all datasets.
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT ?type (COUNT(DISTINCT ?e) AS ?entities)
       (COUNT(DISTINCT ?aligned) AS ?withWikidata)
       (COUNT(DISTINCT ?depicted) AS ?withImage)
WHERE
{
    GRAPH ?g { ?g foaf:primaryTopic ?e }
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?e a ?type .
        OPTIONAL { ?e owl:sameAs ?qid . BIND(?e AS ?aligned) }
        OPTIONAL { ?e foaf:depiction ?img . BIND(?e AS ?depicted) }
    }
}
GROUP BY ?type
ORDER BY DESC(?entities)
```

Rezultatai:

| type | entities | withWikidata | withImage |
|---|---|---|---|
| http://purl.org/dc/terms/Location | 61149 | 0 | 0 |
| http://data.europa.eu/m8g/AdminUnit | 26883 | 642 | 456 |
| http://www.w3.org/ns/org#FormalOrganization | 6037 | 0 | 0 |
| http://www.w3.org/ns/regorg#RegisteredOrganization | 6025 | 0 | 0 |
| http://www.w3.org/2004/02/skos/core#Concept | 257 | 0 | 0 |
| http://xmlns.com/foaf/0.1/Person | 148 | 101 | 148 |
| http://www.w3.org/ns/org#OrganizationalUnit | 136 | 0 | 0 |
| http://www.w3.org/2004/02/skos/core#ConceptScheme | 7 | 0 | 0 |


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
    GRAPH <urn:x-arq:UnionGraph>
    {
        ?membership a org:Membership ;
            org:member ?person ;
            org:organization ?faction ;
            org:role ?role ;
            org:memberDuring ?interval .
        FILTER NOT EXISTS { ?interval time:hasEnd ?end }

        ?role skos:prefLabel ?roleLabel .
        FILTER(LANG(?roleLabel) = "lt" && STRSTARTS(STR(?roleLabel), "Frakcijos seniūn"))
        FILTER(!CONTAINS(STR(?roleLabel), "pavaduotoj"))

        ?faction skos:prefLabel ?factionName .
        ?person foaf:name ?name .
        OPTIONAL { ?person foaf:depiction ?photo . FILTER(CONTAINS(STR(?photo), "lrs.lt")) }
        OPTIONAL { ?person owl:sameAs ?qid }
    }
}
```

Rezultatai:

| subjektas (S) | predikatas (P) | objektas (O) |
|---|---|---|
| <https://linkeddata.lt/org-units/1022/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/1022/#this> | <https://schema.org/name> | "Tėvynės sąjungos-Lietuvos krikščionių demokratų frakcija"@lt |
| <https://linkeddata.lt/org-units/1070/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/1070/#this> | <https://schema.org/name> | "Lietuvos valstiečių, žaliųjų ir Krikščioniškų šeimų sąjungos frakcija"@lt |
| <https://linkeddata.lt/org-units/1322/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/1322/#this> | <https://schema.org/name> | "Demokratų frakcija „Vardan Lietuvos“"@lt |
| <https://linkeddata.lt/org-units/1430/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/1430/#this> | <https://schema.org/name> | "„Nemuno aušros“ frakcija"@lt |
| <https://linkeddata.lt/org-units/47/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/47/#this> | <https://schema.org/name> | "Mišri Seimo narių grupė"@lt |
| <https://linkeddata.lt/org-units/793/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/793/#this> | <https://schema.org/name> | "Lietuvos socialdemokratų partijos frakcija"@lt |
| <https://linkeddata.lt/org-units/870/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Organization> |
| <https://linkeddata.lt/org-units/870/#this> | <https://schema.org/name> | "Liberalų sąjūdžio frakcija"@lt |
| <https://linkeddata.lt/persons/12253/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/12253/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/jaroslav_narkevic.jpg> |
| <https://linkeddata.lt/persons/12253/#this> | <https://schema.org/memberOf> | <https://linkeddata.lt/org-units/1070/#this> |
| <https://linkeddata.lt/persons/12253/#this> | <https://schema.org/name> | "Jaroslav Narkevič" |
| <https://linkeddata.lt/persons/15266/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/orinta_leipute.jpg> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/memberOf> | <https://linkeddata.lt/org-units/793/#this> |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/name> | "Orinta Leiputė" |
| <https://linkeddata.lt/persons/15266/#this> | <https://schema.org/sameAs> | <http://www.wikidata.org/entity/Q1750302> |
| <https://linkeddata.lt/persons/64701/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/laurynas_kasciunas.jpg> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/memberOf> | <https://linkeddata.lt/org-units/1022/#this> |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/name> | "Laurynas Kasčiūnas" |
| <https://linkeddata.lt/persons/64701/#this> | <https://schema.org/sameAs> | <http://www.wikidata.org/entity/Q28735068> |
| <https://linkeddata.lt/persons/65703/#this> | <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> | <https://schema.org/Person> |
| <https://linkeddata.lt/persons/65703/#this> | <https://schema.org/image> | <https://www.lrs.lt/SIPIS/sn_foto/2024/remigijus_zemaitaitis.jpg> |
| … | &nbsp; |&nbsp; |
