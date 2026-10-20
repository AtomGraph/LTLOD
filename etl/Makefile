# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | officials | declarations | legal-entities | facilities | procurement | vtek | taxonomies | calendar | elections
#   make sodra      # opt-in: needs the browser-harvested Sodra zips in sodra/data/

DOMAINS := taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement vtek sodra

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# officials after seimas and admin-units — reuses Seimas persons, links mayors to municipalities
# declarations after seimas and officials — declarants resolve against both persons files
# elections after seimas — candidates, parties and constituencies resolve against it
# procurement after legal-entities — contracts link to calendar days and legal entities (by bare JAR code)
# vtek last — resolves persons, institutions (legal-entities) and Seimas units; offline
# (browser-harvested sources, see .claude/skills/harvest-vtek/)
all: taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement vtek

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
