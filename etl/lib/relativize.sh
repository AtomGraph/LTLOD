#!/usr/bin/env bash
# Rewrite a TriG stream to base-RELATIVE IRIs, emitting NO @base directive, so
# committed datasets/current/**/*.trig stay base-agnostic (the base is supplied
# at load/parse/validate time via `riot --base=…`, never baked into the files).
# IRIs under <base> become relative tokens (e.g. <persons/84854/#this>); external
# IRIs (Wikidata, Wikimedia Commons, lrs.lt, EU authority tables, schema.org,
# mailto/tel) are left absolute.
#
# Recipe (verified, Jena 5.6.0/6.1.0): prepend a parse-time @base, re-serialize
# with riot's STREAMING trig writer (--output — it relativizes against the
# prologue base; --formatted does NOT), then drop the emitted base header line.
# Inverse operation (relative -> absolute) is just `riot --base=<base>`.
#
# Usage: relativize.sh <base-uri> < in.trig > out.trig
set -euo pipefail

base="$1"
jena="${JENA_HOME:?JENA_HOME not set}/bin"

{
    echo "@base <${base}> ."
    cat
} | "$jena/riot" --syntax=trig --output=trig /dev/stdin \
  | sed -E '/^(BASE|@base)[[:space:]]+<[^>]*>[[:space:]]*\.?[[:space:]]*$/d'
