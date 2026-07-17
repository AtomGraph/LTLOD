#!/usr/bin/env bash
# Makes all documents of the end-user application publicly readable.
# Direct-to-triplestore equivalent of LinkedDataHub CLI's make-public.sh:
# runs the same SPARQL update against fuseki-admin from inside the docker
# network, so no owner WebID certificate or published ports are needed.
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage:   $0" '$env_file' >&2
    echo "Example: $0 .env" >&2
    exit 1
fi

env_file="$1"

function envProp {
  local expectedKey=$1
  while IFS='=' read -r k v; do
      if [ -n "$k" ] && [ "$k" == "$expectedKey" ] ; then
        echo "$v";
        break;
      fi
  done < "$env_file"
}

if [ "$(envProp "HTTPS_PORT")" = 443 ]; then
    base_uri="$(envProp "PROTOCOL")://$(envProp "HOST")$(envProp "ABS_PATH")"
else
    base_uri="$(envProp "PROTOCOL")://$(envProp "HOST"):$(envProp "HTTPS_PORT")$(envProp "ABS_PATH")"
fi
admin_base_uri=$(echo "$base_uri" | sed 's|://|://admin.|')

printf "### Granting public access on: %s\n" "$base_uri"

docker compose exec -T linkeddatahub curl -s -f -X POST \
    -H "Content-Type: application/sparql-update" \
    --data-binary @- \
    http://varnish-admin/ds/ <<EOF
PREFIX  acl: <http://www.w3.org/ns/auth/acl#>
PREFIX  def: <https://w3id.org/atomgraph/linkeddatahub/default#>
PREFIX  dh:  <https://www.w3.org/ns/ldt/document-hierarchy#>
PREFIX  nfo: <http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#>
PREFIX  foaf: <http://xmlns.com/foaf/0.1/>

INSERT DATA
{
  GRAPH <${admin_base_uri}acl/authorizations/public/>
  {
    <${admin_base_uri}acl/authorizations/public/#this> acl:accessToClass def:Root, dh:Container, dh:Item, nfo:FileDataObject ;
        acl:accessTo <${base_uri}sparql> .

    <${admin_base_uri}acl/authorizations/public/#sparql-post> a acl:Authorization ;
        acl:accessTo <${base_uri}sparql> ;
        acl:mode acl:Append ;
        acl:agentClass foaf:Agent, acl:AuthenticatedAgent . # hacky way to allow queries over POST
  }
}
EOF

# the update bypassed LDH, so cached ACL lookups must be dropped
docker compose restart varnish-admin

# wait until varnish-admin accepts connections again — LDH returns 500s on ACL
# lookups while it is down
until docker compose exec -T linkeddatahub curl -s -o /dev/null http://varnish-admin/; do
    sleep 1
done
