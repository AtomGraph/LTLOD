> **Status: proposal, not implemented.** Nothing below exists in the repo or on the VM yet.

# Public SPARQL replica on its own port: `https://linkeddata.lt:3030/sparql`

## Context
I removed the `sparql.linkeddata.lt` replica because LDH dataspaces own the `*.linkeddata.lt` subdomains. The goal is still the same: heavy public queries must not hit the Fuseki that renders the site.

A separate port solves the naming problem. `https://linkeddata.lt:3030` is its own origin, and the origin is what LDH matches in `dataspaces.trig`. So the port sits outside both the dataspace subdomains and every dataspace's paths. It also needs no new DNS record and no new certificate, because the existing `linkeddata.lt` certificate covers the host whatever the port.

**Port 3030** is Fuseki's well-known port, and nothing on the VM uses it.

**Trade-offs:**
- Some corporate networks block non-standard ports.
- The Hetzner Cloud firewall may need 3030 opened. I can't see it over ssh; check in the Hetzner console.

## Memory budget (VM: 16 GB total, ~9.5 GB available, KGDN already uses ~5.6 GB)
These are the LTLOD limits as configured. A replica at the old 3584m would overcommit, so shrink it:
- fuseki 5120m
- linkeddatahub 2048m
- varnish caches ~1.4 GB
- sef-compiler 3072m (this is a cap, and the compile only peaks briefly)

**Replica:** `mem_limit: 2048m`, `-Xmx1024m`. TDB2 reads through mmap outside the heap, and the timeouts are tight, so 1 GB of heap is enough for capped queries. `ExitOnOutOfMemoryError` plus `restart: on-failure` covers the rest.

## Changes
1. **`config/fuseki/public.ttl`** (new): modelled on `config/fuseki/config.ttl`.
   - One read-only service, `end-user`, with **only** a `fuseki:query` endpoint. No update and no GSP.
   - `ja:context arq:queryTimeout "10000,30000"`: 10 s to first result, 30 s overall, set on the endpoint (the existing comment explains why it must go there).
   - TDB2 location `/fuseki/databases/end-user/DB2`.
2. **`docker-compose.prod.yml`**: re-add the `fuseki-public` service.
   - `image: atomgraph/fuseki:6.1.0`, `user: root`, the memory settings above.
   - `JAVA_TOOL_OPTIONS=-XX:+ExitOnOutOfMemoryError`.
   - **No egress proxy**: block `SERVICE` outright. Run it on a network with no outbound route, or point the proxy at a dead host. Simplest: `-Dhttp.proxyHost=0.0.0.0 -Dhttps.proxyHost=0.0.0.0 -Dhttp.nonProxyHosts=` so every outbound call fails.
   - `./config/fuseki/public.ttl:/fuseki/config.ttl:ro`, `./fuseki/public:/fuseki/databases`.
   - Networks `default` + `nginx-shared` with alias `ltlod-fuseki-public`.
3. **`nginx-shared/docker-compose.yml`** (KGDN repo): publish `3030:7443` (the container listens on 7443).
4. **`nginx-shared/nginx.conf`** (KGDN repo):
   - Add a `server { listen 7443 ssl; server_name linkeddata.lt; … }` using the `linkeddata.lt` certificate.
   - `location ~ ^/(sparql)?$` handles GET/POST, CORS and OPTIONS 204. Rewrite to `/end-user/sparql` and `proxy_pass http://$ltlod_sparql` (resolved per request, like the other upstreams), with `proxy_read_timeout 40s`.
   - Its own limit zones: 2 r/s burst 10, 2 concurrent per client, 6 in total.
   - `robots.txt` → `Disallow: /`. Everything else → 404.
   - Update the header comment table: `linkeddata.lt:3030 — LTLOD public SPARQL endpoint`.
5. **`make/remote-load.sh`**: re-add the refresh step while fuseki is still stopped. If `fuseki-public` is among the services:
   1. stop it;
   2. `rm -rf fuseki/public/DB2 && cp -a fuseki/end-user/DB2 fuseki/public/DB2`;
   3. remove `tdb.lock`;
   4. `up -d fuseki-public`.
6. **`.env_prod`** comment: mention the replica again.
7. **Docs**: one line in CLAUDE.md's Gotchas. Explain that the public endpoint is the replica on port 3030, refreshed only by `make remote-load`, so it lags any edits made through LDH. Say that `{base}sparql` stays the site's own endpoint. Also note that LDH subdomains are off limits.

## Verification
- **Locally:**
  - run `nginx -t` with dummy certificates in the scratchpad `le/` dir;
  - merge the prod compose files with `docker compose --env-file .env_prod -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.prod.yml config -q`;
  - check `riot --validate config/fuseki/public.ttl`.
- **On the VM, after cutover** (with your confirmation):
  - `curl 'https://linkeddata.lt:3030/sparql?query=ASK{}'` returns true;
  - a deliberately slow query is cut off at about 30 s;
  - an `INSERT` gets 4xx;
  - `SERVICE <https://query.wikidata.org/sparql>` fails;
  - the site keeps working during a flood test (`ab -c 20` against :3030).
