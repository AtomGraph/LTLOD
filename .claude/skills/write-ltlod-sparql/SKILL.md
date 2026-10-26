---
name: write-ltlod-sparql
description: Write, debug or speed up a SPARQL query against the LTLOD datasets — the named-graph-per-document data shape, how to run a query (the throttled live endpoint vs. a local TDB2 store), and the query-shape rules that decide whether a query returns the right rows or hangs. Use whenever a query over the Lithuanian Linked Open Data returns empty or wrong results, is slow, needs a cross-document join, or is being authored for an app view (app/*.ttl) or an example (queries/*.rq).
---

# Write LTLOD SPARQL

How to write a **correct, fast** query against the LTLOD datasets, independent of what
question you are asking. For *which* domains and keys answer a given investigative
question, use the `investigate-ltlod` skill — it builds on this one.

## The data shape (read this first)

**Entity per named graph.** Every document is one named graph whose URI is the document
URI `{base}{container}/{slug}/`; the entity is `{graph}#this`, and secondary entities are
`#fragment`s **in the same graph** (a person's memberships, their intervals and instants;
a contract's value and role fragments; a proceeding's `#period`/`#start`/`#end`). So:

- **One `GRAPH ?g { … }` block per document.** Put `#this` and all its `#fragment`s in
  one block; join *across* documents by sharing a variable between blocks.
- There is **no default graph** of instance data — everything is in named graphs. A query
  with no `GRAPH` wrapper matches nothing.
- `alignments.trig` / `photos.trig` / `*-geo.trig` reuse the entity graph names, so they
  merge with the main data on load — query them as if they were one graph.

The full URI map (containers, slugs, `#fragment` types, which source each comes from) is in
**`etl/URI-SCHEME.md`**. 49 worked, explained queries are in **`queries/EXAMPLES.md`** — copy
the closest one rather than starting blank.

## Running a query

### Local, over the TriG files — preferred for development and anything bulk
`queries/run.sh` bulk-loads **all** `datasets/current/*/*.trig` into a throwaway TDB2 store
and runs the query against it (TDB2 answers an unbound `GRAPH ?g` from its quad indexes;
in-memory `arq` walks every one of ~190k named graphs and is unusable for GRAPH queries):

```shell
queries/run.sh queries/some-query.rq                 # one query, CSV/table to stdout
queries/run.sh queries/some-query.rq --results=csv   # pass extra tdb2.tdbquery args
BASE=https://linkeddata.lt/ queries/run.sh q.rq       # override base (default: prod)
```

It rebuilds the store **every call** (~20 s for the committed data, minutes with the bulk
datasets). **For many queries, build the store once and reuse it:**

```shell
J=/Users/martynas/WebRoot/apache-jena-5.6.0        # 5.6.0 or 6.x both query fine
"$J/bin/riot" --base=https://linkeddata.lt/ --syntax=trig --output=nquads \
    datasets/current/*/*.trig > /tmp/all.nq
"$J/bin/tdb2.tdbloader" --loc /tmp/tdb /tmp/all.nq
"$J/bin/tdb2.tdbquery" --loc /tmp/tdb --query q.rq --results=csv   # repeat, fast
```

Load only the domains a query touches to save time (e.g. `datasets/current/procurement/*.trig
datasets/current/insolvency/*.trig datasets/current/legal-entities/*.trig` for a
procurement×insolvency join — plus the taxonomies if the query resolves a `skos:prefLabel`).

**Datasets must be present.** Committed `.trig` are in the repo; the bulk ones (the full JAR
`legal-entities/entities.trig`, `procurement`, `seimas/votes`, `eu-funds`, `public-spending`,
`taxes/taxpayers`, …) are **gitignored** and built with `make -C etl <domain>` (see CLAUDE.md
Commands). A query that joins a missing bulk domain returns empty, not an error.

**Always pass `--base`.** Committed TriG is base-**relative** with no `@base`; without a base,
relative IRIs resolve to `file://…` garbage and joins silently fail.

### Live endpoint — `https://linkeddata.lt/sparql` — throttled, for a few interactive queries only
```shell
curl -sG https://linkeddata.lt/sparql --data-urlencode "query=$(cat q.rq)" -H "Accept: text/csv"
```
It is **rate-limited by nginx** (default `2r/s`, burst 10; 2 connections per client, 8 total)
and answers **`429`** beyond that, keyed on the client address. Fine for a handful of queries;
**do not** loop or bulk-query it — use `run.sh` / a local TDB2 for that. (On the local stack,
RFC-1918/loopback clients are exempt, so you won't see 429 there.)

## Query-shape rules (these decide empty vs. right, fast vs. hung)

- **One `GRAPH ?g` block per document; join across blocks on shared variables.** A block is
  evaluated on its own, so a `BIND`/`FILTER EXISTS` inside it **cannot see** a variable bound
  outside it (it silently matches everything) — put such a test *after* the block, with the
  `GRAPH` inside the `EXISTS`.
- **A property path that crosses documents can't sit in one block** — split it into hops
  (e.g. settlement → county is a UNION of the 2- and 3-hop `dct:isPartOf+` chains).
- **No alternative path `(a|b)` with an unbound subject inside a `GRAPH` block** — ARQ won't
  resolve it through the quad indexes. Use `?p` + `FILTER(?p IN (…))`, or a `UNION` of the two
  plain triples.
- **Never `FROM <urn:x-arq:UnionGraph>`** (Fuseki/ARQ-specific) — use standard `GRAPH` patterns.
- **Read a value from a triple, never by string-parsing an IRI.** No `REPLACE(STR(?x), …)` /
  `STRAFTER`/`SUBSTR(STR(?x), …)` to pull a code or label out of a resource URI: a concept's
  code is `skos:notation`, its label `skos:prefLabel` (filter `lang`), a legal entity's code
  `dct:identifier`. String ops on genuine *literals* are fine. Matching a *known* resource
  base-agnostically with `FILTER(STRENDS(STR(?x), "/…/#this"))` is OK (the TriG is base-relative,
  so a bare absolute IRI wouldn't match) — that selects a resource, it doesn't extract a value.
- **Avoid per-row `FILTER NOT EXISTS` over the whole store** — it is quadratic and hangs.
  Group/aggregate first so the check runs over a few thousand rows, or dump both URI sets with
  two SELECTs and `comm -23`.
- **Dates link to the calendar.** Events carry `dct:temporal` → `calendar/{yyyy}/{mm}/{dd}/#this`
  (or the year doc) plus a literal; periods are a `time:Interval` with `time:Instant`s that each
  carry `dct:temporal`. Join on the day/year doc for "what happened on/in …".
- **Labels / language.** Lithuanian labels are `@lt`; filter `FILTER(LANG(?l) = "lt")`. A legal
  entity's name is `skos:prefLabel`/`rov:legalName`; a person's is `foaf:name`.

## When a query returns empty — checklist
1. Is every pattern inside a `GRAPH ?g { … }`? (No default graph.)
2. Is the joined **bulk** domain actually loaded? (`entities.trig`, `procurement`, the new
   domains, and the **taxonomies** a `skos:prefLabel` join needs — e.g. `insolvency-types`.)
3. Did you pass `--base` and the same base everywhere?
4. Does a cross-document property path need splitting into hops?
5. Is a value being read by IRI string-parsing (returns nothing if the slug scheme differs)
   instead of from `skos:notation`/`dct:identifier`?
