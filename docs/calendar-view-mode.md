> **Status: implemented in LTLOD (2026-10-17), upstream proposal for LinkedDataHub not started.**

# Calendar view mode

## What exists
`files/calendar-mode.xsl` adds **`ltlod:CalendarMode`** to LinkedDataHub's view layout modes (List, Table, Grid, Chart, Map, Graph). It is compiled into the client SEF.

- **Generic.** Any `ldh:View` can be drawn as a calendar, either picked in the mode switcher or set as the default with `ac:mode ltlod:CalendarMode`.
  - Each result is placed on a date: the value of the view's `ORDER BY` predicate, read through LDH's `$var-predicates`. That value can be an untyped `"yyyy-mm-dd…"` string. Failing that, the result's first `xsd:date` / `xsd:dateTime` literal is used.
  - One grid is drawn per month the results span. A single month gets a full-size grid that lists the items. Several months get compact grids with counts.
- **Unpaged in calendar mode only.** In calendar mode the results request goes out without `LIMIT`/`OFFSET`, capped at 1000. The cached query keeps its paging, so switching back to List or Table pages as before.
- **LTLOD-specific touches:**
  - a result that *is* a calendar day links its cell and shows its public holidays;
  - month titles and "+N" link to `calendar/{yyyy}/{mm}/[{dd}/]`;
  - month and weekday names are in Lithuanian.
- **Where it's used:**
  - `:CalendarDays` on month pages (1 grid) and year pages (12 grids);
  - any other view through the switcher, e.g. a session's plenary sittings.

## Why it needs copied LDH code
LDH's view modes are a **closed list** hard-coded in several places in `client/block/view.xsl` and `resource.xsl`:

| What | Where in LDH | What LTLOD does |
|---|---|---|
| CSS class ↔ mode map | `$ldh:class-modes` | redeclared |
| Icon per mode | `$ldh:mode-icons` | redeclared |
| Switcher items | literal list in the switcher template | wrapped with `xsl:next-match`, Calendar item appended |
| Mode description lookup | `key('resources', $mode, ac: ontology)` in the switcher and its click handler | switcher copied; click handler wrapped (`next-match` + re-render) |
| Rendering dispatch | `xsl:choose` in `ldh:ViewModeChoice` | named template copied, one branch added |
| Paging | `ldh:RenderView` sends the paged query for every mode | named template copied, unpaged request in calendar mode |

The three copied named templates (`ldh:ViewModeSwitcher`, `ldh:ViewModeChoice`, `ldh:RenderView`) must be re-synced with every LDH image upgrade.

## Upstream plan (LinkedDataHub)
Make view modes **pluggable**, then ship the calendar as a built-in mode:

1. **Mode registry.** Replace the hard-coded lists with one global param, `$ldh:view-modes` (a map from mode URI to `{ class, icon, label-key, paged, canvas }`). The switcher, `$ldh:class-modes`, the icons and the pager's "paged modes" test all derive from it, and apps extend it by redeclaring the param.
2. **Dispatch by template.** The `xsl:otherwise` of `ldh:ViewModeChoice` becomes `xsl:apply-templates select="$results" mode="ldh:ViewModeBlock"` with `$active-mode` as a parameter. A new mode is then just a template rule matching its URI, and `next-match` keeps the stock modes reachable.
3. **Per-mode paging.** `ldh:RenderView` asks the registry whether the mode is paged. Unpaged modes (calendar, and arguably map, chart and graph) get the request without `LIMIT`/`OFFSET`, up to a cap.
4. **Mode descriptions.** The switcher looks modes up in the registry, or in a merged document of the `ac:` ontology plus app modes, instead of the `ac:` ontology alone.
5. **`ac:CalendarMode`** in the Web-Client vocabulary. The renderer from `calendar-mode.xsl` moves in minus the LTLOD specifics: its links become optional parameters and its month/weekday names come from `translations.rdf`.

After this, LTLOD would keep only the calendar-day/holiday template and its links, and drop all three copied named templates.

## Possible next steps in LTLOD
- `ac:mode ltlod:CalendarMode` as the default for the session → sittings and day-page views.
- Month and year pages could also list the events of the period, which needs a two-hop query through `dct:temporal`.
