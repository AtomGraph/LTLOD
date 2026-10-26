# Production deployment

> **Status: living document**, validated end-to-end on 2026-10-26 (a clean-slate rebuild
> onto LinkedDataHub 6.3.0 with regenerated certs). It describes the generic procedure,
> server-agnostic (no hostnames, addresses, paths or certificate locations — those live
> outside the repo). The "Confirmed on the first full run" section at the end records what
> the real deployment settled.

Two procedures:

- **[A. LinkedDataHub version bump](#a-linkeddatahub-version-bump)** — move the
  deployment to a new LinkedDataHub release, keeping the data.
- **[B. Clean-slate rebuild](#b-clean-slate-rebuild)** — reset the deployment:
  fresh certificates, empty stores, app scaffolding reinstalled, the full datasets
  reloaded. (Destructive; opens a no-data window.)

## Model (shared assumptions)

- The **server** runs the stack with `docker compose` directly, from a checkout of
  this repo that carries its own `.env`. `make` is not assumed on the server.
- The **workstation** has `make`, Docker, Apache Jena, `uv`, the built datasets, and
  the owner certificate (kept outside the repo), plus ssh access to the server.
- **The client SEF (`files/client.xsl.sef.json`) is committed**, so `git pull` ships
  it to the server — the server never compiles it. Rebuild it with `make sef` on the
  workstation (and commit it) after editing any `files/*.xsl` or bumping the image pin.
- **Images are pinned** in `docker-compose.override.yml`; a version change is a
  deliberate pin bump, not a floating `:latest`.
- **Data** is shipped and loaded from the workstation with `make remote-load`; the
  **app scaffolding** is installed with `make install`. Both target any base over
  HTTPS/ssh (`make install` prompts for the base URL, owner cert, password and proxy).
- **Client-certificate handshake (LinkedDataHub ≥ 6.3.0).** The platform accepts a
  forwarded `Client-Cert` only on a request that also carries the deployment's
  `PROXY_SECRET`. The stack's own nginx sets both. If a **shared front proxy**
  terminates TLS in front of the stack, that proxy must forward `Proxy-Secret`
  (matching the deployment's `PROXY_SECRET`) alongside `Client-Cert`, or every
  authenticated operation is rejected (anonymous read still works).

## Prerequisites (both procedures)

- The datasets are built under `datasets/current/` — the committed set plus whatever
  opt-in bulk should be live (`make -C etl …`; see CLAUDE.md "Commands"). `make
  remote-load` rsyncs **exactly the local file set** (`--delete`), so an incomplete
  local build ships an incomplete dataset.
- The image pin and the committed SEF are current: after any `files/*.xsl` edit or pin
  bump, `make sef` and commit `files/client.xsl.sef.json`.
- The change is on the branch the server pulls (merge first).

## A. LinkedDataHub version bump

**Workstation**

1. Bump the `linkeddatahub` and `sef-compiler` image pins in
   `docker-compose.override.yml` to the new version. Re-sync `docker-compose.yml`
   from the LinkedDataHub release if it changed (it is a verbatim mirror; LTLOD
   deltas live only in the override — see CLAUDE.md).
2. Check the XSLT overrides against the new image: re-sync any stock templates the
   overrides copy (CLAUDE.md "XSLT overrides"), then `make sef` and **commit the
   refreshed `files/client.xsl.sef.json`**.
3. If a shared front proxy mirrors LinkedDataHub's own nginx config, review the
   release's nginx changes and mirror the relevant ones into that proxy (e.g. a new
   auth-header handshake, rate-limit retuning). Coordinate any new secret on both
   sides (see the handshake note above).
4. Merge to the deployed branch.

**Server**

5. `git pull` — brings the new compose and the committed SEF.
6. `docker compose pull` — fetches the pinned images.
7. `docker compose up -d` — recreates what changed.
8. Restart the caches after backends are recreated (the Varnishes; and the stack's
   own nginx if present — they resolve upstreams at start). A front proxy that
   resolves upstreams per request needs no restart.

**Verify**: anonymous read of the base URL and a few pages; if the release changed
auth, one authenticated operation.

## B. Clean-slate rebuild

Use when starting a deployment, or resetting it to the current datasets. This also
**regenerates the certificates and reseeds the admin store**.

> ⚠ **Destructive, with a no-data window.** Dropping the stores empties the site
> until the reload finishes; there is no staging-swap.

**Additional prerequisites**

- The **full** datasets are built locally (every opt-in bulk that should be live).
- `PROXY_SECRET` is set in the deployment's `.env`, and mirrored to the front proxy
  if one terminates TLS.

**Steps**

1. If also bumping LinkedDataHub, do A.1–A.4 first.
2. **Server — drop.** Stop the stack, remove the runtime state (the TDB2 stores, the
   TLS/cert material, uploads), keep or (re)create the secrets (the owner-cert
   password and `PROXY_SECRET` among them), then bring the stack up. First boot
   **regenerates the server / owner / secretary certificates and seeds the admin
   store for the new owner.**
3. **Retrieve the new owner certificate + its password** from the server to the
   workstation's owner-cert location. A new owner cert means a new owner WebID; the
   freshly seeded admin store recognizes it, so this cert — not the previous one —
   is what authenticates the next step.
4. **Workstation — `make install`** (owner cert, base URL, proxy): makes the
   dataspace public, PUTs the app scaffolding (root, containers, taxonomy schemes),
   and installs the namespace ontology (`ns.ttl`, the 1:N entity views). Idempotent.
5. **Workstation — `make remote-load REMOTE=<ssh target>`**: rsyncs
   `datasets/current/` to the server and bulk-loads it into the empty end-user store
   (append-only), then restarts the caches.
6. Restart the edge/caches as needed; **verify** graph counts against CLAUDE.md
   "Verification" and spot-check pages in a browser (a calendar month, an entity
   page, a legal entity's cross-views).

## Notes / gotchas (generic)

- **Committed SEF**: the server never runs `make sef`; the workstation builds and
  commits it, and `git pull` ships it. A stale SEF (pin bumped but SEF not rebuilt)
  renders the old client behaviour.
- **PROXY_SECRET handshake (≥ 6.3.0)**: the deployment's `.env` and the front proxy
  need the **same** value, or authenticated operations return 403 while anonymous
  read keeps working.
- **Load is append-only**: a clean data state requires the end-user store to be
  wiped first — that is why B drops it; A never touches data.
- **Cache restart after recreating backends**: the Varnishes (and a stack-local
  nginx) resolve upstream addresses at start, so they need restarting after a
  backend is recreated; a front proxy that resolves per request does not.

## Confirmed on the first full run (clean-slate + 6.3.0, 2026-10-26)

- **Cert generation.** `bin/server-cert-gen.sh <env> <proxy_host> ssl` makes only the
  **server** cert (`ssl/server/`); the **owner and secretary** WebID keystores
  (`ssl/owner/keystore.p12`, `ssl/secretary/`) are generated by the **LDH container
  entrypoint on fresh boot**, using the passwords in `secrets/*_password.txt`. So the
  clean-slate wipes `ssl/` but **keeps `secrets/`**, regenerates the server cert, then the
  fresh boot regenerates the WebID certs. `proxy_host` is whatever the old server cert's
  SAN shows (read it with `openssl x509 -ext subjectAltName`); it was `nginx`.
- **Fresh-boot command.** `LOAD_DATASETS= docker compose up -d` — `LOAD_DATASETS` set to
  the empty string (not `false`) makes the entrypoint seed the dataspace + generate the
  WebID certs once. The LDH container became healthy and `ssl/owner/keystore.p12` appeared
  within ~1 minute.
- **Retrieve the cert.** `scp` the regenerated `ssl/owner/keystore.p12` **and**
  `secrets/owner_cert_password.txt` to the workstation's owner-cert location. Verify it
  opens with `openssl pkcs12 -passin file:<password-file>` (a bare `pass:` fails on the
  file's trailing newline).
- **`PROXY_SECRET`.** Not written to the tracked `.env_prod` (keep only a `# PROXY_SECRET=`
  template line). Generate `openssl rand -hex 32` into the server's gitignored `.env`, and
  put the **same value** in the front proxy's `nginx-shared/.env` as `LTLOD_PROXY_SECRET`.
- **Admin store.** A clean slate wipes `fuseki/` entirely (admin + end-user), so the fresh
  boot reseeds the admin store for the new owner WebID — a fresh owner cert and a fresh
  admin store go together. `make install` then PUTs the app scaffolding as that new owner.
- **No `make` on the server.** Run `docker compose` directly; the server pulls both repos
  with **`ssh -A`** (agent forwarding) — the private front-proxy repo needs the forwarded
  key.
- **Timings (this host, ~34.6M quads / 2.2 GB).** `make remote-load` ≈ 22–23 min of
  tdb-load (~25,600 quads/s) after the rsync; the clean-slate no-data window is roughly
  that plus the rsync and `make install`.
