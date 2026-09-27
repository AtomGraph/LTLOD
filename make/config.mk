# Settings for the canonical Makefile.

# install is this deployment's own: the canonical Makefile carries no install target
LOCAL_TARGETS := install

# files/client.xsl imports files/overrides.xsl, so both are staged for the SEF compile
SEF_EXTRA := files/overrides.xsl

# `make load` bulk-loads the ETL output straight into the end-user dataset
LOAD_STAGING := datasets/current

# never wipe datasets/current - that is ETL output, not LDH runtime state
DROP_PATHS := datasets/owner datasets/secretary fuseki ssl secrets uploads sef packages settings

include etl/config.mk    # for JENA_HOME (its BASE is unused here)
