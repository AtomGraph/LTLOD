# CLAUDE.md

Lithuanian Linked Open Data: re-runnable ETL pipelines (`etl/`) that regenerate
RDF datasets (`datasets/current/`) from live open-data APIs on every run.

## Commands

```shell
cd etl && make                 # everything: taxonomies → admin-units → seimas → legal-entities
make -C etl/<domain> all       # one domain (fetch is always fresh — FORCE prerequisite)
make -C etl/seimas photos      # opt-in: scrape official portraits from lrs.lt
make BASE=https://linkeddata.lt/   # prod base URI (default https://localhost:4443/, see etl/config.mk);
                               # committed datasets/current/ are generated with the prod base

etl/queries/run.sh <q.rq>      # SPARQL over ALL datasets loaded in-memory (~1M quads, -Xmx4g)
python3 etl/queries/render-examples.py   # regenerate etl/queries/EXAMPLES.md result tables

uv run --project etl/tools ltlod-reconcile <admin-units|persons> --input … --output …

make up                        # deploy LinkedDataHub at https://localhost:4443/ (root Makefile;
                               # bootstraps secrets + server cert, then docker compose up -d)
make install                   # PUT app/ scaffolding (root + containers + taxonomy schemes)
                               # via LDH CLI + install app/ns.ttl (1:N views) into the admin
                               # ontologies/namespace/ doc; needs ../LinkedDataHub (LDH_HOME=…).
                               # Interactive, LinkedDataHub-Apps style: prompts for Base URL /
                               # cert / password / proxy, defaults = the local stack (Enter×4
                               # or `printf '\n\n\n\n' | make install`); enter another Base URL
                               # + owner cert to install onto any LDH instance
make load                      # bulk-load datasets/current/*/*.trig into fuseki-end-user TDB2;
                               # regenerate with `make -C etl` first (committed data has prod base);
                               # ends with `make public` (anonymous read, LDH make-public.sh equivalent)
make down / make drop          # stop stack / wipe LDH runtime state (never datasets/current/)
```

Prerequisites: Docker (only for `atomgraph/csv2rdf`; no docker-compose), Apache Jena
(`JENA_HOME`, Jena 6 needs Java 21+), `xsltproc`, `uv`, `make`, `curl`.

## Architecture

Every domain runs the same four stages (shared scripts in `etl/lib/`):

1. **fetch** — full dump from live API (Spinta UAPI CSV export with `select(...)`
   incl. dereferenced parent keys, e.g. `apskritis.adm_kodas`; Seimas XML). Fails
   loudly on empty results. Cache dirs are gitignored.
2. **normalize** — CSV → CSV2RDF identity transform (docker), XML → XSLT 1.0
   (`xsltproc`), both emit source-shaped RDF with `<{base}#column>` properties.
3. **graphify** — LDH-style quad `CONSTRUCT { GRAPH ?graph {…} }` mapping
   (`mappings/*.rq`, `$base`-parameterized) executed by `arq` → TriG. The `.rq`
   files are reusable verbatim as LinkedDataHub CSV imports.
4. **validate** — `riot --validate` + every graph must have `dct:title` and
   `foaf:primaryTopic` on the graph URI (see `etl/lib/validate.sh`) + SHACL
   shapes per entity type (`etl/shapes/<domain>.ttl`, auto-selected by output
   dir, executed via `etl/lib/shacl.sh`; also run in CI on committed datasets
   by `.github/workflows/shacl-validation.yml`).

Post-ETL: `ltlod-reconcile` matches entities to Wikidata (closed candidate sets
via WDQS, exact label + parent disambiguation) and writes `owl:sameAs` + images
into per-domain `alignments.trig` (same graph names as the entity docs, so they
merge on load). Unmatched entities go to `cache/unmatched*.csv`, never force-matched.

## Conventions (load-bearing)

- **Entity per named graph**: graph URI = document URI `{base}{container}/{slug}/`,
  entity = `{graph}#this`, secondary entities are `#fragment`s. Slugs are **natural
  keys** from the source registry (AR codes, JAR codes, Seimas `asmens_id`) — any
  pipeline mints cross-links from bare foreign keys. Single source of truth:
  `etl/URI-SCHEME.md` — update it when adding containers.
- **LDH document hierarchy**: ETL outputs are *only* `dh:Item` docs with
  `sioc:has_container <its-container>` — add both triples in any new mapping.
  Containers and taxonomy scheme docs come from `app/` (one Turtle file per
  container, PUT via LDH CLI by `make install`); each carries an
  `rdf:_1 <#select-children>` → `ldh:Object`/`ldh:ChildrenView` block, without
  which LDH renders no children listing at all.
- **1:N entity views**: cross-entity listings (county → municipalities, committee
  → members, party → nominees) are `ldh:inverseView` definitions in `app/ns.ttl`
  (the LDH namespace ontology, northwind-traders style): `<property>
  ldh:inverseView <ldh:View>` + `spin:query` → `sp:Select` with `$about`. LDH
  shows a view on every instance whose `rdf:type` matches the property's declared
  `rdfs:range` — exact type match, no subsumption, so view targeting relies on
  discriminating types in the data (`schema:PoliticalParty` for parties,
  `cv:PublicOrganisation` for the Seimas). `app/import-ns.sh` (called by `make
  install`) resets + POSTs the ontology into the admin `ontologies/namespace/`
  document (served at `{base}ns`) and evicts the server-side ontology cache.
- **Vocabulary cascade**: W3C specs first → domain-specific third-party vocabs
  (EU SEMIC, OP authority tables, FOAF) → schema.org as general fallback → custom
  (`http://linkeddata.lt/ns#`) last. Rationale per domain: `etl/ONTOLOGY-NOTES.md`.
- **Change over time**: n-ary `org:Membership` + `org:memberDuring` → `time:Interval`
  (W3C Time). No reification, no RDF-star. Current state = interval without `time:hasEnd`.
- **Docs in Lithuanian** (README, EXAMPLES.md); code, code comments and CLAUDE.md
  in English. Python is uv-managed (`etl/tools/`).
- Committed outputs live in `datasets/current/`; bulk regenerable files
  (settlements/streets TriG, ~59 MB) are gitignored.

## Gotchas

- **BINDs inside OPTIONAL are evaluated bottom-up**: a BIND referencing an outer
  variable (e.g. `?graph`) silently unbinds and drops triples. Keep only triple
  patterns inside OPTIONAL; do URI construction after it, guarded with
  `IF(BOUND(…), …, ?undef)` (see `etl/seimas/mappings/persons.rq`).
- **CSV2RDF must run via docker** — the local jar (`../CSV2RDF/target`) NPEs on
  modern JDKs (tested Java 25).
- **Jena `shacl validate` ignores TriG named graphs** (validates the empty
  default graph → trivially conforms) and **always exits 0** — `etl/lib/shacl.sh`
  flattens with `riot --merge` first and parses the `--text` report. Shapes must
  stay host-agnostic (path-suffix `sh:pattern`s, never the base host).
- Quad `CONSTRUCT { GRAPH … }` is an ARQ extension — works in `arq` CLI (its
  default syntax) and LinkedDataHub, not in strict SPARQL 1.1 engines.
- Cross-graph queries use `FROM <urn:x-arq:UnionGraph>` (union of all named
  graphs as default graph). With only FROM given, `GRAPH ?g {…}` matches nothing.
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
  Load is append-only — clean rebuild: `make down && rm -rf fuseki/end-user &&
  make up && make load`. It stops fuseki-end-user first and removes the stale
  `tdb.lock` (lock PIDs are container-relative), then restarts the Varnish caches.
- **Fuseki ports are never published to the host** — query via
  `https://localhost:4443/sparql` or from inside the network:
  `docker compose exec linkeddatahub curl http://varnish-end-user/ds/`.
- **LDH strips client-sent `sioc:has_parent`/`sioc:has_container` on PUT** and
  manages the hierarchy itself (re-adds `sioc:has_parent` for `dh:Container`,
  adds `dh:Item` + `sioc:has_container` otherwise, plus `dct:created`/
  `acl:owner`) — never put sioc triples in `app/*.ttl`. `make install` is
  idempotent: PUT replaces the whole named graph.
- **Public read access is class-based**: `make public` grants
  `acl:accessToClass def:Root, dh:Container, dh:Item, nfo:FileDataObject` —
  ETL documents match because mappings type them `dh:Item`/`dh:Container`.
  (Untyped docs would also pass: LDH's ACL query leaves `$Type` unbound when
  a document has no `rdf:type`, matching any `acl:accessToClass` — see
  `AuthorizationFilter` + `aclQuery` in LDH web.xml.)
- `COMPOSE_PROJECT_NAME=ltlod` isolates container/volume names from other local
  LDH stacks, but ports 81/4443/5443 still clash — one stack at a time.
- **502 on all public endpoints after restarting backend containers** (fuseki,
  varnish): nginx resolves upstream container IPs at startup — restart nginx
  too. `fuseki-end-user` can be OOM-killed (exit 137) under memory pressure
  when other Docker workloads run; `docker compose up -d fuseki-end-user`
  revives it (LDH health recovers on its own).

## Verification

After changing a mapping: rebuild the domain, check the reported graph count
against source counts (10 counties / 60 municipalities / 584 elderships / 148 MPs),
then run the link-integrity pattern from `etl/queries/` (referenced `#this` targets
vs `foaf:primaryTopic` set — must be 0 dangling) and eyeball one entity graph.
`python3 etl/queries/render-examples.py` re-runs all example queries end-to-end.
SHACL shapes describe *current* data — if `make` fails the shapes check after a
mapping change, update `etl/shapes/<domain>.ttl` in the same commit.
