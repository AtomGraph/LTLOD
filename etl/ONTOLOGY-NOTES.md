# Ontology & taxonomy notes

Vocabulary strategy: **W3C specs first → domain-specific third-party vocabularies (EU SEMIC, OP authority tables, FOAF) → schema.org as the shallow-but-wide general fallback → custom last.** (Membership validity therefore stays on W3C Time intervals, not schema:startDate/endDate.)

The per-domain property/datatype/cardinality constraints implied by these choices are formalized as SHACL shapes in `etl/shapes/` (executed in the validate stage and in CI).

## Choices made

| Domain | Vocabulary | Notes |
|---|---|---|
| Admin units | SEMIC **Core Location 2.1.1**: `cv:AdminUnit`, `cv:level` (`cv:` = `http://data.europa.eu/m8g/`) | `cv:level` points at the EU **ATU-type** authority table (`LTU_APS`, `LTU_MSV`, `LTU_RSV`, `LTU_SV`, `LTU_SEN`) exactly as the CLV spec recommends. Settlements are typed `cv:AdminUnit` pragmatically with a custom level concept (`taxonomies/admin-unit-levels/gyvenamoji-vietove`) — they are territorial rather than administrative units, and ATU-type has no concept for them. |
| Streets | `dct:Location` + `dct:type` → street-type concept | No EU/W3C thoroughfare class; `locn:thoroughfare` is a literal-valued address property. |
| Legal entities | W3C/SEMIC **RegOrg**: `rov:RegisteredOrganization` (⊑ `org:FormalOrganization`), `rov:legalName`, `rov:companyType`, `rov:orgStatus` | Form/status ranges are our SKOS concepts generated from the JAR classifiers. |
| Org structure, positions, memberships | W3C **ORG**: `org:OrganizationalUnit`, `org:unitOf`, `org:Membership`, `org:member`, `org:organization`, `org:role`, `org:memberDuring` | Change over time = n-ary `org:Membership` + `time:Interval` (`time:hasBeginning/hasEnd` → `time:Instant` → `time:inXSDDate`). **No reification, no RDF-star.** Current state = memberships without `time:hasEnd`. |
| Persons | `foaf:Person`, `foaf:givenName/familyName/name/mbox/gender/phone` | Core Person 2.0 compatible (it reuses foaf); revisit `person:` terms if birth data is added later. Phones are normalized to `tel:+370…` E.164 URIs in the mapping (bare 7-digit values are Vilnius landlines, area code 5) — reuse that BIND pattern in any future mapping with phone numbers. |
| Taxonomies | **SKOS** | Concept-per-graph; schemes are containers. |
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
- **Addresses**: AR `adresai`/`adresotaskas` (~1M rows) deferred; when added,
  use `locn:Address` + `cv:adminUnit`, and link JAR `buveines`
  (registered offices) → address → admin unit chain.
- **Geometries**: AR provides point data (adresotaskas) — add
  `locn:Geometry`/GeoSPARQL when addresses land.
- **NUTS/LAU exactMatch**: county/municipality graphs could carry direct
  `skos:exactMatch` → `http://data.europa.eu/nuts/code/LT0xx` (verified
  dereferenceable); currently alignment goes through Wikidata only.
- **Seimas constituency** (`išrinkimo_būdas`) not yet modeled.
