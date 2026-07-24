#!/usr/bin/env bash
# Run a SPARQL query across ALL generated datasets, loaded into an in-memory
# Jena dataset (~1M quads, needs a few GB of heap).
#
# Committed TriG is base-relative; resolve every file against ONE base first
# (arq's per-file --data would resolve each file's relative IRIs against its own
# file:// URL and break cross-graph joins). Default base = prod, since some
# committed queries pin linkeddata.lt URIs; override with BASE=… ./run.sh …
#
# Usage:
#   ./run.sh <query.rq> [extra arq args, e.g. --results=csv]
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
data_args=(--data "$merged")

if [ "${1:-}" = "--all" ]; then
    for q in "$dir"/*.rq; do
        echo "=== $(basename "$q")" >&2
        "$JENA_HOME/bin/arq" "${data_args[@]}" --query "$q"
    done
else
    query="$1"
    shift
    "$JENA_HOME/bin/arq" "${data_args[@]}" --query "$query" "$@"
fi
