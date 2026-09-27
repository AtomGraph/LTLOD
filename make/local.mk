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
