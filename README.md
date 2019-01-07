LTLOD projektą sukūrėme prieš daugiau nei 5 metus. Deja, nei Linked Open Data, nei Open Data situacija apskritai per tą laiką iš esmės nepagerėjo.

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
            <td>Marytė</td>
            <td>https://atviras.vilnius.lt/mokiniai/name</td>
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

Tokie ryšiai reikalautų papildomų lentelių reliacinėje DB. Reliacinio modelio schemos nelankstumas yra vienas didžiausių minusų, palyginus su RDF duomenų bazėmis (triplestores), kuriuose schema nėra būtina.

_Dėl stabilios Subject-Property-Object struktūros, fiziniame lygmenyje RDF duomenų rinkiniai integruojami juos tiesiog sujungiant, kas nieko nekainuoja._ Su reliacinėmis lentelėmis tai tiesiog neįmanoma.

_RDF yra (kryptinio) grafo duomenų modelis, o ne duomenų formatas_. RDF gali būti užrašytas skirtingais formatais naudojant [skirtingas sintakses](https://www.w3.org/TR/rdf11-primer/#section-graph-syntax): plain-text (Turtle), XML (RDF/XML), JSON (JSON-LD) ir t.t. RDF bibliotekos dažniausiai palaiko daugumą standartinių RDF sintaksių.

# Linked (Open) Data

Linked Data (LD), arba Linked Open Data (LOD), priklausomai nuo duomenų atvirumo, yra RDF duomenų publikavimo internete metodas.

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
Pavyzdžiui, vietoje `"Fabijoniškių"` kaip tekstinės reikšmės mokyklai identifikuoti, suteikime mokykloms savus URI adresus, pvz. naudojant jų kodus: `https://atviras.vilnius.lt/mokyklos/190003851`. Patobulintas Linked Data atsakas atrodo taip:

    @prefix mok: <https://atviras.vilnius.lt/mokiniai/> .

    <https://atviras.vilnius.lt/mokiniai/id/1> mok:id 1 ;
        mok:name "Petriukas" ;
        mok:school <https://atviras.vilnius.lt/mokyklos/190003851> ;
        mok:class "3B" ;
        mok:friendsWith <https://atviras.vilnius.lt/mokiniai/id/2> .

Dabar programinė įranga gali naviguoti URI adresais ir užklausti serverio dominančių objektų duomenų, lygiai kaip mes naviguojame interneto puslapius naudodami nuorodas.

## SPARQL

# Knowledge Graph nauda

Pastaruoju metu Linked Data marketingistų vadinama Knowledge Graph, tai nuo šiol vadinkime ir mes taip.

Dažnam gali kilti klausimas: kam Knowledge Graphs naudojami? Kokia iš jų nauda (atviriesiems duomenims)?

Ne paslaptis, kad atvirieji duomenis turi būti lengvai integruojami ir perpanaudojami. _RDF Knowledge Graphs yra vienintelis standartizuotas metodas, leidžiantis sujungti atskirus duomenų rinkinius į vientisą, potencialiai beribį sluoksnį._ Neišradinėkime dviračio, jis jau išrastas. Bet kokios lokalaus ar nacionalinio masto specifikacijos, portalai ar manifestai, ignoruojantys RDF ir Knowledge Graphs, bus tik pinigų ir laiko švaistymas.

Kam mums vientisas sluoksnis? Kad naudomtumėme resursus išmintingai, sluoksniuodami vienas pastangas ant kitų, naudodami vienų darbo vaisius kaip  pagrindą kitiems darbams. Duomenų rinkinio vertė auga [proporcingai ryšių jame skaičiui](https://en.wikipedia.org/wiki/Network_effect).

Netikite? Tada gal įtikins autoritetingi leidiniai:
* Financial Times. [Governments fail to capitalise on swaths of open data](https://www.ft.com/content/f8e9c2ea-b29b-11e8-87e0-d84e0d934341)
* Forbes. [Is The Enterprise Knowledge Graph Finally Going To Make All Data Usable?](https://www.forbes.com/sites/danwoods/2018/09/19/is-the-enterprise-knowledge-graph-going-to-finally-make-all-data-usable/)

## Pritaikymo pavyzdys

Tarkime, norime sudaryti Vilniaus mokiniams naują pietų racioną. Nesvarbu, ar tai idėja hakatone, ar komercinis projektas įmonėje. Mums reikia mokinių ir mokyklų sąrašo patiekalų meniu sudarymui (kalorijų apskaičiavimams ar pan.) Turime 2 įgyvendinimo variantus:
1. parsisiųsti mokinių ir mokyklų CSV, sukišti į savo reliacinę DB ar kitokias duomenų struktūras, atlikti skaičiavimus. Galbūt papublikuoti rezultatus kaip CSV.
2. paversti savo duomenis į RDF, naudojant `atviras.vilnius.lt` URI ryšiams su mokyklomis ir mokiniais nurodyti

Pirmo varianto išdava: buvo 2 paskiri, tarpusavyje nesuintegruoti CSV failai, tapo 3.
Antro varianto išdava: lietuviškas Knowledge Graph pasitarnavo kaip pagrindas naujam RDF rinkiniui, ir to pasekoje išsipletė.

Skirtumą tikiuosi patys matote. Nenaudojant Knowledge Graph, su kiekvienu tokiu pavyzdžiu parandama vis daugiau duomenų perpanaudojimo potencialo.

## Įgyvendinimas praktikoje

CSV2RDF