include ../config.mk

CACHE := cache
OUT := ../../datasets/current/legal-entities
JAR := datasets/gov/rc/jar
AR := datasets/gov/rc/ar

# The full Legal Entities Register (JAR, ~547k entities incl. deregistered ones), one
# mapping, two outputs:
#   institutions.trig  budget institutions (legal forms 580 state, 680 municipal,
#                      950 generic) — committed
#   entities.trig      every other legal entity — bulk (~14.4M quads, ~1 GB), gitignored like
#                      settlements/streets; graphified in chunks (chunked.sh)
FORM_CODES := 580 680 950
# forma.kodas first: the partition awk reads $1, and ja_pavadinimas (the only column
# that can contain quoted commas) last, so the leading code columns split safely.
SELECT := forma.kodas,statusas.kodas,ja_kodas,reg_data,isreg_data,ja_pavadinimas
# chunked graphify of entities.trig (rows per chunk, parallel chunks)
CHUNK_ROWS ?= 25000
JOBS ?= 3
export CHUNK_ROWS JOBS

.PHONY: all institutions entities clean FORCE
all: institutions entities
institutions: $(OUT)/institutions.trig
entities: $(OUT)/entities.trig

$(CACHE)/jar.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR)/iregistruoti/JuridinisAsmuo $@ "$(SELECT)"

$(CACHE)/institutions.csv: $(CACHE)/jar.csv
	awk -F, 'BEGIN{split("$(FORM_CODES)",f," ");for(i in f)form[f[i]]} NR==1||($$1 in form)' $< > $@
$(CACHE)/entities.csv: $(CACHE)/jar.csv
	awk -F, 'BEGIN{split("$(FORM_CODES)",f," ");for(i in f)form[f[i]]} NR==1||!($$1 in form)' $< > $@

# Registered-office chain (cross-domain link to admin-units and streets).
# JuridinisAsmuo has no usable address, so the office resolves Buveine (ja_kodas ->
# aob_kodas, one current office per registered entity) to the AR building Pastatas
# (aob_kodas -> savivaldybe.sav_kodas, gyvenamoji_vietove.gyv_kodas, gatve.gat_kodas,
# pasto_kodas). About half of the offices are a premises address (an office or flat):
# those resolve through AR Patalpa (premises aob_kodas -> its building's aob_kodas).
# All three are national bulk registers — gitignored cache. NOTE: if Spinta ever
# truncates these single-GET dumps, add paging; the office coverage reported by the
# offices.csv step would drop, flagging it.
$(CACHE)/buveines.csv: FORCE
	$(LIB)/fetch-spinta.sh $(JAR)/buveines/Buveine $@ "juridinis_asmuo.ja_kodas,adresas.aob_kodas,adresas_nuo"

$(CACHE)/pastatai.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/pastatas/Pastatas $@ "aob_kodas.aob_kodas,savivaldybe.sav_kodas,gyvenamoji_vietove.gyv_kodas,gatve.gat_kodas,pasto_kodas"

$(CACHE)/patalpos.csv: FORCE
	$(LIB)/fetch-spinta.sh $(AR)/patalpa/Patalpa $@ "aob_kodas.aob_kodas,pastatas.aob_kodas.aob_kodas"

# One row per entity with a resolvable office. Every joined column is a numeric code
# or an LT-nnnnn postcode (no commas), so plain comma-splitting is safe. Spinta CSV
# lines end in CRLF: strip the CR, or a last-column key never matches.
$(CACHE)/offices.csv: $(CACHE)/buveines.csv $(CACHE)/pastatai.csv $(CACHE)/patalpos.csv
	awk -F, -v OFS=, ' \
	  { sub(/\r$$/, "") } \
	  FILENAME ~ /pastatai/ { if (FNR > 1) b[$$1] = $$2 OFS $$3 OFS $$4 OFS $$5; next } \
	  FILENAME ~ /patalpos/ { if (FNR > 1) p[$$1] = $$2; next } \
	  FNR == 1 { print "juridinis_asmuo.ja_kodas,aob_kodas,sav_kodas,gyv_kodas,gat_kodas,pasto_kodas"; next } \
	  { n++; a = $$2; if (!(a in b) && (a in p)) a = p[a]; if (a in b) { m++; print $$1, $$2, b[a] } } \
	  END { printf "offices: %d of %d registered offices resolved to a building\n", m, n > "/dev/stderr" }' \
	  $(CACHE)/pastatai.csv $(CACHE)/patalpos.csv $(CACHE)/buveines.csv > $@

$(CACHE)/institutions-offices.csv: $(CACHE)/offices.csv $(CACHE)/institutions.csv
	awk -F, 'NR==FNR{if(FNR>1)ja[$$3];next} FNR==1||($$1 in ja)' $(CACHE)/institutions.csv $< > $@

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

$(OUT)/institutions.trig: $(CACHE)/institutions.nt $(CACHE)/institutions-offices.nt mappings/legal-entities.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/legal-entities.rq $(BASE) $(CACHE)/institutions.nt $(CACHE)/institutions-offices.nt > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/institutions.csv) - 1))

$(OUT)/entities.trig: $(CACHE)/entities.csv $(CACHE)/offices.csv mappings/legal-entities.rq chunked.sh ../shapes/legal-entities.ttl
	@mkdir -p $(OUT)
	CHUNK_DIR=$(CACHE)/chunks ./chunked.sh $(CACHE)/entities.csv $(CACHE)/offices.csv \
	  mappings/legal-entities.rq ../shapes/legal-entities.ttl $(BASE) $@

clean:
	rm -rf $(CACHE)

FORCE:
