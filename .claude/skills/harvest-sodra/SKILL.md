---
name: harvest-sodra
description: Download Sodra's per-employer monthly open data (insured persons, average wage, contributions; atvira.sodra.lt monthly-{yyyy}.csv.zip) through Claude in Chrome into etl/sodra/data/, then rebuild the employment domain. Use when asked to refresh/update the Sodra (draudėjų, apdraustųjų, darbo užmokesčio) data, or monthly after Sodra publishes a new month.
---

# Harvest Sodra employer data

The employment domain (`etl/sodra/`) has no scripted fetch: atvira.sodra.lt answers every
non-browser client with a Cloudflare challenge (`cf-mitigated: challenge`, HTTP 403 — even
the Internet Archive's crawler gets it). The per-employer files exist nowhere else: the
data.gov.lt Sodra datasets (`/orgs/53/`) are national aggregates only, and Spinta has no
`datasets/gov/sodra` namespace. So the yearly zips are downloaded in the user's real Chrome
and `make` does the rest offline.

Never work around the Cloudflare challenge (no headless/stealth browsers, no reusing its
cookies in curl). If the user's browser can't pass it, stop and tell the user.

## 1. Browser

1. Needs Claude in Chrome connected (the user runs `/chrome`). Load the tools in one
   ToolSearch: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`,
   `computer`, `get_page_text`, `find`.
2. `tabs_context_mcp`, then open a NEW tab and navigate to
   `https://atvira.sodra.lt/imones/rinkiniai/index.html`.
3. If Cloudflare shows a verification page, wait a few seconds and screenshot — in the
   user's browser it normally passes by itself. **Never click the challenge checkbox**: if
   it asks for interaction, ask the user to complete it, then continue.
4. The page (an ExtJS app) lists the downloadable sets. Find the **monthly** files for the
   current and the previous year: `https://atvira.sodra.lt/imones/downloads/{yyyy}/monthly-{yyyy}.csv.zip`
   (there are also `daily-{yyyy-mm}.csv.zip` files — not used). If the page or the file
   names differ, stop and report — Sodra changed the site.

## 2. Download (ask first)

Downloading needs the user's explicit OK every time. Ask, naming the files
(`monthly-{yyyy}.csv.zip` for the two years) and the source page. Only after a clear yes,
click the links (or `navigate` to the file URLs) so Chrome saves them to `~/Downloads`.
Then close the tabs you opened.

## 3. Rebuild

```shell
mkdir -p etl/sodra/data
mv ~/Downloads/monthly-20*.csv.zip etl/sodra/data/      # replaces older copies
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/sodra       # SODRA_MONTHS=12 default
```

`etl/sodra/data/` is gitignored (tens of MB per year), as are the generated
`datasets/current/employment/observations-*.trig`; only `dataset.trig` (the cube
definition) is committed.

The normalizer (`ltlod-sodra`) reports observations / employers / months, merged duplicate
rows, skipped rows without a JAR code and unresolved municipalities.

- **"no [...] column in header"** → Sodra renamed or reordered the columns. The normalizer
  prints the header it saw: extend `COLUMNS` in `etl/tools/src/ltlod_etl/sodra.py`
  (it matches the parenthesised English keys — `jarCode`, `month`, `numInsured`,
  `avgWage`, `tax`, `name`, `municipality` — or the Lithuanian labels).
- **Unresolved municipalities** (`etl/sodra/cache/unmatched-municipalities.csv`): a few
  "not specified" rows are expected. A real municipality listed there means its Sodra
  spelling does not expand to the AR label — fix the expansion in `municipality_resolver`,
  never map by hand.

## 4. Verify and hand over

- Every `observations-NNN.trig` validates (riot, document invariants, SHACL
  `etl/shapes/employment.ttl`); the graph count per chunk equals its distinct JAR codes.
- Run `etl/queries/run.sh etl/queries/employment-wage-by-municipality.rq`: 60
  municipalities, Vilnius city near the top, wages in a plausible EUR range.
- Employer links resolve once the full JAR register is loaded (`legal-entities/`); with
  only the budget institutions, `employment-institutions-by-form.rq` shows the overlap.
