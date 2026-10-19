# VTEK: private interests (PINREG) and lobbying (SKAIDRIS) — feasibility

Status: **not implemented — no scriptable record-level source.** Investigated 2026-10-20.

The Chief Official Ethics Commission (Vyriausioji tarnybinės etikos komisija, VTEK) runs two
registers that would connect `persons/` to `legal-entities/` and to legislation:

| Register | What it would add | Host |
|---|---|---|
| **PINREG** — Privačių interesų registras | a declarant's own ties to legal entities: shareholdings/membership, management and board positions, workplaces; plus gifts and transactions | `https://pinreg.vtek.lt/app/` |
| **SKAIDRIS** — Skaidrių teisėkūros procesų informacinė sistema | registered lobbyists; transparency declarations (lobbyist → client / beneficiary → draft legal act); declarations of officials who experienced lobbying influence | `https://skaidris.vtek.lt/` |

## What was checked

1. **data.gov.lt / Spinta** (`get.data.gov.lt/datasets/gov/vtek/:ns`) — three datasets, all
   **aggregates only**, no record-level data:
   - `ataskaita/Lobistas` — monthly count of registered lobbyists by type
     (`data`, `viso_fiziniu`, `viso_juridiniu`, `viso_lobistu`; e.g. 2026-06-30: 172 natural +
     229 legal = 401);
   - `ataskaita/SkaidrumoDeklaracija` — monthly count of published transparency declarations
     (`paskelbta`, `viso_paskelbta`);
   - `ataskaita/ItakosDeklaracija` — monthly count of experienced-influence declarations;
   - `pinreg_ataskaitos/AsmuoDeklaracija`, `PareigybeDeklaracija` (declarations by position
     type), `Sprendimas` (VTEK decisions: violation / no violation / investigation dropped).
   The data.gov.lt catalogue (searches "lobist", "interes", "VTEK") lists nothing else
   (datasets 2935, 3798, 3799).
2. **The registers themselves** — `pinreg.vtek.lt`, `skaidris.vtek.lt` and `www.vtek.lt` all
   answer `403` with a Cloudflare "Just a moment…" JavaScript challenge to any non-browser
   client. Same situation as vmi.lt for the property declarations. Per project rule, the
   challenge is **not** circumvented (no headless/stealth browsers, no cookie reuse).
3. **e-seimas.lrs.lt** (for the law texts below) is behind the same kind of challenge, so the
   article-level citations below come from search-engine snippets and secondary sources and
   should be re-checked in a browser.

## Legal basis for publication

- **Law on the Reconciliation of Public and Private Interests** (Viešųjų ir privačių
  interesų derinimo įstatymas, VIII-371, new wording in force 2020-01-01, PINREG in use from
  2021). It sets out the declaration content: workplaces, legal entities the declarant (or
  spouse/partner) participates in or can decisively influence, positions in them, gifts,
  transactions. It also has a publicity article ("…deklaracijų viešumas", Art. 10): the
  declarations of politicians, state officials, judges, mayors and council members, among
  others, are published. Personal codes, social-security numbers, special-category data and
  other data the law prohibits are excluded. VTEK guidance: "all their latest declarations, with
  few exceptions, are public".
- **Law on Lobbying Activities** (Lobistinės veiklos įstatymas, XIII-3170 of 2020-06-26, in
  force 2021-01-01) requires each lobbyist to declare, per draft legal act, the client, the
  beneficiary and the act. Each official who was lobbied must declare the influence within
  7 days. Both declaration types and the lobbyist list are published in SKAIDRIS. The
  2025-2026 STT/VTEK reviews note that the published scope is narrow by EU standards: no
  funding, memberships or resources.

## Proposed approach: a browser harvest, like `harvest-declarations`

The working pattern already in the repo is `.claude/skills/harvest-declarations/` together with
`etl/declarations/harvest.js`. The harvest runs in the user's own Chrome via Claude in Chrome,
which passes Cloudflare as a normal visitor. It saves one JSON file that is committed as the
domain's source of truth, and `make` does the rest offline. For VTEK:

1. **Discover the public API from the browser.** Both registers are single-page apps (`/app/`),
   so the public search almost certainly calls JSON endpoints on the same origin. In the user's
   Chrome, open the public search, run one query and read the network log
   (`read_network_requests`) to identify the endpoints and response shape. Not verified yet,
   because the challenge blocks every scripted look.
2. **`etl/vtek/harvest.js`** (same structure as the declarations harvester: idempotent,
   resumable, `window.__harvest` / `__hstatus`, one request per ~2–5 s):
   - PINREG: iterate the declarants who reconcile to `persons/` (the 831 Seimas persons, plus
     ministers and mayors once the `officials` branch lands), searching by name. Keep **only
     the declarant's own** legal-entity ties: JAR code, entity name, relation type (participant
     / shareholder, manager, board or council member), dates. **Drop** spouse/partner and
     close-person sections, gifts and transactions. They concern private individuals or carry
     no JAR key.
   - SKAIDRIS: the full lobbyist list (natural and legal persons — registered lobbyists are
     public by law) and all published transparency and experienced-influence declarations,
     each with its client, beneficiary, draft act and declaration date.
3. **`.claude/skills/harvest-vtek/SKILL.md`**: browser steps, polling, an explicit download
   consent step, rebuild. Same rules as harvest-declarations: never click the challenge, stop on
   form drift. Cadence: lobbying monthly or quarterly; PINREG yearly (it is continuously
   updated, so date each harvest).
4. **`etl/vtek/`**: the JSON goes through a Python normalizer (`etl/tools`, like
   `ltlod_etl.declarations`) to CSV, then CSV2RDF, then the mappings below, then validate.

## Target model (ready for when data is available)

All IRIs follow the existing conventions (natural keys, no blank nodes, entity per graph,
calendar links).

- **Interests** (`interests/{asmens_id}/`, one doc per declarant; `#this` is the declaration):
  - each tie is a fragment `#{jar}-{role}` typed `org:Membership`, with `org:member` set to
    `persons/{asmens_id}/#this`, `org:organization` set to `legal-entities/{jar}/#this`, and
    `org:role` taken from a new taxonomy `taxonomies/interest-roles/` (participant, manager,
    board member, supervisory council member, employee);
  - `org:memberDuring` points to a `time:Interval` whose instants carry `dct:temporal` calendar
    days;
  - this reuses the n-ary membership model and the `:Memberships` view already used for
    Seimas positions.
- **Lobbyists** (`lobbyists/{vtek-id}/`): a legal-person lobbyist gets `owl:sameAs
  legal-entities/{jar}/#this`; a natural-person lobbyist is a `foaf:Person` with its name only.
- **Lobbying declarations** (`lobbying-declarations/{vtek-id}/`), with `#this` typed
  `ltlod:LobbyingDeclaration`:
  - `ltlod:lobbyist` and `ltlod:client`, each pointing to a `legal-entities/{jar}/#this` or a
    lobbyist;
  - `ltlod:beneficiary`;
  - `ltlod:draftAct`, linking to the Seimas legislative project, the same `TAP` document id
    the `seimas-bills` branch mints;
  - `ltlod:influenced`, pointing to `persons/{asmens_id}/#this` for an official who declared
    the influence;
  - `dct:temporal` to the declaration day, plus the date literal.

  There is no W3C, SEMIC or schema.org lobbying vocabulary (the EU Transparency Register
  publishes no RDF terms), so this lands at the `ltlod:` end of the cascade.

### The insight it enables: a conflict-of-interest query (sketch)

```sparql
# An MP who declared a tie to a company, which lobbied on a draft act the MP then voted on.
SELECT ?mp ?company ?act ?vote
WHERE {
  GRAPH ?ig { ?m a org:Membership ; org:member ?mp ; org:organization ?company }
  GRAPH ?lg { ?decl ltlod:client ?company ; ltlod:draftAct ?act }
  GRAPH ?vg { ?vote ltlod:onDraftAct ?act ; ltlod:voter ?mp }   # needs seimas-bills
}
```

## Fallback, not implemented: the aggregates

The Spinta aggregates are scriptable today and could be loaded as an RDF Data Cube (`qb:`)
series: lobbyist counts by month, declarations per month, VTEK decisions by outcome. They link
to nothing else in the graph except calendar months, so they add no cross-referencing value.
They were left out deliberately. They could go into the `statistics` domain if it adopts `qb:`.
