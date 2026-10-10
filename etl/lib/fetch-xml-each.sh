#!/usr/bin/env bash
# Fetch one XML document per id, where the ids are read (with xmlstarlet) from
# already-fetched list documents — e.g. the sessions of every term, then the
# sittings of every session. A single document may legitimately be empty (a
# session that has just opened has no sittings yet), but the run fails loudly
# when the documents hold no <element> at all, or a document is not well-formed.
# The output directory is replaced atomically, so ids that disappeared from the
# source do not linger in the cache.
# Usage: fetch-xml-each.sh <url-prefix> <outdir> <element> <id-xpath> <list.xml>...
set -euo pipefail

prefix="$1"
outdir="$2"
element="$3"
xpath="$4"
shift 4

tmp="${outdir}.tmp"
rm -rf "$tmp"
mkdir -p "$tmp"

ids=$(xmlstarlet sel -t -m "$xpath" -v . -n "$@" | sort -u)
if [ -z "$ids" ]; then
    echo "ERROR: no ids matching ${xpath} in $*" >&2
    exit 1
fi

total=0
for id in $ids; do
    out="${tmp}/${id}.xml"
    curl -fsSL --retry 3 --max-time 300 "${prefix}${id}" -o "$out"
    xmlstarlet val -q -w "$out" || { echo "ERROR: ${prefix}${id} is not well-formed XML" >&2; exit 1; }
    count=$(xmlstarlet sel -t -v "count(//${element})" "$out")
    total=$((total + count))
done

if [ "$total" -eq 0 ]; then
    echo "ERROR: ${prefix}<id> returned no <${element}> elements for any id" >&2
    exit 1
fi

rm -rf "$outdir"
mv "$tmp" "$outdir"
echo "fetched ${prefix}<id> for $(echo "$ids" | wc -l | tr -d ' ') ids: ${total} <${element}> elements -> ${outdir}" >&2
