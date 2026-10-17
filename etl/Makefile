# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | legal-entities | taxonomies | calendar

DOMAINS := taxonomies calendar admin-units seimas legal-entities

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
all: taxonomies calendar admin-units seimas legal-entities

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
