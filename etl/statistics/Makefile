include ../config.mk

CACHE := cache
OUT := ../../datasets/current/statistics
LSD := datasets/gov/lsd/statistika

# First reference year fetched (inclusive). Earlier years exist (population from 1996,
# median age from 1970) — lower it for longer series: make STAT_FROM=2000
STAT_FROM ?= 2015

# Statistics Lithuania (Valstybės duomenų agentūra) indicators, keyed by their OSP
# indicator-database code. The OSP SDMX API (osp-rs.stat.gov.lt/rest_xml) is gone (ORDS
# 404) and the portal is behind a Cloudflare challenge; the same tables are republished
# on get.data.gov.lt under datasets/gov/lsd/statistika/. Per indicator:
#   <code>_MODEL   model path under $(LSD)
#   <code>_SELECT  its territory (+ label) and sex columns — names differ per model
#   <code>_FILTER  pins every dimension other than territory/year/sex to one value
# Metadata (titles, unit, scale) is in data/indicators.csv, keyed by the model path.
INDICATORS := S3R167M3010202 S3R629M3010217 S3R692M30105012 S3R694M30106012 \
              S3R0477M30102201 S7R184M21102562 S3R347M3030903

COMMON := _type,laikotarpis_id,verte,atnaujinta
YEARS = laikotarpis_id>="$(STAT_FROM)"

# Resident population at 1 January — all ages (g000g999 = "Iš viso pagal amžių")
S3R167M3010202_MODEL  := nuolatiniai_gyventojai/S3R167M3010202
S3R167M3010202_SELECT := administracine_teritorija,administracine_teritorija_id,lytis_id
S3R167M3010202_FILTER := &amzius_id="g000g999"
# Median age at 1 January
S3R629M3010217_MODEL  := medianinis_gyvent_amzius/S3R629M3010217
S3R629M3010217_SELECT := teritorija,teritorija_id,lytis_id
# Crude birth / death rates (per 1 000 population)
S3R692M30105012_MODEL  := bendrasis_gimstamumo_rodiklis/S3R692M30105012
S3R692M30105012_SELECT := teritorija,teritorija_id
S3R694M30106012_MODEL  := bendrasis_mirtingumas/S3R694M30106012
S3R694M30106012_SELECT := teritorija,teritorija_id
# Old-age dependency ratio (counties only)
S3R0477M30102201_MODEL  := islaikomo_amziaus_gyventojai/S3R0477M30102201
S3R0477M30102201_SELECT := teritorija,teritorija_id
# GDP per capita (counties only) — thousand EUR (the model also carries "% of the
# national average", which is derivable and would duplicate every observation)
S7R184M21102562_MODEL  := bvp_vienam_gyventojui/S7R184M21102562
S7R184M21102562_SELECT := teritorija,teritorija_id
S7R184M21102562_FILTER := &matavimo_vienetai_id="tukst_euru"
# LFS unemployment rate (counties only) — ages 15 and over: the 15–74 headline (3g) is
# published only from 2021, 15+ has the full series
S3R347M3030903_MODEL  := metinis_nedarbo_lygis/S3R347M3030903
S3R347M3030903_SELECT := teritorija,teritorija_id,lytis_id
S3R347M3030903_FILTER := &amzius_15_24_ir_vyresni_id="15_ir_daugiau"

.PHONY: all clean FORCE
all: $(OUT)/statistics.trig

# Fetches depend on FORCE: every run pulls current data (user requirement)
$(CACHE)/%.csv: FORCE
	$(LIB)/fetch-spinta.sh $(LSD)/$($*_MODEL) $@ "$(COMMON),$($*_SELECT)" '$(YEARS)$($*_FILTER)'

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(CACHE)/indicators.nt: data/indicators.csv
	@mkdir -p $(CACHE)
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/statistics.trig: $(INDICATORS:%=$(CACHE)/%.nt) $(CACHE)/indicators.nt mappings/statistics.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/statistics.rq $(BASE) $(INDICATORS:%=$(CACHE)/%.nt) $(CACHE)/indicators.nt > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
