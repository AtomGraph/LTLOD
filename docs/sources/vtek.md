# VTEK: lobbying (SKAIDRIS) and private interests (PINREG)

Status: **implemented** as the `vtek` ETL domain (`etl/vtek/`, output in
`datasets/current/vtek/`). PINREG is **partial**: 150 of 244 declarations from the
2026-10-20 harvest, finished at the next slow harvest.

The Chief Official Ethics Commission (Vyriausioji tarnybinės etikos komisija, VTEK) runs
two registers. Neither has record-level open data: data.gov.lt / Spinta
(`datasets/gov/vtek/*`) has only monthly aggregates, and both hosts sit behind a
Cloudflare challenge. They are therefore harvested in the user's real browser, as the VMI
property declarations are.

| Register | Host | Harvest | Output |
|---|---|---|---|
| **SKAIDRIS** — registered lobbyists, lobbyists' transparency declarations, officials' experienced-influence declarations | `skaidris.vtek.lt` | `etl/vtek/harvest-skaidris.js`: the app's own JSON endpoints, paged, with the app's same-site CSRF header; no reCAPTCHA | `lobbyists/`, `lobbying-declarations/` |
| **PINREG** — public private-interest declarations (politicians' position groups) | `pinreg.vtek.lt` | `etl/vtek/harvest-pinreg.js`: the search runs through the app's UI (its own reCAPTCHA) while a hook records the results; then a slow per-declaration GET (≥ 8 s) | `interest-declarations/` |

- **How to re-harvest:** the procedure (browser steps, consent before each download,
  Cloudflare and reCAPTCHA rules, resuming PINREG's `pending` ids) is
  [`.claude/skills/harvest-vtek/SKILL.md`](../../.claude/skills/harvest-vtek/SKILL.md).
- **Where things are documented:**
  - the model: [`etl/ONTOLOGY-NOTES.md`](../../etl/ONTOLOGY-NOTES.md);
  - URIs: [`etl/URI-SCHEME.md`](../../etl/URI-SCHEME.md);
  - reconciliation rules: the `ltlod_etl.vtek` docstring.

## Findings that shaped it

- **Re-challenge rate.** Cloudflare re-challenged PINREG's detail GETs after ~150
  requests at 1.2 s spacing. The harvester waits 8 s per request and stops on any
  challenge, never retrying through it.
- **Own data only.** PINREG detail JSON carries:
  - the spouse/partner (`sutuoktinis`, ties with `kienoRysys = PARTNERIO`);
  - the personal code and birth date;
  - transactions and ties with natural persons.

  None of these is kept: they are dropped in the browser at harvest.
- **Free-text names.** SKAIDRIS stores clients, beneficiaries and lobbied institutions as
  free text (with typos and abbreviations). They stay text. Institutions link only by
  exact legal name, Seimas committee label or a curated alias
  (`etl/vtek/data/institution-aliases.csv`).
- **Contacts' e-mail addresses** are in the source but are not emitted.
- **Bill numbers.** Seimas bill numbers (`XIVP-3879`) are cited in 388 declarations'
  legislation names or descriptions. They link to the Seimas bills of the
  `make -C etl/seimas bills` pipeline. Other numbers (TAIS `26-12063`, Government
  projects) are not linked yet.

## Legal basis

- **Law on the Reconciliation of Public and Private Interests** (VIII-371; PINREG since
  2021):
  - the declaration content: workplaces, ties to legal entities, gifts, transactions;
  - the publicity of politicians' and senior officials' declarations, excluding personal
    codes and special-category data.
- **Law on Lobbying Activities** (XIII-3170, in force 2021-01-01): publication in
  SKAIDRIS of the lobbyist list and of each transparency and experienced-influence
  declaration.

The article-level citations were taken from secondary sources while e-seimas was
challenged, so verify them in a browser.
