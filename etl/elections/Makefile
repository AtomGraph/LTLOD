include ../config.mk

# Seimas election results per single-member constituency (apygarda), from the VRK
# election-results map's public ArcGIS feature services (fetch-arcgis.sh says why not
# vrk.lt): both rounds of the single-member races, the party-list (multi-member) vote
# counted in each constituency, turnout, and the constituency boundaries. Candidates
# resolve to persons/ and nominating parties to parties/ (ltlod-elections), constituencies
# to the per-term constituencies/{kadencijos_id}-{nr}/ of the seimas domain.

CACHE := cache
OUT := ../../datasets/current/elections
PERSONS := ../../datasets/current/seimas/persons.trig
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

.PHONY: all clean FORCE
all: $(OUT)/elections.trig $(OUT)/contests.trig $(OUT)/constituencies-geo.trig

# --- fetch (always fresh) ---
$(CACHE)/%.json: FORCE
	@mkdir -p $(CACHE)
	$(eval y := $(word 1,$(subst -, ,$*)))
	$(eval l := $(word 2,$(subst -, ,$*)))
	./fetch-arcgis.sh $(if $(filter geo,$(l)),$(smd1_$(y)) $@ geometry,$($(l)_$(y)) $@)

# --- normalize: flatten the per-constituency wide records, resolve candidates,
# parties and constituencies; boundaries straight to the geo TriG ---
$(TABLES:%=$(CACHE)/%.csv) $(CACHE)/constituencies-geo.trig &: $(SOURCES) data/elections.csv data/party-aliases.csv data/person-aliases.csv $(PERSONS) $(PARTIES) $(CONSTITUENCIES)
	uv run --project ../tools ltlod-elections --base $(BASE) --elections data/elections.csv \
		--years "$(ELECTIONS)" --cache $(CACHE) --persons $(PERSONS) --parties $(PARTIES) \
		--constituencies $(CONSTITUENCIES) --party-aliases data/party-aliases.csv --person-aliases data/person-aliases.csv \
		--simplify $(SIMPLIFY) --geo $(CACHE)/constituencies-geo.trig \
		--report $(CACHE)/unmatched.csv

$(CACHE)/elections.csv: data/elections.csv
	@mkdir -p $(CACHE)
	awk -F, -v years=" $(ELECTIONS) " 'NR==1 || index(years, " " $$2 " ")' $< > $@

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ---
$(OUT)/elections.trig: $(CACHE)/elections.nt mappings/elections.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/elections.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $(words $(ELECTIONS))

$(OUT)/contests.trig: $(TABLES:%=$(CACHE)/%.nt) mappings/contests.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/contests.rq $(BASE) $(TABLES:%=$(CACHE)/%.nt) > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/contests.csv) - 1))

$(OUT)/constituencies-geo.trig: $(CACHE)/constituencies-geo.trig
	@mkdir -p $(OUT)
	$(LIB)/relativize.sh $(BASE) < $< > $@

clean:
	rm -rf $(CACHE)

FORCE:
