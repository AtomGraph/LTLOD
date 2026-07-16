# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | legal-entities | taxonomies

DOMAINS := taxonomies admin-units seimas legal-entities

.PHONY: all clean $(DOMAINS)

# taxonomies first — instance data references the concepts
all: taxonomies admin-units seimas legal-entities

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
