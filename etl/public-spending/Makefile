include ../config.mk

# Public-sector invoice totals from the State Treasury (NBFC) open data on get.data.gov.lt
# (datasets/gov/nbfc/viesojo_sektoriaus_saskaitos): ~14.4M invoices (Saskaitos) joined to their
# ~32M party rows (SaskaituSalys) and aggregated per (buyer, supplier, year). ltlod-public-spending
# streams both feeds (keyset-paginated) into a temporary on-disk SQLite db and aggregates there —
# the party rows cannot be windowed by invoice year, so the whole table is read (~40-90 min fetch).
# Buyer and supplier link to legal-entities/{code}/#this by the bare JAR code. Gitignored bulk output.
#   make -C etl/public-spending

CACHE := cache
OUT := ../../datasets/current/public-spending

# only publish a (buyer, supplier, year) whose billed total (incl. VAT) reaches MIN_TOTAL EUR;
# the default drops the ~63% zero-total credit-note/VAT pairs and the long tail of trivial flows
# (~3.9M aggregates -> ~433k). Lower it (MIN_TOTAL=0) for the complete set.
MIN_TOTAL ?= 1000

.PHONY: all clean FORCE
all: $(OUT)/aggregates.trig

$(CACHE)/aggregates.csv: FORCE
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-public-spending --min-total $(MIN_TOTAL) \
		--output $(CACHE)/aggregates.csv --db $(CACHE)/pubspend.sqlite

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/aggregates.trig: $(CACHE)/aggregates.nt mappings/aggregates.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/aggregates.rq $(BASE) $< > $@
	JVM_ARGS=-Xmx8g $(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/aggregates.csv) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
