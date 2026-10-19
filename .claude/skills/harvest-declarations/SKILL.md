---
name: harvest-declarations
description: Re-harvest VMI's public property declaration extracts (FR0001) of Seimas members, ministers, the President, MEPs, vice-ministers and mayors through Claude in Chrome, then rebuild the declarations domain. Use once a year after VMI publishes the previous year's extracts (by 1 October), or when asked to refresh/update the declarations (turto deklaracijos) data.
---

# Harvest VMI property declarations

The declarations domain (`etl/declarations/`) has no scripted fetch: vmi.lt is behind
a Cloudflare bot challenge and rejects datacenter/VPN IPs (a Lithuanian NordVPN exit
was tried — still blocked). The data is harvested in the user's real Chrome with
`etl/declarations/harvest.js`, saved as `etl/declarations/data/vmi-fr0001.json`
(committed — the domain's source of truth), and `make` does the rest offline.

Never work around the Cloudflare challenge (no headless/stealth browsers, no reusing
its cookies in curl). If the user's browser can't pass it, stop and tell the user.

## 1. Browser

1. Needs Claude in Chrome connected (the user runs `/chrome`). Load the tools in one
   ToolSearch: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`,
   `computer`, `get_page_text`, `javascript_tool`.
2. `tabs_context_mcp`, then open a NEW tab and navigate to
   `https://www.vmi.lt/evmi/metines-gyventojo-seimos-turto-deklaracijos-duomenu-israsai`.
3. Cloudflare shows "Performing security verification". Wait (`computer` → `wait`,
   a few seconds, then screenshot) — in the user's browser it normally passes by
   itself. **Never click the challenge checkbox**: if it asks for interaction, ask the
   user to complete it in their browser, then continue.
4. Check the page has the search form: the iframe `https://www.vmi.lt/TPP/fr0001/default.aspx`
   with fields `ddMetai` (years), `ddPareigGr` (position groups), `butIeskoti`.
   If the page or form differs, stop and report — VMI changed the site.

## 2. Harvest

1. Run the contents of `etl/declarations/harvest.js` with `javascript_tool` in that tab
   (read the file, pass its full text). It returns `'started'` at once and runs ~10 min
   in the page: 6 groups × every offered year since 2012, one query per ~5 s.
2. Poll with short calls — `[window.__hstatus, Object.keys(window.__harvest).length]` —
   every minute or two (do other work in between). Expect ~6 × (years offered) keys.
   `__hstatus` ends as `'done'` or `'error: …'`.
   - Avoid returning `window.__hlog` lines wholesale: the tool's output filter can
     blank responses that look like query strings. Return counts.
   - On `error:` read the message. A "search form missing" usually means a challenge
     reappeared — let the user clear it, then run `harvest.js` again: finished queries
     are kept and skipped. A "found N, parsed M" means the result layout changed:
     stop, the parser needs fixing.
3. `found: null` with 0 people for a group-year is normal: the group code did not
   exist then (e.g. 536 mayors only from 2022, 519 vice-ministers from 2017).

## 3. Download (ask first)

Downloading needs the user's explicit OK every time. Ask, naming the file
(`vmi-fr0001-harvest.json`), source (the harvest just run, generated in the page) and
size (~0.5 MB). Only after a clear yes: `javascript_tool` → `window.__harvestDownload()`
(it returns query/label/people counts). Then close the tabs you opened.

## 4. Rebuild

```shell
mv ~/Downloads/vmi-fr0001-harvest.json etl/declarations/data/vmi-fr0001.json
git diff --stat etl/declarations/data/vmi-fr0001.json      # expect growth, not loss
JENA_HOME=/Users/martynas/WebRoot/apache-jena-5.6.0 make -C etl/declarations all
```

(Newest download if several: `ls -t ~/Downloads/vmi-fr0001-harvest*.json | head -1`.)

The normalizer (`ltlod-declarations`) reports declarations / persons / unmatched rows.

- **Unknown category** → it aborts and names the VMI label. Add a row to
  `etl/taxonomies/data/asset-categories.csv` (ASCII-slug notation, the exact VMI label
  as `label_lt`, an English label, `broader` if it splits an older category), rebuild
  `make -C etl/taxonomies`, then this domain.
- **Unmatched rows** (`etl/declarations/cache/unmatched.csv`): rows of other groups are
  expected (ministers, mayors etc. who never held a Seimas seat). Look at group-506
  rows only. A name spelled differently by VMI and LRS gets a line in
  `etl/declarations/data/aliases.csv` (VMI name, asmens_id, why) — only when the
  person is unambiguous (same seat years); never loosen the matching itself. A 506 row
  for someone not in `persons/` stays unmatched.
- New reporting years are in EUR; years up to 2014 are LTL (the mapping decides by year).

## 5. Verify and hand over

- `make` ends with `valid: …/declarations.trig (N graphs)` (SHACL + no blank nodes).
- Compare with the previous run: declarations and persons should only grow; the new
  year should have ~130–140 group-506 declarations (the Seimas has 141 seats).
- Update the counts in CLAUDE.md's Verification section.
- Commit `data/vmi-fr0001.json`, any `aliases.csv` / taxonomy rows, and
  `datasets/current/declarations/` + `taxonomies/` on a branch; to publish, `make load`
  locally / remote-load to prod as usual.
