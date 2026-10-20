# Political campaign financing (VRK)

Status: **implemented**, in `etl/elections/` (`make -C etl/elections finance`), from a
browser harvest. The harvest procedure is the project skill
[`.claude/skills/harvest-vrk/`](../../.claude/skills/harvest-vrk/SKILL.md), and the
harvest script is [`etl/elections/harvest-vrk.js`](../../etl/elections/harvest-vrk.js).

## Source

VRK prepares the data and the State Data Agency (VDA) publishes it in the data.gov.lt
catalogue, under licence CC BY 4.0.

| data.gov.lt | Dataset | Spinta model | Used |
|---|---|---|---|
| [2016](https://data.gov.lt/datasets/2016/) | Politinės kampanijos pajamos | `datasets/gov/vrk/Pajamos` | yes |
| [2017](https://data.gov.lt/datasets/2017/) | Politinės kampanijos išlaidos ir skolų įsipareigojimai | `datasets/gov/vrk/Islaidos` | yes |
| — | Seimas election candidates | `datasets/gov/vrk/Kandidatai` | yes (VRK candidate ids) |
| [2018](https://data.gov.lt/datasets/2018/) | Politinės kampanijos dalyvių reklamos duomenys | | not yet |
| [2019](https://data.gov.lt/datasets/2019/) | Politinės organizacijos gauti narių mokesčiai | | not yet |

Every distribution resolves to VRK's own Spinta instance,
`https://atviriduomenys.vrk.lt/`. That host, like `www.vrk.lt`, is behind a
**Cloudflare bot challenge**: scripted requests get `403` with `cf-mitigated:
challenge`. In a real browser the challenge passes by itself, and the JSON API works
via `fetch()` from the page. That is the harvest; nothing scripts around the challenge.

The VRK candidate id (`rink_kandidato_id`) is the same id the VRK results map's ArcGIS
layers put in their candidate photo URLs. All 1 719 ArcGIS candidate results of
2020/2024 match a harvested candidate by id and name. So campaign participants link to
`election-results/…/#round-1-{id}` exactly.

## Privacy

- **Natural-person donors** carry no identity in the harvest: their code, gender and age
  group are dropped in the browser. The ETL aggregates their contributions per participant
  and funding source (count + sum).
- **Natural-person service providers** are blanked at harvest and aggregated per
  participant and expense purpose.
- **Legal persons** (donors, providers) are kept row by row with their published name,
  linked by JAR code to `legal-entities/{code}/`.
- **Candidates** are public by law. A campaign participant links to `persons/` only when
  the candidate held a Seimas seat.

The harvested CSVs are gitignored, never committed.
