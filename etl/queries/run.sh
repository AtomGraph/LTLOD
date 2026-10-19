#!/usr/bin/env bash
# Run a SPARQL query across ALL generated datasets, bulk-loaded into a temporary
# TDB2 store (a few million quads with the opt-in votes; ~20 s to load).
#
# Why TDB2 and not `arq --data`: the queries are plain SPARQL 1.1 with one
# `GRAPH ?g { … }` block per document (no Jena-specific union graph), and arq's
# general in-memory dataset answers a GRAPH block with an unbound ?g by visiting
# every named graph (~190k) — minutes to hours per query. TDB2 answers it from
# its quad indexes, as Fuseki does in deployment.
#
# Committed TriG is base-relative; resolve every file against ONE base first
# (arq's per-file --data would resolve each file's relative IRIs against its own
# file:// URL and break cross-graph joins). Default base = prod, since some
# committed queries pin linkeddata.lt URIs; override with BASE=… ./run.sh …
#
# Usage:
#   ./run.sh <query.rq> [extra tdb2.tdbquery args, e.g. --results=csv]
#   ./run.sh --all                # run every .rq in this directory
set -euo pipefail

dir="$(cd "$(dirname "$0")" && pwd)"
data_dir="$dir/../../datasets/current"
JENA_HOME="${JENA_HOME:-/Users/martynas/WebRoot/apache-jena-6.1.0}"
BASE="${BASE:-https://linkeddata.lt/}"
export JVM_ARGS="${JVM_ARGS:--Xmx4g}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
merged="$tmp/all.nq"
"$JENA_HOME/bin/riot" --base="$BASE" --syntax=trig --output=nquads "$data_dir"/*/*.trig > "$merged"
"$JENA_HOME/bin/tdb2.tdbloader" --loc="$tmp/tdb" "$merged" >/dev/null 2>&1
rm -f "$merged"
data_args=(--loc "$tmp/tdb")

if [ "${1:-}" = "--all" ]; then
    for q in "$dir"/*.rq; do
        echo "=== $(basename "$q")" >&2
        "$JENA_HOME/bin/tdb2.tdbquery" "${data_args[@]}" --query "$q"
    done
else
    query="$1"
    shift
    "$JENA_HOME/bin/tdb2.tdbquery" "${data_args[@]}" --query "$query" "$@"
fi
