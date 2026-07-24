# Shared ETL configuration. Override on the command line, e.g.:
#   make BASE=https://linkeddata.lt/
# Committed datasets/current/ are base-RELATIVE (no @base): BASE only labels the
# transient absolute IRIs that relativize.sh strips on write, so the committed
# output is identical for any BASE. The base is (re)applied at load/parse time.
BASE ?= https://localhost:4443/
JENA_HOME ?= /Users/martynas/WebRoot/apache-jena-6.1.0
CSV2RDF_JAR ?= /Users/martynas/WebRoot/CSV2RDF/target/csv2rdf-jar-with-dependencies.jar
LIB := $(dir $(lastword $(MAKEFILE_LIST)))lib

export BASE JENA_HOME CSV2RDF_JAR
