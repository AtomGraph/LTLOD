include ../config.mk

# Public facility registers: education institutions (ŠVIS), licensed health-care
# institutions (VASPVT) and immovable cultural heritage (KPD Cultural Property
# Register, KVR). Each links to the admin units it lies in (locn:Address ->
# locn:adminUnit, by AR code) and, where the register names it, to the legal entity
# that runs it (ltlod:legalEntity -> legal-entities/{ja_kodas}/#this).

CACHE := cache
OUT := ../../datasets/current/facilities
TAXOUT := ../../datasets/current/taxonomies
AR := datasets/gov/rc/ar
TOOLS := uv run --project ../tools ltlod-facilities

# KVR is not in Spinta: data.gov.lt dataset 2192 publishes it as an XLSX
# distribution ("Nekilnojamos kultūros vertybės"), CC BY 4.0. A frozen snapshot
# (2023-02-01) at the time of writing — re-fetched every run all the same, so a
# refreshed upload is picked up automatically.
KVR_URL := https://data.gov.lt/datasets/2192/distribution/13134/download/

.PHONY: all clean FORCE
all: $(OUT)/education.trig $(OUT)/health-care.trig $(OUT)/heritage.trig \
	$(TAXOUT)/education-types.trig $(TAXOUT)/heritage.trig

# --- fetch (always fresh) ------------------------------------------------------

$(CACHE)/svietimo-istaigos.csv: FORCE
	$(LIB)/fetch-spinta.sh datasets/gov/lsd/svietimo_istaigos/SvietimoIstaiga $@

$(CACHE)/bendrojo-ugdymo-mokyklos.csv: FORCE
	$(LIB)/fetch-spinta.sh datasets/gov/nsa/svis/bendrojo_ugdymo_mokyklos/BugdymoMokykla $@

$(CACHE)/spi.csv: FORCE
	$(LIB)/fetch-spinta.sh datasets/gov/vaspvt/licencijos/Istaiga $@

$(CACHE)/spi-adresai.csv: FORCE
	$(LIB)/fetch-spinta.sh datasets/gov/vaspvt/licencijos/IstaigosVeiklosAdresas $@

# AR name lists, to resolve the free-text municipality/eldership names of KVR and
# the VASPVT addresses to AR codes
$(CACHE)/savivaldybes.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/savivaldybe/Savivaldybe $@ "sav_kodas,pavadinimas"

$(CACHE)/seniunijos.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/seniunija/Seniunija $@ "sen_kodas,pavadinimas,sen_iki,savivaldybe.sav_kodas"

$(CACHE)/kvr.xlsx: FORCE
	@mkdir -p $(CACHE)
	curl -fsSL --retry 3 --max-time 600 "$(KVR_URL)" -o $@.tmp
	@test -s $@.tmp || { echo "ERROR: empty KVR download" >&2; exit 1; }
	@mv $@.tmp $@

# --- pre-normalize (reprojection, name -> AR code resolution, slugs) -------------

$(CACHE)/education.csv: $(CACHE)/svietimo-istaigos.csv $(CACHE)/bendrojo-ugdymo-mokyklos.csv
	$(TOOLS) education --institutions $< --schools $(CACHE)/bendrojo-ugdymo-mokyklos.csv \
	  --output $(CACHE)/education.csv --types $(CACHE)/education-types.csv

$(CACHE)/health-care.csv: $(CACHE)/spi.csv $(CACHE)/spi-adresai.csv $(CACHE)/savivaldybes.csv $(CACHE)/seniunijos.csv
	$(TOOLS) health --institutions $< --addresses $(CACHE)/spi-adresai.csv \
	  --municipalities $(CACHE)/savivaldybes.csv --elderships $(CACHE)/seniunijos.csv \
	  --output $(CACHE)/health-care.csv --sites $(CACHE)/health-care-sites.csv

$(CACHE)/heritage.csv: $(CACHE)/kvr.xlsx $(CACHE)/savivaldybes.csv $(CACHE)/seniunijos.csv
	$(TOOLS) heritage --input $< \
	  --municipalities $(CACHE)/savivaldybes.csv --elderships $(CACHE)/seniunijos.csv \
	  --output $(CACHE)/heritage.csv --values $(CACHE)/heritage-values.csv \
	  --taxonomy $(CACHE)/heritage-taxonomy.csv

# secondary outputs of the three runs above (GNU make 3.81 has no grouped targets)
$(CACHE)/education-types.csv: $(CACHE)/education.csv ; @:
$(CACHE)/health-care-sites.csv: $(CACHE)/health-care.csv ; @:
$(CACHE)/heritage-values.csv $(CACHE)/heritage-taxonomy.csv: $(CACHE)/heritage.csv ; @:

# --- normalize ------------------------------------------------------------------

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ----------------------------------------------------------

$(OUT)/education.trig: $(CACHE)/education.nt mappings/education.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/education.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/health-care.trig: $(CACHE)/health-care.nt $(CACHE)/health-care-sites.nt mappings/health-care.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/health-care.rq $(BASE) $(filter %.nt,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/heritage.trig: $(CACHE)/heritage.nt $(CACHE)/heritage-values.nt mappings/heritage.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/heritage.rq $(BASE) $(filter %.nt,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(TAXOUT)/education-types.trig: $(CACHE)/education-types.nt mappings/education-types.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/education-types.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

# the four KVR schemes (statuses, significance, kinds, valuable properties) in one file
$(TAXOUT)/heritage.trig: $(CACHE)/heritage-taxonomy.nt mappings/heritage-taxonomy.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/heritage-taxonomy.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
