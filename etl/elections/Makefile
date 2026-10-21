include ../config.mk

# Seimas election results per single-member constituency (apygarda), from the VRK
# election-results map's public ArcGIS feature services (fetch-arcgis.sh says why not
# vrk.lt): both rounds of the single-member races, the party-list (multi-member) vote
# counted in each constituency, turnout, and the constituency boundaries. Candidates
# resolve to persons/ and nominating parties to parties/ (ltlod-elections), constituencies
# to the per-term constituencies/{kadencijos_id}-{nr}/ of the seimas domain.
#
# Political campaign finance (`make finance`, part of `all`): VRK's campaign income,
# expenses and Seimas candidates, harvested in a browser (atviriduomenys.vrk.lt is behind
# a Cloudflare challenge; procedure: .claude/skills/harvest-vrk/) into data/vrk-*.csv,
# which are gitignored source files (~60 MB). Without them the finance targets are
# skipped with a notice, so `make` still builds the results.

CACHE := cache
OUT := ../../datasets/current/elections
PERSONS := ../../datasets/current/seimas/persons.trig
# schema:deathDate (Wikidata) for the candidate matcher's lifetime guard
ALIGNMENTS := ../../datasets/current/seimas/alignments.trig
PARTIES := ../../datasets/current/seimas/parties.trig
CONSTITUENCIES := ../../datasets/current/constituencies/constituencies.trig

# Elections to build (data/elections.csv holds their dates and terms). VRK's ArcGIS
# layers carry full results (every candidate, vote counts, the elected flag) for 2020
# and 2024 only; the 2016 layers keep just the top five per constituency, as
# percentages, and nothing older is published there.
ELECTIONS ?= 2020 2024
# Constituency boundary simplification tolerance (metres, Douglas–Peucker)
SIMPLIFY ?= 100

# service names per election and layer: smd1/smd2 = single-member round 1/2,
# mmd = the party-list vote, by constituency (APG = apygarda)
smd1_2020 := LRS_2020_V_T1_APG
smd2_2020 := LRS_2020_V_T2_APG
mmd_2020  := LRS_2020_D_APG
smd1_2024 := LRS_2024_V_T1_APG
smd2_2024 := LRS_2024_V_T2_APG
mmd_2024  := LRS_2024_D_APG

LAYERS := smd1 smd2 mmd
SOURCES := $(foreach y,$(ELECTIONS),$(foreach l,$(LAYERS),$(CACHE)/$(y)-$(l).json)) \
	$(foreach y,$(ELECTIONS),$(CACHE)/$(y)-geo.json)
TABLES := contests rounds candidates lists

# Campaign types to include (VRK p_kamp_rusis: SEI Seimas, SAV municipal, PRE
# presidential, EP European Parliament, REF referendum). Persons, elections and
# candidate results exist for the Seimas only, hence the default.
CAMPAIGN_TYPES ?= SEI
FINANCE_SOURCES := data/vrk-pajamos.csv data/vrk-islaidos.csv data/vrk-kandidatai-seimas.csv
FINANCE := participants donations income-totals expense-totals
CODE_SCHEMES := campaign-funding-sources campaign-expense-purposes campaign-participant-types
TAXOUT := ../../datasets/current/taxonomies

.PHONY: all finance clean FORCE
all: $(OUT)/elections.trig $(OUT)/contests.trig $(OUT)/constituencies-geo.trig finance

ifeq ($(wildcard $(FINANCE_SOURCES)),$(FINANCE_SOURCES))
finance: $(OUT)/campaign-finance.trig $(OUT)/campaign-expenses.trig $(CODE_SCHEMES:%=$(TAXOUT)/%.trig)
else
finance:
	@echo "campaign finance skipped: harvest $(FINANCE_SOURCES) first (.claude/skills/harvest-vrk/)" >&2
endif

# --- fetch (always fresh) ---
$(CACHE)/%.json: FORCE
	@mkdir -p $(CACHE)
	$(eval y := $(word 1,$(subst -, ,$*)))
	$(eval l := $(word 2,$(subst -, ,$*)))
	./fetch-arcgis.sh $(if $(filter geo,$(l)),$(smd1_$(y)) $@ geometry,$($(l)_$(y)) $@)

# --- normalize: flatten the per-constituency wide records, resolve candidates,
# parties and constituencies; boundaries straight to the geo TriG ---
$(TABLES:%=$(CACHE)/%.csv) $(CACHE)/constituencies-geo.trig &: $(SOURCES) data/elections.csv data/party-aliases.csv data/person-aliases.csv $(PERSONS) $(ALIGNMENTS) $(PARTIES) $(CONSTITUENCIES)
	uv run --project ../tools ltlod-elections --base $(BASE) --elections data/elections.csv \
		--years "$(ELECTIONS)" --cache $(CACHE) --persons $(PERSONS) --alignments $(ALIGNMENTS) --parties $(PARTIES) \
		--constituencies $(CONSTITUENCIES) --party-aliases data/party-aliases.csv --person-aliases data/person-aliases.csv \
		--simplify $(SIMPLIFY) --geo $(CACHE)/constituencies-geo.trig \
		--report $(CACHE)/unmatched.csv

# every election in data/elections.csv gets a document (campaign finance reaches back
# to 2008); ELECTIONS only limits the results above
$(CACHE)/elections.csv: data/elections.csv
	@mkdir -p $(CACHE)
	cp $< $@

# campaign finance: participants, legal-person rows, natural-person aggregates, codes
$(FINANCE:%=$(CACHE)/finance/%.csv) $(CACHE)/finance/expenses.csv $(CACHE)/finance/codes.csv &: $(FINANCE_SOURCES) $(CACHE)/candidates.csv data/elections.csv data/party-aliases.csv data/person-aliases.csv $(PERSONS) $(ALIGNMENTS) $(PARTIES)
	@mkdir -p $(CACHE)/finance
	uv run --project ../tools ltlod-campaign-finance --base $(BASE) --types "$(CAMPAIGN_TYPES)" \
		--income data/vrk-pajamos.csv --expenses data/vrk-islaidos.csv \
		--candidates data/vrk-kandidatai-seimas.csv --elections data/elections.csv \
		--results $(CACHE)/candidates.csv --persons $(PERSONS) --alignments $(ALIGNMENTS) --parties $(PARTIES) \
		--party-aliases data/party-aliases.csv --person-aliases data/person-aliases.csv \
		--out $(CACHE)/finance --report $(CACHE)/finance/unmatched.csv

$(CODE_SCHEMES:%=$(CACHE)/finance/%.csv): $(CACHE)/finance/%.csv: $(CACHE)/finance/codes.csv
	awk -F, -v s=$* 'NR==1 || $$1 == s' $< > $@

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ---
$(OUT)/elections.trig: $(CACHE)/elections.nt mappings/elections.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/elections.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/elections.csv) - 1))

$(OUT)/contests.trig: $(TABLES:%=$(CACHE)/%.nt) mappings/contests.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/contests.rq $(BASE) $(TABLES:%=$(CACHE)/%.nt) > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/contests.csv) - 1))

$(OUT)/constituencies-geo.trig: $(CACHE)/constituencies-geo.trig
	@mkdir -p $(OUT)
	$(LIB)/relativize.sh $(BASE) < $< > $@

$(OUT)/campaign-finance.trig: $(FINANCE:%=$(CACHE)/finance/%.nt) mappings/campaign-finance.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/campaign-finance.rq $(BASE) $(FINANCE:%=$(CACHE)/finance/%.nt) > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/finance/participants.csv) - 1))

# overlay onto the campaign-finance documents (no document triples): SHACL only, as CI
# does for alignments/*-geo overlays; gitignored bulk output
$(OUT)/campaign-expenses.trig: $(CACHE)/finance/expenses.nt mappings/campaign-expenses.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/campaign-expenses.rq $(BASE) $< > $@
	$(LIB)/shacl.sh ../shapes/elections.ttl $@ $(BASE)

$(TAXOUT)/campaign-%.trig: $(CACHE)/finance/campaign-%.nt mappings/campaign-codes.rq
	$(LIB)/graphify.sh mappings/campaign-codes.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
