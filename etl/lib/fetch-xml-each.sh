#!/usr/bin/env bash
# Fetch one XML document per id, where the ids are read (with xmlstarlet) from
# already-fetched list documents — e.g. the sessions of every term, then the
# sittings of every session. A single document may legitimately be empty (a
# session that has just opened has no sittings yet), but the run fails loudly
# when the documents hold no <element> at all, or a document is not well-formed.
# The output directory is replaced atomically, so ids that disappeared from the
# source do not linger in the cache.
# JOBS (env, default 1) sets how many requests run concurrently — the per-vote
# feeds run to thousands of ids, too many to fetch one at a time.
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

ids=$(xmlstarlet sel -t -m "$xpath" -v . -n "$@" | grep . | sort -u || true)
if [ -z "$ids" ]; then
    echo "ERROR: no ids matching ${xpath} in $*" >&2
    exit 1
fi

fetch_one() {
    local out="${tmp}/${1}.xml"
    curl -fsSL --retry 3 --retry-delay 2 --max-time 300 "${prefix}${1}" -o "$out"
    xmlstarlet val -q -w "$out" || { echo "ERROR: ${prefix}${1} is not well-formed XML" >&2; exit 1; }
}
export -f fetch_one
export prefix tmp

echo "$ids" | xargs -P "${JOBS:-1}" -I{} bash -c 'fetch_one "$1"' _ {}

total=$(find "$tmp" -name '*.xml' -exec xmlstarlet sel -t -v "count(//${element})" -n {} + \
    | awk '{ s += $1 } END { print s + 0 }')

if [ "$total" -eq 0 ]; then
    echo "ERROR: ${prefix}<id> returned no <${element}> elements for any id" >&2
    exit 1
fi

rm -rf "$outdir"
mv "$tmp" "$outdir"
echo "fetched ${prefix}<id> for $(echo "$ids" | wc -l | tr -d ' ') ids: ${total} <${element}> elements -> ${outdir}" >&2
