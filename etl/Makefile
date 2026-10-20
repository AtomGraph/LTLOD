# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | officials | declarations | legal-entities | facilities | procurement | taxonomies | calendar | elections

DOMAINS := taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# officials after seimas and admin-units — reuses Seimas persons, links mayors to municipalities
# declarations after seimas and officials — declarants resolve against both persons files
# elections after seimas — candidates, parties and constituencies resolve against it
# procurement last — contracts link to calendar days and legal entities (by bare JAR code)
all: taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
