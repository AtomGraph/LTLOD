---
name: investigate-ltlod
description: Answer an investigative or journalistic question from the LTLOD (Lithuanian Linked Open Data) datasets — who controls or funds what, how much public money a company or person receives, and which hidden connections the linked registers reveal. Use when asked to follow a company's public money, check a politician's declared interests against contracts or funds, find suppliers below the procurement radar, trace campaign donors, or otherwise connect the Lithuanian registers; it names the domains and join keys to use and the caveats that decide whether a finding is solid.
---

# Investigate LTLOD

Turn an investigative **question** into the right query. For the mechanics of writing and
running the query (named-graph model, `run.sh` vs. the throttled endpoint, the query-shape
rules), load **`write-ltlod-sparql`** — every recipe here produces a query that must obey it.
49 worked queries with explanations are in **`queries/EXAMPLES.md`**; the URI map is in
**`etl/URI-SCHEME.md`**. Start from the closest example, don't write blank.

## The join keys (this is the whole point)

The datasets are separate registers; their investigative power is the keys that connect them.
**The same key is the same IRI in every domain, so joins need no lookup.**

| Key | IRI | Connects (predicate → the shared IRI) |
|---|---|---|
| **JAR code** (9-digit company code) | `legal-entities/{code}/#this` | procurement buyer/contractor (`epo:playedBy`), taxpayer (`ltlod:taxpayer`), Sodra employer (`ltlod:employer`), campaign donor (`ltlod:donor`), EU-fund beneficiary/partner (`ltlod:beneficiary`/`ltlod:fundingPartner`), insolvent company (`ltlod:insolvent`), invoice buyer/supplier (`ltlod:spendingBuyer`/`ltlod:spendingSupplier`), land applicant (`ltlod:applicant`), VTEK interest org (`ltlod:interestOrganization`), lobbyist/agent (`ltlod:agent`) |
| **`asmens_id`** (Seimas person id) | `persons/{asmens_id}/#this` | Seimas members, officials, VMI/PINREG declarants, VRK candidates, lobbied contacts, membership/vote history |
| **AR code** | `admin-units/{code}/#this` | the municipality/county of an observation or location (`sdmx-dimension:refArea`, `schema:location`) |
| **calendar day/year** | `calendar/{yyyy}[/{mm}/{dd}]/#this` | every dated event/period (`dct:temporal`) — "what happened on/in …" |
| **Wikidata QID** | via `owl:sameAs` | aligned persons and places |

So *"which company links procurement and EU funds?"* is just: the same `legal-entities/{code}/#this`
is the object of `epo:playedBy` in one graph and `ltlod:beneficiary` in another.

## Where to look (container → what it holds)

`legal-entities/` JAR register · `persons/` Seimas members & officials · `procurement-contracts/`
VPT contracts · `taxes/` VMI arrears + taxes paid · `employment/` Sodra employer stats ·
`eu-funds/` 2014-2020 EU structural funds · `insolvency-cases/` bankruptcies/restructurings ·
`public-spending/` public-sector invoice aggregates · `land-acquisitions/` NŽT land applications ·
`campaign-finance/` + `election-results/` VRK · `interest-declarations/` PINREG private interests ·
`lobbying-declarations/` + `lobbyists/` VTEK SKAIDRIS · `declarations/` VMI asset declarations ·
`seimas` votes/bills/sittings · `admin-units/` + `calendar/` + `facilities/`.

## Recipes (question → approach → start from)

- **Follow a company's public money.** Join `legal-entities/{code}/#this` across procurement
  (`epo:playedBy`), taxes (`ltlod:taxpayer` — arrears/paid), eu-funds (`ltlod:beneficiary`),
  public-spending (`ltlod:spendingSupplier`), insolvency (`ltlod:insolvent`). → `eu-funds-and-procurement.rq`,
  `taxes-contractors-with-arrears.rq`, `contractors-in-insolvency.rq`.
- **A politician's declared interests vs. public money.** VTEK `ltlod:interestOrganization` →
  the same JAR IRI as a procurement contractor / eu-fund beneficiary / invoice supplier. Filter the
  tie `?role skos:notation` to ownership/control (`akcininkas, dalininkas, savininkas, vadovas,
  valdybos-narys, …`). → `vtek-interest-procurement.rq`, `pinreg-ties-eu-funds.rq`,
  `pinreg-ties-public-spending.rq`.
- **A supplier below the procurement radar.** public-spending suppliers billed a lot via many
  small invoices (group per supplier, avg invoice under the threshold) who hold **no** procurement
  contract. → `suppliers-under-threshold.rq`.
- **Campaign donors and what they got.** campaign-finance `ltlod:donor` → procurement contractor /
  later insolvent. → `finance-donors-procurement.rq`, `donors-later-insolvent.rq`.
- **New companies / land.** land-acquisitions `ltlod:applicant` × legal-entities registration date
  × Sodra headcount. → `land-new-companies.rq`.
- **How a member acted vs. lobbying / their wealth.** seimas votes × VTEK lobbying / VMI
  declarations, by `asmens_id`. → `lobbying-then-vote.rq`, and the story `app/stories/seimo-turtas-2024.ttl`.

## Caveats that change the conclusion (state these in any finding)

- **Name-based person links are marked.** Where a source has no shared code with `persons/`
  (VMI/PINREG declarants, VRK candidates, lobbying contacts, officials), the link carries
  `ltlod:matchMethod` → `name-and-office` (name + an office held then — strong) or `exact-name`
  (name only — weaker; audited precision in CLAUDE.md). **Filter to `name-and-office`** for a solid
  person claim; treat `exact-name` as a lead. **Code joins (JAR, `asmens_id`, AR, aligned QID) are
  exact by construction** and carry no method.
- **Natural persons are counts, never named.** Land (and NMA farm subsidies) publish natural-person
  figures only as per-cell aggregates, with **cells under 3 suppressed**. Don't infer individuals.
- **Links dangle until the full JAR is loaded.** A `legal-entities/{code}/#this` link is correct
  even when the name doesn't resolve — the full register (`entities.trig`) must be loaded
  (`make -C etl/legal-entities entities`) for names and `rov:*` details. "No name" ≠ "no match".
- **Snapshots and windows.** Tax **arrears** are the *current* snapshot (not the state at a past
  contract date); **procurement** is the last 12 months ≥ 10 000 EUR; so "owes tax now" / "has no
  contract" are as-of the data date, not history.
- **Known gaps — don't over-claim.** EU-fund **amounts** exist for only ~3 % of records (the
  ~685 coded projects; the rest are code-less instrument payouts). EU-fund **repayments and
  irregularities**, and **NMA farm-subsidy** applicant identities, are keyed by salted/unpublished
  **hashes** that don't join to any public code — they are *not in the data*. The **2021-2027** EU
  programme is not published. Public-sector invoice flows at the top by value are **state financial
  transfers**, not purchases — filter to small-average-invoice suppliers for real procurement-like spend.
