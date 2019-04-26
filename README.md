LTLOD projektą sukūrėme prieš daugiau nei 5 metus. Deja, nei Linked Open Data, nei Open Data situacija apskritai per tą laiką iš esmės nepagerėjo. Užbuksavome ties [3 žvaigždute](https://5stardata.info/en/).

Žiūrint atgal, mūsų Linked Data [specifikacijos](../../wiki) greičiausiai buvo per daug techniškos ir nieko nesakančios žmonėms, nesusipažinusiems su RDF standartais.
Dabar norime šią klaidą ištaisyti ir palaipsniui išaiškinti, kaip RDF ir Linked Data yra sukuriami, naudojami ir kaip sukuria vertę.

# Grafo duomenų modelis

Su duomenimis dirbantys programuotojai, mokslininkai ir t.t. dažniausiai yra susipažinę su reliaciniu duomenų modeliu, kitaip sakant, lentelėmis. Pavyzdžiui:

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Vardas</th>
            <th>Mokykla</th>
            <th>Klasė</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td>
            <td>Petriukas</td>
            <td>Fabijoniškių</td>
            <td>3B</td>
        </tr>
        <tr>
            <td>2</td>
            <td>Marytė</td>
            <td>Stanevičiaus</td>
            <td>2C</td>
        </tr>
    </tbody>
</table>

Bet kuri lentelė gali būti atvaizduota grafo pavidalu:

![Lentelė grafo pavidalu](../../raw/master/lentele.png)

`ID1`, `ID2` ir t.t. unikaliai identifikuoja kiekvieną įrašą.

## Entity-Attribute-Value

Dabar tokią grafo struktūrą galima užrašyti kaip lentelę, bet kita forma:

<table>
    <thead>
        <tr>
            <th>Įrašas</th>
            <th>Savybė</th>
            <th>Reikšmė</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>ID1</td>
            <td>ID</td>
            <td>1</td>
        </tr>
        <tr>
            <td>ID1</td>
            <td>Vardas</td>
            <td>Petriukas</td>
        </tr>
        <tr>
            <td>ID1</td>
            <td>Mokykla</td>
            <td>Fabijoniškių</td>
        </tr>
        <tr>
            <td>ID1</td>
            <td>Klasė</td>
            <td>3B</td>
        </tr>
        <tr>
            <td>ID2</td>
            <td>ID</td>
            <td>2</td>
        </tr>
        <tr>
            <td>ID2</td>
            <td>Marytė</td>
            <td>Vardas</td>
        </tr>
        <tr>
            <td>ID2</td>
            <td>Mokykla</td>
            <td>Stanevičiaus</td>
        </tr>
        <tr>
            <td>ID2</td>
            <td>Klasė</td>
            <td>2C</td>
        </tr>
    </tbody>
</table>

Gavome ne ką kitą, kaip [Entity-Atttribute-Value](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model) duomenų modelį. 

EAV "ištraukia" kiekvieną stulpelio/reikšmės sąryšį iš mūsų pradinės reliacinės lentelės ir pateikia jį kaip atskirą įrašą. Dėl to ši EAV lentelė turi 8 eilutes: 2 eilutės * 4 stulpeliai pradinėjė lentelėje lygu 8.

_Nepaisant to, kiek stulpelių yra reliacinėje lentelėje, ją visada galima transformuoti į grafo pavidalą bei EAV lentelę su 3 stulpeliais._ Tai tiesiog skirtingi to pačio duomenų rinkinio pavidalai.

# RDF duomenų modelis

[RDF (Resource Description Framework)](https://www.w3.org/TR/rdf11-primer/) yra W3C specifikacija, kuri standartizuoja grafo/EAV pavidalo duomenis ir pritaiko juos publikavimui internete.

Vietoje Entity-Attribute-Value, RDF modelyje ta pati 3 stulpelių lentelė vadinama Subject-Property-Object. Kiekvienas jos įrašas yra vadinamas "[triple](https://www.w3.org/TR/rdf11-primer/section-triple)".

Vienas kertinių RDF "akmenų" yra globalūs URI identifikatoriai. Jie leidžia vienareikšmiškai identifikuoti resursus pasaulinio interneto mastu.
Palyginimui, reliacinėse DB identifikatoriai (paprastai ID stulpelių reikšmės) yra lokalios toms duomenų bazėms ir neturi prasmės globaliame kontekste.

URI naudojami ne tik įrašams, bet ir savybėms (properties) bei tipams (classes) identifikuoti. Dėl to RDF savybės gali būti lengvai perpanaudojamos skirtinguose duomenų rinkiniuose.

Dabar galime patobulinti mūsų EAV pavyzdį, paversdami įrašų ID bei savybes į atitinkamus URI, panaudodami `https://atviras.vilnius.lt/mokiniai/` adresą kaip pagrindą (tuo pačiu savybes pervadinsime angliškai):

<table>
    <thead>
        <tr>
            <th>Subject</th>
            <th>Property</th>
            <th>Object</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/1</td>
            <td>https://atviras.vilnius.lt/mokiniai/id</td>
            <td>1</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/1</td>
            <td>https://atviras.vilnius.lt/mokiniai/name</td>
            <td>Petriukas</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/1</td>
            <td>https://atviras.vilnius.lt/mokiniai/school</td>
            <td>Fabijoniškių</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/1</td>
            <td>https://atviras.vilnius.lt/mokiniai/class</td>
            <td>3B</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/2</td>
            <td>https://atviras.vilnius.lt/mokiniai/id</td>
            <td>2</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/2</td>
            <td>https://atviras.vilnius.lt/mokiniai/name</td>
            <td>Marytė</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/2</td>
            <td>https://atviras.vilnius.lt/mokiniai/school</td>
            <td>Stanevičiaus</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/2</td>
            <td>https://atviras.vilnius.lt/mokiniai/class</td>
            <td>2C</td>
        </tr>
    </tbody>
</table>

Turėdami tokią struktūrą, galime lengvai pridėti naujus ryšius į mūsų grafą. Pavyzdžiui, draugystės ryšius:

<table>
    <thead>
        <tr>
            <th>Subject</th>
            <th>Property</th>
            <th>Object</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>https://atviras.vilnius.lt/mokiniai/id/1</td>
            <td>https://atviras.vilnius.lt/mokiniai/friendsWith</td>
            <td>https://atviras.vilnius.lt/mokiniai/id/2</td>
        </tr>
    </tbody>
</table>

Tokie ryšiai reikalautų papildomų lentelių reliacinėje DB. Reliacinio modelio schemos nelankstumas yra vienas didžiausių minusų, palyginus su RDF duomenų bazėmis ([triplestores](https://en.wikipedia.org/wiki/Triplestore)), kuriuose schema nėra būtina.

_Dėl stabilios Subject-Property-Object struktūros, fiziniame lygmenyje RDF duomenų rinkiniai integruojami juos tiesiog sujungiant, kas nieko nekainuoja._ Su reliacinėmis lentelėmis tai tiesiog neįmanoma.

_RDF yra (kryptinio) grafo duomenų modelis, o ne duomenų formatas_. RDF gali būti užrašytas skirtingais formatais naudojant [skirtingas sintakses](https://www.w3.org/TR/rdf11-primer/#section-graph-syntax): plain-text ([Turtle](https://www.w3.org/TR/turtle/)), XML ([RDF/XML](https://www.w3.org/TR/rdf-syntax-grammar/)), JSON ([JSON-LD](https://www.w3.org/TR/json-ld11/)) ir t.t. RDF bibliotekos dažniausiai palaiko daugumą standartinių RDF sintaksių.

# Linked (Open) Data

[Linked Data (LD)](https://en.wikipedia.org/wiki/Linked_data), arba Linked Open Data (LOD), priklausomai nuo duomenų atvirumo, yra RDF duomenų publikavimo internete metodas.

Principas labai paprastas: HTTP protokolu iškvietę bet kurį URI, panaudotą RDF rinkinyje, turėtume gauti triples apie tuo URI identifikuotą objektą. Pavyzdžiui, užklauskime Linked Data serverio duomenų apie Petriuką tekstiniu RDF formatu Turtle:

    GET https://atviras.vilnius.lt/mokiniai/id/1
    Accept: text/turtle

    200 OK
    Content-Type: text/turtle

    @prefix mok: <https://atviras.vilnius.lt/mokiniai/> .

    <https://atviras.vilnius.lt/mokiniai/id/1> mok:id 1 ;
        mok:name "Petriukas" ;
        mok:school "Fabijoniškių" ;
        mok:class "3B" ;
        mok:friendsWith <https://atviras.vilnius.lt/mokiniai/id/2> .

Gauname serverio atsaką su struktūrizuotais machine-readable duomenimis apie konkretų mus dominantį objektą, šiuo atveju mokinį.

Linked Data metodo galia atsiskleidžia, kai RDF duomenyse naudojamos ne ID ar pavadinimų reikšmės, identifikuojančios susijusius objektus, bet tiesioginė nuoroda į to objekto URI.
Pavyzdžiui, vietoje `"Fabijoniškių"` kaip tekstinės reikšmės mokyklai identifikuoti, suteikime mokykloms savus URI adresus, pvz. naudojant jų kodus: `https://atviras.vilnius.lt/mokyklos/190003851`.

Patobulintas Linked Data atsakas atrodo taip:

    @prefix mok: <https://atviras.vilnius.lt/mokiniai/> .

    <https://atviras.vilnius.lt/mokiniai/id/1> mok:id 1 ;
        mok:name "Petriukas" ;
        mok:school <https://atviras.vilnius.lt/mokyklos/190003851> ;
        mok:class "3B" ;
        mok:friendsWith <https://atviras.vilnius.lt/mokiniai/id/2> .

Dabar programinė įranga gali naviguoti URI adresais ir užklausti serverio dominančių objektų duomenų, lygiai kaip mes naviguojame interneto puslapius naudodami nuorodas.

Galutinis RDF grafas atrodo taip:

![RDF grafas](../../raw/master/mokiniai.png)

## SPARQL

[SPARQL](https://www.w3.org/TR/sparql11-overview/) yra RDF užklausų kalba. Analogiškai, kaip SQL yra RDBMS užklausų kalba, tik SPARQL specifikacija žymiai trumpesnė už SQL. Dauguma RDF triplestores palaiko SPARQL 1.1 ir neišradinėja savo dialektų, dėl to užklausos labai portabilios.

Turėdami mūsų pavyzdinį RDF duomenų rinkinį, galėtume suformuluoti užklausą, kuri atsakytų, kokių mokyklų mokiniai turi daugiausiai draugų:

```sparql
PREFIX mok: <https://atviras.vilnius.lt/mokiniai/>

SELECT ?school (COUNT(?friend) AS ?friendCount)
{
    ?person mok:friendsWith ?friend ;
        mok:school ?school .
}
GROUP BY ?school
ORDER BY DESC(?friendCount)
```

# Knowledge Graph nauda

Pastaruoju metu Linked Data marketingistų vadinama _Knowledge Graph_, tai nuo šiol vadinkime ir mes taip. (Ar reikėtų rašyti _Žinių grafas_?)

Kam Knowledge Graphs naudojami? Kokia iš jų nauda (atviriesiems duomenims)?

Ne paslaptis, kad atvirieji duomenis turi būti lengvai integruojami ir perpanaudojami. _RDF Knowledge Graph yra vienintelis standartizuotas metodas, leidžiantis sujungti atskirus duomenų rinkinius į vientisą, potencialiai beribį sluoksnį._ Neišradinėkime dviračio, jis jau išrastas. Bet kokios lokalaus ar nacionalinio masto specifikacijos, portalai ar manifestai, ignoruojantys RDF ir Knowledge Graphs, bus tik pinigų ir laiko švaistymas.

Kam mums vientisas sluoksnis? Kad naudotumėme resursus išmintingai, sluoksniuodami vienas pastangas ant kitų, naudodami vienų darbo vaisius kaip pagrindą kitiems darbams. Duomenų rinkinio vertė auga [proporcingai ryšių jame skaičiui](https://en.wikipedia.org/wiki/Network_effect).

Tai nėra tik mūsų išmislas. Galbūt įtikinti padės autoritetingi leidiniai:
* Financial Times. [Governments fail to capitalise on swaths of open data](https://www.ft.com/content/f8e9c2ea-b29b-11e8-87e0-d84e0d934341)
* Forbes. [Is The Enterprise Knowledge Graph Finally Going To Make All Data Usable?](https://www.forbes.com/sites/danwoods/2018/09/19/is-the-enterprise-knowledge-graph-going-to-finally-make-all-data-usable/)

> The knowledge graph is the only currently implementable and sustainable way for businesses to move to the higher level of integration needed to make data truly useful for a business.

## Pritaikymo pavyzdys

Tarkime, norime sudaryti Vilniaus mokiniams naują pietų racioną. Nesvarbu, ar tai idėja hakatone, ar komercinis projektas įmonėje. Mums reikia mokinių ir mokyklų sąrašo patiekalų meniu sudarymui (kalorijų apskaičiavimams ar pan.) Turime 2 įgyvendinimo variantus:
1. parsisiųsti mokinių ir mokyklų CSV, sukišti į savo reliacinę DB ar kitokias duomenų struktūras, atlikti skaičiavimus. Galbūt papublikuoti rezultatus kaip CSV.
2. paversti savo duomenis į RDF, naudojant `atviras.vilnius.lt` URI ryšiams su mokyklomis ir mokiniais nurodyti

Pirmo varianto išdava: buvo 2 paskiri, tarpusavyje nesuintegruoti CSV failai, tapo 3.

Antro varianto išdava: lietuviškas Knowledge Graph pasitarnavo kaip pagrindas naujam RDF rinkiniui, ir to pasekoje išsipletė.

Skirtumą tikiuosi patys matote. Nenaudojant Knowledge Graph, su kiekvienu tokiu pavyzdžiu parandama vis daugiau duomenų perpanaudojimo potencialo.

## Įgyvendinimas praktikoje

"Na gerai, tai darykim lietuvišką Knowledge Graph!", jau galvojate tikriausiai. Bet kaip?! Ar tai nereikalauja kosminių semantinių technologijų su nesuvokiamais pavadinimais kaip "ontologija" ar "taksonomija"? Ar nesvietiškai brangios programinės įrangos ir panašiai?

Viskas yra žymiai paprasčiau. Turint duomenis CSV formatu, tereikia vienos SPARQL užklausos, kuri transformuos visą CSV rinkinį į RDF grafą. Turint XML duomenis, analogiškai gali būti pritaikytos [XSLT transformacijos](https://www.w3.org/TR/xslt/all/) konvertavimui į RDF/XML formatą.

Pavyzdžiui panaudokime realius Vilniaus savivaldybės duomenis: CSV su duomenimis apie [mokinius](https://github.com/vilnius/mokyklos/raw/master/Mokiniai.csv) ir [mokyklas](https://github.com/vilnius/mokyklos/raw/master/data/Mokyklu_sarasas.csv). Taipogi panaudosim tuos pačius URI adresus iš aukščiau pateiktų pavyzdžių, kombinuojant "savadarbius" `mok:` terminus su [schema.org](https://schema.org) savybėmis (interneto paieškos varikliai, tokie kaip Google ir Bing, [indeksuoja struktūrizuotus duomenis su schema.org terminais](https://developers.google.com/search/docs/guides/intro-structured-data)). Konvertavimą atliksime naudodami [CSV2RDF](https://github.com/AtomGraph/CSV2RDF) atviro kodo biblioteką.

### Mokiniai

Transformacijos (kai kur vadinama "mapping") užklausa:

```sparql
PREFIX mok:     <https://atviras.vilnius.lt/mokiniai/>
PREFIX schema:  <https://schema.org/>
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>

CONSTRUCT
{
    ?pupil a schema:Person ;
        mok:id ?id ;
        schema:identifier ?id ;
        schema:birthDate ?birth_date ; 
        mok:class ?class ;
        mok:school ?school ;
        schema:affiliation ?school .
}
WHERE
{
    ?pupil_row <#MokinioID> ?id ;
        <#GimimoData> ?birth_date_string ;
        <#KlasesPavadinimas> ?class ;
        <#IstaigosKodas> ?school_code .

    BIND(uri(concat(str(<mokiniai/>), encode_for_uri(?id))) AS ?pupil)
    BIND(xsd:date(?birth_date_string) AS ?birth_date)
    BIND(uri(concat(str(<mokyklos/>), encode_for_uri(?school_code))) AS ?school)
}
```

Paleidžiame CSV2RDF naudodami shell komandą, kuri paima CSV tiesiai iš GitHub ir transformuoja (šiuo atveju nurodome `tab` kaip reikšmių skirtuką, nes toks naudojamas `Mokiniai.csv` faile):

    curl -s https://raw.githubusercontent.com/vilnius/mokyklos/master/Mokiniai.csv -o Mokiniai.csv ; cat Mokiniai.csv | java -jar csv2rdf-1.0.0-SNAPSHOT-jar-with-dependencies.jar https://atviras.vilnius.lt/ Mokiniai.rq $'\t' > Mokiniai.nt    

Gauname 442310 triples [N-Triples](https://www.w3.org/TR/n-triples/) formatu. Vieną CSV eilutę atitinka 7 RDF triples (tiek, kiek suformavome užklausos `CONSTRUCT` dalyje):

    <https://atviras.vilnius.lt/mokiniai/9166267> <https://schema.org/affiliation> <https://atviras.vilnius.lt/mokyklos/190003666> .
    <https://atviras.vilnius.lt/mokiniai/9166267> <https://atviras.vilnius.lt/mokiniai/school> <https://atviras.vilnius.lt/mokyklos/190003666> .
    <https://atviras.vilnius.lt/mokiniai/9166267> <https://atviras.vilnius.lt/mokiniai/class> "8a" .
    <https://atviras.vilnius.lt/mokiniai/9166267> <https://schema.org/birthDate> "2002-06-06"^^<http://www.w3.org/2001/XMLSchema#date> .
    <https://atviras.vilnius.lt/mokiniai/9166267> <https://schema.org/identifier> "9166267" .
    <https://atviras.vilnius.lt/mokiniai/9166267> <https://atviras.vilnius.lt/mokiniai/id> "9166267" .
    <https://atviras.vilnius.lt/mokiniai/9166267> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://schema.org/Person> .

### Mokyklos

Transformacijos užklausa:

```sparql
PREFIX schema:     <https://schema.org/> 

CONSTRUCT
{
    ?school a schema:School ;
        schema:name ?name ;
        schema:identifier ?code ;
        schema:address ?address ;
        schema:telephone ?telephone ;
        a [ schema:name ?type ] ;
        schema:email ?email .
}
WHERE
{
    ?school_row <#name> ?name ;
        <#code> ?code ;
        <#address> ?address ;
        <#tel> ?telephone_string ;
        <#type> ?type ;
        <#email> ?email_string .

    BIND(uri(concat(str(<mokyklos/>), encode_for_uri(?code))) AS ?school)
    BIND(concat("+", ?telephone_string) AS ?telephone)
    BIND(uri(concat("mailto:", ?email_string)) AS ?email)
}
```

Komanda (reikšmių skirtukas `;`):

    curl -s https://raw.githubusercontent.com/vilnius/mokyklos/master/data/Mokyklu_sarasas.csv -o Mokyklu_sarasas.csv ; cat Mokyklu_sarasas.csv | java -jar csv2rdf-1.0.0-SNAPSHOT-jar-with-dependencies.jar https://atviras.vilnius.lt/ Mokyklu_sarasas.rq ';' > Mokyklu_sarasas.nt

Gauname 984 triples, arba po 8 triples iš kiekvienos CSV eilutės:

    <https://atviras.vilnius.lt/mokyklos/190003666> <https://schema.org/email> <mailto:rastine@ateities.vilnius.lm.lt> .
    <https://atviras.vilnius.lt/mokyklos/190003666> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> _:BX2D7b9d6c03X3A16833b6771fX3AX2D7ffd .
    <https://atviras.vilnius.lt/mokyklos/190003666> <https://schema.org/telephone> "+37052478447" .
    <https://atviras.vilnius.lt/mokyklos/190003666> <https://schema.org/address> "Vilniaus m. sav. Vilniaus m. S. Stanevičiaus g. 98" .
    <https://atviras.vilnius.lt/mokyklos/190003666> <https://schema.org/identifier> "190003666" .
    <https://atviras.vilnius.lt/mokyklos/190003666> <https://schema.org/name> "Vilniaus Ateities mokykla" .
    <https://atviras.vilnius.lt/mokyklos/190003666> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://schema.org/School> .
    _:BX2D7b9d6c03X3A16833b6771fX3AX2D7ffd <https://schema.org/name> "Pagrindinė mokykla" .

### Duomenų sujungimas

Mokyklų kodai - raktas ([foreign key](https://en.wikipedia.org/wiki/Foreign_key)) tarp lentelių `Mokiniai` (stulpelio `IstaigosKodas`) ir `Mokyklu_sarasas` (stulpelio `code`). Transformavimo užklausos pasirūpina, kad abejais atvejais iš mokyklų kodų (pvz. kaip `190003666`) būtų sugeneruojami vienodi URL, pvz. `https://atviras.vilnius.lt/mokyklos/190003666`. Tai mūsų sukurti globalūs Vilniaus mokyklų identifikatoriai.

Dabar tiesiog sumetame abu `Mokiniai.nt` ir `Mokyklu_sarasas.nt` į triplestore, tokią kaip Apache Jena [Fuseki](https://jena.apache.org/documentation/fuseki2/) ar [Dydra](https://dydra.com), ir viskas. _RDF magija įvyko._ Vientisame, bendrame Knowledge Graph'e turime 443293 triples, kitaip sakant ["datapoints"](https://en.wikipedia.org/wiki/Unit_of_observation), apie Vilniaus mokyklas ir mokinius. Tai atlikti ir tuo pačiu rašyti šį tekstą užtruko porą valandų.

Deja (?), neturime duomenų apie mokinių draugystės ryšius, dėl to nėra prasmės vykdyti SPARQL užklausą [iš pavyzdžio](#sparql). Tačiau galima gauti atsakymų į kitus klausimus. Pavyzdžiui, koks vidutinis mokinių amžius kiekvienoje mokykloje, surūšiuotas nuo didžiausio?

```sparql
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>
PREFIX schema:  <https://schema.org/> 

SELECT ?school (SAMPLE(?schoolName) AS ?schoolNameSample) (AVG(?age) / xsd:dayTimeDuration("P365D") AS ?avgAge)
{
    ?pupil schema:affiliation ?school ;
        schema:birthDate ?birthDate .
    ?school schema:name ?schoolName .
    BIND (xsd:date(NOW()) - ?birthDate AS ?age)
}
GROUP BY ?school
ORDER BY DESC (?avgAge)
```

Rezultatai "šokiruoja": jauniausi mokiniai [Vilniaus Vilkpėdės darželyje-mokykloje](http://www.vilkpedes.lt) (vidutiniškai 7 metų), vyriausi -- [Vilniaus Gabrielės Petkevičaitės-Bitės suaugusiųjų mokymo centre](http://www.gpbite.eu) (vidutiniškai 41+ metų).

<table>
    <thead>
        <tr>
            <th><code>?school</code></th>
            <th><code>?schoolNameSample</code></th>
            <th><code>?avgAge</code></th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/291710460</td>
            <td>Vilniaus Gabrielės Petkevičaitės-Bitės suaugusiųjų mokymo centras</td>
            <td>41.446445</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/190009548</td>
            <td>Vilniaus suaugusiųjų mokymo centras</td>
            <td>34.39103</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/190009733</td>
            <td>Vilniaus Židinio suaugusiųjų gimnazija</td>
            <td>28.863071</td>
        </tr>
        <tr>
            <td>...</td>
            <td>...</td>
            <td>...</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/191713046</td>
            <td>Vilniaus Volungės darželis-mokykla</td>
            <td>8.066992</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/190022061</td>
            <td>Vilniaus darželis - mokykla Saulutė</td>
            <td>7.9250603</td>
        </tr>
        <tr>
            <td>https://atviras.vilnius.lt/mokyklos/190016699</td>
            <td>Vilniaus Vilkpėdės darželis-mokykla</td>
            <td>6.999386</td>
        </tr>
    </tbody>
</table>

Jeigu turėjome hipotezę apie darželius vs. suaugusiųjų centrus, dabar galime ją pagrįsti faktais.

**[Išbandykite SPARQL užklausą patys](http://atomgraph.dydra.com/ltlod/vilnius/@query#vidutinis-mokiniu-amzius-mokyklose)**

Vilniaus savivaldybei norint paviešinti šiuos duomenis Linked Data principų, tereikia po `atviras.vilnius.lt` URL adresu sukonfiguruoti Linked Data serverį ir prijungti jį prie triplestore. Mes jų siūlome net keletą (visi atviro kodo): nuo paprasto [`Core`](https://github.com/AtomGraph/Core) iki pilno [`Web-Node`](https://github.com/AtomGraph/Web-Node), kuriame integruotas ir HTML UI.

## Reziumuojant

Šis pavyzdys su mokiniais ir mokyklomis trivialus. RDF gali aprašyti viską nuo [molekulių](https://www.ebi.ac.uk/rdf/) iki [zodiako ženklų](http://data.totl.net/zodiac/), o didžiausi grafai (dauguma iš jų [atviri](https://lod-cloud.net/)) siekia dešimtis milijardų triples.

Lietuvos mastu galima būtų pradėti kukliau, iš pradžių imtis transformuoti mažai besikeičiančius duomenis. Kai kuriems tipams/klasėms, pvz. asmenims, organizacijoms, departamentams mes jau esame paruošę [schemas](../../wiki). Taip pat sudarėme AD aktualių [RDF standartų sąrašą](../../wiki/RDF-standartai).

[IPVK](https://ivpk.lrv.lt/) už mus Knowledge Graph nepadarys. Greičiau Vilnius metro atidarys. Jeigu norim progreso, turim daryti mes _patys_, Atvirų Duomenų bendruomenė. _Bendradarbiaudami_, išnaudodami standartus ir open-source programinę įrangą.

![Do it!](https://media.giphy.com/media/3o85xtLX7zCyeeWGLC/giphy.gif)

Susidomėjote Knowledge Graph technologija? Norite išmokti daugiau ar turite idėjų pritaikymui? Užmeskit akį į [mūsų projektus](https://atomgraph.com/cases/) ir brūkštelkit [emailą](mailto:martynas@atomgraph.com).
