---
name: harvest-vtek
description: Re-harvest VTEK's public lobbying register (SKAIDRIS — lobbyists, transparency and experienced-influence declarations) and the public private-interest declarations of politicians (PINREG) through Claude in Chrome, then rebuild the vtek domain. Use when asked to refresh/update the lobbying (lobistai, lobistinė veikla) or private interests (privačių interesų deklaracijos, PINREG) data, or to finish a partial PINREG harvest.
---

# Harvest VTEK registers (SKAIDRIS + PINREG)

The vtek domain (`etl/vtek/`) has no scripted fetch: `skaidris.vtek.lt` and
`pinreg.vtek.lt` are behind a Cloudflare bot challenge, and PINREG's search is gated by
the app's own reCAPTCHA. The data is harvested in the user's real Chrome with
`etl/vtek/harvest-skaidris.js` and `etl/vtek/harvest-pinreg.js`, saved as
`etl/vtek/data/skaidris.json` and `etl/vtek/data/pinreg.json` (gitignored: re-harvest,
never edit by hand), and `make` does the rest offline.

Rules, without exception:
- **Never work around Cloudflare.** No headless or stealth browsers, no reusing its
  cookies in curl, no clicking its checkbox. If a challenge appears, stop and ask the user
  to pass it in their browser.
- **reCAPTCHA only through the app's own UI.** PINREG's search runs the app's invisible
  reCAPTCHA when IEŠKOTI is clicked. Never call the search endpoint from script. If a
  visible reCAPTCHA appears, the user may solve it; you never do.
- **Never retry through a challenge.** Both scripts stop on HTTP 403 / `cf-mitigated`;
  re-run only after the browser has passed it normally.
- **Ask before every download**, naming the file and its approximate size
  (`skaidris.json`, ~4 MB; `pinreg.json`, ~0.4 MB for 244 declarations).
- **Own data only (PINREG).** The script keeps the declarant's own workplaces and
  legal-entity ties only. Never extend it to spouse/partner data, personal codes, birth
  dates, transactions or ties with natural persons.

## 1. Browser

1. Needs Claude in Chrome connected (the user runs `/chrome`). Load the tools in one
   ToolSearch: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`,
   `computer`, `find`, `get_page_text`, `javascript_tool`, `read_network_requests`.
2. Tell the user up front: Chrome blocks a site's second and later automatic downloads
   until they allow "automatic downloads" for it (an icon in the address bar). Both
   harvests save one file each, on different hosts, so normally this does not trigger.
   If a download does not appear, ask the user to allow it and call the download function
   again.

## 2. SKAIDRIS (lobbying): no reCAPTCHA, ~1 min

1. `tabs_context_mcp`, then open a NEW tab at `https://skaidris.vtek.lt/public/home/main`.
   Wait for Cloudflare to pass by itself (screenshot after a few seconds). The page must
   show the public SKAIDRIS home.
2. Run the full text of `etl/vtek/harvest-skaidris.js` with `javascript_tool`. It
   returns `'started'` and pages through the three lists at 1.5 s per request (~30
   requests).
3. Poll `[window.__skStatus, window.__skLog.length, window.__skLog.slice(-1)[0]]` every
   ~30 s. Expect `done`. Counts on 2026-10-21: 422 lobbyists, 1833 transparency and 438
   influence declarations.
   - `error: … Cloudflare challenge`: ask the user to reload the tab and pass the
     challenge, then re-run the script. Fetched pages are kept.
   - `error: … success`/HTTP 4xx without a challenge: the API changed. Use
     `read_network_requests` while clicking through the public lists to see what the app
     now sends, and fix the script. Never guess.
4. Ask to download (`skaidris.json`, ~4 MB). After a clear yes, run
   `window.__skDownload()` (it returns the counts).

## 3. PINREG (private interests): two phases, slow

### Phase 1: search, through the UI

1. Open a NEW tab at `https://pinreg.vtek.lt/app/deklaraciju-paieska` and wait for
   Cloudflare. Decline the cookie banner ("Atmesti").
2. Run the full text of `etl/vtek/harvest-pinreg.js` with `javascript_tool`. It returns
   `'hooked'`: it records the search results the app receives. It does not search.
3. In "Pagrindinių pareigų pobūdis" (multi-select), tick:
   - Europos Parlamento narys
   - Meras
   - Ministras pirmininkas, ministras
   - Respublikos Prezidentas
   - Seimo pirmininkas, Seimo narys

   Use `find` + `computer` clicks. Click **IEŠKOTI**, then the paginator's NEXT arrow
   (the second arrow button) until the last page. On 2026-10-20 there were 244 results
   in 5 pages of 50.
4. `window.__pinregRows()` must report `rows == total`. If not, page through again;
   pages already seen are kept.

### Phase 2: details, one request per 15 s

1. **Finishing a partial harvest?** Seed the previous file first, so its declarations are
   kept. Read `etl/vtek/data/pinreg.json` and pass its content:
   `window.__pinregLoad(<the JSON>)`. Check the declaration count it returns.
2. Run `window.__pinregDetails()` (15 s per request: a polite pace). It returns how many
   are left to fetch: ~244 × 15 s ≈ 1 h for a full run.
3. Poll `[window.__pinregStatus, window.__pinregLog.length]` every few minutes, and do
   other work in between.
   - On `error: … Cloudflare challenge`, **stop** and download what you have (it is marked
     `complete: false` and lists the `pending` ids). If the user passes the challenge by
     reloading the tab, redo phase 1, seed the downloaded file (step 1) and resume;
     otherwise finish another day.
4. Ask to download (`pinreg.json`, ~0.4 MB). After a clear yes, run
   `window.__pinregDownload()`. It returns `{declarations, pending, complete}`. Then close
   the tabs you opened.

## 4. Rebuild

```shell
mv ~/Downloads/skaidris.json ~/Downloads/pinreg.json etl/vtek/data/
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/vtek all
```

(For the newest download when there are several: `ls -t ~/Downloads/pinreg*.json | head -1`.)

The normalizer (`ltlod-vtek`) prints the counts:
- lobbyists (legal, natural, with a JAR code, natural ones matched to `persons/`);
- declarations, the Seimas bills they cite, and contacts resolved to `persons/` and to
  institutions;
- interest declarations, declarants matched, ties, and whether the harvest was partial.

What to do when something doesn't match:
- **Unknown lobbying area or tie nature**: it aborts and names the label. Add a row to
  `etl/taxonomies/data/lobbying-areas.csv` or `interest-roles.csv` (ASCII-slug notation,
  the exact label as `label_lt`, an English label), rebuild `make -C etl/taxonomies`,
  then this domain.
- **Lobbied institution not resolved** (free text): add frequent spellings to
  `etl/vtek/data/institution-aliases.csv` (name, base-relative target IRI, note). Only
  unambiguous ones; never loosen the matching itself.
- **Declarants/contacts not matched to persons**: expected for officials outside
  `persons/` (vice-ministers, civil servants; mayors and ministers until the officials
  domain is loaded). VMI-style spelling differences go to
  `etl/declarations/data/aliases.csv`, which this domain reuses.

## 5. Verify and hand over

- `make` ends with `valid: …` for `lobbyists.trig`, `lobbying.trig` and
  `interests.trig` (SHACL, no blank nodes, graph counts).
- Counts should only grow, apart from lobbyists who left the register. Those stay as
  `UNLISTED` stubs while declarations cite them.
- Update the counts in CLAUDE.md's Verification section. If PINREG is now complete,
  remove the "partial" notes from CLAUDE.md, README.md and `docs/sources/vtek.md`.
- Commit `datasets/current/vtek/` (plus any alias or taxonomy rows) on a branch, but
  never the `data/*.json` harvests.
