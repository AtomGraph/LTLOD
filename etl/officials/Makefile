include ../config.mk

# Public officials beyond the Seimas: the President, the Prime Minister and the
# ministers, mayors (Wikidata, CC0) and MEPs elected in Lithuania (European Parliament
# open data, CC BY 4.0), as persons with org:Membership offices since 1990. Persons
# who also held a Seimas seat keep their persons/{asmens_id}/ document (resolved
# through seimas/alignments.trig), so this runs after seimas and admin-units, and
# before declarations, whose non-Seimas declarants (ministers, mayors, MEPs, the
# President) resolve against persons.trig here.
#
# Vice-ministers (VMI group 519) and municipal council members have no scriptable
# source: lrv.lt and vrk.lt are behind a Cloudflare bot challenge, and Wikidata
# barely covers either (see the PR/README notes).

CACHE := cache
OUT := ../../datasets/current/officials
TAXOUT := ../../datasets/current/taxonomies
CUR := ../../datasets/current
GEO := --municipalities $(CUR)/admin-units/municipalities.trig --alignments $(CUR)/admin-units/alignments.trig

.PHONY: all clean FORCE
all: $(OUT)/persons.trig $(TAXOUT)/official-position-types.trig

# --- fetch (always fresh): WDQS office statements + EP API mandates ---
$(CACHE)/.fetched: FORCE data/positions.csv
	@mkdir -p $(CACHE)
	uv run --project ../tools ltlod-officials fetch --base $(BASE) --positions data/positions.csv \
		$(GEO) --out-dir $(CACHE)
	touch $@

# --- normalize: resolve persons (Seimas reuse), flatten to CSV ---
$(CACHE)/persons.csv $(CACHE)/offices.csv $(CACHE)/roles.csv &: $(CACHE)/.fetched \
		$(CUR)/seimas/persons.trig $(CUR)/seimas/alignments.trig
	uv run --project ../tools ltlod-officials normalize --base $(BASE) --positions data/positions.csv \
		$(GEO) --cache $(CACHE) \
		--persons $(CUR)/seimas/persons.trig --seimas-alignments $(CUR)/seimas/alignments.trig \
		--persons-out $(CACHE)/persons.csv --offices-out $(CACHE)/offices.csv --roles-out $(CACHE)/roles.csv

$(CACHE)/%.nt: $(CACHE)/%.csv
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# --- graphify + validate ---
$(OUT)/persons.trig: $(CACHE)/persons.nt $(CACHE)/offices.nt mappings/officials.rq
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/officials.rq $(BASE) $(CACHE)/persons.nt $(CACHE)/offices.nt > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(wc -l < $(CACHE)/persons.csv) - 1))

$(TAXOUT)/official-position-types.trig: $(CACHE)/roles.nt mappings/position-types.rq
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh mappings/position-types.rq $(BASE) $< > $@
	$(LIB)/validate.sh $@ $(BASE) $$(($$(cut -d, -f2 $(CACHE)/roles.csv | sort -u | wc -l) - 1))

clean:
	rm -rf $(CACHE)

FORCE:
