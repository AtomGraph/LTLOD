# CLAUDE.md

Lithuanian Linked Open Data: re-runnable ETL pipelines (`etl/`) that regenerate
RDF datasets (`datasets/current/`) from live open-data APIs on every run.

## Commands

```shell
cd etl && make                 # everything: taxonomies → calendar → admin-units → seimas →
                               # officials → declarations → legal-entities → elections → facilities → procurement → vtek
make -C etl/officials          # President, Government, mayors (Wikidata P39) + MEPs (EP API);
                               # reuses persons/{asmens_id}/ for officials who held a seat
make -C etl/<domain> all       # one domain (fetch is always fresh — FORCE prerequisite)
make -C etl/seimas photos      # opt-in: scrape official portraits from lrs.lt
make -C etl/seimas votes       # opt-in: plenary roll-call votes, latest term (VOTE_TERMS="9 10"
                               # for more; ~12k requests at VOTE_JOBS=6 concurrency, ~20 min);
                               # votes.trig is gitignored bulk output (~435k quads per term)
make -C etl/seimas bills       # opt-in: bills (+ member initiators) and plenary agenda items
                               # (stage, bills considered, speakers, e-seimas doc), same VOTE_TERMS
                               # scope; shares the votes' eiga/klausimai fetch (+1 agenda request per
                               # sitting, ~1 min per term for initiators); agenda-items.trig gitignored
make -C etl/legal-entities entities   # the full JAR register (~547k entities incl. deregistered;
                               # ~15 min, ~10 of them fetching; graphified in CHUNK_ROWS=25000
                               # chunks, JOBS=3 in parallel); entities.trig is gitignored bulk
                               # output (~14.4M quads, ~1 GB). `all` builds it too;
                               # `make -C etl/legal-entities institutions` = the committed part
make -C etl/elections all      # Seimas election results per constituency (ELECTIONS="2020 2024")
                               # from VRK's public ArcGIS layers, plus campaign finance
                               # (`finance`, CAMPAIGN_TYPES="SEI") from the browser-harvested
                               # data/vrk-*.csv (gitignored; skipped with a notice if absent)
/harvest-vrk                   # after an election's campaign reports: re-harvest VRK campaign
                               # income/expenses + Seimas candidates in the user's Chrome
                               # (atviriduomenys.vrk.lt is Cloudflare-blocked for scripts) ->
                               # etl/elections/data/; procedure: .claude/skills/harvest-vrk/
make -C etl/procurement        # public procurement contracts (VPT CVP IS via get.data.gov.lt
                               # datasets/gov/lsd/vpt/cvpp), windowed: concluded in the last 12
                               # months, >= 10 000 EUR (SINCE=…, MIN_VALUE=…); parties fetched in
                               # dok_id OR-batches (~56k contracts, ~30 min); contracts.trig is
                               # gitignored bulk output (~120 MB); amendments are excluded
make BASE=https://linkeddata.lt/   # prod base URI (default https://localhost:4443/, see etl/config.mk);
                               # committed datasets/current/ are base-RELATIVE (no @base) — identical
                               # for any BASE; the base is (re)applied at load/parse/validate time

/harvest-declarations          # yearly (after 1 Oct): re-harvest VMI property declarations in
                               # the user's Chrome (Claude in Chrome) -> etl/declarations/data/,
                               # then make -C etl/declarations; no scripted fetch exists
                               # (Cloudflare + IP block). Procedure: .claude/skills/harvest-declarations/
/harvest-vtek                  # re-harvest VTEK's lobbying register (SKAIDRIS) and politicians'
                               # private-interest declarations (PINREG) in the user's Chrome ->
                               # etl/vtek/data/*.json (gitignored), then make -C etl/vtek. Cloudflare
                               # on both hosts; PINREG search only via the app UI (its reCAPTCHA),
                               # details at >= 8 s/request (1.2 s got re-challenged after ~150).
                               # Procedure: .claude/skills/harvest-vtek/
/harvest-sodra                 # opt-in, not in `make all`: download Sodra's per-employer
                               # monthly-{yyyy}.csv.zip (atvira.sodra.lt, Cloudflare) in Chrome ->
                               # etl/sodra/data/ (gitignored), then make -C etl/sodra: one
                               # summary observation per employer (latest month + SODRA_MONTHS=12
                               # window aggregates) -> gitignored employment/employers.trig
                               # (~1.9M quads); SODRA_CUBE=1 adds the monthly series as overlay
                               # chunks observations-NNN.trig (~14M quads, SODRA_CHUNK=10000
                               # employers each); dataset.trig is committed.
                               # make -C etl/sodra test = the pipeline over synthetic fixtures

make -C etl/facilities         # ŠVIS education + VASPVT health-care institutions + KVR heritage
                               # (KVR: data.gov.lt XLSX snapshot, no coordinates); heritage.trig
                               # is gitignored bulk output (~43 MB)
etl/queries/run.sh <q.rq>      # SPARQL over ALL datasets, bulk-loaded into a temporary TDB2 store
                               # (~20 s load; arq's in-memory dataset walks every named graph for
                               # an unbound GRAPH ?g, so it is unusable with GRAPH-pattern queries)
python3 etl/queries/render-examples.py   # regenerate etl/queries/EXAMPLES.md result tables

uv run --project etl/tools ltlod-reconcile <admin-units|persons> [--base …] --input … --output …

make sef                       # compile the client-side XSLT override (files/client.xsl) to a
                               # Saxon-JS SEF (files/client.xsl.sef.json, gitignored). Run once
                               # BEFORE the first `make up` (the compose mount needs the file to
                               # exist) and after every edit to files/client.xsl; then recreate
                               # the linkeddatahub container to reload. See "Client-side XSLT".
cp .env_sample .env            # once: the deployment's settings; .env is gitignored (LDH's
                               # convention), .env_sample holds the local defaults
make up ARGS=-d                # deploy LinkedDataHub at https://localhost:4443/ (shared
                               # Makefile; bootstraps secrets + server cert, then
                               # docker compose up $(ARGS) — WITHOUT -d it stays attached
                               # to the logs, and stopping it stops the stack)
make install                   # set up the dataspace via LDH CLI: make it public + PUT app/
                               # scaffolding (root + containers + taxonomy schemes) + install
                               # app/ns.ttl (1:N views) into the admin ontologies/namespace/
                               # doc; needs ../LinkedDataHub (LDH_HOME=…).
                               # Interactive, LinkedDataHub-Apps style: prompts for Base URL /
                               # cert / password / proxy, defaults = the local stack (Enter×4
                               # or `printf '\n\n\n\n' | make install`); enter another Base URL
                               # + owner cert to install onto any LDH instance
make load                      # bulk-load datasets/current/*/*.trig into the end-user TDB2 dataset;
                               # resolves the base-relative TriG against BASE_URI (.env) via riot
                               # before tdb2.tdbloader; ends with `make public` (anonymous read)
make down / make drop          # stop stack / wipe LDH runtime state (never datasets/current/)
```

Prerequisites: Docker (only for `atomgraph/csv2rdf`; no docker-compose), Apache Jena
**5.6.0** (`JENA_HOME` — arq 6.x cannot output quad CONSTRUCT results at all:
"No dataset writer for Turtle_pretty", `--results=trig` dropped; see
[apache/jena#4091](https://github.com/apache/jena/issues/4091)), `xsltproc`,
`uv`, `make`, `curl`. The `make
sef` target additionally needs Node/`npx` (`xslt3-he`, the Saxon-JS compiler) and
`xmlstarlet`.

## Architecture

Every domain runs the same four stages (shared scripts in `etl/lib/`):

1. **fetch** — full dump from live API (Spinta UAPI CSV export with `select(...)`
   incl. dereferenced parent keys, e.g. `apskritis.adm_kodas`; Seimas XML). Fails
   loudly on empty results. Cache dirs are gitignored. Child feeds keyed by a parent
   id (Seimas sessions per term, sittings per session) go through
   `etl/lib/fetch-xml-each.sh` (ids read with xmlstarlet, one document per id, merged
   under a wrapper element before `xsltproc`).
2. **normalize** — CSV → CSV2RDF identity transform (docker), XML → XSLT 1.0
   (`xsltproc`), both emit source-shaped RDF with `<{base}#column>` properties.
3. **graphify** — LDH-style quad `CONSTRUCT { GRAPH ?graph {…} }` mapping
   (`mappings/*.rq`, `$base`-parameterized) executed by `arq`; the CONSTRUCT mints
   ABSOLUTE IRIs in-model, then `etl/lib/relativize.sh` rewrites the output to
   base-RELATIVE IRIs with no `@base` → TriG. The `.rq` files are reusable verbatim
   as LinkedDataHub CSV imports. (`ltlod-reconcile`/photos take `--base` as the
   rdflib publicID and are relativized the same way; see the relative-TriG gotcha.)
4. **validate** — `riot --validate` + every graph must have `dct:title` and
   `foaf:primaryTopic` on the graph URI (see `etl/lib/validate.sh`) + SHACL
   shapes per entity type (`etl/shapes/<domain>.ttl`, auto-selected by output
   dir, executed via `etl/lib/shacl.sh`; also run in CI on committed datasets
   by `.github/workflows/shacl-validation.yml`). Both `validate.sh` and `shacl.sh`
   take a base to resolve the relative IRIs (validate.sh pre-resolves to N-Quads).

Post-ETL: `ltlod-reconcile` matches entities to Wikidata (closed candidate sets
via WDQS, exact label + parent disambiguation) and writes `owl:sameAs` + images
into per-domain `alignments.trig` (same graph names as the entity docs, so they
merge on load). Unmatched entities go to `cache/unmatched*.csv`, never force-matched.
Emitted image URLs (the coat of arms P94 → `foaf:img`, other photos P18 →
`foaf:depiction`, `schema:logo` from P154; and the lrs.lt portraits from the photos
scraper → `foaf:depiction`) are https-normalized (WDQS returns http:// Commons URIs,
which GitHub/browsers won't render) and HTTP-liveness-checked via `ltlod_etl.images`
— dead images are skipped so they never enter the data (`--no-image-check` disables
the check for offline/CI runs). The liveness check **retries 429/503** with backoff
(Commons rate-limits liveness bursts; a naive check treats the 429 as "dead" and
strips live images en masse). **P94 goes on `foaf:img`, not `foaf:depiction`,
deliberately**: `foaf:img` is `rdfs:subPropertyOf foaf:depiction` ("particularly
representative"), and LDH's `ac:image` thumbnail selector ranks `foaf:img` >
`foaf:logo` > `foaf:depiction`, picking only the first — so grid/card views (e.g.
the frontpage AdminUnit grid) show the coat of arms deterministically, while the
scenery photo stays a plain `foaf:depiction` on the entity page. Persons have no
coat of arms but can still carry several `foaf:depiction` (P18 *and* the scraped
lrs.lt portrait); showcase queries that render one image per row must collapse that
(filter to one source, or `GROUP BY` + `SAMPLE`) — plain `SELECT DISTINCT` won't,
since the rows differ in the image cell.

## Conventions (load-bearing)

- **Entity per named graph**: graph URI = document URI `{base}{container}/{slug}/`,
  entity = `{graph}#this`, secondary entities are `#fragment`s. Slugs are **natural
  keys** from the source registry (AR codes, JAR codes, Seimas `asmens_id`) — any
  pipeline mints cross-links from bare foreign keys. Single source of truth:
  `etl/URI-SCHEME.md` — update it when adding containers.
- **No blank nodes, ever**: every resource in ETL output is a minted IRI — a
  document, its `#this`, or a `#fragment` (deterministic, from natural keys: e.g.
  `#tenure-{kadencijos_id}-{yyyymmdd}`, a declaration's `#{category}` amount). Blank
  nodes can't be linked to, dereferenced, or updated in place by LDH, and they make
  re-runs non-diffable. `etl/lib/validate.sh` fails any output that has one. CSV2RDF's
  row bnodes are intermediate (`cache/`) and must never reach the CONSTRUCT template.
- **LDH document hierarchy**: ETL outputs are *only* `dh:Item` docs with
  `sioc:has_container <its-container>` — add both triples in any new mapping,
  plus `dct:created ?now` with a top-level `BIND(NOW() AS ?now)` at the end of
  the WHERE (the build timestamp; `make load` bypasses LDH, which would set it).
  Containers and taxonomy scheme docs come from `app/` (one Turtle file per
  container, PUT via LDH CLI by `make install`); each carries an
  `rdf:_1 <#select-children>` → `ldh:Object`/`ldh:ChildrenView` block, without
  which LDH renders no children listing at all. `app/persons.ttl` swaps the stock
  `ldh:ChildrenView` for its own `ldh:View` + `sp:Select` (`ac:GridMode`) so the
  listing gets person filter/sort columns — see the next bullet.
- **Container listings**: keep a children listing only where its first page, in a
  meaningful order, answers something, and its query fits the page's time budget;
  otherwise leave it out and rely on the other ways in (the hierarchy, cross-links,
  calendar days, charts). The stock `ldh:ChildrenView` sorts by title and counts every
  child for paging, so its cost grows with the container: ~17 s + ~5 s for the 547k JAR
  entities, where `persons/` (~1k) takes well under a second. Measure the query, not the
  child count. Current choices: `streets/` has no listing (reached from settlements);
  `admin-units/` lists only the 10 counties (the top of the hierarchy); `calendar/`
  lists the years.
- **1:N entity views**: cross-entity listings (county → municipalities, committee
  → members, party → nominees, Seimas → terms, term → sessions / members, session →
  sittings, activity type → its sittings or sessions, person → terms, sitting → votes,
  person → votes per choice, decision method → votes, calendar day → its sittings / votes /
  procurement contracts / election rounds / campaign donations / expenses, term → its election, election →
  constituency contests / campaign participants, constituency → its contest, person →
  candidacies, party → list results by constituency, person or party → campaign
  accounts, campaign participant → income / expenses, organization → campaign
  donations made / services provided,
  year → months → days, sitting → agenda items, agenda item → votes, bill → agenda items /
  votes, person → bills initiated / items spoken on, stage → items, day → items / bills,
  Government / President / EP / municipality → office holders, legal entity → its procurement
  contracts as buyer / as contractor — two views on `epo:playedBy`, the ePO role's agent; VTEK: lobbyist → declarations, person / institution / draft act /
  area / day → lobbying, legal entity → officials with a declared tie, declaration → ties) are `ldh:inverseView` definitions in `app/ns.ttl`
  (the LDH namespace ontology, northwind-traders style): `<property>
  ldh:inverseView <ldh:View>` + `spin:query` → `sp:Select` with `$about`. LDH
  shows a view on every instance whose `rdf:type` matches the property's declared
  `rdfs:range` — exact type match, no subsumption, so view targeting relies on
  discriminating types in the data (`schema:PoliticalParty` for parties,
  `cv:PublicOrganisation` for the Seimas, `schema:EventSeries` / `schema:Event` for
  sessions / sittings, which are both `eli-dl:Activity`). Views attach **per
  property**: every `ldh:inverseView` of a property shows on every type in its
  `rdfs:range`, so a new link needing its own view needs its own property — never
  reuse one that already carries a view (`dct:isPartOf` carries `:SubUnits`, hence
  session → term is `eli-dl:parliamentary_term`, sitting → session
  `eli-dl:forms_part_of`). Views set `ldh:showWhenEmpty false`, so a view whose query
  finds nothing for a given instance stays hidden. `app/import-ns.sh` (called by `make
  install`) installs it with `ldh admin import ontology --file`, which replaces the
  admin `ontologies/namespace/` document (served at `{base}ns`) and evicts the
  server-side ontology cache.
- **View filter/sort columns**: LDH builds a view's facet pills and its sort
  dropdown from the BGP triples whose **subject is the query's FIRST projected
  variable** and whose **object is a variable** (`ldh:RenderFacets` and
  `$var-predicates` in LDH's `client/block/view.xsl`). Those variables must stay
  **unprojected**: LDH wraps the SELECT into `DESCRIBE *`, so every projected term
  becomes a rendered card/row — hence the "project a single entity type" rule in
  `app/root.ttl`. Consequences for authoring a view query:
  - the focus variable has to be the entity carrying the columns (`?person` =
    `{doc}#this`, never the `dh:Item` document — the attributes hang off `#this`);
  - a column is only a *filter* pill when its predicate is a plain URI (a property
    path still yields a sort option, labelled with the bare variable name);
  - a column triple may sit inside an `OPTIONAL` (LDH collects BGPs at any depth of
    the parsed query), so a column the entities don't all carry needn't filter them
    out — `app/persons.ttl` keeps `foaf:gender`/`ltlod:nominatedBy` optional;
  - column labels come from the `{base}ns` ontology, so every faceted predicate
    needs an `rdfs:label` in `app/ns.ttl`;
  - `ORDER BY` sets the initial sort; a second condition is the tie-breaker. Both
    are re-applied client-side over the (unordered) DESCRIBEd graph;
  - opening a pill makes LDH append a label lookup to the facet-value-count query
    that ARQ cannot index inside a `GRAPH` block (~104 s per pill → 500);
    `files/client.xsl` rewrites it — see the XSLT overrides below. Keep writing
    `GRAPH ?graph` in view queries.
  Person listings — the `persons/` container view and the `:CurrentMembers`,
  `:FormerMembers`, `:NominatedMembers`, `:MembersElectedHere` ontology views —
  therefore project only `?person` and carry `foaf:givenName`/`foaf:familyName`/
  `foaf:gender`/`ltlod:nominatedBy` triples, sorted by family then given name.
- **XSLT overrides** (`files/`): custom Saxon-JS templates that change how LDH
  renders, layered over the stock stylesheets — the linkeddatahub.com pattern.
  Three files mounted over the running image's `ROOT/static` for the
  **end-user app only** (admin untouched), plus one compiled into the SEF only:
  - `files/overrides.xsl` — the **shared** module: suppresses the n-ary
    membership plumbing blocks (`ldh:BlockRow`). Matching is **property-centric via
    `key()`**, never bare `rdf:type`, so a block is hidden only when it is a
    rendered target of the `:Memberships` 1:N view *on this page* — a membership
    whose `org:member` is `key('resources', ac:absolute-path(ldh:request-uri()))`'s
    `foaf:primaryTopic`; an interval/instant that is the object of
    `org:memberDuring` / `time:hasBeginning`|`hasEnd` (`key('predicates-by-object',
    …)`). Imported by **both** client.xsl and layout.xsl so the blocks are omitted
    server-side *and* client-side — server-only would still let CSR re-render them
    (flash); client-only lets the server render them first (flash).
  - `files/client.xsl` — imports `client.xsl` + `overrides.xsl`; overrides the
    stock `ldh:bgp-value-counts` **facet label lookup**: to label a filter pill's
    values LDH appends `OPTIONAL { { ?value <7-way alt path> ?label } UNION
    { GRAPH ?g { … } } }`, and ARQ does not resolve an alternative path through the
    quad indexes inside a `GRAPH` block — it walks the ~117k named graphs, so one
    pill took ~104 s (a 500 in the browser). The override emits the equivalent
    `?value ?labelProp ?label` + `FILTER (?labelProp IN (…))` (same predicates,
    same order, so `SAMPLE(?label)` is unchanged) — ~0.1 s per pill. It also adds
    the **client-only** `:Memberships` table tidy (restrict columns to role /
    organization / memberDuring, drop the anchor column, render the `memberDuring`
    cell as the interval's `dct:title` period *text* not a link). Compiled to the
    SEF; the view table is client-rendered so these needn't run server-side.
    Also **overrides the stock `ldh:geo-resources-string` global param** (from
    navigation.xsl — the default geo-map modal query) to add
    `FILTER EXISTS { ?resource a cv:AdminUnit ; gsp:asWKT ?wkt }`: the stock query `DESCRIBE *`s
    every `geo:lat/long` resource (~21k, incl. all point-only settlements) → ~21 MB
    → exceeds `MAX_CONTENT_LENGTH` (4 MB) → **502**. The filter keeps only the ~606
    admin units with a WKT boundary → ~3.1 MB (the type is load-bearing: the ~22.5k
    streets carry centreline WKT too, as `dct:Location`). Scoped map
    views (`:SubUnits`, the frontpage counties map) use their own `spin:query` and
    are unaffected, so settlement points stay mappable there.
    And it **overrides the pivot-discovery query** (`ldh:link-predicates`, the
    view's link-predicate chips): the stock query joins the view with the
    outgoing/incoming UNION and deduplicates with a top-level DISTINCT, which on
    persons/ walks ~4.9M incoming vote quads (27.7 s on prod); the override joins
    each direction separately with a `GROUP BY ?predicate` per subquery — same
    rows, 8.5 s. A hotfix: drop it once LDH ships the same query.
  - `files/layout.xsl` — imports base `layout.xsl` + `overrides.xsl`; repoints the
    client bootstrap (`xhtml:Script` → `client-stylesheet`) at our SEF, and
    **replaces the stock `ac:Footer`** with the LTLOD one (own wordmark, dataset
    shortcuts, source attribution, licence; the developer entry points — SPARQL,
    example queries, dataset downloads, `{base}ns` — live there instead of on the
    frontpage). The footer keeps the stock markup contract, since `app.css` styles
    it structurally: `.ldh-footer > .cols` is a `1.4fr repeat(4, 1fr)` grid, so
    exactly one `.brand-col` plus FOUR `.col` children, each a `.ftitle` followed
    by bare `<a>`s, then `.legal` with two space-between spans. Only the wordmark
    `.mark` deviates — restyled inline to the Lithuanian tricolour, class-supplied
    geometry kept. Footer-only because `ac:Footer` is applied ONCE server-side
    (LDH `layout.xsl`) and never re-rendered by client.xsl — so it belongs here,
    not in `overrides.xsl`, and needs no SEF rebuild. Likewise it overrides the
    header wordmark (`ldh:Brand`) with the same tricolour `.mark`; the header text is
    the dataspace `dct:title` in `config/dataspaces*.trig` — keep it `linkeddata.lt`,
    matching the footer wordmark. And it extends `xhtml:Meta` with the **social-preview
    image**: stock LDH emits `og:image` only from the page *document*'s `ac:image`, which
    ETL docs never have, so it falls back to the `foaf:primaryTopic`'s image (Commons
    SVGs get `?width=630` → PNG thumbnail; unfurlers don't render SVG), else the
    `files/og-image.png` card (1200×630, mounted at `static/lt/linkeddata/og-image.png`;
    regenerate from `files/og-image.html`, see its header comment). Mounted at the end-user app's
    `ac:stylesheet` target `static/xsl/layout.xsl`; imports `overrides.xsl` from
    `static/xsl/` (its own dir).
    **Declare `xmlns="http://www.w3.org/1999/xhtml"` on `xsl:stylesheet`** whenever
    this file emits literal result elements: LDH's own layout.xsl declares it, so
    its bare `<div>`s are XHTML; without it ours land in no namespace and the
    serialiser emits a stray `xmlns=""` on the block (HTML parsers ignore it, but
    namespace-sensitive XPath/XSLT matching on `xhtml:*` then misses those nodes).
  - `files/calendar-mode.xsl` — imported by `client.xsl` (client-only, in the SEF,
    not mounted): **`ltlod:CalendarMode`, a generic view layout mode** that draws a
    view's results as Monday-first month grids, each result on the date of the
    view's ORDER BY predicate (else its first `xsd:date`/`dateTime`); one month →
    a full-size grid with items, several → compact year-style grids. Calendar days
    themselves link their cell and show their holidays. It appears in every view's
    mode switcher (`ac:mode ltlod:CalendarMode` makes it a view's default, as on
    `:CalendarDays`, the month/year page view). LDH's mode list is closed, so the
    wiring redeclares `$ldh:class-modes` / `$ldh:mode-icons`, wraps the switcher
    items and the switcher click with `xsl:next-match`, and **copies three named
    templates from the pinned image's `client/block/view.xsl`** — `ldh:ViewModeSwitcher`,
    `ldh:ViewModeChoice`, `ldh:RenderView` — each with one marked `LTLOD:` change
    (in `RenderView`: the request goes out unpaged, ≤ 1000, **in calendar mode only**;
    the cached query keeps its paging). **Re-sync those three on every LDH image
    upgrade** (diff against the image's `view.xsl`, not `../LinkedDataHub` — they
    can differ). Upstreaming plan: `docs/calendar-view-mode.md`.
  Wiring: `make sef` c14n's `client.xsl`+`overrides.xsl`+`calendar-mode.xsl` (`SEF_EXTRA`) and compiles the SEF
  against the pinned image's `static/` tree; `docker-compose.yml` bind-mounts the
  four files (`layout.xsl`, `overrides.xsl` under `static/xsl/`; `client.xsl`,
  `client.xsl.sef.json` under `static/lt/linkeddata/xsl/`). Rebuild the SEF + recreate
  the container after editing any of them — `docker compose restart linkeddatahub`
  does NOT pick up an edited mount (it keeps serving the stylesheet compiled at the
  previous start); `docker compose up -d --force-recreate linkeddatahub` does, and
  then restart `nginx`/varnish per the 502 gotcha below. The `:Memberships` table
  replaces the suppressed blocks; it needs a readable period, so `persons.rq` puts a `dct:title`
  (e.g. `"2024-11-14 – dabar"`) on each `time:Interval` — `ldh:View`/`ac:TableMode`
  is DESCRIBE-based, so date literals can't be view columns; the interval's
  `dct:title` surfaces in the `org:memberDuring` cell via object-label resolution.
- **Vocabulary cascade**: W3C specs first → domain-specific third-party vocabs
  (EU SEMIC, OP authority tables, FOAF) → schema.org as general fallback → custom
  (`http://linkeddata.lt/ns#`) last. Rationale per domain: `etl/ONTOLOGY-NOTES.md`.
- **Change over time**: n-ary `org:Membership` + `org:memberDuring` → `time:Interval`
  (W3C Time). No reification, no RDF-star. Current state = interval without `time:hasEnd`.
- **Docs in Lithuanian** (README, EXAMPLES.md); code, code comments and CLAUDE.md
  in English. Python is uv-managed (`etl/tools/`).
- Committed outputs live in `datasets/current/`; bulk regenerable files
  (settlements/streets TriG, ~59 MB; the calendar, ~16 MB) are gitignored.
- **Temporal relationships link to the calendar (ETL rule)**: every date in ETL
  output is a link to a calendar document *as well as* a literal. Days are
  `calendar/{yyyy}/{mm}/{dd}/#this` (plus month/year docs, `time:intervalIn`),
  generated offline by `etl/calendar/` from 1977-01-01 (the earliest JAR registration) to
  the end of next year.
  When a mapping emits a date:
  - **an event on a day** (sitting, vote): `?entity dct:temporal ?day` on the
    entity itself;
  - **a period** (term, session, membership, any validity span): a
    `time:Interval` (`time:hasTime` / `org:memberDuring`) with `time:hasBeginning` /
    `time:hasEnd` → `time:Instant` (`time:inXSDDate`), and each instant gets
    `?instant dct:temporal ?day` — never link the entity straight to its start/end
    day, which would erase the begin/end distinction. If the source has the period
    only as literals on the entity (ELI-DL `activity_start_date`), add the interval
    beside them (as sessions.rq does);
  - **mint `?day` from the date, no lookup**: `IF(BOUND(?date), uri(concat(str($base),
    "calendar/", REPLACE(STR(?date), "-", "/"), "/#this")), ?undef)`, bound after
    the OPTIONALs, in the same guard as the date;
  - **keep the literal** (`eli-dl:activity_date`, `time:inXSDDate`, …): views sort
    and range queries need it;
  - **make it visible**: add an `ldh:inverseView` on `dct:temporal` in
    `app/ns.ttl` whose query reaches the entity (through the instant for periods;
    `ldh:showWhenEmpty false`) and extend `dct:temporal`'s `rdfs:domain`;
  - **validate**: a `dct:temporal` property shape (IRI, path pattern
    `/calendar/[0-9]{4}/[0-9]{2}/[0-9]{2}/#this$`) in the domain's SHACL, then the
    dangling check against calendar.trig's `foaf:primaryTopic`s (must be 0) and a
    day page in the browser;
  - **dates before the calendar start** (1977-01-01, set by the earliest JAR
    registration 1977-11-11) would dangle: extend the calendar range in
    `calendar.rq` first (start date + the weekday offset), never drop the link.
  Linked now: sittings, votes, agenda items, bill registrations, election rounds, campaign donations and expenses, procurement contracts, lobbying declarations, lobbyist registrations (event; a
  contract's expiry date is left out — it reaches 2055, past the calendar); terms,
  sessions, Seimas seats, unit positions, parliamentary groups, public offices —
  `etl/officials/`, legal-entity registration / deregistration, PINREG ties (instants). Not yet:
  admin-unit validity. Days that were public holidays carry
  `dct:type` → `taxonomies/holidays/{slug}/#this`, matched in `calendar.rq` from
  `etl/calendar/data/holidays.csv` (rules: fixed date / Easter + offset, Easter
  computed in SPARQL / first Sunday of a month; per-row validity by the acts'
  effective dates — add a row, never edit history away, when the law changes).

## Gotchas

- **LDH's top-level stylesheet params and variables carry the `ldh:` prefix** (6.2):
  an override must use the prefixed name (`ldh:geo-resources-string` in
  `files/client.xsl`, declared in LDH's `client/navigation.xsl`). An override of the
  old unprefixed name still compiles and is **silently ignored** — the stock value wins
  (for the geo-map query that means the 21 MB response and the 502 again). After an
  LDH upgrade, grep `files/*.xsl` for every global `xsl:param` that overrides a stock
  one and check its name against the LDH stylesheets.
- **`$ldt:base` no longer exists in LDH** — use `lds:base()` (`xs:anyURI`, the dataspace base) in
  `files/layout.xsl` and `files/client.xsl`. LinkedDataHub `ffc28c0f4` and Web-Client `d7cac4638`
  (2026-09-12) removed the param with no back-compat shim, so an app stylesheet still referencing it
  fails to compile (`XPST0008` -> "Too many errors") and EVERY end-user page 500s. `xmlns:lds` must
  be declared on the stylesheet. Both stylesheet trees define `lds:base()`, so the same call works
  server-side (`server.xsl`) and client-side (`client/functions.xsl`).
- **BINDs inside OPTIONAL are evaluated bottom-up**: a BIND referencing an outer
  variable (e.g. `?graph`) silently unbinds and drops triples. Keep only triple
  patterns inside OPTIONAL; do URI construction after it, guarded with
  `IF(BOUND(…), …, ?undef)` (see `etl/seimas/mappings/persons.rq`).
- **An exported `JENA_HOME` beats `etl/config.mk`**: it pins 5.6.0 with `?=`, so a
  shell that exports `JENA_HOME` (e.g. a 6.x install) silently overrides it and the
  quad CONSTRUCT fails. Run the ETL with `JENA_HOME=…/apache-jena-5.6.0 make …`.
- **CSV2RDF must run via docker** — the local jar (`../CSV2RDF/target`) NPEs on
  modern JDKs (tested Java 25).
- **Jena `shacl validate` ignores TriG named graphs** (validates the empty
  default graph → trivially conforms) and **always exits 0** — `etl/lib/shacl.sh`
  flattens with `riot --merge` first and parses the `--text` report. Shapes must
  stay host-agnostic (path-suffix `sh:pattern`s, never the base host).
- Quad `CONSTRUCT { GRAPH … }` is an ARQ extension — works in `arq` CLI (its
  default syntax) and LinkedDataHub, not in strict SPARQL 1.1 engines.
- **Cross-graph queries use standard `GRAPH` patterns, never `FROM
  <urn:x-arq:UnionGraph>`** (Fuseki/ARQ-specific). One `GRAPH ?xGraph {…}` block per
  *document*: an entity doc holds `#this` and all its `#fragment`s (a person's
  memberships, intervals, instants, portraits; a declaration's amounts; a term's
  interval), and joins happen across blocks. Consequences:
  - a property path that crosses documents can't sit inside one block — split it into
    hops (`dct:isPartOf+` settlement → county is a UNION of the 2- and 3-hop chains,
    see `app/admin-units.ttl`);
  - a block is evaluated on its own, so a `BIND`/`FILTER EXISTS` inside it can't see a
    variable bound outside it (it silently matches everything) — put such tests after
    the block, with the GRAPH inside the EXISTS (`app/stories/seimo-turtas-2024.ttl`
    votes query);
  - no alternative path (`a|b`) with an unbound subject inside a block (see the
    facet-pill note) — use `?p` + `FILTER(?p IN (…))`.
  App chart and view queries (`app/*.ttl`) and `etl/queries/*.rq` follow this.
- **Avoid per-row `FILTER NOT EXISTS` over the full dataset** in ad-hoc integrity
  checks — quadratic, hangs for ~40 min on ~800k quads. Dump both URI sets with
  two SELECTs and `comm -23` instead.
- `arq` CONSTRUCT output ordering is nondeterministic across runs → large git
  diffs with no real changes. Compare with `riot --output=nquads | sort` when in doubt.
- Spinta (get.data.gov.lt) is pre-alpha: model paths can drift; fetch scripts
  fail on unknown properties (HTTP 400) by design. Its `:format/rdf` output is
  nonstandard RDF/XML — always pull CSV instead.
- Seimas API params: `kadencijos_id` (not `p_kade_id`); position rows may reference
  units absent from current feeds (dissolved commissions, the Board) — org-units
  mapping derives those from the members feed.
- **Switching `BASE` auto-invalidates static-CSV taxonomies** via the
  `cache/.base` stamp in `etl/taxonomies/Makefile` (normalize outputs embed
  the base URI; fetched domains are immune — fetch is FORCE'd). Note `make
  clean` alone does NOT force the rebuild: missing `cache/*.nt` are
  intermediate files, which make skips when the `.trig` looks up to date.
- **`make load` bypasses LDH's HTTP API**: it runs `tdb2.tdbloader` directly against
  the end-user TDB2 store via the one-off `tdb-loader` compose service (the
  `atomgraph/fuseki` image bundles the full Jena CLI inside the fuseki-server jar).
  Because the committed TriG is base-relative, the service first resolves it against
  `BASE_URI` (from `.env`, passed as `-e BASE_URI=…`) with `riotcmd.riot --base=…
  --output=nquads`, then loads the N-Quads (tdb2.tdbloader has no `--base`).
  Load is append-only — clean rebuild: `make down && rm -rf fuseki/end-user &&
  make up && make load`. It stops fuseki first — one server now holds both roles, so
  the admin store goes down with it — and removes the stale `tdb.lock` (lock PIDs are
  container-relative), then restarts the Varnish caches.
- **`docker-compose.yml` is a verbatim mirror of `../LinkedDataHub/docker-compose.yml`**
  — a byte-identical copy, so `diff ../LinkedDataHub/docker-compose.yml docker-compose.yml`
  prints nothing. Every LTLOD-specific delta lives in the **committed**
  `docker-compose.override.yml` (compose auto-merges it), the `image:` lines that stand
  in for the base's `build:` included — this repo has no Dockerfile:
  `linkeddatahub` and `sef-compiler` images, `TZ="Europe/Vilnius"`,
  `ENABLE_WEBID_SIGNUP=false`, the `openai_api_key` secret + `OPENAI_API_KEY_FILE` for
  the `web-algebra` assistant (as in LDH's own override), and the
  `tdb-loader` bulk-load service (`profiles: [ load ]`, so `make up` skips it and `make
  load` starts it via `docker compose run`). The assistant is **opt-in** (LDH 6.2.1): the
  base puts `web-algebra` under the `assistant` profile, so it runs only with
  `COMPOSE_PROFILES=assistant` in `.env` (LDH reads the variable too and offers the
  assistant in the UI only then); it then needs `secrets/openai_api_key.txt`, which
  `make secrets` does not generate. Re-sync from upstream by re-copying LDH's
  file — no LTLOD edit touches the base. Both images are `:latest`, **not pinned**: they
  move with each LDH release, and `make sef` compiles against the image's `static/` tree,
  so after a pull run `make sef` + recreate, or the client SEF is stale.
- **The `Makefile` is LDH's canonical deployment Makefile, byte-identical to
  `../LinkedDataHub/Makefile`** (`up`, `down`, `secrets`, `cert`, `sef`, `public`,
  `load`, `drop`, …) — never edit it; re-sync with `cp ../LinkedDataHub/Makefile .`.
  LTLOD settings live in `make/config.mk` (e.g. `LOAD_STAGING`), its own targets
  (`install`) in `make/local.mk`.
- **Committed TriG is base-RELATIVE with no `@base`** (base-agnostic: one dataset
  serves any deployment base). RDF stores only absolute IRIs, so the base must be
  reapplied on EVERY read — always pass `--base` to `riot`/`arq`/`shacl`
  (`riot --base=$BASE …`) or relative IRIs resolve to `file://…` garbage. The write
  path (`etl/lib/relativize.sh`) uses riot's STREAMING trig writer (`--output`, which
  relativizes against a prepended `@base`; `--formatted` does NOT) and strips the base
  header. Only base-internal IRIs relativize; external URIs (Wikidata, Commons, lrs.lt,
  EU tables, schema.org, mailto/tel) stay absolute. Round-trip proof:
  `riot --base=$BASE --output=nquads file.trig | sort` is base-independent.
- **Admin-unit coordinates live in `*-geo.trig`** (`ltlod-geo`, from the AR spatial
  `gra*` models), merged on load like `alignments.trig` — the committed level
  `*.trig` carry no geo. LDH map mode (`ac:MapMode`) plots `geo:lat`+`geo:long`
  (WGS84 point marker) and/or `gsp:asWKT` (GeoSPARQL polygon). **⚠ EPSG:3346 (LKS-94)
  axis order is (Northing, Easting)**: the source WKT stores the ~6·10⁶ northing
  first, ~3–6·10⁵ easting second, so `ltlod-geo` feeds pyproj `(easting, northing)`
  under `always_xy=True` → `(lon, lat)`. Every point is bounds-checked against
  Lithuania's bbox — a swapped axis lands far outside and aborts. Sanity check:
  Vilnius ≈ lat 54.6–54.7, lon 25.2–25.3.
- **Geometries are `gsp:asWKT` on `#this`, simplified, coarse levels + streets**
  (`ltlod-geo --simplify <metres>`, set per level in `admin-units/Makefile`). The WKT
  must be **bare WGS84 lon-lat** (no leading `<crs>` URI — OpenLayers' `ol.format.WKT`
  can't parse one) typed `http://www.opengis.net/ont/geosparql#wktLiteral`; put it
  directly on `#this` (not a `geo:hasGeometry` node) so the map feature id is the unit
  URI. LDH does **no** client-side simplification (raw polygons are ~160 MB), hence
  Douglas–Peucker in ETL. No LTLOD XSL change needed — `map.xsl` ships via the
  imported stock `client.xsl`; the committed coarse `*-geo.trig` hold points + WKT,
  settlements stay point-only. Streets get centreline `LINESTRING`s (gitignored
  `streets-geo.trig`, `ltlod-geo --container streets/`) from `gragatve/GraGatve`,
  whose own `gat_kodas` is a code space disjoint from the register's — no crosswalk is
  published, so `ltlod-streetkeys` re-keys it by joining on (settlement `gyv_kodas`,
  "name abbr.") against current `gatve/Gatve` rows (22 543 of 22 547 match uniquely;
  ambiguous keys are skipped, never guessed). ~⅓ of register streets have no centreline.
- **Fuseki ports are never published to the host** — query via
  `https://localhost:4443/sparql` or from inside the network:
  `docker compose exec linkeddatahub curl http://varnish-end-user/ds/`.
- **LDH strips client-sent `sioc:has_parent`/`sioc:has_container` on PUT** and
  manages the hierarchy itself (re-adds `sioc:has_parent` for `dh:Container`,
  adds `dh:Item` + `sioc:has_container` otherwise, plus `dct:created`/
  `acl:owner`) — never put sioc triples in `app/*.ttl`. `make install` is
  idempotent: PUT replaces the whole named graph.
- **Public read access is class-based**: both `make public` and `make install` run
  `ldh admin make-public` through LDH's HTTP API, granting
  `acl:accessToClass def:Root, dh:Container, dh:Item, nfo:FileDataObject` —
  ETL documents match because mappings type them `dh:Item`/`dh:Container`.
  (Untyped docs would also pass: LDH's ACL query leaves `$Type` unbound when
  a document has no `rdf:type`, matching any `acl:accessToClass` — see
  `AuthorizationFilter` + `aclQuery` in LDH web.xml.)
- `COMPOSE_PROJECT_NAME=ltlod` isolates container/volume names from other local
  LDH stacks, but ports 81/4443/5443 still clash — one stack at a time.
- **502 on all public endpoints after restarting backend containers** (fuseki,
  varnish): nginx resolves upstream container IPs at startup — restart nginx
  too. `fuseki` runs with `-XX:+ExitOnOutOfMemoryError` and `restart: on-failure`,
  so a heap-exhausting query (or a Docker OOM kill, exit 137) restarts it within
  seconds — after which nginx needs that restart.
- **External `/sparql` is rate-limited by nginx** (LDH 6.2, `NGINX_SPARQL_RATE`
  default `2r/s` burst 10, `NGINX_SPARQL_CONN_PER_CLIENT` 2,
  `NGINX_SPARQL_CONN_TOTAL` 8; set them in `.env`), answering `429` beyond that.
  Keyed on `$remote_addr`, and RFC 1918 addresses are exempt — LDH's own calls, but
  also every browser request on the local stack (Docker Desktop's gateway address is
  private), so local testing never sees a 429. Bulk querying goes through
  `etl/queries/run.sh` on the TriG, not the endpoint.

## Verification

After changing a mapping: rebuild the domain, check the reported graph count
against source counts (10 counties / 60 municipalities / 584 elderships / 831 persons
who held a Seimas seat since 1990 — 148 in the current term, its sitting members'
term counts matching the feed's `kadencijų_skaičius`),
and the Seimas calendar (10 terms / 131 sessions / 4 771 plenary sittings since 1990,
195 in term 10; 4 scheduled sittings have no date — every dated one carries `dct:temporal`; the calendar: 19 290 documents
for 1977–2027 (51 years / 612 months / 18 627 days), 16 public holidays, 16 holiday days in 2026; opt-in votes for term 10: 5 633 votes —
3 639 open / 1 776 consensus / 191 alternative / 55 secret — with ~336k individual choices; opt-in bills
for term 10 (2026-10-13 feeds): 4 766 agenda items (4 770 listings, grouped items counted once), 2 086
bills of which 799 member-initiated, 9 stages, every agenda/bill/vote link resolving; declarations
from the 2026-10-19 VMI harvest: 84 queries / 2 761 published rows -> 2 213 declarations of 455
persons (1 953 of 360 without the officials), 23 asset categories, amounts LTL for reporting years
<= 2014 (1 533) and EUR since (9 649), group-506 unmatched rows only for declarants absent from persons/ plus Mažylis 2025, 548 unmatched rows
in all — 320 of them vice-ministers (group 519, no source); officials: 350 persons (161 reusing a
Seimas person, 189 new) with 492 offices since 1990-03-11 — 7 President, 263 Government, 134 mayor,
88 MEP; elections: 2 elections
(2020, 2024) / 142 constituency contests / 273 contest rounds / 1 719 candidate results, 680 resolved to
persons/ — every winner, else the build fails — / 2 272 party-list results / 140 boundaries, the diaspora
constituency Nr. 71 has none; campaign finance from the 2026-10-20 VRK harvest, Seimas campaigns: 1 883
participants of 15 campaigns (5 general elections 2008–2024 + by-elections) — 98 → parties/, 1 616 VRK
candidates, 725 → persons/, 485 → election-results/ (the VRK candidate id = the ArcGIS photo id, 1 719/1 719),
1 368 nominating parties; 5 492 legal-person income rows, 25 641 natural-person rows → 3 741 totals;
32 269 legal-person expenses (gitignored campaign-expenses.trig, ~21 MB), 2 818 natural-person rows →
1 008 totals; only legal-entities/ links dangle — 2 491, all but 7 resolved by the full JAR of #59; legal entities (JAR, 2026-10-20): 547 382 = 6 028 institutions (forms 580/680/950) + 541 354
in entities.trig, 314 788 deregistered, 217 987 of 229 645 registered offices resolved
(building or premises → building), 0 dangling links; facilities:
10 032 education institutions (of 10 034 ŠVIS rows — 2 nameless one-week records dropped; 5 767
active, every active one with WGS84 coordinates), 4 130 health-care institutions (one licence row
with an 11-digit code skipped) with 8 332 activity sites, 26 058 KVR heritage objects (only 37
without a municipality); their legal-entity links resolve only for the budget-institution subset
until the full JAR is loaded; procurement for the
12 months to 2026-10-19: 55 663 contracts >= 10 000 EUR (amendments excluded — 12 059 more rows that
restate the whole value), every one with a buyer and a contractor; 2 077 of 2 801 distinct buyers and
98 of 9 325 contractors resolve in legal-entities/ — the rest dangle until the full JAR is loaded;
0 dangling calendar days; VTEK from the
2026-10-20 harvest: 427 lobbyists (422 listed + 5 UNLISTED stubs; 230 with a JAR code, 3 natural ones
-> persons/), 2 269 lobbying declarations (1 834 transparency + 435 influence; 388 cite 181 Seimas bills;
3 101 contacts, 963 -> persons/, 2 506 -> an institution), PINREG PARTIAL: 150 of 244 declarations
(99 declarants -> persons/), 602 ties incl. workplaces; legal-entities/ links dangle until the full JAR
is loaded, bills/ links until `make -C etl/seimas bills`), then run the link-integrity
pattern from `etl/queries/` (referenced `#this` targets
vs `foaf:primaryTopic` set — must be 0 dangling) and eyeball one entity graph.
Sodra (`employment/`, 2026-10-20 harvest, 12 months to 2026-08): employers.trig = 114 316
employer graphs (1.89M quads, 125 MB, ~1.5 min), 104 188 of them with reference month 2026-08;
27 504 `Nenustatyta` rows have no municipality; employment-wage-by-municipality.rq → 60
municipalities, Vilnius city top (2026-08: 2 662 EUR, 12 770 employers, 497 732 insured).
With SODRA_CUBE=1 the overlay adds 12 chunks (1 254 110 monthly observations, ~710 MB, ~5 min). `ltlod:employer` links into `legal-entities/` dangle for every non-budget-institution
employer until the full JAR register is loaded — expected, not an error.
`python3 etl/queries/render-examples.py` re-runs all example queries end-to-end.
SHACL shapes describe *current* data — if `make` fails the shapes check after a
mapping change, update `etl/shapes/<domain>.ttl` in the same commit.
