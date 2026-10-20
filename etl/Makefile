# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | declarations | legal-entities | procurement | taxonomies | calendar

DOMAINS := taxonomies calendar admin-units seimas declarations legal-entities procurement

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# declarations after seimas — declarants resolve against persons.trig
# procurement last — contracts link to calendar days and legal entities (by bare JAR code)
all: taxonomies calendar admin-units seimas declarations legal-entities procurement

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
