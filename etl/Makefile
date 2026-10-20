# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | declarations | legal-entities | taxonomies | calendar | land-acquisitions

DOMAINS := taxonomies calendar admin-units seimas declarations legal-entities land-acquisitions

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# declarations after seimas — declarants resolve against persons.trig
# land-acquisitions after admin-units — municipalities resolve against municipalities.trig
all: taxonomies calendar admin-units seimas declarations legal-entities land-acquisitions

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
