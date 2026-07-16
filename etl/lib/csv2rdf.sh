#!/usr/bin/env bash
# Normalize CSV to source-shaped N-Triples using AtomGraph CSV2RDF (identity transform).
# Column values become <{base}#column> literal properties on per-row resources,
# which the graphify mapping queries then match as <#column>.
# Uses the atomgraph/csv2rdf Docker image (the local jar requires an older JDK).
# Usage: csv2rdf.sh <input.csv> <base-uri> > output.nt
set -euo pipefail

csv="$1"
base="$2"
lib="$(cd "$(dirname "$0")" && pwd)"

docker run --rm -i -a stdin -a stdout -a stderr \
    -v "$lib/identity.rq":/tmp/identity.rq \
    atomgraph/csv2rdf /tmp/identity.rq "$base" < "$csv"
