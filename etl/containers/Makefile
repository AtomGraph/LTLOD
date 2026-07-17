include ../config.mk

OUT := ../../datasets/current/containers

.PHONY: all clean FORCE

all: $(OUT)/containers.trig

# no source data — the container list lives in the mapping's VALUES block;
# FORCE because the output depends on $(BASE)
$(OUT)/containers.trig: mappings/containers.rq FORCE
	@mkdir -p $(OUT)
	$(LIB)/graphify.sh mappings/containers.rq $(BASE) > $@
	$(LIB)/validate.sh $@ 9

clean:

FORCE:
