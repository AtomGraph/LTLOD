include ../config.mk

CACHE := cache
OUT := ../../datasets/current/seimas
TAXOUT := ../../datasets/current/taxonomies
LRS := https://apps.lrs.lt/sip

UNIT_FEEDS := frakcijos komitetai komisijos

.PHONY: all reconcile clean FORCE
all: $(OUT)/persons.trig $(OUT)/org-units.trig $(OUT)/parties.trig $(TAXOUT)/position-types.trig reconcile

# Wikidata reconciliation + photo enrichment
reconcile: $(OUT)/alignments.trig

$(OUT)/alignments.trig: $(OUT)/persons.trig
	uv run --project ../tools ltlod-reconcile persons \
		--input $(OUT)/persons.trig \
		--output $@ --report $(CACHE)/unmatched-persons.csv

# Official portraits scraped from lrs.lt biography pages (opt-in: scraping fallback,
# ~1 req/s; covers nearly all current members vs ~half from Wikidata P18)
.PHONY: photos
photos: $(OUT)/persons.trig
	uv run --project ../tools python -m ltlod_etl.scrape.seimas_photos \
		$(OUT)/persons.trig "$(BASE)" $(OUT)/photos.trig

# --- fetch (always fresh) ---
$(CACHE)/nariai.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_nariai" $@ SeimoNarys

$(CACHE)/frakcijos.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_frakcijos" $@ SeimoFrakcija

$(CACHE)/komitetai.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_komitetai" $@ SeimoKomitetas

$(CACHE)/komisijos.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_komisijos" $@ SeimoKomisija

# --- normalize (XML -> source-shaped RDF/XML) ---
$(CACHE)/nariai.rdf: $(CACHE)/nariai.xml xslt/nariai.xsl
	xsltproc --stringparam base "$(BASE)" xslt/nariai.xsl $< > $@

$(CACHE)/units-%.rdf: $(CACHE)/%.xml xslt/org-units.xsl
	xsltproc --stringparam base "$(BASE)" xslt/org-units.xsl $< > $@

# --- graphify ---
$(OUT)/persons.trig: $(CACHE)/nariai.rdf mappings/persons.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/persons.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@

$(OUT)/org-units.trig: $(UNIT_FEEDS:%=$(CACHE)/units-%.rdf) $(CACHE)/nariai.rdf mappings/org-units.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/org-units.rq $(BASE) \
	  $(UNIT_FEEDS:%=$(CACHE)/units-%.rdf) $(CACHE)/nariai.rdf > $@
	$(LIB)/validate.sh $@

$(OUT)/parties.trig: $(CACHE)/nariai.rdf mappings/parties.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/parties.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@

$(TAXOUT)/position-types.trig: $(CACHE)/nariai.rdf mappings/position-types.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/position-types.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@

clean:
	rm -rf $(CACHE)

FORCE:
