# LTLOD ETL — re-running any target always fetches current data from the live APIs.
# Usage:
#   make            # everything, in dependency order
#   make BASE=https://my-ldh-instance.example/   # custom base URI
#   make admin-units | seimas | officials | declarations | legal-entities | facilities | procurement | vtek | land-acquisitions | taxonomies | calendar | elections
#   make sodra            # opt-in: needs the browser-harvested Sodra zips in sodra/data/
#   make public-spending  # opt-in: ~46M-row public-sector invoice fetch (~40-90 min)

DOMAINS := taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement vtek land-acquisitions taxes insolvency eu-funds public-spending sodra

.PHONY: all clean $(DOMAINS)

# taxonomies and the calendar first — instance data references the concepts and days
# officials after seimas and admin-units — reuses Seimas persons, links mayors to municipalities
# declarations after seimas and officials — declarants resolve against both persons files
# elections after seimas — candidates, parties and constituencies resolve against it
# procurement after legal-entities — contracts link to calendar days and legal entities (by bare JAR code)
# vtek last — resolves persons, institutions (legal-entities) and Seimas units; offline
# (browser-harvested sources, see .claude/skills/harvest-vtek/)
# land-acquisitions after admin-units — municipalities resolve against municipalities.trig
# taxes after legal-entities — tax records link to legal entities (by bare JAR code) and
# calendar days/years; a plain Spinta fetch, so (unlike sodra) it is part of `all`
# insolvency after legal-entities and admin-units — proceedings link to legal entities and
# municipalities; a plain Spinta fetch, committed output
# eu-funds after legal-entities and admin-units — contracts link to beneficiaries/partners
# (by bare JAR code) and municipalities; a plain Spinta fetch, gitignored bulk output
# public-spending — NOT in `all`: a ~46M-row fetch (~40-90 min) of the public-sector invoice
# feeds, aggregated per buyer-supplier-year; run on demand (make -C etl public-spending)
all: taxonomies calendar admin-units seimas officials declarations legal-entities elections facilities procurement vtek land-acquisitions taxes insolvency eu-funds

$(DOMAINS):
	$(MAKE) -C $@ all

clean:
	@for d in $(DOMAINS); do $(MAKE) -C $$d clean; done
