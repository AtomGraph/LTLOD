# Shared ETL configuration. Override on the command line, e.g.:
#   make BASE=https://my-ldh-instance.example/
BASE ?= https://linkeddata.lt/
JENA_HOME ?= /Users/martynas/WebRoot/apache-jena-6.1.0
CSV2RDF_JAR ?= /Users/martynas/WebRoot/CSV2RDF/target/csv2rdf-jar-with-dependencies.jar
LIB := $(dir $(lastword $(MAKEFILE_LIST)))lib

export BASE JENA_HOME CSV2RDF_JAR
