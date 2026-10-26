# Production deployment

> **Status: living document.** It describes the generic procedure, server-agnostic
> (no hostnames, addresses, paths or certificate locations — those live outside the
> repo). Update it as the procedure is validated against a real deployment; items
> still to confirm are marked **TBD**.

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

## To confirm / fill in as we deploy (TBD)

- Exactly how the owner certificate is generated on the server (container entrypoint
  on first boot vs. another mechanism) — this fixes when and where
  `ssl/owner/keystore.p12` appears to be retrieved in B.3.
- Whether `PROXY_SECRET` is generated on the server (`make secrets` writes it on a
  workstation) or must be set by hand in the deployment's `.env` before first boot,
  then mirrored to the front proxy.
- Whether B necessarily wipes the admin store (a fresh owner cert implies it) or
  there is a path that rotates the cert while keeping the admin store.
