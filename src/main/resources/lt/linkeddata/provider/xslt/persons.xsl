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
    <!ENTITY og "http://ogp.me/ns#">
    <!ENTITY fb "http://ogp.me/ns/fb#">
    <!ENTITY dbpedia-owl "http://dbpedia.org/ontology/">
    <!ENTITY dis "http://semantic-web.dk/ontologies/disclosures#">
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
xmlns:og="&og;"
xmlns:fb="&fb;"
xmlns:dbpedia-owl="&dbpedia-owl;"
xmlns:dis="&dis;"
exclude-result-prefixes="#all">

    <xsl:key name="financial-disclosures-by-agent" match="dis:FinancialDisclosure | *[rdf:type/@rdf:resource = '&dis;FinancialDisclosure']" use="dis:agent/@rdf:resource"/>

    <xsl:template match="foaf:Person[@rdf:about] | *[rdf:type/@rdf:resource = '&foaf;Person'][@rdf:about]">
	<xsl:apply-imports/>

	<xsl:variable name="articles" select="key('resources-by-topic', @rdf:about)"/>
	<xsl:if test="$articles">
	    <h3>
		<!-- <a href="{@rdf:about}/articles"> -->
		<xsl:value-of select="key('resources', 'articles', document('translations.rdf'))/rdfs:label[lang($lang) or lang(substring-before($lang, '-'))]"/>
	    </h3>

	    <table class="table table-bordered table-striped">
		<xsl:variable name="predicates" as="element()*">
		    <xsl:for-each-group select="$articles/dct:title" group-by="concat(namespace-uri(.), local-name(.))">
			<xsl:sequence select="current-group()[1]"/>
		    </xsl:for-each-group>
		    <xsl:for-each-group select="$articles/dct:issued" group-by="concat(namespace-uri(.), local-name(.))">
			<xsl:sequence select="current-group()[1]"/>
		    </xsl:for-each-group>
		</xsl:variable>

		<thead>
		    <tr>
			<xsl:apply-templates select="$predicates" mode="g:TableHeaderMode"/>
		    </tr>
		</thead>
		<tbody>
		    <xsl:apply-templates select="$articles" mode="g:TableMode">
			<xsl:with-param name="predicates" select="$predicates"/>
			<xsl:sort select="xs:date(dct:issued)" order="descending"/>
			<xsl:sort select="dct:title"/>
		    </xsl:apply-templates>
		</tbody>
	    </table>
	</xsl:if>

	<xsl:variable name="financial-disclosures" select="key('financial-disclosures-by-agent', @rdf:about)"/>
	<xsl:if test="$financial-disclosures">
	    <h3>
		<xsl:value-of select="key('resources', 'financial-disclosures', document('translations.rdf'))/rdfs:label[lang($lang) or lang(substring-before($lang, '-'))]"/>
	    </h3>
	    
	    <table class="table table-bordered table-striped">
		<xsl:variable name="predicates" as="element()*">
		    <xsl:for-each-group select="$financial-disclosures/*" group-by="concat(namespace-uri(.), local-name(.))">
			<xsl:sort select="g:label(xs:anyURI(concat(namespace-uri(.), local-name(.))), /, $lang)" data-type="text" order="ascending" lang="{$lang}"/>
			<xsl:sequence select="current-group()[1]"/>
		    </xsl:for-each-group>
		</xsl:variable>
		<thead>
		    <tr>
			<xsl:apply-templates select="$predicates" mode="g:TableHeaderMode"/>
		    </tr>
		</thead>
		<tbody>
		    <xsl:apply-templates select="$financial-disclosures" mode="g:TableMode">
			<xsl:with-param name="predicates" select="$predicates"/>
			<xsl:sort select="xs:date(dct:date)" order="descending"/>
		    </xsl:apply-templates>
		</tbody>
	    </table>
	</xsl:if>

    </xsl:template>

    <!-- ARTICLES (PAGES) -->

    <xsl:template match="*[key('resources', foaf:topic/@rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']" mode="g:TableMode">
	<xsl:param name="predicates" as="element()*"/>

	<tr>
	    <xsl:variable name="subject" select="."/>
	    <xsl:for-each select="$predicates">
		<xsl:variable name="this" select="xs:anyURI(concat(namespace-uri(.), local-name(.)))" as="xs:anyURI"/>
		<xsl:variable name="predicate" select="$subject/*[concat(namespace-uri(.), local-name(.)) = $this]"/>
		<xsl:choose>
		    <xsl:when test="$predicate">
			<xsl:apply-templates select="$predicate" mode="g:TableMode"/>
		    </xsl:when>
		    <xsl:otherwise>
			<td></td>
		    </xsl:otherwise>
		</xsl:choose>
	    </xsl:for-each>
	</tr>
    </xsl:template>

    <xsl:template match="dct:title[key('resources', ../foaf:topic/@rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']" mode="g:TableMode">
	<td>
	    <a href="{../@rdf:about}">
		<xsl:value-of select="."/>
	    </a>
	</td>
    </xsl:template>

<!--
    <xsl:template match="foaf:topic[key('resources', @rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']" mode="g:TableHeaderMode"/>
    
    <xsl:template match="foaf:topic[key('resources', @rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']" mode="g:TableMode"/>
-->
    <!-- hide articles from default view -->
    
    <xsl:template match="*[key('resources', foaf:topic/@rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']"/>
    
    <xsl:template match="foaf:Person/foaf:page | *[rdf:type/@rdf:resource = '&foaf;Person']/foaf:page" mode="gldp:PropertyListMode"/>

    <!-- FINANCIAL DISCLOSURES -->
    
    <!-- hide disclosures from default view -->

    <xsl:template match="*[key('resources', dis:agent/@rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']" mode="g:TableMode">
	<xsl:param name="predicates" as="element()*"/>

	<tr>
	    <xsl:variable name="subject" select="."/>
	    <xsl:for-each select="$predicates">
		<xsl:variable name="this" select="xs:anyURI(concat(namespace-uri(.), local-name(.)))" as="xs:anyURI"/>
		<xsl:variable name="predicate" select="$subject/*[concat(namespace-uri(.), local-name(.)) = $this]"/>
		<xsl:choose>
		    <xsl:when test="$predicate">
			<xsl:apply-templates select="$predicate" mode="g:TableMode"/>
		    </xsl:when>
		    <xsl:otherwise>
			<td></td>
		    </xsl:otherwise>
		</xsl:choose>
	    </xsl:for-each>
	</tr>
    </xsl:template>

    <xsl:template match="*[key('resources', dis:agent/@rdf:resource)/rdf:type/@rdf:resource = '&foaf;Person']"/>
    
    <!-- OTHER RESOURCES -->
    
    <xsl:template match="*[*][@rdf:about] | *[*][@rdf:nodeID]" priority="0"/>

</xsl:stylesheet>