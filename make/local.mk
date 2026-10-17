# Deployment-specific targets.

# Install the app structure (root + containers + the namespace ontology and its views) onto a
# LinkedDataHub instance through the ldh CLI. Interactive, with defaults from the local stack
# (.env, ssl/, secrets/): press Enter to install locally, or give another base URL and owner
# certificate to install on any LDH instance. Re-running is safe (PUT replaces).
# Local order: make up -> make install -> make load.
install:
	@[ -x "$(LDH)" ] && [ -f "$(LDH_HOME)/cli/target/ldh.jar" ] || \
		{ echo "ERROR: ldh CLI not found - clone https://github.com/AtomGraph/LinkedDataHub to $(LDH_HOME) (or pass LDH_HOME=...) and run 'make cli' there"; exit 1; }
	@read -p "Enter Base URL [$(BASE_URI)]: " BASE_URL; \
	BASE_URL=$${BASE_URL:-$(BASE_URI)}; \
	read -p "Enter Certificate Path [$(OWNER_CERT)]: " CERT_PATH; \
	CERT_PATH=$${CERT_PATH:-$(OWNER_CERT)}; \
	[ -f "$$CERT_PATH" ] || { echo "ERROR: certificate not found: $$CERT_PATH"; exit 1; }; \
	PW_DEFAULT=""; \
	[ -f $(OWNER_PASSWORD_FILE) ] && PW_DEFAULT="$$(cat $(OWNER_PASSWORD_FILE))"; \
	if [ -n "$$PW_DEFAULT" ]; then \
		read -r -s -p "Enter Certificate Password [from $(OWNER_PASSWORD_FILE)]: " PASSWORD; \
	else \
		read -r -s -p "Enter Certificate Password (required): " PASSWORD; \
	fi; \
	echo ""; \
	PASSWORD=$${PASSWORD:-$$PW_DEFAULT}; \
	if [ -z "$$PASSWORD" ]; then echo "Password cannot be empty. Aborting."; exit 1; fi; \
	PROXY_DEFAULT=""; \
	[ "$$BASE_URL" = "$(BASE_URI)" ] && PROXY_DEFAULT="$(PROXY_URI)"; \
	read -p "Enter Proxy URL (optional) [$$PROXY_DEFAULT]: " PROXY_URL; \
	PROXY_URL=$${PROXY_URL:-$$PROXY_DEFAULT}; \
	if [ "$$BASE_URL" = "$(BASE_URI)" ] && [ -n "$$($(COMPOSE) ps -q linkeddatahub 2>/dev/null)" ]; then \
		echo "Waiting for LinkedDataHub health (first-boot seeding must finish)..."; \
		until [ "$$(docker inspect -f '{{.State.Health.Status}}' $$($(COMPOSE) ps -q linkeddatahub))" = "healthy" ]; do \
			sleep 5; echo "  ...waiting"; \
		done; \
	fi; \
	export PATH="$$(cd $(LDH_HOME) && pwd)/cli/bin:$$PATH"; \
	if [ -n "$$PROXY_URL" ]; then \
		./app/install.sh "$$BASE_URL" "$$CERT_PATH" "$$PASSWORD" "$$PROXY_URL"; \
	else \
		./app/install.sh "$$BASE_URL" "$$CERT_PATH" "$$PASSWORD"; \
	fi

# Bulk-load the local ETL output into a remote deployment, the way `make load` loads the local
# one: rsync $(LOAD_STAGING)/ to the server's checkout, then run the load recipe there over ssh
# (make/remote-load.sh - the server needs docker compose and a checkout with its .env, not make).
# The connection is plain ssh, so anything ssh accepts works:
#     make remote-load REMOTE=user@host
#     make remote-load REMOTE=user@host SSH_KEY=~/.ssh/id_ed25519 REMOTE_DIR=/srv/git/LTLOD
#     make remote-load REMOTE=myhost SSH_OPTS="-p 2222"    # or a Host alias from ~/.ssh/config
# The rsync deletes remote files absent locally, so the server loads exactly the local file set
# (gitignored bulk files included). APPEND-ONLY like `make load`: for a clean rebuild wipe the
# server's fuseki/end-user and re-run `make install` against it first. Anonymous read needs no
# re-grant - the ACLs live in the admin store, which the load does not touch.
REMOTE     ?=
REMOTE_DIR ?= /srv/git/LTLOD
SSH_KEY    ?=
SSH_OPTS   ?=
SSH         = ssh $(if $(SSH_KEY),-i $(SSH_KEY)) $(SSH_OPTS)

remote-load:
	@[ -n "$(REMOTE)" ] || { echo "ERROR: usage: make remote-load REMOTE=user@host [SSH_KEY=...] [REMOTE_DIR=$(REMOTE_DIR)]" >&2; exit 1; }
	@ls $(LOAD_STAGING)/*/*.trig >/dev/null 2>&1 || \
		{ echo "ERROR: no TriG files under $(LOAD_STAGING)/ - run 'make -C etl' first." >&2; exit 1; }
	$(SSH) $(REMOTE) 'test -f $(REMOTE_DIR)/docker-compose.yml' || \
		{ echo "ERROR: no LTLOD checkout at $(REMOTE):$(REMOTE_DIR)" >&2; exit 1; }
	rsync -az --delete --progress -e "$(SSH)" $(LOAD_STAGING)/ $(REMOTE):$(REMOTE_DIR)/$(LOAD_STAGING)/
	$(SSH) $(REMOTE) 'bash -s' -- $(REMOTE_DIR) < make/remote-load.sh
