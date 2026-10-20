#!/usr/bin/env bash
# Graphify the full JAR register in row chunks. arq's CONSTRUCT and validate.sh hold
# the whole model in memory, and the ~540k-entity register (~14.5M output quads) does
# not fit in one run; every entity is self-contained (its office row is keyed by the
# same ja_kodas), so the chunks are independent and their TriG outputs concatenate
# into one valid document (TriG allows repeated PREFIX directives).
#
# Each chunk: rows -> CSV2RDF; its office rows (offices.csv filtered to the chunk's
# codes) -> CSV2RDF; mapping -> relativized TriG; validate.sh (syntax, LDH graph
# invariants, no bnodes, graph count = row count) + the domain's SHACL shapes.
#
# Assumes no embedded newlines in the CSV (true of the JAR dump: line count = row
# count + 1; validate.sh's per-chunk graph count would catch a split record) and
# ja_kodas as column 3 of the entities CSV / column 1 of offices.csv (numeric, unquoted).
#
# Usage: chunked.sh <entities.csv> <offices.csv> <mapping.rq> <shapes.ttl> <base> <out.trig>
# Env:   CHUNK_ROWS (default 25000), JOBS (parallel chunks, default 3),
#        CHUNK_DIR (scratch dir, default cache/chunks — wiped on every run)
set -euo pipefail

if [ "${1:-}" = "--chunk" ]; then
    # one chunk (invoked via xargs below)
    part="$2" offices="$3" mapping="$4" shapes="$5" base="$6"
    lib="$(cd "$(dirname "$0")/../lib" && pwd)"
    awk -F, 'NR==FNR{if(FNR>1)ja[$3];next} FNR==1||($1 in ja)' "$part.csv" "$offices" > "$part-offices.csv"
    "$lib/csv2rdf.sh" "$part.csv" "$base" > "$part.nt"
    "$lib/csv2rdf.sh" "$part-offices.csv" "$base" > "$part-offices.nt"
    "$lib/graphify.sh" "$mapping" "$base" "$part.nt" "$part-offices.nt" > "$part.trig"
    rows=$(($(wc -l < "$part.csv") - 1))
    "$lib/validate.sh" "$part.trig" "$base" "$rows"
    "$lib/shacl.sh" "$shapes" "$part.trig" "$base"
    rm -f "$part.nt" "$part-offices.nt" "$part-offices.csv"
    exit 0
fi

entities="$1" offices="$2" mapping="$3" shapes="$4" base="$5" out="$6"
rows="${CHUNK_ROWS:-25000}"
jobs="${JOBS:-3}"
self="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

dir="${CHUNK_DIR:-cache/chunks}"
rm -rf "$dir"
mkdir -p "$dir"

header="$(head -1 "$entities")"
tail -n +2 "$entities" | split -l "$rows" -a 3 - "$dir/part-"
for p in "$dir"/part-???; do
    { echo "$header"; cat "$p"; } > "$p.csv"
    rm "$p"
done

ls "$dir"/part-???.csv | sed 's/\.csv$//' \
    | xargs -P "$jobs" -I{} "$self" --chunk {} "$offices" "$mapping" "$shapes" "$base"

cat "$dir"/part-???.trig > "$out.tmp"
mv "$out.tmp" "$out"
rm -rf "$dir"
echo "graphified $(($(wc -l < "$entities") - 1)) rows in chunks -> $out" >&2
