include ../config.mk

OUT := ../../datasets/current/calendar

.PHONY: all clean FORCE
all: $(OUT)/calendar.trig

# Self-contained mapping (no input data). FORCE'd: the range ends with next year,
# so the output moves with the build date.
$(OUT)/calendar.trig: mappings/calendar.rq FORCE
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh $< $(BASE) > $@
	$(LIB)/validate.sh $@ $(BASE)

clean:

FORCE:
