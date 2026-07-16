#!/usr/bin/env bash
# Fetch a full CSV dump of a get.data.gov.lt (Spinta/UAPI) model.
# Usage: fetch-spinta.sh <model-path> <output.csv> [select-expr]
#   model-path  e.g. datasets/gov/rc/ar/apskritis/Apskritis
#   select-expr e.g. "adm_kodas,pavadinimas,adm_nuo" (dereferencing supported: apskritis.adm_kodas)
set -euo pipefail

model="$1"
out="$2"
select="${3:-}"

url="https://get.data.gov.lt/${model}/:format/csv"
if [ -n "$select" ]; then
    url="${url}?select(${select})"
fi

mkdir -p "$(dirname "$out")"
curl -fsSL --retry 3 --max-time 600 "$url" -o "${out}.tmp"

# Fail loudly on empty/short results (schema drift, API errors)
lines=$(wc -l < "${out}.tmp" | tr -d ' ')
if [ "$lines" -le 1 ]; then
    echo "ERROR: ${model} returned no data rows" >&2
    rm -f "${out}.tmp"
    exit 1
fi

mv "${out}.tmp" "$out"
echo "fetched ${model}: $((lines-1)) rows -> ${out}" >&2
