#!/usr/bin/env bash
# Sets up the LTLOD dataspace on a running LinkedDataHub instance with the ldh CLI: makes it
# publicly readable, pushes the container scaffolding (root document + containers + taxonomy scheme
# containers) and installs the namespace ontology (ns.ttl with 1:N entity views). Requires `ldh`
# on $PATH — `make install` in the root Makefile sets this up from ../LinkedDataHub/cli. The public
# grant is the same `ldh admin make-public` that `make public` runs, so either works against a
# remote instance; both are idempotent, and PUT replaces each document.
set -euo pipefail

if [ "$#" -ne 3 ] && [ "$#" -ne 4 ]; then
  echo "Usage:   $0" '$base $cert_file $cert_password [$proxy]' >&2
  echo "Example: $0" 'https://localhost:4443/ ./ssl/owner/keystore.p12 Password https://localhost:5443/' >&2
  echo "Note: special characters such as $ need to be escaped in passwords!" >&2
  exit 1
fi

base="$1"
cert_file=$(realpath "$2")
cert_password="$3"
proxy="${4:-$base}"

app_dir="$(cd "$(dirname "$0")" && pwd)"

printf "\n### Creating authorization to make the dataspace public\n"
ldh admin make-public -b "$base" -c "$cert_file" -p "$cert_password" --proxy "$proxy"

printf "\n### Pushing root and container documents\n"
ldh push -b "$base" -c "$cert_file" -p "$cert_password" --proxy "$proxy" --dir "$app_dir" "$base"

printf "\n### Updating namespace ontology\n"
"$app_dir/import-ns.sh" "$base" "$cert_file" "$cert_password" "$proxy"
