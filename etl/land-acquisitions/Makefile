include ../config.mk

# NŽT (National Land Service) applications to acquire agricultural or forest land - the
# consent the Law on the Acquisition of Agricultural Land requires - from the open
# get.data.gov.lt model nzt/paraiskos/Paraiska (2023 onwards). NŽT identifies legal-entity
# applicants only: their applications become documents linked to legal-entities/{ja_kodas}/
# (after a name check against the JAR), natural persons' are counted per municipality, year
# and land purpose (ltlod-land; cells under 3 suppressed).
#
# Outputs (datasets/current/land-acquisitions/):
#   applications.trig  one document per legal-entity application (~17.8k)
#   natural-persons.trig  the totals as qb:Observations (~450)
#   dataset.trig       their cube definition
# cache/name-check.csv lists the applications whose name and code disagree, for review.

CACHE := cache
OUT := ../../datasets/current/land-acquisitions
MODEL := datasets/gov/nzt/paraiskos/Paraiska
JAR := datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo
MUNICIPALITIES := ../../datasets/current/admin-units/municipalities.trig
FIELDS := paraiskos_id,pateikimo_data,prasymo_tipas,atstovavimas,teikejo_vardas,gavejo_asmens_kodas,savivaldybe,prasytojo_tipas,sprendimo_data,sprendimas,isigyjamas_plotas,bendras_prasytojo_valdomas_plotas,bendras_plotas_po_isigyjimo

.PHONY: all clean FORCE
all: $(OUT)/dataset.trig $(OUT)/applications.trig $(OUT)/natural-persons.trig

# --- fetch: every application (~140k rows), and the JAR names the codes are checked against ---
$(CACHE)/applications.csv: FORCE
	$(LIB)/fetch-spinta.sh $(MODEL) $@ "$(FIELDS)"

$(CACHE)/jar-names.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR) $@ "ja_kodas,ja_pavadinimas"

# --- normalize: legal-entity applications + natural-person totals ---
$(CACHE)/le-applications.csv $(CACHE)/totals.csv &: $(CACHE)/applications.csv $(CACHE)/jar-names.csv $(MUNICIPALITIES)
	uv run --project ../tools ltlod-land --input $(CACHE)/applications.csv \
		--jar-names $(CACHE)/jar-names.csv --municipalities $(MUNICIPALITIES) --base $(BASE) \
		--applications $(CACHE)/le-applications.csv --totals $(CACHE)/totals.csv \
		--report $(CACHE)/name-check.csv

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ---
$(OUT)/dataset.trig: mappings/dataset.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) > $@
	$(LIB)/validate.sh $@ $(BASE) 1

$(OUT)/applications.trig: $(CACHE)/le-applications.nt mappings/applications.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/applications.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/le-applications.csv) - 1))

$(OUT)/natural-persons.trig: $(CACHE)/totals.nt mappings/totals.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/totals.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/totals.csv) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
