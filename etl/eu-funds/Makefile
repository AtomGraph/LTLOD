include ../config.mk

# 2014-2020 EU structural-funds implementation contracts from the Finance Ministry's open
# data on get.data.gov.lt (datasets/gov/finmin/sutartys), joined to the project applications
# (finmin/paraiskos) for the code and decision amounts. ltlod-eu-funds fetches Contract
# (~26k, keyset-paginated), its partners (ConPartner) and financing sources (ConFinSource),
# crosswalks the municipality text to the AR code, and emits contracts.csv + partners.csv.
# One ltlod:EUFundingContract per document, keyed by the source _id. Most contracts are
# code-less financial-instrument payouts; ~685 carry a formal project code with amounts.
# Repayments and irregularities are not modelled (their source keys are an unpublished hash).
#   make -C etl/eu-funds

CACHE := cache
OUT := ../../datasets/current/eu-funds

.PHONY: all clean FORCE
all: $(OUT)/contracts.trig

# one run writes both files (partners.csv is a by-product; not a grouped target — macOS make 3.81)
$(CACHE)/contracts.csv: FORCE
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-eu-funds \
		--contracts $(CACHE)/contracts.csv --partners $(CACHE)/partners.csv

$(CACHE)/partners.csv: $(CACHE)/contracts.csv ;

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/contracts.trig: $(CACHE)/contracts.nt $(CACHE)/partners.nt mappings/contracts.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/contracts.rq $(BASE) $(CACHE)/contracts.nt $(CACHE)/partners.nt > $@
	JVM_ARGS=-Xmx8g $(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/contracts.csv) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
