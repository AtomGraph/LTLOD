#!/usr/bin/env bash
# Validate a TriG output file: syntax + LDH named-graph invariants
# (every graph must carry dct:title and foaf:primaryTopic on the graph/document
# URI — ETL outputs are dh:Item documents only; containers come from app/).
# Committed TriG carries base-RELATIVE IRIs with no @base; the base is supplied
# here so validation resolves them to real absolute URIs (not file://). arq's
# --base is the *query* base, not the data-parse base, so pre-resolve once to
# N-Quads and run every check (and SHACL) against that.
# Usage: validate.sh <file.trig> <base-uri> [expected-graph-count]
set -euo pipefail

f="$1"
base="$2"
expected="${3:-}"
jena="${JENA_HOME:?JENA_HOME not set}/bin"

"$jena/riot" --validate --base="$base" "$f"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
nq="$tmp/data.nq"
"$jena/riot" --base="$base" --syntax=trig --output=nquads "$f" > "$nq"

count() {
    "$jena/arq" --data "$nq" --results=csv --query <(echo "$1") | tail -1 | tr -d '\r'
}

graphs=$(count 'SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { GRAPH ?g { } }')

bad=$(count 'PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE {
    GRAPH ?g { }
    FILTER NOT EXISTS { GRAPH ?g { ?g dct:title ?t ; foaf:primaryTopic ?e } }
}')

if [ "$bad" != "0" ]; then
    echo "ERROR: $f has $bad graph(s) missing dct:title/foaf:primaryTopic" >&2
    exit 1
fi

if [ -n "$expected" ] && [ "$graphs" != "$expected" ]; then
    echo "ERROR: $f has $graphs graphs, expected $expected" >&2
    exit 1
fi

# SHACL shapes: resolved by output directory name (datasets/current/<domain>/).
# Hand shacl the already-absolute N-Quads so it needs no base.
shapes="$(dirname "$0")/../shapes/$(basename "$(dirname "$f")").ttl"
if [ -f "$shapes" ]; then
    "$(dirname "$0")/shacl.sh" "$shapes" "$nq"
fi

echo "valid: $f ($graphs graphs)" >&2
