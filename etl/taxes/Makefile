include ../config.mk

# VMI tax data of legal entities (get.data.gov.lt, CC BY 4.0), keyed by the JAR code:
#   vmi/ja_nepriemokos  the current tax-arrears snapshot (one row per entity that owes tax)
#   vmi/ja_mokesciai    taxes paid per entity per year (menuo is always 12 — the year total)
# One document per legal entity: taxes/{ja_kodas}/, #this the arrears snapshot observation
# plus #paid-{yyyy} observations for the taxes paid each year. The taxpayer, municipality
# and calendar-day/year links are minted from the bare codes and dates; the taxpayer link
# dangles until the full JAR register is loaded (expected).
#
# SINCE_YEAR: the earliest reporting year for taxes paid (default: 4 years back -> 5 years).
# taxpayers.trig / taxes-paid.trig are gitignored bulk output (~138k entities); the cube
# definitions (dataset.trig) are small and committed.
#
#   make -C etl/taxes                  # cube definitions + per-entity documents + paid series
#   make -C etl/taxes SINCE_YEAR=2020  # a longer taxes-paid window

SINCE_YEAR ?= $(shell echo $$(( $(shell date +%Y) - 4 )))

CACHE := cache
OUT := ../../datasets/current/taxes

.PHONY: all clean FORCE
all: $(OUT)/dataset.trig $(OUT)/taxpayers.trig $(OUT)/taxes-paid.trig

$(OUT)/dataset.trig: mappings/dataset.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) > $@
	$(LIB)/validate.sh $@ $(BASE) 1

# --- fetch + normalize: both VMI feeds -> companies.csv (one row per entity) +
#     paid.csv (one row per entity-year). One run writes both files (paid.csv is a
#     by-product; not a grouped target — macOS make 3.81 has no `&:`). ---
$(CACHE)/companies.csv: FORCE
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-taxes --since-year $(SINCE_YEAR) \
		--companies $(CACHE)/companies.csv --paid $(CACHE)/paid.csv

$(CACHE)/paid.csv: $(CACHE)/companies.csv ;

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate: taxpayers.trig is the per-entity documents (arrears #this);
#     taxes-paid.trig is the taxes-paid overlay onto the same graphs (no document triples,
#     like the Sodra monthly cube — so riot + SHACL only). Both merge on load. ---
$(OUT)/taxpayers.trig: $(CACHE)/companies.nt mappings/taxes.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/taxes.rq $(BASE) $< > $@
	JVM_ARGS=-Xmx8g $(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/companies.csv) - 1))

$(OUT)/taxes-paid.trig: $(CACHE)/paid.nt mappings/paid.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/paid.rq $(BASE) $< > $@
	$(JENA_HOME)/bin/riot --validate --base=$(BASE) $@
	JVM_ARGS=-Xmx8g $(LIB)/shacl.sh ../shapes/taxes.ttl $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
