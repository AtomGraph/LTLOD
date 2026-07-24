include ../config.mk

CACHE := cache
OUT := ../../datasets/current/legal-entities
JAR := datasets/gov/rc/jar
AR := datasets/gov/rc/ar

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

# Registered-office chain (cross-domain link to admin-units). JuridinisAsmuo has no
# usable address, so the office resolves Buveine (ja_kodas -> aob_kodas) joined to
# Pastatas (aob_kodas -> savivaldybe.sav_kodas + pasto_kodas). Both are national bulk
# registers (Buveine ~all legal entities, Pastatas ~all buildings) — gitignored like
# settlements/streets. NOTE: if Spinta ever truncates these single-GET dumps, add
# paging; the institution match rate in the validate step would drop, flagging it.
$(CACHE)/buveines.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR)/buveines/Buveine $@ "juridinis_asmuo.ja_kodas,adresas.aob_kodas,adresas_nuo"

$(CACHE)/pastatai.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/pastatas/Pastatas $@ "aob_kodas.aob_kodas,savivaldybe.sav_kodas,gyvenamoji_vietove.gyv_kodas,pasto_kodas"

# Narrow the bulk registers to our institutions BEFORE csv2rdf/graphify (keeps the
# mapping's per-entity latest-office FILTER NOT EXISTS cheap — bounded to our set,
# not the full national registers). All joined columns are numeric codes (no commas)
# and only $1/$2 are read, so plain comma-splitting is safe.
$(CACHE)/buveines-inst.csv: $(CACHE)/buveines.csv $(CACHE)/institutions.csv
	awk -F, 'NR==FNR{ja[$$1];next} FNR==1||($$1 in ja)' $(CACHE)/institutions.csv $(CACHE)/buveines.csv > $@
$(CACHE)/pastatai-inst.csv: $(CACHE)/pastatai.csv $(CACHE)/buveines-inst.csv
	awk -F, 'NR==FNR{aob[$$2];next} FNR==1||($$1 in aob)' $(CACHE)/buveines-inst.csv $(CACHE)/pastatai.csv > $@

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/institutions.trig: $(CACHE)/institutions.nt $(CACHE)/buveines-inst.nt $(CACHE)/pastatai-inst.nt mappings/institutions.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/institutions.rq $(BASE) \
	  $(CACHE)/institutions.nt $(CACHE)/buveines-inst.nt $(CACHE)/pastatai-inst.nt > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
