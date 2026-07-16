#!/usr/bin/env bash
# Fetch an XML document and fail loudly if it lacks expected elements.
# Usage: fetch-xml.sh <url> <output.xml> <required-element-name>
set -euo pipefail

url="$1"
out="$2"
element="$3"

mkdir -p "$(dirname "$out")"
curl -fsSL --retry 3 --max-time 300 "$url" -o "${out}.tmp"

count=$(grep -c "<${element}" "${out}.tmp" || true)
if [ "$count" -eq 0 ]; then
    echo "ERROR: ${url} returned no <${element}> elements" >&2
    rm -f "${out}.tmp"
    exit 1
fi

mv "${out}.tmp" "$out"
echo "fetched ${url}: ${count} <${element}> elements -> ${out}" >&2
