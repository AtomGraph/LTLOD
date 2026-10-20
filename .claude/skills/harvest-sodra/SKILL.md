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
2. `tabs_context_mcp`, then open a NEW tab and navigate to the downloads index
   `https://atvira.sodra.lt/imones/rinkiniai/index.html` (not the site root: it redirects
   to the search page `/imones/paieska/index.html`).
3. If Cloudflare shows a verification page, wait a few seconds and screenshot — in the
   user's browser it normally passes by itself. **Never click the challenge checkbox**: if
   it asks for interaction, ask the user to complete it, then continue.
4. The page (an ExtJS app) lists the downloadable sets. Find the **monthly** files for the
   current and the previous year: `https://atvira.sodra.lt/imones/downloads/{yyyy}/monthly-{yyyy}.csv.zip`
   (there are also `daily-{yyyy-mm}.csv.zip` files — not used). If the page or the file
   names differ, stop and report — Sodra changed the site.

## 2. Download (ask first)

Downloading needs the user's explicit OK every time. Ask, naming the files
(`monthly-{yyyy}.csv.zip` for the two years, ~11–15 MB each) and the source page. Only
after a clear yes, `navigate` the tab to each file URL in turn — the zips download on
navigation and Chrome saves them to `~/Downloads`. Chrome may block the 2nd automatic
download from the site ("This site attempted to download multiple files"): ask the user
to allow it, then navigate to that URL again. Then close the tabs you opened.

## 3. Rebuild

```shell
mkdir -p etl/sodra/data
mv ~/Downloads/monthly-20*.csv.zip etl/sodra/data/      # replaces older copies
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/sodra       # SODRA_MONTHS=12 default
# optional: + the full monthly series (~710 MB, ~5 min)
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/sodra SODRA_CUBE=1
```

`etl/sodra/data/` is gitignored (tens of MB per year), as are the generated
`datasets/current/employment/employers.trig` (one summary observation per employer: latest
month + window aggregates) and the opt-in `observations-*.trig`; only `dataset.trig` (the
cube definitions) is committed. Without `SODRA_CUBE=1` stale `observations-*.trig` are deleted.

The normalizer (`ltlod-sodra`) reports employers / months / cube observations, merged duplicate
rows, skipped rows without a JAR code and unresolved municipalities.

- **"no [...] column in header"** → Sodra renamed or reordered the columns. The normalizer
  prints the header it saw: extend `COLUMNS` in `etl/tools/src/ltlod_etl/sodra.py`
  (it matches the parenthesised English keys — `jarCode`, `month`, `numInsured`,
  `avgWage`, `tax`, `name`, `municipality` — or the Lithuanian labels). The header seen
  on 2026-10-20: 13 `;`-separated UTF-8 columns, `Draudėjo kodas (code)` …
  `Valstybinio socialinio draudimo įmoka (tax)`, incl. the ignored `avgWage2` /
  `numInsured2` and `ecoActCode` / `ecoActCodeStr` / `ecoActName`.
- **Unresolved municipalities** (`etl/sodra/cache/unmatched-municipalities.csv`):
  `Nenustatyta` ("not determined") is expected — 27 504 rows in the 2026-10-20 run; those
  observations simply carry no `sdmx-dimension:refArea`. Any other (real) municipality listed there means its Sodra
  spelling does not expand to the AR label — fix the expansion in `municipality_resolver`,
  never map by hand.

## 4. Verify and hand over

- `employers.trig` validates (riot, document invariants, no blank nodes, graph count =
  employers, SHACL `etl/shapes/employment.ttl`); with `SODRA_CUBE=1` every
  `observations-NNN.trig` overlay passes riot + SHACL.
- Graph counts: 2026-10-20 run (monthly-2025 + monthly-2026, SODRA_MONTHS=12) → 114 316
  employer graphs, 1.89M quads, 125 MB, ~1.5 min (cube: +12 chunks, 1 254 110 observations, ~710 MB, ~5 min).
- Run `etl/queries/run.sh etl/queries/employment-wage-by-municipality.rq`: 60
  municipalities, Vilnius city on top (2026-08: 2 662 EUR, 12 770 employers, 497 732
  insured).
- Employer links resolve once the full JAR register is loaded (`legal-entities/`); with
  only the budget institutions, `employment-institutions-by-form.rq` shows the overlap.
