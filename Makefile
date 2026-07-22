SHELL := /bin/bash

.PHONY: up down stop logs cert secrets install load public drop

# LDH CLI checkout (provides put.sh etc.); Jena provides the `turtle` command
LDH_HOME ?= ../LinkedDataHub
include etl/config.mk          # for JENA_HOME (its BASE is unused here)
include .env                   # PROTOCOL/HOST/HTTPS_PORT/HTTPS_CLIENT_CERT_PORT/ABS_PATH

ifeq ($(HTTPS_PORT),443)
BASE_URI  := $(PROTOCOL)://$(HOST)$(ABS_PATH)
else
BASE_URI  := $(PROTOCOL)://$(HOST):$(HTTPS_PORT)$(ABS_PATH)
endif
PROXY_URI := $(PROTOCOL)://$(HOST):$(HTTPS_CLIENT_CERT_PORT)$(ABS_PATH)

SECRET_FILES := secrets/owner_cert_password.txt \
                secrets/secretary_cert_password.txt \
                secrets/client_truststore_password.txt

secrets/%.txt:
	@mkdir -p secrets
	openssl rand -base64 24 > $@

secrets: $(SECRET_FILES)

ssl/server/server.crt:
	./bin/server-cert-gen.sh .env nginx ssl

cert: ssl/server/server.crt

up: secrets cert
	mkdir -p datasets/owner datasets/secretary uploads fuseki/admin fuseki/end-user
	docker compose up -d
	@echo "LinkedDataHub starting — first boot takes ~1-2 min (self-signed cert)."
	@echo "URL: https://localhost:4443/"

down:
	docker compose down

stop:
	docker compose stop

logs:
	docker compose logs -f linkeddatahub

# Install the app structure (root + containers + taxonomy schemes + the
# namespace ontology with 1:N views) onto a LinkedDataHub instance via LDH CLI
# PUTs. Interactive, LinkedDataHub-Apps style: prompts for the target instance
# with defaults from the local docker-compose stack (.env, ssl/, secrets/) —
# press Enter to install locally, or enter another Base URL + owner cert to
# install on any LDH instance. Re-running is safe (PUT replaces). Local order:
# make up -> make install -> make load.
install:
	@[ -d "$(LDH_HOME)/bin" ] || \
		{ echo "ERROR: LDH CLI not found — clone https://github.com/AtomGraph/LinkedDataHub to $(LDH_HOME) or pass LDH_HOME=…"; exit 1; }
	@read -p "Enter Base URL [$(BASE_URI)]: " BASE_URL; \
	BASE_URL=$${BASE_URL:-$(BASE_URI)}; \
	read -p "Enter Certificate Path [ssl/owner/cert.pem]: " CERT_PATH; \
	CERT_PATH=$${CERT_PATH:-ssl/owner/cert.pem}; \
	[ -f "$$CERT_PATH" ] || { echo "ERROR: certificate not found: $$CERT_PATH"; exit 1; }; \
	PW_DEFAULT=""; \
	[ -f secrets/owner_cert_password.txt ] && PW_DEFAULT="$$(cat secrets/owner_cert_password.txt)"; \
	if [ -n "$$PW_DEFAULT" ]; then \
		read -r -s -p "Enter Certificate Password [from secrets/owner_cert_password.txt]: " PASSWORD; \
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
	if [ "$$BASE_URL" = "$(BASE_URI)" ] && [ -n "$$(docker compose ps -q linkeddatahub 2>/dev/null)" ]; then \
		echo "Waiting for LinkedDataHub health (first-boot seeding must finish)..."; \
		until [ "$$(docker inspect -f '{{.State.Health.Status}}' $$(docker compose ps -q linkeddatahub))" = "healthy" ]; do \
			sleep 5; echo "  ...waiting"; \
		done; \
	fi; \
	export PATH="$$(find "$$(cd $(LDH_HOME) && pwd)/bin" -type d | tr '\n' ':')$(JENA_HOME)/bin:$$PATH"; \
	if [ -n "$$PROXY_URL" ]; then \
		./app/install.sh "$$BASE_URL" "$$CERT_PATH" "$$PASSWORD" "$$PROXY_URL"; \
	else \
		./app/install.sh "$$BASE_URL" "$$CERT_PATH" "$$PASSWORD"; \
	fi

# Bulk-load datasets/current/*/*.trig into the end-user TDB2 store. APPEND-ONLY:
# clean rebuild = `make down && rm -rf fuseki/end-user && make up && make load`.
load:
	@ls datasets/current/*/*.trig >/dev/null 2>&1 || \
		{ echo "ERROR: no TriG files under datasets/current/ — run 'make -C etl' first."; exit 1; }
	@[ -n "$$(docker compose ps -q fuseki-end-user)" ] || \
		{ echo "ERROR: fuseki-end-user container not found — run 'make up' first."; exit 1; }
	@echo "Waiting for LinkedDataHub health (first-boot seeding must finish)..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' $$(docker compose ps -q linkeddatahub))" = "healthy" ]; do \
		sleep 5; echo "  ...waiting"; \
	done
	docker compose stop fuseki-end-user
	rm -f fuseki/end-user/DB2/tdb.lock
	docker compose run --rm tdb-loader
	docker compose up -d fuseki-end-user
	docker compose restart varnish-end-user varnish-frontend
	$(MAKE) public

# Grant anonymous read access (idempotent; equivalent of LDH CLI make-public.sh)
public:
	./bin/make-public.sh .env

# Wipes LDH runtime state. NEVER touches datasets/current/.
drop:
	@read -p "Delete fuseki/, ssl/, secrets/, uploads/, datasets/{owner,secretary}? [y/N] " ans && \
	[ "$$ans" = "y" ] && { docker compose down -v; sudo rm -rf datasets/owner datasets/secretary fuseki ssl secrets uploads; } || echo "Aborted."
