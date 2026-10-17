include ../config.mk

CACHE := cache
OUT := ../../datasets/current/calendar
TAXOUT := ../../datasets/current/taxonomies

.PHONY: all clean FORCE
all: $(OUT)/calendar.trig $(TAXOUT)/holidays.trig

# the static CSV never refetches, so its normalized form must invalidate when
# BASE changes (same stamp as etl/taxonomies/Makefile)
$(CACHE)/.base: FORCE
	@mkdir -p $(CACHE)
	@echo "$(BASE)" | cmp -s - $@ || echo "$(BASE)" > $@

$(CACHE)/holidays.nt: data/holidays.csv $(CACHE)/.base
	$(LIB)/csv2rdf.sh $< $(BASE) > $@

# The days are generated, the holiday rows mark them. FORCE'd: the range ends
# with next year, so the output moves with the build date.
$(OUT)/calendar.trig: mappings/calendar.rq $(CACHE)/holidays.nt FORCE
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) $(CACHE)/holidays.nt > $@
	$(LIB)/validate.sh $@ $(BASE)

# public holiday concepts (taxonomies/holidays/), from the same CSV
$(TAXOUT)/holidays.trig: mappings/holidays.rq $(CACHE)/holidays.nt
	@mkdir -p $(TAXOUT)
	$(LIB)/graphify.sh $< $(BASE) $(CACHE)/holidays.nt > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:
	rm -rf $(CACHE)

FORCE:
