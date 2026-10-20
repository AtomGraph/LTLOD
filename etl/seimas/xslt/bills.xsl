<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize the bills initiated by Seimas members (p2b.ad_sn_inicijuoti_ta_projektai,
  one document per term, merged under a wrapper element) to source-shaped RDF/XML
  rows: one row per member and bill. A bill initiated by a group of members is
  listed under each of them (požymis "Grupėje"), so the rows of one bill carry its
  initiators. The registration number (registracijos_numeris, e.g. "XVP-208") is the
  bill's natural key; the agenda feeds cite the same number with a revision suffix.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<xsl:param name="base"/>
<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<xsl:template name="prop">
    <xsl:param name="name"/>
    <xsl:param name="value"/>
    <xsl:if test="string($value) != ''">
        <xsl:element name="p:{$name}" namespace="{concat($base, '#')}">
            <xsl:value-of select="$value"/>
        </xsl:element>
    </xsl:if>
</xsl:template>

<xsl:template match="/">
    <rdf:RDF>
        <xsl:apply-templates select="/feeds/SeimoInformacija/SeimoKadencija/SeimoNarys/SeimoNarioPateiktasTeisėsAktoProjektas"/>
    </rdf:RDF>
</xsl:template>

<xsl:template match="SeimoNarioPateiktasTeisėsAktoProjektas">
    <rdf:Description rdf:nodeID="{generate-id()}">
        <xsl:call-template name="prop"><xsl:with-param name="name">projekto_nr</xsl:with-param><xsl:with-param name="value" select="normalize-space(@registracijos_numeris)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">projekto_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pavadinimas)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">registracijos_data</xsl:with-param><xsl:with-param name="value" select="substring(normalize-space(@registracijos_data), 1, 10)"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">iniciatoriaus_asmens_id</xsl:with-param><xsl:with-param name="value" select="../@asmens_id"/></xsl:call-template>
        <xsl:call-template name="prop"><xsl:with-param name="name">kadencijos_id</xsl:with-param><xsl:with-param name="value" select="../../@kadencijos_id"/></xsl:call-template>
    </rdf:Description>
</xsl:template>

</xsl:stylesheet>
