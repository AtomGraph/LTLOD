include ../config.mk

CACHE := cache
OUT := ../../datasets/current/seimas
TAXOUT := ../../datasets/current/taxonomies
CONSTOUT := ../../datasets/current/constituencies
LRS := https://apps.lrs.lt/sip

UNIT_FEEDS := frakcijos komitetai komisijos

.PHONY: all reconcile votes clean FORCE
all: $(OUT)/persons.trig $(OUT)/org-units.trig $(OUT)/parties.trig $(TAXOUT)/position-types.trig $(CONSTOUT)/constituencies.trig \
	$(OUT)/terms.trig $(OUT)/sessions.trig $(OUT)/sittings.trig $(TAXOUT)/activity-types.trig reconcile

# Wikidata reconciliation + photo enrichment
reconcile: $(OUT)/alignments.trig

$(OUT)/alignments.trig: $(OUT)/persons.trig
	@mkdir -p $(OUT) $(CACHE)
	uv run --project ../tools ltlod-reconcile persons --base $(BASE) \
		--input $(OUT)/persons.trig \
		--output $(CACHE)/alignments.trig --report $(CACHE)/unmatched-persons.csv
	$(LIB)/relativize.sh $(BASE) < $(CACHE)/alignments.trig > $@

# Official portraits scraped from lrs.lt biography pages (opt-in: scraping fallback,
# ~1 req/s; covers nearly all current members vs ~half from Wikidata P18)
.PHONY: photos
photos: $(OUT)/persons.trig
	@mkdir -p $(OUT) $(CACHE)
	uv run --project ../tools python -m ltlod_etl.scrape.seimas_photos \
		$(OUT)/persons.trig "$(BASE)" $(CACHE)/photos.trig
	$(LIB)/relativize.sh $(BASE) < $(CACHE)/photos.trig > $(OUT)/photos.trig

# --- fetch (always fresh) ---
# members of every term: without kadencijos_id the feed only returns the
# current term, so a member's earlier seats would be lost
$(CACHE)/nariai/.fetched: $(CACHE)/kadencijos.xml
	$(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_seimo_nariai?kadencijos_id=" $(@D) SeimoNarys \
		'//SeimoKadencija/@kadencijos_id' $<
	touch $@

$(CACHE)/frakcijos.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_frakcijos" $@ SeimoFrakcija

$(CACHE)/komitetai.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_komitetai" $@ SeimoKomitetas

$(CACHE)/komisijos.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_komisijos" $@ SeimoKomisija

# calendar: terms -> sessions (one request per term) -> plenary sittings (one
# request per session). The per-id documents land in a directory, which
# fetch-xml-each.sh replaces as a whole; the .fetched stamp is its make target.
$(CACHE)/kadencijos.xml: FORCE
	$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_seimo_kadencijos" $@ SeimoKadencija

$(CACHE)/sesijos/.fetched: $(CACHE)/kadencijos.xml
	$(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_seimo_sesijos?kadencijos_id=" $(@D) SeimoSesija \
		'//SeimoKadencija/@kadencijos_id' $<
	touch $@

$(CACHE)/posedziai/.fetched: $(CACHE)/sesijos/.fetched
	$(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_seimo_posedziai?sesijos_id=" $(@D) SeimoPosėdis \
		'//SeimoSesija/@sesijos_id' $(CACHE)/sesijos/*.xml
	touch $@

# votes (opt-in, `make votes`): plenary sitting -> its agenda items (eiga) -> each
# item's course of consideration (its votes' ids) -> each vote's results. Four
# request levels (~12k requests per term), hence JOBS-way concurrency and the
# term scope: VOTE_TERMS defaults to the latest term only; pass e.g.
# VOTE_TERMS="9 10" for more. The sitting ids are read from the posedziai
# documents of those terms' sessions.
VOTE_JOBS ?= 6
vote_terms = $(or $(VOTE_TERMS),$$(xmlstarlet sel -t -v '//SeimoKadencija/@kadencijos_id' -n $(CACHE)/kadencijos.xml | sort -n | tail -1))
vote_sitting_lists = $$(for t in $(vote_terms); do \
	xmlstarlet sel -t -m '//SeimoSesija[@pavadinimas]' -v 'concat("$(CACHE)/posedziai/", @sesijos_id, ".xml")' -n $(CACHE)/sesijos/$$t.xml; done)

$(CACHE)/eiga/.fetched: $(CACHE)/posedziai/.fetched
	JOBS=$(VOTE_JOBS) $(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_sp_eiga?posedzio_id=" $(@D) EigosKlausimas \
		'//SeimoPosėdis/@posėdžio_id' $(vote_sitting_lists)
	touch $@

$(CACHE)/klausimai/.fetched: $(CACHE)/eiga/.fetched
	JOBS=$(VOTE_JOBS) $(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_sp_klausimo_svarstymo_eiga?svarstomo_klausimo_id=" $(@D) SvarstymoEigosĮvykis \
		'//EigosKlausimas/@svarstomo_klausimo_id' $(CACHE)/eiga/*.xml
	touch $@

$(CACHE)/balsavimai/.fetched: $(CACHE)/klausimai/.fetched
	JOBS=$(VOTE_JOBS) $(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_sp_balsavimo_rezultatai?balsavimo_id=" $(@D) BendriBalsavimoRezultatai \
		'//SvarstymoEigosĮvykis/@balsavimo_id' $(CACHE)/klausimai/*.xml
	touch $@

# --- normalize (XML -> source-shaped RDF/XML) ---
$(CACHE)/nariai.rdf: $(CACHE)/nariai/.fetched xslt/nariai.xsl
	{ echo '<feeds>'; xmlstarlet sel -t -c '/*' $(@D)/nariai/*.xml; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/nariai.xsl - > $@

$(CACHE)/units-%.rdf: $(CACHE)/%.xml xslt/org-units.xsl
	xsltproc --stringparam base "$(BASE)" xslt/org-units.xsl $< > $@

# the per-id documents are merged under one wrapper element (each feed root
# copied without its XML declaration) so one xsltproc run covers a whole level
$(CACHE)/kadencijos.rdf: $(CACHE)/kadencijos.xml xslt/calendar.xsl
	xsltproc --stringparam base "$(BASE)" xslt/calendar.xsl $< > $@

$(CACHE)/sesijos.rdf: $(CACHE)/sesijos/.fetched xslt/calendar.xsl
	{ echo '<feeds>'; xmlstarlet sel -t -c '/*' $(@D)/sesijos/*.xml; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/calendar.xsl - > $@

$(CACHE)/posedziai.rdf: $(CACHE)/posedziai/.fetched xslt/calendar.xsl
	{ echo '<feeds>'; xmlstarlet sel -t -c '/*' $(@D)/posedziai/*.xml; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/calendar.xsl - > $@

# the three vote feed levels merged into one input; votes.xsl joins them by id
$(CACHE)/votes.rdf: $(CACHE)/balsavimai/.fetched xslt/votes.xsl
	{ echo '<feeds>'; find $(CACHE)/eiga $(CACHE)/klausimai $(CACHE)/balsavimai -name '*.xml' \
		-exec xmlstarlet sel -t -c '/*' {} +; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/votes.xsl - > $@

# --- graphify ---
$(OUT)/persons.trig: $(CACHE)/nariai.rdf mappings/persons.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/persons.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/org-units.trig: $(UNIT_FEEDS:%=$(CACHE)/units-%.rdf) $(CACHE)/nariai.rdf mappings/org-units.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/org-units.rq $(BASE) \
	  $(UNIT_FEEDS:%=$(CACHE)/units-%.rdf) $(CACHE)/nariai.rdf > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/parties.trig: $(CACHE)/nariai.rdf mappings/parties.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/parties.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

$(TAXOUT)/position-types.trig: $(CACHE)/nariai.rdf mappings/position-types.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/position-types.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/terms.trig: $(CACHE)/kadencijos.rdf mappings/terms.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/terms.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/sessions.trig: $(CACHE)/sesijos.rdf mappings/sessions.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/sessions.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

# sitting rows + session rows (joined on the session id to reach the term)
$(OUT)/sittings.trig: $(CACHE)/posedziai.rdf $(CACHE)/sesijos.rdf mappings/sittings.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/sittings.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

# ELI-DL activity types (session + sitting types), derived from the calendar feeds
$(TAXOUT)/activity-types.trig: $(CACHE)/sesijos.rdf $(CACHE)/posedziai.rdf mappings/activity-types.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/activity-types.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

# Plenary votes (opt-in, see the fetch section). votes.trig is bulk output
# (~1M voter triples per term) and gitignored like the settlements/streets files;
# the decision-method taxonomy is small and committed.
votes: $(OUT)/votes.trig $(TAXOUT)/decision-methods.trig

$(OUT)/votes.trig: $(CACHE)/votes.rdf $(CACHE)/posedziai.rdf $(CACHE)/sesijos.rdf mappings/votes.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/votes.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(TAXOUT)/decision-methods.trig: $(CACHE)/votes.rdf mappings/decision-methods.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/decision-methods.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

# Electoral districts (apygardos) parsed from the members feed. Own container
# constituencies/ — not admin units (see mappings/constituencies.rq). Term-scoped,
# so the term rows come along for the district titles.
$(CONSTOUT)/constituencies.trig: $(CACHE)/nariai.rdf $(CACHE)/kadencijos.rdf mappings/constituencies.rq
	@mkdir -p $(CONSTOUT)
	$(LIB)/graphify.sh mappings/constituencies.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
