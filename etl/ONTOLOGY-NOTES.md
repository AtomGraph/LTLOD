# Ontology & taxonomy notes

Vocabulary strategy: **W3C specs first → domain-specific third-party vocabularies (EU SEMIC, OP authority tables, FOAF) → schema.org as the shallow-but-wide general fallback → custom last.** (Membership validity therefore stays on W3C Time intervals, not schema:startDate/endDate.)

The per-domain property/datatype/cardinality constraints implied by these choices are formalized as SHACL shapes in `etl/shapes/` (executed in the validate stage and in CI).

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
- **Geometries**: AR provides point data (adresotaskas) — add
  `locn:Geometry`/GeoSPARQL when addresses land.
- **NUTS/LAU exactMatch** *(counties done)*: counties carry `skos:exactMatch` →
  `http://data.europa.eu/nuts/code/LT0xx` (NUTS3, from Wikidata P605) in
  `admin-units/alignments.trig`. Municipalities are LAU (no P605) and inherit
  NUTS3 through their county; a direct municipality → LAU code link (Wikidata
  P782) is still open.
- **Seimas constituency** *(done)*: single-member electoral districts (apygardos)
  are parsed from `išrinkimo_būdas` into a `constituencies/{nr}/` container
  (`ltlod:ElectoralDistrict`), and the single-member seat (`org:Membership`
  tenure) carries `ltlod:electoralDistrict`. Party-list seats ("Pagal sąrašą")
  have none. An apygarda is not an admin unit (own container, no `dct:isPartOf`
  into `admin-units/`). No clean online apygardos table exists (VRK's
  get.data.gov.lt `Apygarda` is municipal-election granularity), so the district
  is parsed from the members-feed string.
