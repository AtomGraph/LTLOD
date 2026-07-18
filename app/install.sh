#!/usr/bin/env bash
# Creates/updates the LTLOD container scaffolding (root document + containers +
# taxonomy scheme containers) and the namespace ontology (ns.ttl with 1:N
# entity views) on a running LinkedDataHub instance via the LDH CLI. Requires
# LinkedDataHub's bin/ subdirs and Jena's bin/ (for `turtle`) on
# $PATH — `make install` in the root Makefile sets this up.
# Deliberately does NOT call make-public.sh: `make load` ends with `make public`.
set -euo pipefail

if [ "$#" -ne 3 ] && [ "$#" -ne 4 ]; then
  echo "Usage:   $0" '$base $cert_pem_file $cert_password [$proxy]' >&2
  echo "Example: $0" 'https://localhost:4443/ ./ssl/owner/cert.pem Password https://localhost:5443/' >&2
  echo "Note: special characters such as $ need to be escaped in passwords!" >&2
  exit 1
fi

base="$1"
cert_pem_file=$(realpath "$2")
cert_password="$3"
proxy="${4:-$base}"

app_dir="$(cd "$(dirname "$0")" && pwd)"

printf "\n### Updating root document: %s\n" "$base"
turtle --base="$base" < "$app_dir/root.ttl" | put.sh \
    -f "$cert_pem_file" \
    -p "$cert_password" \
    --proxy "$proxy" \
    -t "application/n-triples" \
    "$base"

printf "\n### Updating container documents\n"
"$app_dir/update-folder.sh" "$base" "$cert_pem_file" "$cert_password" "$app_dir" "$app_dir" "$proxy"

printf "\n### Updating namespace ontology\n"
"$app_dir/import-ns.sh" "$base" "$cert_pem_file" "$cert_password" "$proxy"
