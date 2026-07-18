#!/usr/bin/env bash
# Installs/updates the LTLOD namespace ontology (ns.ttl) into the admin
# dataspace's ontologies/namespace/ document, which LinkedDataHub serves at
# {base}ns. Mirrors LinkedDataHub-Apps demo/northwind-traders:
# 1. PATCH-reset the ontology document (drop everything except the document
#    resource and its foaf:primaryTopic),
# 2. POST ns.ttl with a prepended @base <{base}ns> directive so its : prefix
#    (<#>) resolves to the end-user namespace,
# 3. clear the ontology from server memory so it reloads fresh.
# Requires LinkedDataHub's bin/ subdirs on $PATH (patch.sh, post.sh,
# clear-ontology.sh) — `make install` in the root Makefile sets this up.
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

admin_uri() {
    echo "$1" | sed 's|://|://admin.|'
}

admin_base=$(admin_uri "$base")
admin_proxy=$(admin_uri "$proxy")

printf "\n### Resetting namespace ontology document: %sontologies/namespace/\n" "$admin_base"
{ echo "BASE <${admin_base}ontologies/namespace/>"; cat "$app_dir/patch-ontology.ru"; } | patch.sh \
    -f "$cert_pem_file" \
    -p "$cert_password" \
    --proxy "$admin_proxy" \
    "${admin_base}ontologies/namespace/"

printf "\n### Appending ns.ttl to the namespace ontology\n"
{ echo "@base <${base}ns> ."; cat "$app_dir/ns.ttl"; } | post.sh \
    -f "$cert_pem_file" \
    -p "$cert_password" \
    --proxy "$admin_proxy" \
    --content-type "text/turtle" \
    "${admin_base}ontologies/namespace/"

printf "\n### Clearing ontology from server memory: %sns#\n" "$base"
clear-ontology.sh \
    -f "$cert_pem_file" \
    -p "$cert_password" \
    -b "$admin_base" \
    --proxy "$admin_proxy" \
    --ontology "${base}ns#"
