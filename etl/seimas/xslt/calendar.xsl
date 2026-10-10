<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize the Seimas calendar feeds to source-shaped RDF/XML rows:
  terms (p2b.ad_seimo_kadencijos), sessions (p2b.ad_seimo_sesijos, one document
  per term) and plenary sittings (p2b.ad_seimo_posedziai, one document per
  session). The per-id documents are merged under a single wrapper element
  before this runs, so the input may hold many <SeimoInformacija> roots.
  The child feeds wrap their rows in a bare parent element carrying only its id
  (<SeimoKadencija kadencijos_id> around sessions, <SeimoSesija sesijos_id>
  around sittings), so rows are told apart from wrappers by @pavadinimas.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<xsl:param name="base"/>
<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<!-- transliteration tables for slug generation (same as nariai.xsl) -->
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
        <xsl:apply-templates select="//SeimoKadencija[@pavadinimas] | //SeimoSesija[@pavadinimas] | //SeimoPosėdis"/>
    </rdf:RDF>
</xsl:template>

<xsl:template match="SeimoKadencija">
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">kadencijos_id</xsl:with-param><xsl:with-param name="value" select="@kadencijos_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">kadencijos_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pavadinimas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">data_nuo</xsl:with-param><xsl:with-param name="value" select="@data_nuo"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">data_iki</xsl:with-param><xsl:with-param name="value" select="@data_iki"/></xsl:call-template>
    </rdf:Description>
</xsl:template>

<!-- pavadinimas is "5 eilinė" / "neeilinė": the number is the ordinal within the
     term, the rest the session type ("eilinė sesija" / "neeilinė sesija") -->
<xsl:template match="SeimoSesija">
    <xsl:variable name="type" select="concat(normalize-space(translate(@pavadinimas, '0123456789', '')), ' sesija')"/>
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">sesijos_id</xsl:with-param><xsl:with-param name="value" select="@sesijos_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">sesijos_kadencijos_id</xsl:with-param><xsl:with-param name="value" select="../@kadencijos_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">sesijos_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pavadinimas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">numeris</xsl:with-param><xsl:with-param name="value" select="@numeris"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">data_nuo</xsl:with-param><xsl:with-param name="value" select="@data_nuo"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">data_iki</xsl:with-param><xsl:with-param name="value" select="@data_iki"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">veiklos_tipas</xsl:with-param><xsl:with-param name="value" select="$type"/></xsl:call-template>
        <xsl:call-template name="prop">
            <xsl:with-param name="name">veiklos_tipo_slug</xsl:with-param>
            <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="$type"/></xsl:call-template></xsl:with-param>
        </xsl:call-template>
    </rdf:Description>
</xsl:template>

<!-- pradžia/pabaiga are local "yyyy-mm-dd hh:mm" (empty when unknown); sittings
     before ~1998 carry only pabaiga at 00:00, i.e. just the date -->
<xsl:template match="SeimoPosėdis">
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">posedzio_id</xsl:with-param><xsl:with-param name="value" select="@posėdžio_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">posedzio_sesijos_id</xsl:with-param><xsl:with-param name="value" select="../@sesijos_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">numeris</xsl:with-param><xsl:with-param name="value" select="@numeris"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">pradzia</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pradžia)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">pabaiga</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pabaiga)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">protokolo_nuoroda</xsl:with-param><xsl:with-param name="value" select="Protokolas/@protokolo_nuoroda"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">stenogramos_nuoroda</xsl:with-param><xsl:with-param name="value" select="Stenograma/@stenogramos_nuoroda"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">veiklos_tipas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@tipas)"/></xsl:call-template>
        <xsl:call-template name="prop">
            <xsl:with-param name="name">veiklos_tipo_slug</xsl:with-param>
            <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="normalize-space(@tipas)"/></xsl:call-template></xsl:with-param>
        </xsl:call-template>
    </rdf:Description>
</xsl:template>

</xsl:stylesheet>
