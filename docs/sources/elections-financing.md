# Political campaign financing (VRK): feasibility

Status: **not implemented**. The election *results* are built (`etl/elections/`) from
VRK's public ArcGIS layers. Campaign financing (who donated to which party or candidate)
was in scope for the same pipeline but no scriptable source exists.

## What VRK publishes

The data.gov.lt catalogue lists the datasets. VRK prepares them; the State Data Agency
(VDA) is the publisher. Licence: CC BY 4.0.

| data.gov.lt | Dataset | Content |
|---|---|---|
| [2016](https://data.gov.lt/datasets/2016/) | Politinės kampanijos pajamos | campaign income: donations and donors per campaign participant |
| [2017](https://data.gov.lt/datasets/2017/) | Politinės kampanijos išlaidos ir skolų įsipareigojimai | campaign expenses and debts |
| [2018](https://data.gov.lt/datasets/2018/) | Politinės kampanijos dalyvių reklamos duomenys | political advertising |
| [2019](https://data.gov.lt/datasets/2019/) | Politinės organizacijos gauti narių mokesčiai | party membership fees |
| [2129](https://data.gov.lt/datasets/2129/) | Kandidatų ir kandidatų sąrašų iškėlimo parėmimas | signatures supporting nominations |

The same VRK instance also serves the full election results by polling station:
[2012](https://data.gov.lt/datasets/2012/) *Balsavimo rezultatai rinkimuose ir
referendumuose*, [2013](https://data.gov.lt/datasets/2013/) preference votes, and
[2015](https://data.gov.lt/datasets/2015/) the current composition of elected bodies. All
of these carry VRK's own candidate and party ids, which the ArcGIS layers lack.

## Blocker

Every distribution of these datasets resolves to VRK's own Spinta instance,
`https://atviriduomenys.vrk.lt/datasets/gov/vrk/…` (e.g. `…/Rezultatai`, `…/Isrinkti`).
That host, like `www.vrk.lt`, is behind a **Cloudflare bot challenge**: every request,
including the UAPI `:format/csv` and `:ns` endpoints, answers `403` with
`cf-mitigated: challenge`. The datasets are not mirrored on `get.data.gov.lt`, where
`datasets/gov/vrk/` holds only four unrelated models. The ArcGIS hub
(`rinkimai-vrk.opendata.arcgis.com`) has results maps only, nothing on financing.

The pipeline does not get around the challenge.

## Possible approaches

1. **Ask VRK or VDA** (atverimas@stat.gov.lt) to exempt the Spinta API from the
   challenge or mirror it on get.data.gov.lt, like the other `datasets/gov/*`
   publishers. This is the cleanest fix, and it would also give the pipeline
   polling-station results and VRK candidate ids.
2. **Browser harvest**, like `.claude/skills/harvest-declarations/`: run a
   Claude-in-Chrome skill that pages through the Spinta JSON in the user's own browser
   (past the challenge, as a person) and commits the dump under
   `etl/elections/data/`. Financing changes once per campaign, so a harvest per
   election is enough.

## Modelling notes for when it lands

- **Donors who are legal entities** get full detail: the donation links to
  `legal-entities/{ja_kodas}/#this` by natural key, so it works as soon as the full
  JAR is loaded.
- **Donors who are natural persons** are private individuals. Mint nothing for them:
  aggregate per recipient and year (count, sum), or link only donors who resolve to an
  existing `persons/` entry (public officials).
- **Recipients**: parties link to `parties/{slug}/` via the same slug and alias rules
  as `ltlod-elections`; candidates link to `persons/`. VRK candidate ids also appear
  in the ArcGIS photo URLs (`photo_{id}.jpeg`), which `ltlod-elections` already uses
  as result keys. If they match the Spinta candidate ids (not verified, since that host
  is unreachable), financing rows can join to candidate results on that id.
- **Vocabulary**: a donation is a `schema:MonetaryAmount` (as in declarations),
  attached to an `ltlod:Donation` (donor, recipient, campaign/election, date →
  calendar day). No W3C/EU vocabulary covers political finance.
