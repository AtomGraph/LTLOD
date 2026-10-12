<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize the Seimas vote feeds to source-shaped RDF/XML rows, one per vote.
  The input merges three per-id feed levels under one wrapper element:
  - p2b.ad_sp_eiga (per sitting): the agenda items (EigosKlausimas) of a sitting;
  - p2b.ad_sp_klausimo_svarstymo_eiga (per agenda item): the item's course of
    consideration, whose Balsavimas events carry the vote id and voting method;
  - p2b.ad_sp_balsavimo_rezultatai (per vote): totals + one row per member.
  Each vote row is joined (via keys) to its event, agenda item and sitting, so
  the mapping needs no joins. The individual results become multi-valued
  per-choice columns (uz_/pries_/susilaike_asmens_id) holding member ids; a
  member who did not vote has an empty kaip_balsavo and is left out.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<xsl:param name="base"/>
<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<xsl:key name="item" match="EigosKlausimas" use="@svarstomo_klausimo_id"/>
<xsl:key name="event" match="SvarstymoEigosĮvykis[@balsavimo_id != '']" use="@balsavimo_id"/>

<!-- transliteration tables for slug generation (same as calendar.xsl) -->
<xsl:variable name="upper">AĄBCČDEĘĖFGHIĮYJKLMNOPRSŠTUŲŪVZŽ</xsl:variable>
<xsl:variable name="lower">aąbcčdeęėfghiįyjklmnoprsštuųūvzž</xsl:variable>
<xsl:variable name="diacritics">ąčęėįšųūž</xsl:variable>
<xsl:variable name="ascii">aceeisuuz</xsl:variable>

<xsl:template name="prop">
    <xsl:param name="name"/>
    <xsl:param name="value"/>
    <xsl:if test="string($value) != ''">
        <xsl:element name="p:{$name}" namespace="{concat($base, '#')}">
            <xsl:value-of select="$value"/>
        </xsl:element>
    </xsl:if>
</xsl:template>

<!-- lowercase, strip diacritics and punctuation, spaces to dashes -->
<xsl:template name="slug">
    <xsl:param name="value"/>
    <xsl:variable name="lowered" select="translate($value, $upper, $lower)"/>
    <xsl:variable name="asciified" select="translate($lowered, $diacritics, $ascii)"/>
    <xsl:value-of select="translate(normalize-space(translate($asciified, '„“&quot;().,', '')), ' ', '-')"/>
</xsl:template>

<xsl:template match="/">
    <rdf:RDF>
        <xsl:apply-templates select="//SeimoNariųBalsavimas[BendriBalsavimoRezultatai]"/>
    </rdf:RDF>
</xsl:template>

<xsl:template match="SeimoNariųBalsavimas">
    <!-- an item can list the same vote more than once; the first event wins -->
    <xsl:variable name="event" select="key('event', @balsavimo_id)[1]"/>
    <xsl:variable name="item" select="key('item', $event/../@svarstomo_klausimo_id)[1]"/>
    <xsl:variable name="totals" select="BendriBalsavimoRezultatai"/>
    <xsl:variable name="method" select="normalize-space($event/@balsavimo_tipas)"/>
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">balsavimo_id</xsl:with-param><xsl:with-param name="value" select="@balsavimo_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">posedzio_id</xsl:with-param><xsl:with-param name="value" select="$item/../@posėdžio_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">klausimo_id</xsl:with-param><xsl:with-param name="value" select="$item/@svarstomo_klausimo_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">klausimo_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space($item/@pavadinimas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">stadija</xsl:with-param><xsl:with-param name="value" select="normalize-space($item/@stadija)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">balsavimo_tipas</xsl:with-param><xsl:with-param name="value" select="$method"/></xsl:call-template>
        <xsl:call-template name="prop">
            <xsl:with-param name="name">balsavimo_tipo_slug</xsl:with-param>
            <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="$method"/></xsl:call-template></xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">balsavimo_laikas</xsl:with-param><xsl:with-param name="value" select="normalize-space($totals/@balsavimo_laikas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">balsavo</xsl:with-param><xsl:with-param name="value" select="$totals/@balsavo"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">uz</xsl:with-param><xsl:with-param name="value" select="$totals/@už"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">pries</xsl:with-param><xsl:with-param name="value" select="$totals/@prieš"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">susilaike</xsl:with-param><xsl:with-param name="value" select="$totals/@susilaikė"/></xsl:call-template>
        <xsl:for-each select="IndividualusBalsavimoRezultatas[@kaip_balsavo = 'Už']">
            <xsl:call-template name="prop"><xsl:with-param name="name">uz_asmens_id</xsl:with-param><xsl:with-param name="value" select="@asmens_id"/></xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="IndividualusBalsavimoRezultatas[@kaip_balsavo = 'Prieš']">
            <xsl:call-template name="prop"><xsl:with-param name="name">pries_asmens_id</xsl:with-param><xsl:with-param name="value" select="@asmens_id"/></xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="IndividualusBalsavimoRezultatas[@kaip_balsavo = 'Susilaikė']">
            <xsl:call-template name="prop"><xsl:with-param name="name">susilaike_asmens_id</xsl:with-param><xsl:with-param name="value" select="@asmens_id"/></xsl:call-template>
        </xsl:for-each>
    </rdf:Description>
</xsl:template>

</xsl:stylesheet>
