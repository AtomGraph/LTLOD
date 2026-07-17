# SHACL formos

SHACL validacijos formos kiekvieno domeno esybių tipams — lygiagrečiai
žodynų pasirinkimams (`etl/ONTOLOGY-NOTES.md`). Failo pavadinimas atitinka
`datasets/current/` pakatalogį:

| Formų failas | Duomenys | Esybių tipai |
|---|---|---|
| `taxonomies.ttl` | `datasets/current/taxonomies/*.trig` | `skos:ConceptScheme`, `skos:Concept` |
| `admin-units.ttl` | `datasets/current/admin-units/*.trig` | `cv:AdminUnit`, `dct:Location` (gatvės) |
| `legal-entities.ttl` | `datasets/current/legal-entities/*.trig` | `rov:RegisteredOrganization` |
| `seimas.ttl` | `datasets/current/seimas/*.trig` | `foaf:Person`, `org:Membership`, `time:Interval`/`time:Instant`, `org:OrganizationalUnit`, `org:FormalOrganization` |

## Kaip vykdoma validacija

- `etl/lib/shacl.sh <formos.ttl> <failas.trig>` — TriG failas pirmiausia
  suplokštinamas į jo grafų sąjungą (`riot --merge`), nes Jena `shacl`
  ignoruoja vardinius grafus; atitikimas nustatomas iš `--text` ataskaitos.
- Formos parenkamos automatiškai pagal išvesties katalogą ETL `validate`
  etape (`etl/lib/validate.sh`), todėl vykdomos per kiekvieną `make`.
- CI: `.github/workflows/shacl-validation.yml` validuoja visus
  commit'intus `.trig` failus per kiekvieną push/PR. Gitignore'inti
  masyvūs failai (`settlements.trig`, `streets.trig`) validuojami tik
  lokaliai per `make`.

## Principai

- Formos aprašo **esamus** duomenis (ką mapping'ai garantuoja), o ne
  siekiamybę — pasikeitus mapping'ui, atitinkamą formų failą reikia
  atnaujinti tame pačiame commit'e.
- URI šablonai (`sh:pattern`) tikrina tik kelio galūnę, ne host'ą, todėl
  `make BASE=…` išvestys taip pat validuojasi.
- Nuorodos tarp failų (`dct:isPartOf`, `rov:companyType`, `org:organization`
  ir kt.) tikrinamos tik kaip IRI — nuorodų vientisumas (ar taikinys
  egzistuoja) lieka `etl/queries/` atsakomybė.
- `sh:languageIn` + `sh:uniqueLang` sąmoningai griežti: pridėjus naują
  kalbą duomenyse, CI nepraeis, kol formos nebus atnaujintos (drift'o
  aptikimas).
