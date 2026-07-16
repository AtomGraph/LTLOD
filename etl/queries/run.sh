#!/usr/bin/env bash
# Run a SPARQL query across ALL generated datasets, loaded into an in-memory
# Jena dataset (~1M quads, needs a few GB of heap).
#
# Usage:
#   ./run.sh <query.rq> [extra arq args, e.g. --results=csv]
#   ./run.sh --all                # run every .rq in this directory
set -euo pipefail

dir="$(cd "$(dirname "$0")" && pwd)"
data_dir="$dir/../../datasets/current"
JENA_HOME="${JENA_HOME:-/Users/martynas/WebRoot/apache-jena-5.6.0}"
export JVM_ARGS="${JVM_ARGS:--Xmx4g}"

data_args=()
for f in "$data_dir"/*/*.trig; do
    data_args+=(--data "$f")
done

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
