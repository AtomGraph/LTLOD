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
exclude-result-prefixes="#all">

    <xsl:import href="../../../../org/graphity/ldp/provider/xslt/Resource.xsl"/>
    
    <xsl:output method="xhtml" encoding="UTF-8" indent="yes" omit-xml-declaration="yes" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd" doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN" media-type="application/xhtml+xml"/>

    <xsl:key name="resources-by-topic" match="*[@rdf:about] | *[@rdf:nodeID]" use="foaf:topic/@rdf:resource"/>
    <xsl:key name="resources-by-primary-topic-of" match="*[@rdf:about] | *[@rdf:nodeID]" use="foaf:isPrimaryTopicOf/@rdf:resource"/>

    <xsl:template match="/">
	<html xmlns:og="&og;" xmlns:fb="&fb;">
	    <head>
		<title>
		    <xsl:apply-templates mode="gldp:TitleMode"/>
		</title>
		<base href="{$base-uri}" />
		
		<xsl:for-each select="key('resources', $base-uri, $ont-model)">
		    <meta name="author" content="{dct:creator/@rdf:resource}"/>
		    <meta name="description" content="{dct:description}" xml:lang="{dct:description/@xml:lang}" lang="{dct:description/@xml:lang}"/>
		</xsl:for-each>
		<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
		
		<link href="static/css/bootstrap.css" rel="stylesheet"/>
		<link href="static/css/bootstrap-responsive.css" rel="stylesheet"/>
		
		<style type="text/css">
		    <![CDATA[
			body { padding-top: 60px; padding-bottom: 40px; }
			form.form-inline { margin: 0; }
			ul.inline { margin-left: 0; }
			.inline li { display: inline; }
			.well-small { background-color: #FAFAFA ; }
			textarea#query-string { font-family: monospace; }
		    ]]>
		</style>
		
		<xsl:apply-templates mode="gldp:ScriptMode"/>
      	    </head>
	    <body>
		<div id="fb-root"></div>
		<script type="text/javascript"><![CDATA[(function(d, s, id) {
		var js, fjs = d.getElementsByTagName(s)[0];
		if (d.getElementById(id)) return;
		js = d.createElement(s); js.id = id;
		js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
		fjs.parentNode.insertBefore(js, fjs);
		}(document, 'script', 'facebook-jssdk'));]]></script>

		<div class="navbar navbar-fixed-top">
		    <div class="navbar-inner">
			<div class="container-fluid">    
			    <xsl:apply-templates select="." mode="gldp:HeaderMode"/>
			</div>
		    </div>
		</div>

		<div class="container-fluid">
		    <div class="row-fluid">
			<xsl:apply-templates/>
		    </div>		    
		    
		    <div class="footer">
			<xsl:apply-templates select="." mode="gldp:FooterMode"/>
		    </div>
		</div>
	    </body>
	</html>
    </xsl:template>
    
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

    <xsl:template match="rdf:RDF">
	<div class="span8">
	    <xsl:choose>
		<xsl:when test="$mode = '&g;ListMode'">
		    <xsl:apply-templates select="." mode="g:ListMode"/>
		</xsl:when>
		<xsl:when test="$mode = '&g;TableMode'">
		    <xsl:apply-templates select="." mode="g:TableMode"/>
		</xsl:when>
		<xsl:when test="$mode = '&g;InputMode'">
		    <xsl:apply-templates select="." mode="g:InputMode"/>
		    
		    <xsl:apply-templates select="." mode="g:StmtInputMode"/>
		</xsl:when>
		<xsl:otherwise>
		    <xsl:apply-templates select="key('resources', $absolute-path)"/>

		    <xsl:apply-templates select="key('resources-by-primary-topic-of', $absolute-path)"/>

		    <!-- apply all other URI resources -->
		    <xsl:apply-templates select="*[not(@rdf:about = $absolute-path)][not(foaf:isPrimaryTopicOf/@rdf:resource = $absolute-path)][not(key('predicates-by-object', @rdf:nodeID))]"/>
		</xsl:otherwise>
	    </xsl:choose>
	</div>
	
	<div class="span4">
	    <xsl:for-each-group select="*/*" group-by="concat(namespace-uri(.), local-name(.))">
		<xsl:sort select="g:label(xs:anyURI(concat(namespace-uri(.), local-name(.))), /, $lang)" data-type="text" order="ascending" lang="{$lang}"/>
		<xsl:apply-templates select="current-group()[1]" mode="gldp:SidebarNavMode"/>
	    </xsl:for-each-group>
	</div>
    </xsl:template>

    <xsl:template match="*[*][@rdf:about] | *[*][@rdf:nodeID]" mode="gldp:HeaderMode" priority="1">
	<div class="well">
	    <xsl:apply-templates mode="gldp:HeaderImageMode"/>

	    <xsl:apply-templates select="@rdf:about | @rdf:nodeID" mode="gldp:HeaderMode"/>

	    <xsl:apply-templates select="@rdf:about | @rdf:nodeID" mode="g:DescriptionMode"/>

	    <div class="pull-right">
		<fb:like href="{@rdf:about}" send="true" layout="button_count" width="100" show_faces="false"></fb:like>
	    </div>

	    <!-- xsl:apply-templates? -->
	    <xsl:if test="rdf:type">
		<ul class="inline">
		    <xsl:apply-templates select="rdf:type" mode="gldp:HeaderMode">
			<xsl:sort select="g:label(@rdf:resource | @rdf:nodeID, /, $lang)" data-type="text" order="ascending" lang="{$lang}"/>
		    </xsl:apply-templates>
		</ul>
	    </xsl:if>
	</div>
    </xsl:template>

    <!-- PERSON -->

    <xsl:template match="foaf:Person[@rdf:about] | *[rdf:type/@rdf:resource = '&foaf;Person'][@rdf:about]">
	<xsl:apply-imports/>

	<h3>Straipsniai</h3>

	<xsl:variable name="articles" select="key('resources-by-topic', @rdf:about)"/>
	<xsl:variable name="predicates" as="element()*">
	    <xsl:for-each-group select="$articles/*" group-by="concat(namespace-uri(.), local-name(.))">
		<xsl:sort select="g:label(xs:anyURI(concat(namespace-uri(.), local-name(.))), /, $lang)" data-type="text" order="ascending" lang="{$lang}"/>
		<xsl:sequence select="current-group()[1]"/>
	    </xsl:for-each-group>
	</xsl:variable>
	<table class="table table-bordered table-striped">
	    <thead>
		<tr>
		    <th>
			<xsl:apply-templates select="key('resources', '&dct;title', document('&dct;'))/@rdf:about" mode="g:LabelMode"/>
		    </th>

		    <xsl:apply-templates select="$predicates" mode="gldp:TableHeaderMode"/>
		</tr>
	    </thead>
	    <tbody>
		<xsl:apply-templates select="$articles" mode="g:TableMode">
		    <xsl:with-param name="predicates" select="$predicates"/>
		    <xsl:sort select="xs:date(dct:issued)" order="descending"/>
		</xsl:apply-templates>
	    </tbody>
	</table>
    </xsl:template>

    <xsl:template match="foaf:topic" mode="g:TableHeaderMode"/>
    
    <xsl:template match="foaf:topic" mode="g:TableMode"/>

    <!-- hide articles from default view -->
    
    <xsl:template match="*[foaf:topic][@rdf:about]"/>
    
    <xsl:template match="foaf:Person/foaf:page | *[rdf:type/@rdf:resource = '&foaf;Person']/foaf:page" mode="gldp:PropertyListMode"/>

    <!--
    <xsl:template match="@rdf:about" mode="g:LabelMode">
	<xsl:copy-of select="document('translations.rdf')"/>
	!!<xsl:value-of select="key('resources', '&foaf;Person', document('translations.rdf'))/rdfs:label[lang($lang)]"/>!!
    </xsl:template>
    -->

</xsl:stylesheet>