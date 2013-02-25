Atviri duomenys Lietuvoje
=========================

Atsakingos institucijos
-----------------------

* [Informacinės Visuomenės Plėtros Komitetas](http://opendata.gov.lt)
* [Ūkio ministerija](http://data.ukmin.lt/apie.html): galimybių studija
* [Valstybinė Duomenų apsaugos inspekcija](http://www.ada.lt)

Nevyriausybinės organizacijos
-----------------------------

* [Transparency International](http://transparency.lt)

Iniciatyvos
-----------

* [Atvira valdžia](http://atviravaldzia.org)
* [Kur Gyvenu](http://kurgyvenu.lt)
* [Mano Balsas](http://www.manobalsas.lt)
* [manoSeimas](http://manoseimas.lt)
* [ManoValstybė](http://manovalstybe.lt)
* [Seime.lt](http://seime.lt)
* [Viešai.lt](http://www.viesai.lt)

Duomenų šaltiniai
-----------------

<table>
    <thead>
	<tr>
	    <th>Šaltinis</th>
	    <th>Duomenų tipai</th>
	    <th>Formatai</th>
	    <th>Prieinamumas</th>
	</tr>
    </thead>
    <tbody>
	<tr>
	    <td>LR Seimas</td>
	    <td>Teisės aktai</td>
	    <td>HTML</td>
	    <td>Atviri</td>
	</tr>
	<tr>
	    <td>LR Vyriausioji rinkimų komisija</td>
	    <td>Kandidatų deklaracijos (asmens, turto, interesų)</td>
	    <td>HTML</td>
	    <td>Atviri</td>
	</tr>
	<tr>
	    <td>Tarpžinybinė mokestinių duomenų saugykla (TDS)</td>
	    <td>Finansų ministerija, VMI, Muitinės departamentas, VSDF valdyba, Statistikos departamentas, FNTT</td>
	    <td>BusinessObjects</td>
	    <td>Uždari</td>
	</tr>
	<tr>
	    <td>Registrų centras</td>
	    <td>Registrai (NT, adresų, juridinių asmenų)</td>
	    <td></td>
	    <td>Uždari</td>
	</tr>
    </tbody>
</table>

Teisinė bazė
---------------

* [LR Teisės gauti informaciją iš valstybės ir savivaldybių institucijų ir įstaigų įstatymas](http://www3.lrs.lt/pls/inter3/dokpaieska.showdoc_l?p_id=373811)
* [Lietuvos informacinės visuomenės plėtros tendencijų ir prioritetų 2014-2020 metais vertinimas](http://www.ivpk.lt/news/1790/158/Lietuvos-informacines-visuomenes-pletros-tendenciju-ir-prioritetu-2014-2020-metais-vertinimas)
* [Tarpžinybinės mokestinių duomenų saugyklos nuostatai](http://www3.lrs.lt/pls/inter3/dokpaieska.showdoc_l?p_id=303933&p_query=&p_tr2=)
* [Tarpžinybinės mokestinių duomenų saugyklos duomenų saugos nuostatai](http://www3.lrs.lt/pls/inter3/dokpaieska.showdoc_l?p_id=305433&p_query=&p_tr2=)
* [Asmens duomenų teisinės apsaugos įstatymas](http://www3.lrs.lt/pls/inter3/oldsearch.preps2?Condition1=29193&Condition2=)

Poveikio priemonės
------------------

Top-down
* Open Data politikos formavimas
* bendradarbiavimas su valstybės institucijomis (IVPK)

Bottom-up
* Gero pavyzdžio rodymas
* Inovatyvių duomenų technologijų naudojimas

Tikslai
-------

5 atvirų duomenų lygiai:

1. duomenys internete (bet kokiu formatu) atvira licencija
2. struktūrizuoti duomenys (pvz., Excel vietoj nuskanuotos lentelės paveiksliuko)
3. standartiniai ("non-proprietary") formatai (pvz., CSV vietoj Excel)
4. URI naudojimas resursams identifikuoti - juos bus galima naudoti nuorodoms
5. duomenų sujungimas su kitais duomenimis, pateikiant kontekstą

Šaltinis: [5 star Open Data](http://5stardata.info)

Linked Open Data
================

* RDF duomenų modelis
* XML ir tekstinė sintaksės (RDF/XML, Turtle)
* SPARQL užklausų kalba
* W3C standartai

Privalumai
----------

Norint integruoti N duomenų šaltinių
* reikalingos 2 transformacijos
* įš formato/šaltinio į RDF/iš RDF į formatą/šaltinį
* dabartiniais metodais -- N² transformacijų

Tiesiniai integracijos kaštai
* dabartiniais metodais -- kvadratiniai
* nereikia kurti programinių sprendimų integruojant naujus duomenų tipus

Nemokamas kontekstas
* pasaulinis duomenų tinklas
* užsienio praktika ir pavyzdžiai

Pavyzdžiai
----------

* [data.gov.uk](http://data.gov.uk) (D. Britanija)
* [opendata.cz](http://www.opendata.cz/en/linked-data) (Čekija)
* [World Bank Link Data](http://worldbank.270a.info)
* [New York Times LOD](http://data.nytimes.com) (JAV)
* [Linked Life Data](http://linkedlifedata.com)

Daugiau pavyzdžių:
* [Linked Data - Connect Distributed Data across the Web](http://linkeddata.org)

Standartai
----------

* [Linked Data](http://www.w3.org/standards/semanticweb/data) (W3C)
* [Government Linked Data Working Group](http://www.w3.org/2011/gld/wiki/Main_Page) (W3C)
* [RDF](http://www.w3.org/RDF/) (W3C)
* [Open Data Commons](http://opendatacommons.org)

LTLOD
=====

Suintegruokime lietuviškus atvirus duomenis kaip Linked Open Data!

* [LOD specifikacija](../../wiki) (rekomenduojami URI templates ir ontologijos)
* ["Žaliaviniai" duomenys](datasets)
* [Pavyzdžiai (Turtle)](datasets/LTLOD%20examples.ttl)

Bottom-up open-source procesas
------------------------------

1. Duomenų šaltinio ir jo formatų identifikavimas ([atviriduomenys.lt](http://atviriduomenys.lt) ir/arba [opendata.gov.lt](http://opendata.gov.lt))
2. Konvertavimas į RDF naudojant LTLOD specifikaciją ir pavyzdžius
3. "Žaliavinių" duomenų ir/arba jų aprašų patalpinimas į CKAN [atviriduomenys.lt](http://atviriduomenys.lt)
4. RDF duomenų patalpinimas į CKAN [atviriduomenys.lt](http://atviriduomenys.lt)
5. RDF duomenų patalpinimas į [LTLOD](http://dydra.com/graphity/ltlod/sparql) SPARQL servisą
6. LOD publikavimas [linkeddata.lt](http://linkeddata.lt)
7. [linkeddata.lt](http://linkeddata.lt) užklausų ir sąsajos konfigūravimas (naudojant GitHub pull-requests, užtenka minimalios koordinacijos)
8. Komunikacija (Facebook, Twitter)

Įrankiai
--------
* [OpenRefine](https://github.com/OpenRefine/OpenRefine)
* [RDF Refine](http://refine.deri.ie) (Google Refine RDF extension)
* [RDF validator](http://www.rdfabout.com/demo/validator/)
* [GitHub](http://github.com)
* [Dydra](http://dydra.com) (RDF cloud triplestore)

Progresas
---------

Duomenys, publikuoti kaip LOD:
* 2012 m. Seimo rinkimų kandidatų deklaracijos (asmens, turto, interesų)
* 2006-2011 m. savivaldybių viešieji pirkimai
* LR valstybinių institucijų tinklas

Duomenys, tinkami LOD publikavimui:
* Registrai
* Statistika
* Geografiniai
* Nuorodos į žiniasklaidą ir faktinę medžiagą
* Nuorodos į vaizdinę medžiagą

[linkeddata.lt](http://linkeddata.lt)
-------------

* [Graphity LOD framework](http://graphity.org)
* [Sitemap ontologija](src/main/resources/lt/linkeddata/vocabulary/ltlod.ttl)
* [SPARQL endpoint](http://dydra.com/graphity/ltlod/sparql)
* [Sąsajos vertimas](src/main/resources/lt/linkeddata/provider/xslt/translations.rdf)

Media
=====

* [atviri duomenys Google Group](https://groups.google.com/forum/?fromgroups=#!forum/atviriduomenys)
* [The Open Knowledge Foundation](The Open Knowledge Foundation)
* [Atvirų duomenų vadovėlis](http://opendatahandbook.org/lt_LT/index.html)
* [International Open Data Hackathon](http://opendataday.org)
* [Open Data Institute](http://www.theodi.org)
* [Open Data White Paper: Unleashing the Potential](https://www.gov.uk/government/publications/open-data-white-paper-unleashing-the-potential) (D. Britanija)
* [Tim Berners-Lee: The next Web of open, Linked Data](http://www.youtube.com/watch?v=OM6XIICm_qo)
* [The Open Data Economy: Unlocking Economic Value by Opening Government and Public Data](http://www.capgemini-consulting.com/ebook/The-Open-Data-Economy/files/assets/downloads/publication.pdf) (Capgemini Consulting 2012)
* [Learning SPARQL](http://www.learningsparql.com)