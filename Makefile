SHELL := /bin/bash

.PHONY: up down stop logs cert secrets load public drop

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
