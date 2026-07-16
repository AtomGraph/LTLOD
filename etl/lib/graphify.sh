#!/usr/bin/env bash
# Apply an LDH-style quad CONSTRUCT mapping (entity per named graph) to source-shaped RDF.
# The mapping query uses $base exactly like LinkedDataHub CSV import queries; this script
# binds it and sets the query BASE so <#column> property patterns resolve against it.
# Usage: graphify.sh <mapping.rq> <base-uri> <data-file> [more-data-files...] > output.trig
set -euo pipefail

query="$1"
base="$2"
shift 2

tmp=$(mktemp -t graphify.XXXXXX.rq)
trap 'rm -f "$tmp"' EXIT

{
    echo "BASE <${base}>"
    sed "s|\$base|<${base}>|g" "$query"
} > "$tmp"

data_args=()
for d in "$@"; do
    data_args+=(--data "$d")
done

"${JENA_HOME:?JENA_HOME not set}/bin/arq" "${data_args[@]}" --query "$tmp"
