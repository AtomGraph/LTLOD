include ../config.mk

# VMI annual property declarations (FR0001) of Seimas members, ministers, the President,
# MEPs, vice-ministers and mayors. There is no scripted fetch:
# vmi.lt is behind a Cloudflare bot challenge and rejects datacenter/VPN IPs, so the
# source is harvested in a real browser once a year (harvest.js; the procedure, also
# for Claude in Chrome, is .claude/skills/harvest-declarations/SKILL.md) into the
# committed data/vmi-fr0001.json, which is this domain's source of truth.
# Declarants resolve to Seimas persons and, for the other groups, to the officials of
# etl/officials/ (ministers, mayors, MEPs, the President), so this runs after both;
# vice-ministers stay unmatched (no source lists them).

CACHE := cache
OUT := ../../datasets/current/declarations
PERSONS := ../../datasets/current/seimas/persons.trig
OFFICIALS := ../../datasets/current/officials/persons.trig
# schema:deathDate (Wikidata) for the matcher's lifetime guard
ALIGNMENTS := ../../datasets/current/seimas/alignments.trig
CATEGORIES := ../taxonomies/data/asset-categories.csv

.PHONY: all clean
all: $(OUT)/declarations.trig

# --- normalize: resolve declarants to persons/{slug}/, flatten to CSV ---
$(CACHE)/declarations.csv $(CACHE)/items.csv &: data/vmi-fr0001.json data/aliases.csv $(PERSONS) $(OFFICIALS) $(ALIGNMENTS) $(CATEGORIES)
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-declarations --base $(BASE) --persons $(PERSONS) \
		--officials $(OFFICIALS) --alignments $(ALIGNMENTS) \
		--categories $(CATEGORIES) --input $< --aliases data/aliases.csv \
		--declarations $(CACHE)/declarations.csv --items $(CACHE)/items.csv \
		--report $(CACHE)/unmatched.csv

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ---
$(OUT)/declarations.trig: $(CACHE)/declarations.nt $(CACHE)/items.nt mappings/declarations.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/declarations.rq $(BASE) $(CACHE)/declarations.nt $(CACHE)/items.nt > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(cut -d, -f1 $(CACHE)/declarations.csv | sort -u | wc -l) - 1))

clean:
	rm -rf $(CACHE)
