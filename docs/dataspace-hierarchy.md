> **Status: decided 2026-10-17: convention only, nothing deployed.** `linkeddata.lt` stays a single dataspace pair. Municipal subdomain dataspaces are a documented naming convention, created only when a municipality's own data exists. The naming option (below) is still open.

# Dataspace hierarchy: countries as domains, municipal sources as subdomains

## Verdict
- **No municipal dataspaces now.** Every LTLOD dataset comes from national registries, and `linkeddata.lt` already holds all the geographic levels (county → municipality → eldership → settlement/street) as RDF documents. An empty or mirrored `vilnius.linkeddata.lt` would add running cost and split the store for nothing.
- **Fix the naming in advance.** Hostnames become URIs and can't change once published. Documenting the rule now (free) means the first municipal dataset has a permanent home from day one.
- **When to create one:** when we ingest a source **the municipality itself publishes** (e.g. Vilnius municipal open data). National registries with a municipality column (schools, JAR, AR) stay in `linkeddata.lt`.

## How LDH resolves dataspaces
- **Flat registry; no sub-dataspaces.** `Application.getAppByOrigin` (in `../LinkedDataHub`) matches the request's normalized origin exactly against each `lds:origin`. `vilnius.linkeddata.lt` would be one more end-user + admin `lds:Dataspace` pair in `config/dataspaces.trig`, a peer of `linkeddata.lt`, not a child.
- **No parent relation.** The `lds:` vocabulary has `origin`, `ontology`, `service`, `public`, `allowRead` and similar, but no `parent`. A `dct:isPartOf` between dataspace resources only documents the relation; LDH ignores it.

So the hierarchy is **a naming hierarchy, not a runtime one**. With what LDH has today:

| Layer | Inherited from the national dataspace? | How |
|---|---|---|
| Name | Yes, visually | The `<municipality>.linkeddata.lt` hostname |
| Ontology and views | **Yes** | The municipal ontology `owl:imports <https://linkeddata.lt/ns#>`, reusing the national classes, labels and 1:N views and adding its own |
| Entities | By reference | Links to `linkeddata.lt/admin-units/{code}/#this`; dereferencing works across origins |
| Data / SPARQL | No | Separate store; cross-queries need `SERVICE <https://linkeddata.lt/sparql>` |
| ACL, owners, UI | No | Configured per dataspace (the stylesheet can point at the same `files/layout.xsl`) |

Real nesting (an `lds:parent` property with inherited ACL/ontology and union or federated queries) would be a new LDH feature in `../LinkedDataHub`, not configuration here.

## Hierarchy
```
                         ┌──────────────────────────────┐
  SUPRANATIONAL          │ linkeddata.eu  (hub)         │  indexes/aggregates national
  (separate domain)      │ admin.linkeddata.eu          │  dataspaces; links, never copies
                         └──────────────┬───────────────┘
                 links (owl:sameAs, void:Linkset, catalogue)
         ┌──────────────────────┼───────────────────────┐
         ▼                      ▼                       ▼
  NATIONAL (ccTLD = one dataspace pair per country)
  ┌──────────────────┐  ┌──────────────────┐   ┌──────────────────┐
  │ linkeddata.lt    │  │ linkeddata.lv    │   │ linkeddata.ee    │ …
  │ admin.…lt        │  │ admin.…lv        │   │ admin.…ee        │
  └────────┬─────────┘  └──────────────────┘   └──────────────────┘
           │
           │  subdomain = a municipality's own data sources (peer dataspace, not a child)
           │  ── NOT CREATED YET: convention only ──
           ├─────────────────────────┬──────────────────────────┐
           ▼                         ▼                          ▼
  ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
  │ vilnius.linkeddata.lt  │ │ kaunas.linkeddata.lt   │ │ …  (up to 60)          │
  │ admin.vilnius.…        │ │ admin.kaunas.…         │ │                        │
  │ municipal datasets:    │ │                        │ │                        │
  │ budgets, permits, …    │ │                        │ │                        │
  └───────────┬────────────┘ └────────────────────────┘ └────────────────────────┘
              │ links up to the national entity, doesn't redefine it:
              │ <#this> dct:spatial <https://linkeddata.lt/admin-units/13/#this>
              │
              ✗  no 3rd DNS level (elderships): *.vilnius.linkeddata.lt would need its own
                 wildcard cert and DNS, plus an admin twin, for bodies that don't publish data

  GEOGRAPHIC STRATA INSIDE linkeddata.lt (RDF documents, not DNS)
  linkeddata.lt/admin-units/            (flat container; see etl/URI-SCHEME.md principle 2)
  ├── 10/#this    Vilniaus apskritis      (county, adm_kodas)
  │     ▲ dct:isPartOf
  ├── 13/#this    Vilniaus m. sav.        (municipality, sav_kodas)
  │     ▲ dct:isPartOf
  ├── {sen_kodas}/#this   seniūnija       (eldership)
  │     ▲ dct:isPartOf
  ├── {gyv_kodas}/#this   gyvenvietė      (settlement);  streets/{gat_kodas}/
  ├── persons/…  organizations/…  legal-entities/…   ← span every stratum, so one store
  └── sparql                                         ← global queries stay possible
```

**How to read it:**
- **Boxes are dataspaces.** Each is an `lds:origin` entry in `dataspaces.trig`; all are peers.
- **Vertical lines between boxes are links**: HTTP dereferenceable RDF across origins. Nothing is inherited at runtime except via `owl:imports`, and there's no shared store.
- **The bottom tree is data**: the existing `dct:isPartOf` hierarchy inside one dataspace. A new geographic level means new documents, not a new subdomain.
- **Countries get ccTLDs, not subdomains** (see `docs/linkeddata-domains.md`).

## Pros and cons of municipal subdomains
**Pros**
- **Ownership is clear.** National registries stay at `linkeddata.lt`, municipal sources get the municipality's host; a URI's host says whose data it is.
- **Handover is easy.** A municipality can take over its dataspace (ACL, owners, admin) without any URI changing. This is the strongest argument, since URIs can't move later.
- **Isolation.** Large or messy municipal datasets don't slow down or bloat the national store, and each can be loaded, rebuilt or dropped on its own.
- **Branding.** A host the municipality can put on its own website, with its own home page.
- **Cheap infrastructure.** One `*.linkeddata.lt` wildcard cert and one DNS wildcard cover all 60; views come in through `owl:imports`.

**Cons**
- **No cross-municipal queries.** "Schools per municipality across Lithuania" needs `SERVICE` federation across up to 60 endpoints, or an aggregate copy in the national store.
- **Running cost grows per municipality.** Each is a dataspace pair with its own Fuseki dataset, Varnish cache, admin, install and `make load`. VM memory is already tight (see `docs/public-sparql-replica.md`).
- **Many sources aren't municipal.** Schools, JAR and AR are national registries with a municipality column and belong in the national store, so the subdomains would only hold genuinely municipal publications.
- **The names have to be designed** (below), and they're permanent once published.
- **No runtime hierarchy.** Search, SPARQL and the UI don't span dataspaces; users have to know which host to look on.

## Rules
1. **A municipal dataspace holds sources the municipality itself publishes.** National registries stay in `linkeddata.lt`, whatever their spatial column.
2. **Link, don't copy.** A municipal dataspace references the national entities (`linkeddata.lt/admin-units/{sav_kodas}/#this`) and never re-mints them; its ontology `owl:imports` the national `ns#`.
3. **At most two DNS levels:** country domain → municipality subdomain. No eldership subdomains.
4. **`*.linkeddata.lt` is reserved for dataspaces.** Never put a non-LDH service there (see `docs/public-sparql-replica.md`).
5. **Pilot with one municipality** (Vilnius has the most open data) and measure the operating cost and the cross-municipal query pain before adding more. If many follow, consider a national aggregate copy or a native `lds:parent` in LDH.

## Naming (open decision)
Constraints:
- **Six city/district name clashes:** Vilniaus (AR `13` m. / `41` r.), Kauno (`19` / `52`), Klaipėdos (`21` / `55`), Šiaulių (`29` / `91`), Panevėžio (`27` / `66`), Alytaus (`11` / `33`). Plain `vilnius.` is ambiguous.
- **Hostnames must be ASCII.** `šiauliai` would become `xn--…` punycode, so transliterate (š→s, ž→z, ė→e, ų→u, …).
- **Deterministic from the AR code** via one published table (all options below except C need one).

| Option | Vilnius city / district | Birštono sav. | Pro | Con |
|---|---|---|---|---|
| A. Official name, mechanical | `vilniaus-m` / `vilniaus-r` | `birstono` | Derived 1:1 from the official name (drop "savivaldybė", miesto→`m`, rajono→`r`, transliterate); no judgement calls | Genitive forms read oddly as hostnames |
| B. Colloquial name, `-r` suffix for districts | `vilnius` / `vilniaus-r` | `birstonas` | Nicest branding (`vilnius.linkeddata.lt`) | Nominative forms need hand-picking for all 60; mixes grammatical cases |
| C. AR code | `13` / `41` | `…` | No table, no clashes, mirrors `admin-units/{code}/` | Opaque to people; a digit-only label is legal but unfriendly |

Once chosen, publish the rule and the full AR code → host table in `etl/URI-SCHEME.md`.
