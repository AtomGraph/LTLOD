# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | declarations | legal-entities | vtek | taxonomies | calendar

DOMAINS := taxonomies calendar admin-units seimas declarations legal-entities vtek

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# declarations after seimas — declarants resolve against persons.trig
# vtek last — resolves persons, institutions (legal-entities) and Seimas units; offline
# (browser-harvested sources, see .claude/skills/harvest-vtek/)
all: taxonomies calendar admin-units seimas declarations legal-entities vtek

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
