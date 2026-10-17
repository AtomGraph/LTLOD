#!/usr/bin/env bash
# The remote half of `make remote-load`: the `make load` recipe, run on the server over
# `ssh … bash -s`, because the server needs no make (only docker compose and a checkout of this
# repo whose .env says where the deployment lives). The TriG was rsynced into datasets/current/
# just before; the loader resolves it against the server's own base URI, read from its .env.
# Usage: ssh <host> 'bash -s' -- <repo dir> < make/remote-load.sh
set -euo pipefail

cd "${1:?usage: remote-load.sh <repo dir>}"
[ -f docker-compose.yml ] && [ -f .env ] || \
    { echo "ERROR: $(pwd) is not an LTLOD checkout with a .env" >&2; exit 1; }

# the same derivation as the Makefile's BASE_URI: the port is omitted when it is 443
set -a; . ./.env; set +a
: "${PROTOCOL:?.env has no PROTOCOL}" "${HOST:?.env has no HOST}"
port=""; [ "${HTTPS_PORT:-443}" != 443 ] && port=":${HTTPS_PORT}"
base_uri="${PROTOCOL}://${HOST}${port}/"
echo "Loading $(pwd)/datasets/current into ${base_uri}"

[ -n "$(docker compose ps -q fuseki)" ] || \
    { echo "ERROR: fuseki container not found - start the stack first" >&2; exit 1; }
echo "Waiting for LinkedDataHub health (first-boot seeding must finish)..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q linkeddatahub)")" = "healthy" ]; do
    sleep 5; echo "  ...waiting"
done

docker compose stop fuseki
rm -f fuseki/*/DB2/tdb.lock
# </dev/null: this script itself arrives on stdin (`ssh … bash -s`), which `docker compose run`
# would otherwise inherit and consume - the restarts below silently never ran (exit 0, fuseki down)
docker compose run --rm -T -e BASE_URI="${base_uri}" tdb-loader </dev/null

docker compose up -d fuseki
docker compose restart varnish-end-user varnish-frontend
