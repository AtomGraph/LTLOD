---
name: harvest-vrk
description: Re-harvest VRK's open political campaign finance data (campaign income and expenses) and the Seimas election candidates through Claude in Chrome, then rebuild the elections domain's campaign finance. Use after an election's campaign reports are published (VRK publishes them in the months after the vote), or when asked to refresh/update the campaign finance (politinių kampanijų finansavimas) data.
---

# Harvest VRK campaign finance

The campaign-finance part of the elections domain (`etl/elections/`, `make finance`)
has no scripted fetch. VRK's open-data Spinta API (`https://atviriduomenys.vrk.lt/`,
where every data.gov.lt VRK distribution points) sits behind a Cloudflare bot
challenge. In a real browser the challenge passes by itself, and the Spinta JSON API
then works via `fetch()` from the page.

The data is harvested in the user's Chrome with `etl/elections/harvest-vrk.js` into
three CSVs under `etl/elections/data/`. They are gitignored source files, ~60 MB in
total; never commit them. `make` does the rest offline.

Never work around the Cloudflare challenge: no headless or stealth browsers, no
reusing its cookies in curl. **Never click the challenge checkbox.** If the user's
browser can't pass it by itself, stop and tell the user.

**Tell the user up front:** Chrome blocks the 2nd and later automatic (script-initiated)
downloads from one site. They will need to allow "Automatic downloads" for
`atviriduomenys.vrk.lt`, either in the prompt Chrome shows after the first file or via
the site settings (padlock icon → Site settings → Automatic downloads → Allow).
Otherwise only the first of the three files arrives.

## 1. Browser

1. Needs Claude in Chrome connected (the user runs `/chrome`). Load the tools in one
   ToolSearch: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`,
   `computer`, `get_page_text`, `javascript_tool`.
2. `tabs_context_mcp`, then open a NEW tab and navigate to
   `https://atviriduomenys.vrk.lt/datasets/gov/vrk/:ns`.
3. Cloudflare may show "Performing security verification". Wait (`computer` → `wait`,
   a few seconds, then screenshot). In the user's browser it normally passes by itself.
   If it asks for interaction, ask the user to complete it in their browser, then
   continue.
4. Check the page lists the VRK models (`Pajamos`, `Islaidos`, `Kandidatai` among them).
   If the page or the models differ, stop and report: VRK changed the API.

## 2. Harvest

1. Run the contents of `etl/elections/harvest-vrk.js` with `javascript_tool` in that
   tab (read the file, pass its full text). It returns `'started'` at once and runs
   about a minute in the page: one request per model.
2. Poll with short calls (`window.__vrkStatus`) every 15–30 s. It moves through
   `income` → `expenses` → `candidates` → `done`, or ends with `'error: …'`.
   - Return only the status and counts, never row contents. The tool's output filter
     can blank responses that look like data dumps.
   - On `error: … no rows` or `HTTP 403` the challenge probably reappeared. Let the
     user clear it (reload the tab), then run `harvest-vrk.js` again.
3. When `done`, run `window.__vrkSizes()`. It returns each file's row count and size.
   The previous harvest (2026-10-20) had:

   | File | Rows | Size |
   |---|---|---|
   | `vrk-pajamos.csv` | 73 721 | ~29 MB |
   | `vrk-islaidos.csv` | 63 522 | ~29 MB |
   | `vrk-kandidatai-seimas.csv` | 13 270 | ~3.4 MB |

   Counts should only grow. A large drop means a truncated response: stop and report.

## 3. Download (ask first)

Downloading needs the user's explicit OK every time. Ask, naming:
- the three files and their sizes from `__vrkSizes()`;
- the source (the harvest just run, generated in the page);
- the destination (`~/Downloads`, then moved to `etl/elections/data/`).

Remind the user to allow automatic downloads for `atviriduomenys.vrk.lt` (see above).

Only after a clear yes, call `javascript_tool` → `window.__vrkDownload('vrk-pajamos.csv')`,
then the same for `vrk-islaidos.csv` and `vrk-kandidatai-seimas.csv`: one call per file,
a few seconds apart. Check `~/Downloads` for all three; if one is missing, Chrome blocked
it. Ask the user to allow automatic downloads, then repeat that call. Finally close the
tabs you opened.

## 4. Rebuild

```shell
mv ~/Downloads/vrk-pajamos.csv ~/Downloads/vrk-islaidos.csv \
   ~/Downloads/vrk-kandidatai-seimas.csv etl/elections/data/
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/elections all
```

(Chrome renames repeated downloads to `vrk-pajamos (1).csv`. Take the newest:
`ls -t ~/Downloads/vrk-pajamos*.csv | head -1`.)

`ltlod-campaign-finance` reports participants, links (parties, VRK candidates, persons,
candidate results) and unmatched rows (`etl/elections/cache/finance/unmatched.csv`).

- **A new general Seimas election**: add its row to `etl/elections/data/elections.csv`
  (slug, year, term, both round dates, VRK `rinkimu_id` as `vrk_id`). Without it the
  participants still build but link to no `elections/` document.
- **Unmatched parties** are parties without a `parties/` document (never won a seat).
  That is expected. Add a `data/party-aliases.csv` line only when VRK spells an existing
  party differently.
- **Unmatched candidates** are participant names that contain no harvested candidate's
  "FIRST LAST", or contain two. Check a few; never loosen the matching.
- Campaign types other than the Seimas are in the CSVs too: `CAMPAIGN_TYPES="SEI SAV PRE EP"`.

## 5. Verify and hand over

- `make` ends with `valid: …/campaign-finance.trig (N graphs)` and
  `conforms: …/campaign-expenses.trig` (SHACL + no blank nodes).
- Run the link-integrity check from `etl/queries/`. Only `legal-entities/` links may
  dangle, until the full JAR register is loaded.
- Update the counts in CLAUDE.md's Verification section.
- Commit `datasets/current/elections/campaign-finance.trig` and the
  `datasets/current/taxonomies/campaign-*.trig` schemes on a branch, **never the CSVs**;
  `campaign-expenses.trig` is gitignored bulk output. Then load as usual (`make load`).
