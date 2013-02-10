<?xml version="1.0" encoding="UTF-8"?>
<!--
Copyright (C) 2012 Martynas Jusevičius <martynas@graphity.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY java "http://xml.apache.org/xalan/java/">
    <!ENTITY g "http://graphity.org/ontology/">
    <!ENTITY gldp "http://ldp.graphity.org/ontology/">
    <!ENTITY rdf "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <!ENTITY rdfs "http://www.w3.org/2000/01/rdf-schema#">
    <!ENTITY owl "http://www.w3.org/2002/07/owl#">
    <!ENTITY xsd "http://www.w3.org/2001/XMLSchema#">
    <!ENTITY ldp "http://www.w3.org/ns/ldp#">
    <!ENTITY dct "http://purl.org/dc/terms/">
    <!ENTITY foaf "http://xmlns.com/foaf/0.1/">
    <!ENTITY sioc "http://rdfs.org/sioc/ns#">
    <!ENTITY sp "http://spinrdf.org/sp#">
    <!ENTITY list "http://jena.hpl.hp.com/ARQ/list#">
    <!ENTITY gr "http://purl.org/goodrelations/v1#">
    <!ENTITY skos "http://www.w3.org/2004/02/skos/core#">
    <!ENTITY xhv "http://www.w3.org/1999/xhtml/vocab#">
    <!ENTITY ref "http://semantic-web.dk/ontologies/refrigeration#">
]>
<xsl:stylesheet version="2.0"
xmlns="http://www.w3.org/1999/xhtml"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:xhtml="http://www.w3.org/1999/xhtml"
xmlns:xs="http://www.w3.org/2001/XMLSchema"
xmlns:g="&g;"
xmlns:gldp="&gldp;"
xmlns:rdf="&rdf;"
xmlns:rdfs="&rdfs;"
xmlns:owl="&owl;"
xmlns:ldp="&ldp;"
xmlns:dct="&dct;"
xmlns:foaf="&foaf;"
xmlns:sioc="&sioc;"
xmlns:sp="&sp;"
xmlns:list="&list;"
xmlns:gr="&gr;"
xmlns:skos="&skos;"
xmlns:xhv="&xhv;"
xmlns:ref="&ref;"
exclude-result-prefixes="#all">

    <xsl:import href="../../../../org/graphity/ldp/provider/xslt/Resource.xsl"/>
    
    <xsl:output method="xhtml" encoding="UTF-8" indent="yes" omit-xml-declaration="yes" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd" doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN" media-type="application/xhtml+xml"/>

    <xsl:template match="/" mode="gldp:HeaderMode">
	<xsl:apply-imports/>

	<div class="nav-collapse pull-right">
	    <ul class="nav">
		<li>
		    <a href="https://twitter.com/LTLOD">Twitter</a>
		</li>
		<li>
		    <a href="https://github.com/pumba-lt/LTLOD">GitHub</a>
		</li>
		<li>
		    <a href="http://dydra.com/graphity/lithuanian-politics/sparql">SPARQL endpoint</a>
		</li>		
	    </ul>
	</div>
    </xsl:template>
    
</xsl:stylesheet>