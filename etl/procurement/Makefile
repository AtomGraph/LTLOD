include ../config.mk

# Public procurement contracts from the VPT CVP IS contract subsystem, published daily by
# the State Data Agency (VDA) on get.data.gov.lt as datasets/gov/lsd/vpt/cvpp (CC BY 4.0):
# Sutartis (one row per contract) joined to Salis (its buyer and contractor parties) on
# the document id. ~1.1M contracts a year, most of them small purchases, so the fetch is
# windowed: contracts CONCLUDED between SINCE and today worth at least MIN_VALUE EUR
# (10 000 EUR is CVP IS's own publication threshold for contracts since 2024), contract
# amendments excluded (they restate the whole contract value — see ltlod-procurement). The full
# window is ~56k contracts / ~30 min of batched party requests; the output is gitignored
# bulk data like settlements/streets/votes.
#   make -C etl/procurement SINCE=2024-01-01 MIN_VALUE=50000

CACHE := cache
OUT := ../../datasets/current/procurement

# default window: the last 12 months (BSD date first, GNU date as the fallback)
SINCE ?= $(shell date -u -v-1y +%Y-%m-%d 2>/dev/null || date -u -d '1 year ago' +%Y-%m-%d)
MIN_VALUE ?= 10000

.PHONY: all clean FORCE
all: $(OUT)/contracts.trig

# --- fetch + normalize: windowed contracts and their parties, flattened to CSV ---
# One run writes both files. Not a grouped target (`&:` needs GNU make 4.3; macOS ships
# 3.81, which would run the ~40 min fetch once per file): parties.csv is a by-product.
$(CACHE)/contracts.csv: FORCE
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-procurement --since $(SINCE) --min-value $(MIN_VALUE) \
		--contracts $(CACHE)/contracts.csv --parties $(CACHE)/parties.csv

$(CACHE)/parties.csv: $(CACHE)/contracts.csv ;

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate (one graph per contract) ---
$(OUT)/contracts.trig: $(CACHE)/contracts.nt $(CACHE)/parties.nt mappings/contracts.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/contracts.rq $(BASE) $(CACHE)/contracts.nt $(CACHE)/parties.nt > $@
	JVM_ARGS=-Xmx8g $(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/contracts.csv) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
