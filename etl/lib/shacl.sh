#!/usr/bin/env bash
# SHACL-validate a TriG file against a shapes graph.
# Jena's `shacl validate` ignores TriG named graphs (it validates the empty
# default graph) and always exits 0, so flatten to the union of graphs first
# and detect conformance by parsing the --text report.
# Usage: shacl.sh <shapes.ttl> <file.trig>
set -euo pipefail

shapes="$1"
f="$2"
jena="${JENA_HOME:?JENA_HOME not set}/bin"
export JVM_ARGS="${JVM_ARGS:--Xmx2g}"   # streets.trig ~0.7M triples

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
nt="$tmp/data.nt"                       # real file + .nt extension required:
                                        # shacl/riot detect format by extension

"$jena/riot" --merge --output=ntriples "$f" > "$nt"

report="$("$jena/shacl" validate --text --shapes "$shapes" --data "$nt")"

if [ "$report" != "Conforms" ]; then
    echo "$report" >&2
    echo "ERROR: $f does not conform to $shapes" >&2
    exit 1
fi

echo "conforms: $f ($shapes)" >&2
