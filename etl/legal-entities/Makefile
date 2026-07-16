include ../config.mk

CACHE := cache
OUT := ../../datasets/current/legal-entities
JAR := datasets/gov/rc/jar

# Budget-institution legal forms: 580 state, 680 municipal, 950 generic.
# Full JAR (~540k entities) can be enabled later by widening/removing the filter.
FORM_CODES := 580 680 950
SELECT := ja_kodas,ja_pavadinimas,reg_data,isreg_data,forma.kodas,statusas.kodas

.PHONY: all clean FORCE
all: $(OUT)/institutions.trig

$(CACHE)/institutions.csv: FORCE
	@mkdir -p $(CACHE)
	@rm -f $@.tmp
	@for code in $(FORM_CODES); do \
	  curl -fsSL --retry 3 --max-time 600 \
	    "https://get.data.gov.lt/$(JAR)/iregistruoti/JuridinisAsmuo/:format/csv?select($(SELECT))&forma.kodas=$$code" \
	    > $(CACHE)/institutions-$$code.csv; \
	  echo "fetched forma.kodas=$$code: $$(($$(wc -l < $(CACHE)/institutions-$$code.csv) - 1)) rows" >&2; \
	done
	@head -1 $(CACHE)/institutions-$(firstword $(FORM_CODES)).csv > $@.tmp
	@for code in $(FORM_CODES); do tail -n +2 $(CACHE)/institutions-$$code.csv >> $@.tmp; done
	@mv $@.tmp $@

$(CACHE)/institutions.nt: $(CACHE)/institutions.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/institutions.trig: $(CACHE)/institutions.nt mappings/institutions.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/institutions.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@

clean:
	rm -rf $(CACHE)

FORCE:
