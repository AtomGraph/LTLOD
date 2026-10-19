# LTLOD URI scheme

Single source of truth for how every pipeline mints and references entity URIs.
All mappings are parameterized with `$base` (LinkedDataHub import convention).
The committed outputs under `datasets/current/` are base-RELATIVE (no `@base`) —
`{container}/{slug}/#this` rather than `{base}{container}/{slug}/#this` — so they
are base-agnostic; the base is (re)applied at load/parse time (default
`https://linkeddata.lt/`). External URIs (Wikidata, Commons, EU tables, schema.org)
stay absolute. `{base}…` below denotes the resolved absolute form.

## Principles

1. **Entity per named graph** (LinkedDataHub): graph URI = document URI
   `{base}{container}/{slug}/`; the entity is `{graph}#this`; secondary
   entities are `{graph}#<fragment>`. Every ETL graph self-describes:
   `?graph a dh:Item; sioc:has_container <{base}{container}/>;
   dct:title ...; foaf:primaryTopic <#this>` — the `dh:`/`sioc:` triples
   make documents browsable in LinkedDataHub (its container pages list
   children via `sioc:has_parent`/`sioc:has_container`).
   The container documents themselves (top-level containers and taxonomy
   scheme docs) are **not** ETL output: they are scaffolding, one Turtle
   file per container under `app/`, PUT over HTTP by `make install` via the
   LDH CLI — LDH adds `sioc:has_parent` and ownership metadata server-side.
2. **Fold standalone entities by type; nest constituent parts under their
   whole.** Independent entities of one class share one flat top-level
   container (`persons/`, `parties/`, `organizations/`, `admin-units/`). But an
   entity that is a *structural part* of another — an organization's units and
   groups (`org:unitOf` / `org:hasSubOrganization`) — nests under that parent's
   document URI, so the path mirrors the RDF composition
   (`organizations/lietuvos-respublikos-seimas/org-units/{id}/`). This and the
   calendar (`calendar/{yyyy}/{mm}/{dd}/`, whose parent month and year are read
   off the date itself) are the only cases URI depth encodes hierarchy; membership and other relationships
   are *not* composition and never nest (a person is a *member* of the Seimas,
   not a part of it, so `persons/` stays top-level). The same pattern applies
   to any future organization with internal structure (a ministry, a court).
   **Precondition — the parent must be fixed and derivable from the child's
   key.** Nesting only preserves principle 3 (mint a link from a bare foreign
   key) when every instance has the *same, well-known* parent, so `{key}` plus a
   constant prefix yields the URI with no lookup. The Seimas qualifies: every
   org-unit belongs to the one Seimas. Admin units do **not** — a settlement's
   eldership (and a municipality's county) is not encoded in its AR code
   (municipality `12` is in county `2`, `13` in county `10`; settlement `23643`
   in eldership `1867`), so a partonomy path like
   `admin-units/{county}/…/{gyv_kodas}/` would demand a per-entity ancestry
   lookup and would churn under municipal reforms. Also do not encode class
   *subsumption* in the path (`rdf:type` + `rdfs:subClassOf` already carry it,
   and an instance's most-specific class is mutable). Such part-of and is-a
   hierarchies stay in the RDF (`dct:isPartOf`, `rdf:type`) and the 1:N views,
   never in the path — `admin-units/` and `streets/` are flat.
3. **Natural keys as slugs**: official codes from the source registry, never
   name-derived strings (except parties, see below). Any pipeline can mint a
   link from a bare foreign key without looking up the target dataset.
4. Cross-dataset links always point at `{container}/{key}/#this`.
5. **No blank nodes**: secondary entities are `{graph}#<fragment>` IRIs minted from
   keys in the data (see Fragments below), never `[]`/`_:` nodes — everything must be
   linkable and updatable. `etl/lib/validate.sh` rejects output containing any.

## Hosts

Everything in this document lives under ONE dataspace, `{base}` =
`https://linkeddata.lt/`, which holds all national registry data at every
geographic level. Subdomains `*.linkeddata.lt` are **reserved for LinkedDataHub
dataspaces** (`admin.linkeddata.lt` today) — never for side services. A
municipality gets its own peer dataspace `<municipality>.linkeddata.lt` only
for data the municipality itself publishes; it links to the national entities
(`https://linkeddata.lt/admin-units/{sav_kodas}/#this`) and never re-mints them.
None exists yet; the subdomain naming rule is still open.

## Containers

| Container | Slug (natural key) | Class | Source |
|---|---|---|---|
| `admin-units/{code}/` | AR code: county `adm_kodas` (1 digit), municipality `sav_kodas` (2), eldership `sen_kodas` (4), settlement `gyv_kodas` (5) — ranges verified non-colliding | `cv:AdminUnit` | AR via get.data.gov.lt |
| `streets/{gat_kodas}/` | AR street code (7 digits) | `dct:Location` | AR |
| `persons/{asmens_id}/` | Seimas person id | `foaf:Person` | apps.lrs.lt |
| `organizations/{slug}/` | name slug (no natural key in source) | `org:FormalOrganization` | `organizations/lietuvos-respublikos-seimas/` — a **container** (its parts nest under it, see below) that is also the org entity |
| `organizations/lietuvos-respublikos-seimas/org-units/{padalinio_id}/` | Seimas structural-unit id | `org:OrganizationalUnit` | apps.lrs.lt (nested under the Seimas via `org:unitOf`) |
| `organizations/lietuvos-respublikos-seimas/groups/{grupes_id}/` | Seimas parliamentary-group id (separate id space from `padalinio_id`) | `org:OrganizationalUnit` | apps.lrs.lt (nested under the Seimas) |
| `organizations/lietuvos-respublikos-seimas/terms/{kadencijos_id}/` | Seimas term id (1 = 1990–1992 … 10 = 2024–2028) | `eli-dl:ParliamentaryTerm` | apps.lrs.lt `p2b.ad_seimo_kadencijos` (nested under the Seimas) |
| `organizations/lietuvos-respublikos-seimas/sessions/{sesijos_id}/` | Seimas session id (global, not per term) | `eli-dl:Activity` + `schema:EventSeries` | apps.lrs.lt `p2b.ad_seimo_sesijos` (nested under the Seimas) |
| `organizations/lietuvos-respublikos-seimas/sittings/{posėdžio_id}/` | Seimas plenary sitting id (negative in the source, kept verbatim, e.g. `-502172`) | `eli-dl:Activity` + `schema:Event` | apps.lrs.lt `p2b.ad_seimo_posedziai` (nested under the Seimas; `eli-dl:forms_part_of` its session) |
| `organizations/lietuvos-respublikos-seimas/votes/{balsavimo_id}/` | Seimas plenary vote id (negative in the source, kept verbatim, e.g. `-54520`) | `eli-dl:Vote` | apps.lrs.lt `p2b.ad_sp_balsavimo_rezultatai`, reached via `p2b.ad_sp_eiga` → `p2b.ad_sp_klausimo_svarstymo_eiga` (nested under the Seimas; `schema:superEvent` its sitting; opt-in, latest term by default, gitignored bulk output) |
| `declarations/{asmens_id}-{year}/` | Seimas person id + reporting year (one VMI property declaration per person and year) | `ltlod:AssetDeclaration` | VMI annual property declaration extracts (FR0001), harvested in a browser (`etl/declarations/harvest.js`); declarant resolved to `persons/` by name (`ltlod-declarations`) |
| `stories/{slug}/` | editorial slug naming the subject and period (`seimo-turtas-2024`) | `schema:Article` | **not ETL output**: authored scaffolding, `app/stories/{slug}.ttl`, PUT by `make install`; XHTML text plus live charts whose queries are pinned to the period the text describes |
| `parties/{slug}/` | transliterated party-name slug (JAR code once matched — parties keep slug for continuity, `owl:sameAs`/`dct:identifier` carry the code) | `org:FormalOrganization` | apps.lrs.lt (VRK/JAR later) |
| `legal-entities/{ja_kodas}/` | JAR company code (9 digits) | `rov:RegisteredOrganization` | JAR via get.data.gov.lt |
| `constituencies/{kadencijos_id}-{nr}/` | Seimas term id + single-member electoral-district number (districts are redrawn every election, so the number alone is ambiguous) | `ltlod:ElectoralDistrict` | apps.lrs.lt members feed (`išrinkimo_būdas`) — **not** an admin unit, own container |
| `education/{ins_id}/` | ŠVIS institution id (11+ digits; branches without a JAR code have one too) | `schema:EducationalOrganization` + `org:Organization` | ŠVIS via get.data.gov.lt (`lsd/svietimo_istaigos/SvietimoIstaiga`, enriched from `nsa/svis/bendrojo_ugdymo_mokyklos/BugdymoMokykla`); `ltlod:legalEntity` → `legal-entities/{ja_kodas}/#this`, branches `org:subOrganizationOf` their parent |
| `health-care/{ja_kodas}/` | JAR company code of the licence holder (unique in the VASPVT register) | `schema:MedicalOrganization` + `org:Organization` | VASPVT licence register via get.data.gov.lt (`vaspvt/licencijos/Istaiga` + `IstaigosVeiklosAdresas`); the same code mints `ltlod:legalEntity` → `legal-entities/{ja_kodas}/#this` |
| `heritage/{unikalus_kodas}/` | KVR unique code of the immovable cultural property | `schema:LandmarksOrHistoricalBuildings` | KPD Cultural Property Register, data.gov.lt dataset 2192 (XLSX); complex members `schema:containedInPlace` the complex |
| `calendar/{yyyy}/`, `calendar/{yyyy}/{mm}/`, `calendar/{yyyy}/{mm}/{dd}/` | ISO year / month / day (zero-padded, so the paths sort chronologically) | `time:DateTimeInterval` + `dct:PeriodOfTime` | generated (`etl/calendar/`, 1990-01-01 to the end of next year; no source). All are `dh:Item`s in the one `calendar/` container; day → month → year is `time:intervalIn`. Dated entities link with `dct:temporal`, minted from the date: `calendar/` + `REPLACE(?date, "-", "/")` + `/#this`. Gitignored bulk output |
| `taxonomies/{scheme}/` | scheme slug | `skos:ConceptScheme` | — |
| `taxonomies/{scheme}/{notation}/` | concept notation (classifier code or ASCII slug) | `skos:Concept` | JAR classifiers / hand-authored |

## Fragments (secondary entities inside a document graph)

| Fragment | Type | Used in |
|---|---|---|
| `#this` | the primary entity | everywhere |
| `#tenure-{kadencijos_id}-{yyyymmdd}` | `org:Membership` (Seimas seat, one per term served; the start date separates a member who left and returned within a term) | persons |
| `#membership-{padalinio_id}-{yyyymmdd}` | `org:Membership` (committee/commission/faction position) | persons |
| `#pg-membership-{grupes_id}-{yyyymmdd}` | `org:Membership` (parliamentary group) | persons |
| `#...-interval`, `#...-start`, `#...-end` | `time:Interval` / `time:Instant` of a membership | persons |
| `#interval`, `#start`, `#end` | `time:Interval` / `time:Instant` of a term (`time:hasTime`) | terms |
| `#{category}` | `schema:MonetaryAmount` (one declared amount; the asset-categories notation, e.g. `#pinigai-lt`) | declarations |
| `#registered-office` | `org:Site` (registered office) | legal entities |
| `#registered-address` | `locn:Address` → `locn:adminUnit admin-units/{sav_kodas}/#this` + `locn:postCode` | legal entities |
| `#address` | `locn:Address` → `locn:adminUnit` municipality / eldership / settlement by AR code (+ street, house number for schools) | education, heritage |
| `#registration`, `#registration-start`, `#registration-end` | `time:Interval` / `time:Instant` of the period on the register (`time:hasTime`; instants → calendar day) | education, heritage |
| `#licence`, `#licence-validity`, `#licence-start` | `schema:Permit` (licence number, `schema:validFrom`) and its `time:Interval` / start `time:Instant` → calendar day | health care |
| `#site-{id}`, `#site-{id}-address` | `org:Site` (licensed activity address; `{id}` = the VASPVT address GUID, lower-cased) → `locn:Address` (`locn:fullAddress` + `locn:adminUnit` municipality / eldership parsed from the text) | health care |

## Taxonomy schemes

| Scheme | Concepts keyed by | Origin |
|---|---|---|
| `taxonomies/legal-forms/{kodas}/` | JAR form code | fetched from JAR |
| `taxonomies/legal-statuses/{kodas}/` | JAR status code | fetched from JAR |
| `taxonomies/activity-types/{slug}/` | type-label slug (`eiline-sesija`, `rytinis-posedis`, …) | derived from the Seimas calendar feeds (`eli-dl:ActivityType`) |
| `taxonomies/decision-methods/{slug}/` | voting-method slug (`atviras`, `pritarta-bendru-sutarimu`, `alternatyvus-balsavimas`, `slaptas`) | derived from the Seimas vote feeds (`eli-dl:DecisionMethod`) |
| `taxonomies/asset-categories/{slug}/` | category slug (`pinigai-lt`, `zemes-sklypai`, …) | static CSV — VMI FR0001 categories; the older undivided ones are `skos:broader` of their Lithuania/abroad splits |
| `taxonomies/declarant-groups/{code}/` | VMI position-group code (`506` = Seimas members, …) | static CSV |
| `taxonomies/position-types/{slug}/` | position-string slug | derived from Seimas members feed |
| `taxonomies/org-unit-types/{slug}/` | slug | static CSV |
| `taxonomies/settlement-types/{slug}/` | slug | static CSV |
| `taxonomies/street-types/{slug}/` | slug | static CSV |
| `taxonomies/admin-unit-levels/{slug}/` | slug | static CSV (only levels missing from EU ATU-type) |
| `taxonomies/education-types/{slug}/` | type-label slug (`gimnazija`, `ikimokyklinio-ugdymo-mokykla`, …) | derived from the ŠVIS register (main type, else purpose group) |
| `taxonomies/heritage-statuses/{slug}/`, `taxonomies/heritage-significance/{slug}/`, `taxonomies/heritage-kinds/{slug}/`, `taxonomies/heritage-values/{slug}/` | label slug (`valstybes-saugomas`, `nacionalinis`, `statinys`, `archeologinis`, …) | derived from the KVR register (status, significance, object kind, valuable-property flags) |
| `taxonomies/holidays/{slug}/` | holiday slug (`kucios`, `antroji-velyku-diena`, …) | static CSV `etl/calendar/data/holidays.csv` (built by `etl/calendar/`; one row per holiday and validity period, which the calendar also uses to mark the days with `dct:type`) |

Administrative levels use the **EU ATU-type authority table directly** as
`cv:level` values: `atu-type:LTU_APS` (county), `atu-type:LTU_MSV` /
`atu-type:LTU_RSV` / `atu-type:LTU_SV` (municipality kinds),
`atu-type:LTU_SEN` (eldership), where
`atu-type:` = `http://publications.europa.eu/resource/authority/atu-type/`.

## External alignment

- `owl:sameAs` → `http://www.wikidata.org/entity/Q...` (individuals),
  `skos:exactMatch` for taxonomy concepts — produced by the reconciliation
  stage into per-domain `alignments.trig` files.
- `skos:exactMatch` → `http://data.europa.eu/nuts/code/LT0xx` on counties
  (Wikidata P605, NUTS3, into `admin-units/alignments.trig`); municipalities are
  LAU (no P605) and inherit NUTS3 through their county.
- Images from Wikidata: `foaf:depiction` (photo P18, coat of arms P94),
  `schema:logo` (logo P154) — Wikimedia Commons `Special:FilePath` URLs.

## Custom vocabulary

Minimal custom terms live under the stable namespace `http://linkeddata.lt/ns#`
(prefix `ltlod:`), independent of `$base`. Currently:

- `ltlod:nominatedBy` — person (every term) and tenure (that term) → nominating party (a nomination is not a
  membership, and no EU/W3C vocabulary has a term for it).
- `ltlod:AssetDeclaration` / `ltlod:declaredValue` — a public official's annual
  property declaration (VMI FR0001) and its declared amounts (`schema:MonetaryAmount`).
  Neither W3C/EU vocabularies nor schema.org model asset declarations.
- `ltlod:declarant` (`rdfs:subPropertyOf dct:creator`) — declaration → declarant. Its
  own term so the person view attaches to this relationship only, not to every
  `dct:creator` (views attach per property; see `app/ns.ttl`).
- `ltlod:legalEntity` (`rdfs:subPropertyOf org:linkedTo`) — a facility (school, health-care
  institution) → the JAR legal entity that runs it; for a school branch without its own JAR
  code, its parent's. Not `owl:sameAs`: a branch is not the legal entity, and the facility
  record is a register role, not the company. Its own term so the legal-entity view attaches
  to this relationship only.
- `ltlod:licence` — health-care institution → its VASPVT licence (`schema:Permit`); schema.org
  has no holder → permit property.
- `ltlod:protectionStatus` / `ltlod:significance` — a heritage object's KVR legal protection
  status and level of significance (SKOS concepts); no W3C/EU/schema.org term.
- `ltlod:ElectoralDistrict` / `ltlod:electoralDistrict` — a Seimas single-member
  electoral district (apygarda) and the seat (`org:Membership` tenure) → district
  link. No W3C/EU term exists, and an apygarda is not an administrative unit
  (electoral divisions do not coincide with counties/municipalities).
