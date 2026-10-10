#!/usr/bin/env bash
# Installs/updates the LTLOD namespace ontology (ns.ttl) into the admin dataspace's
# ontologies/namespace/ document, which LinkedDataHub serves at {base}ns. Mirrors
# LinkedDataHub-Apps demo/northwind-traders:
# 1. PATCH-reset the ontology document (drop everything except the document resource and its
#    foaf:primaryTopic),
# 2. POST ns.ttl with a prepended @base <{base}ns> directive so its : prefix (<#>) resolves to the
#    end-user namespace,
# 3. clear the ontology from server memory so it reloads fresh.
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

admin_uri() {
    echo "$1" | sed 's|://|://admin.|'
}

admin_base=$(admin_uri "$base")
admin_proxy=$(admin_uri "$proxy")
ontology_doc="${admin_base}ontologies/namespace/"

printf "\n### Resetting namespace ontology document: %s\n" "$ontology_doc"
{ echo "BASE <${ontology_doc}>"; cat "$app_dir/patch-ontology.ru"; } | ldh patch \
    -f "$cert_file" \
    -p "$cert_password" \
    --proxy "$admin_proxy" \
    "$ontology_doc"

printf "\n### Appending ns.ttl to the namespace ontology\n"
{ echo "@base <${base}ns> ."; cat "$app_dir/ns.ttl"; } | ldh post \
    -f "$cert_file" \
    -p "$cert_password" \
    --proxy "$admin_proxy" \
    -t text/turtle \
    "$ontology_doc"

printf "\n### Clearing ontology from server memory: %sns#\n" "$base"
ldh admin clear ontology \
    -b "$admin_base" \
    -f "$cert_file" \
    -p "$cert_password" \
    --proxy "$admin_proxy" \
    --ontology "${base}ns#"
