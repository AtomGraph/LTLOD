include ../config.mk

CACHE := cache
OUT := ../../datasets/current/seimas
TAXOUT := ../../datasets/current/taxonomies
CONSTOUT := ../../datasets/current/constituencies
LRS := https://apps.lrs.lt/sip

UNIT_FEEDS := frakcijos komitetai komisijos

.PHONY: all reconcile votes bills clean FORCE
all: $(OUT)/persons.trig $(OUT)/org-units.trig $(OUT)/parties.trig $(TAXOUT)/position-types.trig $(CONSTOUT)/constituencies.trig \
	$(OUT)/terms.trig $(OUT)/sessions.trig $(OUT)/sittings.trig $(TAXOUT)/activity-types.trig reconcile

# Wikidata reconciliation + photo enrichment
reconcile: $(OUT)/alignments.trig

# data/wikidata-alignments.csv: curated asmens_id -> QID for persons the exact-label match
# cannot place (LRS and Wikidata spell the name differently); the alignment also brings
# Wikidata's date of death (schema:deathDate), which the name matchers use as a guard
$(OUT)/alignments.trig: $(OUT)/persons.trig data/wikidata-alignments.csv
	@mkdir -p $(OUT) $(CACHE)
	uv run --project ../tools ltlod-reconcile persons --base $(BASE) \
		--input $(OUT)/persons.trig --curated data/wikidata-alignments.csv \
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
		'//EigosKlausimas/@svarstomo_klausimo_id' $(CACHE)/eiga
	touch $@

# bills (opt-in, `make bills`, same term scope as the votes): the planned agenda of
# each sitting (its items' e-seimas documents), one request per sitting, and the bills
# each member initiated, one request per term (slow — ~1 min per term)
$(CACHE)/darbotvarke/.fetched: $(CACHE)/eiga/.fetched
	JOBS=$(VOTE_JOBS) $(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_sp_darbotvarke?posedzio_id=" $(@D) DarbotvarkėsKlausimas \
		'//SeimoPosėdis/@posėdžio_id' $(CACHE)/eiga
	touch $@

$(CACHE)/inicijuoti/.fetched: $(CACHE)/kadencijos.xml
	rm -rf $(@D) && mkdir -p $(@D)
	for t in $(vote_terms); do \
		$(LIB)/fetch-xml.sh "$(LRS)/p2b.ad_sn_inicijuoti_ta_projektai?kadencijos_id=$$t" $(@D)/$$t.xml \
			SeimoNarioPateiktasTeisėsAktoProjektas || exit 1; \
	done
	touch $@

$(CACHE)/balsavimai/.fetched: $(CACHE)/klausimai/.fetched
	JOBS=$(VOTE_JOBS) $(LIB)/fetch-xml-each.sh "$(LRS)/p2b.ad_sp_balsavimo_rezultatai?balsavimo_id=" $(@D) BendriBalsavimoRezultatai \
		'//SvarstymoEigosĮvykis/@balsavimo_id' $(CACHE)/klausimai
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

# the three vote feed levels joined by votes.xsl, normalized in chunks of VOTE_CHUNK votes: one
# xsltproc run over every term's feeds (1.4 GB) exceeds libxml2's 10M-node XPath node-set cap, which
# both `//` and xsl:key indexing hit. Every chunk gets all agenda items and consideration events -
# the side votes.xsl's keys index - plus a slice of the vote results (~1k nodes each against ~3.5M
# for the join side), so each vote still finds its event and item. One RDF/XML file per chunk; their
# blank nodes stay apart, since every file is parsed in its own scope
VOTE_CHUNK ?= 4000
$(CACHE)/votes/.normalized: $(CACHE)/balsavimai/.fetched xslt/votes.xsl
	rm -rf $(@D) && mkdir -p $(@D)
	{ echo '<feeds>'; find $(CACHE)/eiga $(CACHE)/klausimai -name '*.xml' -exec xmlstarlet sel -t -c '/*' {} +; } > $(@D)/joins.part
	find $(CACHE)/balsavimai -name '*.xml' | sort | split -l $(VOTE_CHUNK) - $(@D)/chunk.
	for c in $(@D)/chunk.*; do \
		{ cat $(@D)/joins.part; xargs xmlstarlet sel -t -c '/*' < $$c; echo '</feeds>'; } \
			| xsltproc --stringparam base "$(BASE)" xslt/votes.xsl - > $(@D)/$${c##*.}.rdf || exit 1; \
	done
	rm $(@D)/joins.part $(@D)/chunk.*
	touch $@

# agenda items: the considered items (eiga) joined with their course of consideration
# (klausimai) and the planned agenda (darbotvarke), one xsltproc run — a term's three
# levels stay well under libxml2's node-set cap that forces votes.xsl into chunks
$(CACHE)/agenda-items.rdf: $(CACHE)/darbotvarke/.fetched $(CACHE)/klausimai/.fetched xslt/agenda-items.xsl
	{ echo '<feeds>'; find $(CACHE)/eiga $(CACHE)/klausimai $(CACHE)/darbotvarke -name '*.xml' -exec xmlstarlet sel -t -c '/*' {} +; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/agenda-items.xsl - > $@

$(CACHE)/bills.rdf: $(CACHE)/inicijuoti/.fetched xslt/bills.xsl
	{ echo '<feeds>'; xmlstarlet sel -t -c '/*' $(@D)/inicijuoti/*.xml; echo '</feeds>'; } \
		| xsltproc --stringparam base "$(BASE)" xslt/bills.xsl - > $@

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

$(OUT)/votes.trig: $(CACHE)/votes/.normalized $(CACHE)/posedziai.rdf $(CACHE)/sesijos.rdf mappings/votes.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/votes.rq $(BASE) $(CACHE)/votes/*.rdf $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(TAXOUT)/decision-methods.trig: $(CACHE)/votes/.normalized mappings/decision-methods.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/decision-methods.rq $(BASE) $(CACHE)/votes/*.rdf > $@
	$(LIB)/validate.sh $@ $(BASE)

# Bills and plenary agenda items (opt-in, `make bills`; VOTE_TERMS scope, latest term by
# default): the items considered at each sitting (-> sitting, stage, bills, speakers,
# e-seimas document), the bills they cite plus those members initiated (-> initiators),
# and the stage taxonomy. Shares the eiga/klausimai fetch with `make votes`, whose
# votes link to these items.
bills: $(OUT)/bills.trig $(OUT)/agenda-items.trig $(TAXOUT)/process-stages.trig

$(OUT)/agenda-items.trig: $(CACHE)/agenda-items.rdf $(CACHE)/posedziai.rdf $(CACHE)/sesijos.rdf mappings/agenda-items.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/agenda-items.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(OUT)/bills.trig: $(CACHE)/bills.rdf $(CACHE)/agenda-items.rdf mappings/bills.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/bills.rq $(BASE) $(filter %.rdf,$^) > $@
	$(LIB)/validate.sh $@ $(BASE)

$(TAXOUT)/process-stages.trig: $(CACHE)/agenda-items.rdf mappings/process-stages.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/process-stages.rq $(BASE) $< > $@
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
