include ../config.mk

# VTEK (Vyriausioji tarnybinės etikos komisija) registers:
#   SKAIDRIS — registered lobbyists, lobbyists' transparency declarations and officials'
#              declarations of experienced lobbying influence  -> lobbyists/, lobbying-declarations/
#   PINREG   — politicians' public private-interest declarations (their own ties to legal
#              entities and workplaces only)                      -> interest-declarations/
# There is no scripted fetch: both hosts are behind a Cloudflare challenge, so the source is
# harvested in a real browser (harvest-skaidris.js, harvest-pinreg.js; the procedure, also for
# Claude in Chrome, is .claude/skills/harvest-vtek/SKILL.md) into data/skaidris.json and
# data/pinreg.json (gitignored: re-harvest, never edit). Everything below runs offline.

CACHE := cache
OUT := ../../datasets/current/vtek
CURRENT := ../../datasets/current
# officials who never held a Seimas seat (etl/officials/) resolve too, once that domain exists
PERSONS := $(CURRENT)/seimas/persons.trig $(wildcard $(CURRENT)/officials/persons.trig)
INSTITUTIONS := $(CURRENT)/legal-entities/institutions.trig
UNITS := $(CURRENT)/seimas/org-units.trig
ALIASES := ../declarations/data/aliases.csv
AREAS := ../taxonomies/data/lobbying-areas.csv
ROLES := ../taxonomies/data/interest-roles.csv

CSVS := lobbyists lobbying lobbying-acts lobbying-contacts interests interest-ties

.PHONY: all clean
all: $(OUT)/lobbyists.trig $(OUT)/lobbying.trig $(OUT)/interests.trig

# --- normalize: reconcile persons/institutions/bills, flatten to CSV ---
$(CSVS:%=$(CACHE)/%.csv) &: data/skaidris.json data/pinreg.json data/institution-aliases.csv \
		$(PERSONS) $(INSTITUTIONS) $(UNITS) $(ALIASES) $(AREAS) $(ROLES) ../tools/src/ltlod_etl/vtek.py
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-vtek --base $(BASE) \
		--skaidris data/skaidris.json --pinreg data/pinreg.json \
		--persons $(PERSONS) --aliases $(ALIASES) \
		--institutions $(INSTITUTIONS) --seimas-units $(UNITS) \
		--institution-aliases data/institution-aliases.csv \
		--areas $(AREAS) --roles $(ROLES) --out $(CACHE)

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# expected graph count per output: the normalizer's document count (the CSVs carry
# multi-line quoted fields, so line-based counting would be wrong)
rows = $$(cat $(1:.csv=.count))

# --- graphify + validate ---
$(OUT)/lobbyists.trig: $(CACHE)/lobbyists.nt mappings/lobbyists.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/lobbyists.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $(call rows,$(CACHE)/lobbyists.csv)

$(OUT)/lobbying.trig: $(CACHE)/lobbying.nt $(CACHE)/lobbying-acts.nt $(CACHE)/lobbying-contacts.nt mappings/lobbying.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/lobbying.rq $(BASE) $(CACHE)/lobbying.nt $(CACHE)/lobbying-acts.nt $(CACHE)/lobbying-contacts.nt > $@
	$(LIB)/validate.sh $@ $(BASE) $(call rows,$(CACHE)/lobbying.csv)

$(OUT)/interests.trig: $(CACHE)/interests.nt $(CACHE)/interest-ties.nt mappings/interests.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/interests.rq $(BASE) $(CACHE)/interests.nt $(CACHE)/interest-ties.nt > $@
	$(LIB)/validate.sh $@ $(BASE) $(call rows,$(CACHE)/interests.csv)

clean:
	rm -rf $(CACHE)
