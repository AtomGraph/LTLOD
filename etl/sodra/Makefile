include ../config.mk

# Sodra per-insurer monthly open data (atvira.sodra.lt): insured persons, average wage and
# contributions per legal entity, keyed by the JAR code. There is no scripted fetch:
# atvira.sodra.lt is behind a Cloudflare bot challenge, so the yearly monthly-{yyyy}.csv.zip
# files are downloaded in a real browser into data/ (procedure:
# .claude/skills/harvest-sodra/SKILL.md) and the rest runs offline. data/ is gitignored
# (tens of MB per year).
#
# Default output: employers.trig — one document per employer with its latest month in the
# window and window aggregates (~114k employers, ~2M quads; gitignored bulk output). The
# cube definitions (dataset.trig) are small and committed.
#
# SODRA_MONTHS: the window — the latest N months present in data/ (0 = all).
# SODRA_CUBE=1: also the full monthly series, an overlay into the same employer documents,
# graphified in chunks of SODRA_CHUNK employers (observations-NNN.trig; a year is ~1.2M
# employer-months, ~14M quads, ~900 MB — gitignored). Without it, stale chunks are removed
# so an old series never loads next to a newer summary.
#
#   make -C etl/sodra                   # cube definitions + per-employer summary
#   make -C etl/sodra SODRA_CUBE=1      # + the monthly series
#   make -C etl/sodra test              # the pipeline over test/ fixtures (synthetic, cache-only)

SODRA_MONTHS ?= 12
SODRA_CHUNK ?= 10000
SODRA_CUBE ?=

CACHE := cache
DATA ?= data
OUT ?= ../../datasets/current/employment
MUNICIPALITIES := ../../datasets/current/admin-units/municipalities.trig

.PHONY: all employers test clean
all: $(OUT)/dataset.trig employers

$(OUT)/dataset.trig: mappings/dataset.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) > $@
	$(LIB)/validate.sh $@ $(BASE) 1

# --- normalize: data/*.csv.zip -> summary CSV (+ chunked monthly CSV with SODRA_CUBE) ---
# --- graphify + validate: employers.trig; observations-NNN.trig per chunk (overlay: no
#     document triples, so riot + SHACL only, as for alignments.trig in CI) ---
employers: mappings/employers.rq mappings/observations.rq $(MUNICIPALITIES)
	@mkdir -p $(CACHE) $(OUT)
	uv run --project ../tools ltlod-sodra --input-dir $(DATA) --months $(SODRA_MONTHS) \
		--municipalities $(MUNICIPALITIES) --base $(BASE) --summary $(CACHE)/employers.csv \
		$(if $(SODRA_CUBE),--cube --chunk-size $(SODRA_CHUNK)) --out-dir $(CACHE)/chunks \
		--report $(CACHE)/unmatched-municipalities.csv
	$(LIB)/csv2rdf.sh $(CACHE)/employers.csv $(BASE) > $(CACHE)/employers.nt
	$(LIB)/graphify.sh mappings/employers.rq $(BASE) $(CACHE)/employers.nt > $(OUT)/employers.trig
	$(LIB)/validate.sh $(OUT)/employers.trig $(BASE) $$(($$(wc -l < $(CACHE)/employers.csv) - 1))
	rm -f $(OUT)/observations-*.trig
	for csv in $$(find $(CACHE)/chunks -name 'observations-*.csv' | sort); do \
		n=$$(basename $$csv .csv); \
		$(LIB)/csv2rdf.sh $$csv $(BASE) > $(CACHE)/chunks/$$n.nt || exit 1; \
		$(LIB)/graphify.sh mappings/observations.rq $(BASE) $(CACHE)/chunks/$$n.nt > $(OUT)/$$n.trig || exit 1; \
		$(JENA_HOME)/bin/riot --validate --base=$(BASE) $(OUT)/$$n.trig || exit 1; \
		$(LIB)/shacl.sh ../shapes/employment.ttl $(OUT)/$$n.trig $(BASE) || exit 1; \
	done

# The whole pipeline over synthetic fixtures (fictitious JAR codes 1000000xx), into the
# cache only — never into datasets/current/. The output dir is named employment/ so
# validate.sh picks up etl/shapes/employment.ttl.
test:
	$(MAKE) all DATA=test OUT=$(CACHE)/test/employment CACHE=$(CACHE)/test

clean:
	rm -rf $(CACHE)
