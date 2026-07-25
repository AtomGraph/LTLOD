include ../config.mk

CACHE := cache
OUT := ../../datasets/current/admin-units
AR := datasets/gov/rc/ar

LEVELS := counties municipalities elderships settlements streets
RECONCILED := counties municipalities elderships
GEOLEVELS := counties municipalities elderships settlements

# Spatial (erdviniai duomenys) source per level: {model, code col, geometry col,
# simplify tolerance}. Geometry is LKS-94/EPSG:3346 WKT; ltlod-geo reprojects a
# representative point to WGS84. <level>_SIMPLIFY (metres) additionally emits the
# Douglas–Peucker-simplified boundary as gs:asWKT; unset = point-only (settlements
# skip the geometry: 20k detailed polygons are too heavy for the client map).
counties_SPATIAL       := graapskritis/GraApskritis
counties_CODECOL       := aps_kodas
counties_GEOMCOL       := apskritys
counties_SIMPLIFY      := 50
municipalities_SPATIAL := grasavivaldybe/GraSavivaldybe
municipalities_CODECOL := sav_kodas
municipalities_GEOMCOL := savivaldybes
municipalities_SIMPLIFY := 50
elderships_SPATIAL     := graseniunija/GraSeniunija
elderships_CODECOL     := sen_kodas
elderships_GEOMCOL     := seniunijos
elderships_SIMPLIFY    := 50
settlements_SPATIAL    := gragyvenamojivietove/GraGyvenamojiVietove
settlements_CODECOL    := gyv_kodas
settlements_GEOMCOL    := gyv_vietoves

.PHONY: all reconcile geo clean FORCE
all: $(LEVELS:%=$(OUT)/%.trig) reconcile geo

# Wikidata reconciliation + image enrichment (settlements/streets not reconciled yet)
reconcile: $(OUT)/alignments.trig

# WGS84 coordinates per admin unit, from the AR spatial polygons: geo:lat/geo:long
# representative point (all levels) + gs:asWKT simplified boundary (coarse levels,
# via <level>_SIMPLIFY). Emitted to separate *-geo.trig, same graph names → merged on
# load (the alignments.trig convention). Unlocks ac:MapMode for admin-unit listings.
geo: $(GEOLEVELS:%=$(OUT)/%-geo.trig)

$(OUT)/alignments.trig: $(RECONCILED:%=$(OUT)/%.trig)
	@mkdir -p $(OUT) $(CACHE)
	uv run --project ../tools ltlod-reconcile admin-units --base $(BASE) \
		$(RECONCILED:%=--input $(OUT)/%.trig) \
		--output $(CACHE)/alignments.trig --report $(CACHE)/unmatched.csv
	$(LIB)/relativize.sh $(BASE) < $(CACHE)/alignments.trig > $@

# Fetches depend on FORCE: every run pulls current data (user requirement)
$(CACHE)/counties.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/apskritis/Apskritis $@ "adm_kodas,pavadinimas,adm_nuo"

$(CACHE)/municipalities.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/savivaldybe/Savivaldybe $@ "sav_kodas,pavadinimas,sav_nuo,apskritis.adm_kodas"

$(CACHE)/elderships.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/seniunija/Seniunija $@ "sen_kodas,pavadinimas,sen_nuo,sen_iki,savivaldybe.sav_kodas"

$(CACHE)/settlements.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/gyvenamojivietove/GyvenamojiVietove $@ "gyv_kodas,tipas,pavadinimas,gyv_nuo,gyv_iki,seniunija.sen_kodas,savivaldybe.sav_kodas"

$(CACHE)/streets.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/gatve/Gatve $@ "gat_kodas,tipas,tipo_santrumpa,pavadinimas,gat_nuo,gat_iki,gyvenamoji_vietove.gyv_kodas"

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/%.trig: $(CACHE)/%.nt mappings/%.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/$*.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

# Spatial fetch (FORCE — fresh) then reproject to WGS84. Selecting only {code,
# geometry}; ltlod-geo skips units without geometry (partial coverage OK). Coarse
# levels also emit a simplified gs:asWKT boundary (--simplify $($*_SIMPLIFY)).
$(CACHE)/%-geo.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/$($*_SPATIAL) $@ "$($*_CODECOL),$($*_GEOMCOL)"

$(OUT)/%-geo.trig: $(CACHE)/%-geo.csv
	@mkdir -p $(OUT)
	uv run --project ../tools ltlod-geo --base $(BASE) --input $< \
		--code-col $($*_CODECOL) --geom-col $($*_GEOMCOL) \
		$(if $($*_SIMPLIFY),--simplify $($*_SIMPLIFY)) --output $(CACHE)/$*-geo.trig
	$(LIB)/relativize.sh $(BASE) < $(CACHE)/$*-geo.trig > $@

clean:
	rm -rf $(CACHE)

FORCE:
