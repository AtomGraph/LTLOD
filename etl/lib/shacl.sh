#!/usr/bin/env bash
# SHACL-validate a TriG file against a shapes graph.
# Jena's `shacl validate` ignores TriG named graphs (it validates the empty
# default graph) and always exits 0, so flatten to the union of graphs first
# and detect conformance by parsing the --text report.
# The optional <base> resolves base-relative IRIs in a committed .trig against
# the real host (ignored for already-absolute .nq/.nt input, e.g. from
# validate.sh); without it the suffix-anchored sh:pattern shapes still match,
# but resolving keeps the report meaningful.
# Usage: shacl.sh <shapes.ttl> <file.trig|.nq> [base]
set -euo pipefail

shapes="$1"
f="$2"
base="${3:-}"
jena="${JENA_HOME:?JENA_HOME not set}/bin"
export JVM_ARGS="${JVM_ARGS:--Xmx2g}"   # streets.trig ~0.7M triples

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
nt="$tmp/data.nt"                       # real file + .nt extension required:
                                        # shacl/riot detect format by extension

if [ -n "$base" ]; then
    "$jena/riot" --merge --base="$base" --output=ntriples "$f" > "$nt"
else
    "$jena/riot" --merge --output=ntriples "$f" > "$nt"
fi

report="$("$jena/shacl" validate --text --shapes "$shapes" --data "$nt")"

if [ "$report" != "Conforms" ]; then
    echo "$report" >&2
    echo "ERROR: $f does not conform to $shapes" >&2
    exit 1
fi

echo "conforms: $f ($shapes)" >&2
