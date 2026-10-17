# Ontology & taxonomy notes

Vocabulary strategy: **W3C specs first → domain-specific third-party vocabularies (EU SEMIC, OP authority tables, FOAF) → schema.org as the shallow-but-wide general fallback → custom last.** (Membership validity therefore stays on W3C Time intervals, not schema:startDate/endDate.)

The per-domain property/datatype/cardinality constraints implied by these choices are formalized as SHACL shapes in `etl/shapes/` (executed in the validate stage and in CI).

## Overview

The main classes per domain and the links between them. Literal attributes, the `dh:Item`
documents that wrap every entity, and the two link targets every domain shares are left out
(they follow the diagram).

```mermaid
flowchart TB
    subgraph geo["Admin units · SEMIC Core Location"]
        AU["cv:AdminUnit<br/>county · municipality · eldership · settlement"]
        ST["dct:Location<br/>street"]
    end

    subgraph le["Legal entities · RegOrg + ORG"]
        RO["rov:RegisteredOrganization"]
        SITE["org:Site"]
        ADDR["locn:Address"]
    end

    subgraph seimas["Seimas · ORG + FOAF + W3C Time"]
        LRS["org:FormalOrganization<br/>+ cv:PublicOrganisation<br/>the Seimas"]
        OU["org:OrganizationalUnit<br/>committee · commission · group"]
        P["foaf:Person"]
        M["org:Membership<br/>seat · unit · group"]
        I["time:Interval"]
        PARTY["org:FormalOrganization<br/>+ schema:PoliticalParty"]
        ED["ltlod:ElectoralDistrict"]
    end

    subgraph cal["Seimas calendar · ELI-DL"]
        T["eli-dl:ParliamentaryTerm"]
        SES["eli-dl:Activity<br/>+ schema:EventSeries<br/>session"]
        SIT["eli-dl:Activity<br/>+ schema:Event<br/>sitting"]
    end

    AU -- "dct:isPartOf" --> AU
    ST -- "dct:isPartOf" --> AU

    RO -- "org:hasRegisteredSite" --> SITE
    SITE -- "org:siteAddress" --> ADDR
    ADDR -- "locn:adminUnit" --> AU

    OU -- "org:unitOf" --> LRS
    M -- "org:member" --> P
    M -- "org:organization" --> LRS
    M -- "org:organization" --> OU
    M -- "org:memberDuring" --> I
    M -- "ltlod:electoralDistrict" --> ED
    M -- "epvoc:memberDuringParliamentaryTerm" --> T
    P -- "ltlod:nominatedBy" --> PARTY

    SIT -- "eli-dl:forms_part_of" --> SES
    SES -- "eli-dl:parliamentary_term" --> T
    SES -- "eli-dl:had_responsible_organization" --> LRS
    T -- "time:hasTime" --> I
```

Classifications point at **SKOS** concepts (`skos:Concept`, one scheme per taxonomy):
`cv:level`/`dct:type` on admin units and streets, `rov:companyType`/`rov:orgStatus` on legal
entities, `dct:type` on Seimas units, `org:role` on memberships, `eli-dl:had_activity_type` on
sessions and sittings. Admin units and persons are aligned to **Wikidata** with `owl:sameAs`
(in the per-domain `alignments.trig`).

Sittings also carry `eli-dl:parliamentary_term` and `eli-dl:had_responsible_organization`
(drawn on sessions only). `cv:level` points at the EU ATU-type
authority table except for settlements. Each `time:Interval` has `time:hasBeginning` /
`time:hasEnd` → `time:Instant`; an interval with no end is the current state.

## Choices made

| Domain | Vocabulary | Notes |
|---|---|---|
| Admin units | SEMIC **Core Location 2.1.1**: `cv:AdminUnit`, `cv:level` (`cv:` = `http://data.europa.eu/m8g/`) | `cv:level` points at the EU **ATU-type** authority table (`LTU_APS`, `LTU_MSV`, `LTU_RSV`, `LTU_SV`, `LTU_SEN`) exactly as the CLV spec recommends. Settlements are typed `cv:AdminUnit` pragmatically with a custom level concept (`taxonomies/admin-unit-levels/gyvenamoji-vietove`) — they are territorial rather than administrative units, and ATU-type has no concept for them. |
| Streets | `dct:Location` + `dct:type` → street-type concept | No EU/W3C thoroughfare class; `locn:thoroughfare` is a literal-valued address property. |
| Legal entities | W3C/SEMIC **RegOrg**: `rov:RegisteredOrganization` (⊑ `org:FormalOrganization`), `rov:legalName`, `rov:companyType`, `rov:orgStatus` | Form/status ranges are our SKOS concepts generated from the JAR classifiers. |
| Registered office (legal entities) | W3C **ORG** + SEMIC **Core Location**: `org:hasRegisteredSite` → `org:Site` → `org:siteAddress` → `locn:Address` (`locn:adminUnit`, `locn:postCode`) | Office resolved JAR `Buveine` ⋈ AR `Pastatas` on `aob_kodas` (see backlog note). `locn:adminUnit` is IRI-valued here (CLV's `adminUnitL1/L2` are literal name fields — mild documented extension); its `rdfs:range cv:AdminUnit` in `ns.ttl` also targets the "organizations registered here" 1:N view. |
| Electoral districts | custom **`ltlod:ElectoralDistrict`** + `ltlod:electoralDistrict` | No W3C/EU term for a parliamentary constituency; apygardos parsed from the members feed into their own `constituencies/` container. Not admin units. Cascade-justified (custom last), mirrors `ltlod:nominatedBy`. |
| Org structure, positions, memberships | W3C **ORG**: `org:OrganizationalUnit`, `org:unitOf`, `org:Membership`, `org:member`, `org:organization`, `org:role`, `org:memberDuring` | Change over time = n-ary `org:Membership` + `time:Interval` (`time:hasBeginning/hasEnd` → `time:Instant` → `time:inXSDDate`). **No reification, no RDF-star.** Current state = memberships without `time:hasEnd`. |
| Persons | `foaf:Person`, `foaf:givenName/familyName/name/mbox/gender/phone` | Core Person 2.0 compatible (it reuses foaf); revisit `person:` terms if birth data is added later. Phones are normalized to `tel:+370…` E.164 URIs in the mapping (bare 7-digit values are Vilnius landlines, area code 5) — reuse that BIND pattern in any future mapping with phone numbers. |
| Taxonomies | **SKOS** | Concept-per-graph; schemes are containers. |
| Parties | `org:FormalOrganization` + `schema:PoliticalParty` | No W3C/SEMIC political-party class exists; schema.org (general-fallback cascade level) has one. The extra type also lets LinkedDataHub target party-only views (`ldh:inverseView` matches instance types against a property's declared `rdfs:range` — exact match, no subsumption). |
| The Seimas | `org:FormalOrganization` + `cv:PublicOrganisation` (SEMIC **CPOV**) | Distinguishes the parliament from parties and legal entities, which share `org:FormalOrganization`; used to target Seimas-only LinkedDataHub views (members, units). |
| Seimas calendar (terms, sessions, sittings) | EU **ELI-DL** (ELI Draft Legislation ontology): `eli-dl:ParliamentaryTerm`, `eli-dl:Activity`, `eli-dl:had_activity_type` → `eli-dl:ActivityType` concepts, `eli-dl:parliamentary_term`, `eli-dl:forms_part_of`, `eli-dl:had_responsible_organization`, `eli-dl:recorded_in_a_realization_of`; tenure → term via EP **EPVOC** `epvoc:memberDuringParliamentaryTerm` (domain `org:Membership`, range `eli-dl:ParliamentaryTerm`) | Sessions and sittings are both `eli-dl:Activity`; the second type (`schema:EventSeries` session, `schema:Event` sitting) only discriminates them for LinkedDataHub views (exact-type `rdfs:range` match), as `schema:PoliticalParty` does for parties. Activity dates use ELI-DL's own `activity_date` / `activity_start_date` / `activity_end_date` directly on the activity rather than a `time:Interval`: LDH view sort/filter columns must hang off the projected entity. Sitting times are Vilnius local time from the source, emitted as `xsd:dateTime` without a zone offset. `eli-dl:ParliamentaryTerm` has no date properties, so a term's period is a W3C Time interval (`time:hasTime`). Session → term and sitting → session deliberately avoid `dct:isPartOf`: LDH attaches `ldh:inverseView`s per property, and `dct:isPartOf` already carries the admin-unit `:SubUnits` view. |
| Validity dates | `schema:validFrom` / `schema:validThrough` (admin units), `schema:foundingDate` / `schema:dissolutionDate` (legal entities) | No EU RDF term for registry lifecycle dates (INSPIRE models them as `beginLifespanVersion` in GML only). |

## Legacy vocabulary disposition (2012 datasets)

- `ltlod.ttl` (in the removed Graphity webapp) was a **Graphity sitemap
  ontology** (URL routing), not a domain ontology. The whole proto-LinkedDataHub
  webapp (`src/`, `pom.xml`) has been removed — LinkedDataHub supersedes that
  layer entirely; everything remains in git history.
- `dis:` (semantic-web.dk disclosures) and `pc:` (purl.org/procurement) are
  unmaintained. When declarations/procurement domains are refreshed:
  procurement → EU **ePO** (`http://data.europa.eu/a4g/ontology#`);
  declarations → small custom vocabulary under `http://linkeddata.lt/ns#`.
- `owl:sameAs` → DBpedia links in the 2012 data remain valid where entities are
  re-minted with the same keys; the new alignment target is **Wikidata**.
- `translations.rdf` (the webapp's XSLT label dictionary) is gone with it —
  labels now live in the data itself (`@lt` + `@en`).

## Known modeling debts / improvement backlog

- **Gendered position concepts**: Seimas position strings are gendered
  ("Komiteto narys"/"Komiteto narė" become two concepts). Add a
  gender-neutral concept layer linked via `skos:related`/`skos:broader`, or
  normalize during mapping.
- **Party identity**: parties are keyed by name slug until matched to JAR
  codes / VRK identifiers; then add `dct:identifier` + `owl:sameAs`.
- **Person identity across sources**: `persons/{asmens_id}/` is
  Seimas-scoped. When VRK/declaration sources are added, cross-source
  identity via Wikidata QIDs and shared natural keys.
- **Registered office → municipality** *(done)*: legal entities link to their
  registered office via the SEMIC chain `org:hasRegisteredSite → org:Site →
  org:siteAddress → locn:Address`, resolved deterministically from JAR
  `buveines/Buveine` (`juridinis_asmuo.ja_kodas → adresas.aob_kodas`) joined to AR
  `pastatas/Pastatas` (`aob_kodas → savivaldybe.sav_kodas` + `pasto_kodas`) on
  `aob_kodas`; `locn:adminUnit` → `admin-units/{sav_kodas}/#this` (committed
  primary), `locn:postCode` literal. Latest office per entity (Buveine has
  `adresas_nuo`, no `adresas_iki`). Postcode is an attribute, **not** a join key
  (postcode→municipality is not guaranteed 1:1; `aob_kodas → sav_kodas` is exact).
  Still deferred: full AR `adresai`/`adresotaskas` address entities, and finer
  eldership/settlement/street office links (those point into the gitignored bulk
  layer, so the committed link stops at the municipality).
- **Admin-unit coordinates** *(done)*: every admin-unit level carries a WGS84
  representative point as `geo:lat`/`geo:long` (WGS84 Basic Geo,
  `http://www.w3.org/2003/01/geo/wgs84_pos#`, `xsd:decimal`), computed by
  `ltlod-geo` from the AR spatial models (`gra{apskritis,savivaldybe,seniunija,
  gyvenamojivietove}`, LKS-94/EPSG:3346 polygons → `shapely.representative_point`
  → reproject to EPSG:4326). Emitted to `*-geo.trig` (same graph names, merged on
  load — the `alignments.trig` convention). **Why `geo:lat`/`geo:long`, not
  GeoSPARQL/`locn:Geometry`**: (a) it is the exact pair LinkedDataHub's map reader
  keys on (`RDFXML2GeoJSON.xsl` matches `[geo:lat][geo:long]`), so it unlocks
  `ac:MapMode`; (b) W3C-first per the vocab cascade; (c) AutoGraph precedent.
- **Admin-unit boundaries** *(done, coarse levels)*: counties/municipalities/
  elderships also carry their polygon as **GeoSPARQL** `gsp:asWKT`
  (`http://www.opengis.net/ont/geosparql#`, datatype `gsp:wktLiteral`) so LDH's
  `map.xsl` draws the shape (a `wktLiteral` is what it reads; WGS84 Basic Geo has
  no WKT property). Placed **directly on `#this`** (not via `geo:hasGeometry`) so
  the OpenLayers feature id is the admin-unit URI → the polygon is clickable and
  its info-window resolves to the unit. The WKT is **bare WGS84 lon-lat** (no
  CRS-URI prefix — OpenLayers can't parse one) and **Douglas–Peucker simplified**
  (`ltlod-geo --simplify`, ~50 m in source metres): LDH does no client-side
  simplification and the raw polygons are ~160 MB, so we simplify for display
  (~95–99 % fewer vertices, identical at map zoom). Settlements stay **point-only**
  (20 880 polygons are too heavy for the client). Full-resolution geometries,
  `adresotaskas` address points, and per-feature topology (shared borders) remain
  future work.
- **NUTS/LAU exactMatch** *(counties done)*: counties carry `skos:exactMatch` →
  `http://data.europa.eu/nuts/code/LT0xx` (NUTS3, from Wikidata P605) in
  `admin-units/alignments.trig`. Municipalities are LAU (no P605) and inherit
  NUTS3 through their county; a direct municipality → LAU code link (Wikidata
  P782) is still open.
- **Seimas constituency** *(done)*: single-member electoral districts (apygardos)
  are parsed from `išrinkimo_būdas` into a `constituencies/{kadencijos_id}-{nr}/`
  container (`ltlod:ElectoralDistrict`), and the single-member seat (`org:Membership`
  tenure) carries `ltlod:electoralDistrict`. Districts are term-scoped because they
  are redrawn every election — the same number names a different district in
  another term. Party-list seats ("Pagal sąrašą", and the "Vyriausioji rinkimų
  komisija" / "Daugiamandatėje" Nr. 100 pseudo-district of older terms) have none. An apygarda is not an admin unit (own container, no `dct:isPartOf`
  into `admin-units/`). No clean online apygardos table exists (VRK's
  get.data.gov.lt `Apygarda` is municipal-election granularity), so the district
  is parsed from the members-feed string.
