include ../config.mk

# Company insolvency proceedings from the Audito, apskaitos, turto vertinimo ir nemokumo
# valdymo tarnyba (AVNT), published on get.data.gov.lt (datasets/gov/avnt): bankruptcies
# (imoniu_bankrotas, 2020+) and restructurings (imoniu_restrukturizavimas, 2020+) with their
# report fields, plus the intentional-bankruptcy list (tyciniai_bankrotai, 1994-2025) which
# adds the older intentional cases. One document per proceeding, keyed by {imones_kodas}-{start}.
# ltlod-insolvency fetches all three (small tables), crosswalks the territory code to the AR
# municipality and emits one tidy proceedings.csv. Committed output (~6.4k proceedings).
#   make -C etl/insolvency

CACHE := cache
OUT := ../../datasets/current/insolvency

.PHONY: all clean FORCE
all: $(OUT)/proceedings.trig

$(CACHE)/proceedings.csv: FORCE
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-insolvency --output $(CACHE)/proceedings.csv

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/proceedings.trig: $(CACHE)/proceedings.nt mappings/proceedings.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/proceedings.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/proceedings.csv) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
