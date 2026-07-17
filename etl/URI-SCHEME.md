# LTLOD URI scheme

Single source of truth for how every pipeline mints and references entity URIs.
All mappings are parameterized with `$base` (LinkedDataHub import convention);
the committed outputs under `datasets/current/` use the default
`https://linkeddata.lt/`.

## Principles

1. **Entity per named graph** (LinkedDataHub): graph URI = document URI
   `{base}{container}/{slug}/`; the entity is `{graph}#this`; secondary
   entities are `{graph}#<fragment>`. Every graph self-describes:
   `?graph a dh:Item; sioc:has_container <{base}{container}/>;
   dct:title ...; foaf:primaryTopic <#this>` — the `dh:`/`sioc:` triples
   make documents browsable in LinkedDataHub (its container pages list
   children via `sioc:has_parent`/`sioc:has_container`).
   Container documents themselves come from `etl/containers/`
   (`datasets/current/containers/containers.trig`): each top-level container
   is a `dh:Container` with `sioc:has_parent <{base}>`; taxonomy scheme
   documents are `dh:Container`s with `sioc:has_parent <{base}taxonomies/>`
   (their concepts attach via `sioc:has_container` to the scheme document).
2. **Fold by type**: all instances of one class share one flat container.
   Hierarchy lives in RDF (`dct:isPartOf`), never in URI paths.
3. **Natural keys as slugs**: official codes from the source registry, never
   name-derived strings (except parties, see below). Any pipeline can mint a
   link from a bare foreign key without looking up the target dataset.
4. Cross-dataset links always point at `{container}/{key}/#this`.

## Containers

| Container | Slug (natural key) | Class | Source |
|---|---|---|---|
| `admin-units/{code}/` | AR code: county `adm_kodas` (1 digit), municipality `sav_kodas` (2), eldership `sen_kodas` (4), settlement `gyv_kodas` (5) — ranges verified non-colliding | `cv:AdminUnit` | AR via get.data.gov.lt |
| `streets/{gat_kodas}/` | AR street code (7 digits) | `dct:Location` | AR |
| `persons/{asmens_id}/` | Seimas person id | `foaf:Person` | apps.lrs.lt |
| `org-units/{padalinio_id}/` | Seimas structural-unit id | `org:OrganizationalUnit` | apps.lrs.lt |
| `parliamentary-groups/{grupes_id}/` | Seimas parliamentary-group id (separate id space from `padalinio_id`) | `org:OrganizationalUnit` | apps.lrs.lt |
| `organizations/{slug}/` | name slug (no natural key in source) | `org:FormalOrganization` | e.g. `organizations/lietuvos-respublikos-seimas/` |
| `parties/{slug}/` | transliterated party-name slug (JAR code once matched — parties keep slug for continuity, `owl:sameAs`/`dct:identifier` carry the code) | `org:FormalOrganization` | apps.lrs.lt (VRK/JAR later) |
| `legal-entities/{ja_kodas}/` | JAR company code (9 digits) | `rov:RegisteredOrganization` | JAR via get.data.gov.lt |
| `taxonomies/{scheme}/` | scheme slug | `skos:ConceptScheme` | — |
| `taxonomies/{scheme}/{notation}/` | concept notation (classifier code or ASCII slug) | `skos:Concept` | JAR classifiers / hand-authored |

## Fragments (secondary entities inside a document graph)

| Fragment | Type | Used in |
|---|---|---|
| `#this` | the primary entity | everywhere |
| `#tenure-{kadencijos_id}` | `org:Membership` (Seimas seat) | persons |
| `#membership-{padalinio_id}-{yyyymmdd}` | `org:Membership` (committee/commission/faction position) | persons |
| `#pg-membership-{grupes_id}-{yyyymmdd}` | `org:Membership` (parliamentary group) | persons |
| `#...-interval`, `#...-start`, `#...-end` | `time:Interval` / `time:Instant` of a membership | persons |

## Taxonomy schemes

| Scheme | Concepts keyed by | Origin |
|---|---|---|
| `taxonomies/legal-forms/{kodas}/` | JAR form code | fetched from JAR |
| `taxonomies/legal-statuses/{kodas}/` | JAR status code | fetched from JAR |
| `taxonomies/position-types/{slug}/` | position-string slug | derived from Seimas members feed |
| `taxonomies/org-unit-types/{slug}/` | slug | static CSV |
| `taxonomies/settlement-types/{slug}/` | slug | static CSV |
| `taxonomies/street-types/{slug}/` | slug | static CSV |
| `taxonomies/admin-unit-levels/{slug}/` | slug | static CSV (only levels missing from EU ATU-type) |

Administrative levels use the **EU ATU-type authority table directly** as
`cv:level` values: `atu-type:LTU_APS` (county), `atu-type:LTU_MSV` /
`atu-type:LTU_RSV` / `atu-type:LTU_SV` (municipality kinds),
`atu-type:LTU_SEN` (eldership), where
`atu-type:` = `http://publications.europa.eu/resource/authority/atu-type/`.

## External alignment

- `owl:sameAs` → `http://www.wikidata.org/entity/Q...` (individuals),
  `skos:exactMatch` for taxonomy concepts — produced by the reconciliation
  stage into per-domain `alignments.trig` files.
- Images from Wikidata: `foaf:depiction` (photo P18, coat of arms P94),
  `schema:logo` (logo P154) — Wikimedia Commons `Special:FilePath` URLs.

## Custom vocabulary

Minimal custom terms live under the stable namespace `http://linkeddata.lt/ns#`
(prefix `ltlod:`), independent of `$base`. Currently:

- `ltlod:nominatedBy` — person → nominating party (a nomination is not a
  membership, and no EU/W3C vocabulary has a term for it).
