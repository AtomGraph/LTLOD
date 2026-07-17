#!/usr/bin/env bash
# Validate a TriG output file: syntax + LDH named-graph invariants
# (every graph must carry dct:title on the graph/document URI, plus
# foaf:primaryTopic unless the document is a dh:Container).
# Usage: validate.sh <file.trig> [expected-graph-count]
set -euo pipefail

f="$1"
expected="${2:-}"
jena="${JENA_HOME:?JENA_HOME not set}/bin"

"$jena/riot" --validate "$f"

count() {
    "$jena/arq" --data "$f" --results=csv --query <(echo "$1") | tail -1 | tr -d '\r'
}

graphs=$(count 'SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { GRAPH ?g { } }')

bad=$(count 'PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dh:   <https://www.w3.org/ns/ldt/document-hierarchy#>
SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE {
    GRAPH ?g { }
    FILTER(
        NOT EXISTS { GRAPH ?g { ?g dct:title ?t } } ||
        (NOT EXISTS { GRAPH ?g { ?g foaf:primaryTopic ?e } } &&
         NOT EXISTS { GRAPH ?g { ?g a dh:Container } })
    )
}')

if [ "$bad" != "0" ]; then
    echo "ERROR: $f has $bad graph(s) missing dct:title/foaf:primaryTopic" >&2
    exit 1
fi

if [ -n "$expected" ] && [ "$graphs" != "$expected" ]; then
    echo "ERROR: $f has $graphs graphs, expected $expected" >&2
    exit 1
fi

# SHACL shapes: resolved by output directory name (datasets/current/<domain>/)
shapes="$(dirname "$0")/../shapes/$(basename "$(dirname "$f")").ttl"
if [ -f "$shapes" ]; then
    "$(dirname "$0")/shacl.sh" "$shapes" "$f"
fi

echo "valid: $f ($graphs graphs)" >&2
