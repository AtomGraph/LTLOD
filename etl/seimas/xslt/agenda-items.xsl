<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize the Seimas plenary agenda items to source-shaped RDF/XML rows, one per
  item considered at a sitting. The input merges three per-id feed levels under one
  wrapper element:
  - p2b.ad_sp_eiga (per sitting): the items considered (EigosKlausimas, keyed by
    svarstomo_klausimo_id), with stage and start time;
  - p2b.ad_sp_klausimo_svarstymo_eiga (per item): its course of consideration -
    speeches (Kalba, with the speaker's asmens_id), votes (Balsavimas) and the bills
    the item covers with their responsible committees (AtsakingiPadaliniai, by bill
    number with a revision suffix, e.g. "XIP-672(2)");
  - p2b.ad_sp_darbotvarke (per sitting): the planned agenda, whose item stages link
    the e-seimas document considered (dokumento_nuoroda). Joined on sitting +
    agenda number (+ stage when an item lists several); items of supplementary
    agendas are absent from this feed and get no document link.
  Multi-valued columns (projekto_nr, kalbetojo_asmens_id) hold one value per element.
  The bill number in the item title is extracted by the mapping (regex).
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<xsl:param name="base"/>
<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<xsl:key name="item" match="EigosKlausimas" use="@svarstomo_klausimo_id"/>
<xsl:key name="consideration" match="SeimoPosėdžioKlausimas" use="@svarstomo_klausimo_id"/>
<xsl:key name="agenda" match="DarbotvarkėsKlausimas" use="concat(../@posėdžio_id, '|', normalize-space(@numeris))"/>

<!-- transliteration tables for slug generation (same as calendar.xsl / votes.xsl) -->
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
        <!-- a group of items considered together ("Klausimų grupė: 1 - 12, 1 - 13") is listed
             once per agenda number under one id; the first listing wins -->
        <xsl:apply-templates select="/feeds/SeimoInformacija/SeimoPosėdis/EigosKlausimas[generate-id() = generate-id(key('item', @svarstomo_klausimo_id)[1])]"/>
    </rdf:RDF>
</xsl:template>

<xsl:template match="EigosKlausimas">
    <xsl:variable name="sitting" select="parent::SeimoPosėdis"/>
    <xsl:variable name="stage" select="normalize-space(@stadija)"/>
    <xsl:variable name="day" select="substring(normalize-space(concat($sitting/@vyko_nuo, ' ', $sitting/@vyko_iki)), 1, 10)"/>
    <xsl:variable name="consideration" select="key('consideration', @svarstomo_klausimo_id)"/>
    <xsl:variable name="planned" select="key('agenda', concat($sitting/@posėdžio_id, '|', normalize-space(@numeris)))/KlausimoStadija"/>
    <xsl:variable name="document">
        <xsl:choose>
            <xsl:when test="$planned[@pavadinimas = $stage][@dokumento_nuoroda != '']">
                <xsl:value-of select="$planned[@pavadinimas = $stage][@dokumento_nuoroda != ''][1]/@dokumento_nuoroda"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$planned[@dokumento_nuoroda != ''][1]/@dokumento_nuoroda"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:variable>
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">klausimo_id</xsl:with-param><xsl:with-param name="value" select="@svarstomo_klausimo_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">posedzio_id</xsl:with-param><xsl:with-param name="value" select="$sitting/@posėdžio_id"/></xsl:call-template>
        <!-- position on the sitting's course of proceedings (the source agenda number repeats when an item is resumed) -->
        <xsl:call-template name="prop"><xsl:with-param name="name">eiles_nr</xsl:with-param><xsl:with-param name="value" select="count(preceding-sibling::EigosKlausimas) + 1"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">darbotvarkes_nr</xsl:with-param><xsl:with-param name="value" select="normalize-space(@numeris)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pavadinimas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">stadija</xsl:with-param><xsl:with-param name="value" select="$stage"/></xsl:call-template>
        <xsl:call-template name="prop">
            <xsl:with-param name="name">stadijos_slug</xsl:with-param>
            <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="$stage"/></xsl:call-template></xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">data</xsl:with-param><xsl:with-param name="value" select="$day"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">laikas_nuo</xsl:with-param><xsl:with-param name="value" select="normalize-space(@laikas_nuo)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">dokumento_nuoroda</xsl:with-param><xsl:with-param name="value" select="$document"/></xsl:call-template>
        <xsl:for-each select="$consideration/AtsakingiPadaliniai">
            <!-- the bill, not its revision: "XIP-672(2)" -> "XIP-672" -->
            <xsl:call-template name="prop"><xsl:with-param name="name">projekto_nr</xsl:with-param><xsl:with-param name="value" select="normalize-space(substring-before(concat(@dokumento_numeris, '('), '('))"/></xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="$consideration/SvarstymoEigosĮvykis[@įvykio_tipas = 'Kalba']">
            <xsl:call-template name="prop"><xsl:with-param name="name">kalbetojo_asmens_id</xsl:with-param><xsl:with-param name="value" select="@asmens_id"/></xsl:call-template>
        </xsl:for-each>
    </rdf:Description>
</xsl:template>

</xsl:stylesheet>
