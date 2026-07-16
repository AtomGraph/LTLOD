<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize Seimas structural-unit XML feeds (p2b.ad_seimo_frakcijos / _komitetai /
  _komisijos) to source-shaped RDF/XML rows: padalinio_id, pavadinimas, santrumpa,
  tipas (derived from the element name). Member lists in these feeds are skipped —
  memberships come from the members feed (nariai.xsl).
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
        <xsl:for-each select="//SeimoFrakcija | //SeimoKomitetas | //SeimoKomisija">
            <rdf:Description rdf:nodeID="{generate-id()}">
                <xsl:call-template name="prop"><xsl:with-param name="name">padalinio_id</xsl:with-param><xsl:with-param name="value" select="@padalinio_id"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@padalinio_pavadinimas)"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">santrumpa</xsl:with-param><xsl:with-param name="value" select="@padalinio_pavadinimo_santrumpa"/></xsl:call-template>
                <xsl:call-template name="prop">
                    <xsl:with-param name="name">tipas</xsl:with-param>
                    <xsl:with-param name="value">
                        <xsl:choose>
                            <xsl:when test="self::SeimoFrakcija">frakcija</xsl:when>
                            <xsl:when test="self::SeimoKomitetas">komitetas</xsl:when>
                            <xsl:otherwise>komisija</xsl:otherwise>
                        </xsl:choose>
                    </xsl:with-param>
                </xsl:call-template>
            </rdf:Description>
        </xsl:for-each>
    </rdf:RDF>
</xsl:template>

</xsl:stylesheet>
