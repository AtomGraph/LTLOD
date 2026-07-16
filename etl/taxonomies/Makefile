include ../config.mk

CACHE := cache
OUT := ../../datasets/current/taxonomies
JAR := datasets/gov/rc/jar

# hand-authored schemes (source of truth: data/*.csv)
STATIC_SCHEMES := settlement-types street-types admin-unit-levels org-unit-types
# schemes derived from live classifier data
FETCHED_SCHEMES := legal-forms legal-statuses

.PHONY: all clean FORCE
all: $(STATIC_SCHEMES:%=$(OUT)/%.trig) $(FETCHED_SCHEMES:%=$(OUT)/%.trig)

$(CACHE)/legal-forms.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR)/formos_statusai/Forma $@ "kodas,pavadinimas,name,tipas"

$(CACHE)/legal-statuses.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR)/formos_statusai/Statusas $@ "kodas,pavadinimas,name"

$(CACHE)/%.nt: data/%.csv
	@mkdir -p $(CACHE)
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/%.trig: $(CACHE)/%.nt mappings/%.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/$*.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@

clean:
	rm -rf $(CACHE)

FORCE:
