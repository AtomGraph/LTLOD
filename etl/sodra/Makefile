include ../config.mk

# Sodra per-insurer monthly open data (atvira.sodra.lt): insured persons, average wage and
# contributions per legal entity, as a W3C Data Cube keyed by the JAR code. There is no
# scripted fetch: atvira.sodra.lt is behind a Cloudflare bot challenge, so the yearly
# monthly-{yyyy}.csv.zip files are downloaded in a real browser into data/ (procedure:
# .claude/skills/harvest-sodra/SKILL.md) and the rest runs offline. data/ is gitignored
# (tens of MB per year), as are the observation chunks (bulk output); the cube definition
# (dataset.trig) is small and committed.
#
# SODRA_MONTHS: the latest N months present in data/ (0 = all). A year is ~1.2M
# employer-months (~10M quads), so the observations are graphified in chunks of
# SODRA_CHUNK employers, one gitignored observations-NNN.trig each.
#
#   make -C etl/sodra                   # cube definition + observations from data/
#   make -C etl/sodra SODRA_MONTHS=24
#   make -C etl/sodra test              # the pipeline over test/ fixtures (synthetic, cache-only)

SODRA_MONTHS ?= 12
SODRA_CHUNK ?= 10000

CACHE := cache
DATA ?= data
OUT ?= ../../datasets/current/employment
MUNICIPALITIES := ../../datasets/current/admin-units/municipalities.trig

.PHONY: all observations test clean
all: $(OUT)/dataset.trig observations

$(OUT)/dataset.trig: mappings/dataset.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) > $@
	$(LIB)/validate.sh $@ $(BASE) 1

# --- normalize: data/*.csv.zip -> chunked CSV (one row per employer and month) ---
# --- graphify + validate: one observations-NNN.trig per chunk, stale chunks removed ---
observations: mappings/observations.rq $(MUNICIPALITIES)
	@mkdir -p $(CACHE) $(OUT)
	uv run --project ../tools ltlod-sodra --input-dir $(DATA) --months $(SODRA_MONTHS) \
		--chunk-size $(SODRA_CHUNK) --municipalities $(MUNICIPALITIES) --base $(BASE) \
		--out-dir $(CACHE)/chunks --report $(CACHE)/unmatched-municipalities.csv
	rm -f $(OUT)/observations-*.trig
	for csv in $(CACHE)/chunks/observations-*.csv; do \
		n=$$(basename $$csv .csv); \
		$(LIB)/csv2rdf.sh $$csv $(BASE) > $(CACHE)/chunks/$$n.nt || exit 1; \
		$(LIB)/graphify.sh mappings/observations.rq $(BASE) $(CACHE)/chunks/$$n.nt > $(OUT)/$$n.trig || exit 1; \
		$(LIB)/validate.sh $(OUT)/$$n.trig $(BASE) $$(($$(tail -n +2 $$csv | cut -d, -f1 | sort -u | wc -l))) || exit 1; \
	done

# The whole pipeline over synthetic fixtures (fictitious JAR codes 1000000xx), into the
# cache only — never into datasets/current/. The output dir is named employment/ so
# validate.sh picks up etl/shapes/employment.ttl.
test:
	$(MAKE) all DATA=test OUT=$(CACHE)/test/employment CACHE=$(CACHE)/test

clean:
	rm -rf $(CACHE)
