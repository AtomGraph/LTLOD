# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | declarations | legal-entities | taxonomies | calendar
#   make sodra      # opt-in: needs the browser-harvested Sodra zips in sodra/data/

DOMAINS := taxonomies calendar admin-units seimas declarations legal-entities sodra

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# declarations after seimas — declarants resolve against persons.trig
all: taxonomies calendar admin-units seimas declarations legal-entities

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
