include ../config.mk

CACHE := cache
OUT := ../../datasets/current/admin-units
AR := datasets/gov/rc/ar

LEVELS := counties municipalities elderships settlements streets
RECONCILED := counties municipalities elderships

.PHONY: all reconcile clean FORCE
all: $(LEVELS:%=$(OUT)/%.trig) reconcile

# Wikidata reconciliation + image enrichment (settlements/streets not reconciled yet)
reconcile: $(OUT)/alignments.trig

$(OUT)/alignments.trig: $(RECONCILED:%=$(OUT)/%.trig)
	uv run --project ../tools ltlod-reconcile admin-units \
		$(RECONCILED:%=--input $(OUT)/%.trig) \
		--output $@ --report $(CACHE)/unmatched.csv

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
	$(LIB)/validate.sh $@

clean:
	rm -rf $(CACHE)

FORCE:
