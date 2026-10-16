#!/usr/bin/env bash
# Installs/updates the LTLOD namespace ontology (ns.ttl) as the dataspace's namespace ontology, which
# LinkedDataHub serves at {base}ns. `ldh admin import ontology --file` finds the admin dataspace and the
# ontology IRI from the links the base advertises, resolves ns.ttl against it (so its : prefix, <#>,
# is the end-user namespace), replaces the ontologies/namespace/ document keeping its seeded header,
# and clears the ontology from server memory. Re-running converges.
# Requires `ldh` on $PATH — `make install` in the root Makefile sets this up.
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

printf "\n### Installing the namespace ontology from %s\n" "$app_dir/ns.ttl"
ldh admin import ontology \
    -c "$cert_file" \
    -p "$cert_password" \
    --proxy "$proxy" \
    --file "$app_dir/ns.ttl" \
    "$base"
