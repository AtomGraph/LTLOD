# CLAUDE.md

Lithuanian Linked Open Data: re-runnable ETL pipelines (`etl/`) that regenerate
RDF datasets (`datasets/current/`) from live open-data APIs on every run.

## Commands

```shell
cd etl && make                 # everything: taxonomies → admin-units → seimas → legal-entities
make -C etl/<domain> all       # one domain (fetch is always fresh — FORCE prerequisite)
make -C etl/seimas photos      # opt-in: scrape official portraits from lrs.lt
make BASE=https://host/        # override base URI (default https://linkeddata.lt/, see etl/config.mk)

etl/queries/run.sh <q.rq>      # SPARQL over ALL datasets loaded in-memory (~1M quads, -Xmx4g)
python3 etl/queries/render-examples.py   # regenerate etl/queries/EXAMPLES.md result tables

uv run --project etl/tools ltlod-reconcile <admin-units|persons> --input … --output …
```

Prerequisites: Docker (only for `atomgraph/csv2rdf`; no docker-compose), Apache Jena
(`JENA_HOME`, Java 17+), `xsltproc`, `uv`, `make`, `curl`.

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
   `foaf:primaryTopic` on the graph URI (see `etl/lib/validate.sh`).

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

## Verification

After changing a mapping: rebuild the domain, check the reported graph count
against source counts (10 counties / 60 municipalities / 584 elderships / 148 MPs),
then run the link-integrity pattern from `etl/queries/` (referenced `#this` targets
vs `foaf:primaryTopic` set — must be 0 dangling) and eyeball one entity graph.
`python3 etl/queries/render-examples.py` re-runs all example queries end-to-end.
