<?xml version="1.0" encoding="UTF-8"?>
<!--
  Normalize the Seimas members XML (p2b.ad_seimo_nariai) to source-shaped RDF/XML:
  one resource per member, one per position (Pareigos), properties in the
  {$base}# namespace so graphify mappings can match them as <#name> —
  the same convention CSV2RDF uses for CSV columns.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

<xsl:param name="base"/>
<xsl:output method="xml" indent="yes" encoding="UTF-8"/>

<!-- transliteration tables for slug generation -->
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
        <xsl:for-each select="//SeimoNarys">
            <xsl:variable name="kadencija" select="ancestor::SeimoKadencija/@kadencijos_id"/>
            <rdf:Description rdf:nodeID="{generate-id()}">
                <xsl:call-template name="prop"><xsl:with-param name="name">asmens_id</xsl:with-param><xsl:with-param name="value" select="@asmens_id"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">vardas</xsl:with-param><xsl:with-param name="value" select="@vardas"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">pavarde</xsl:with-param><xsl:with-param name="value" select="@pavardė"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">lytis</xsl:with-param><xsl:with-param name="value" select="@lytis"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">iskelusi_partija</xsl:with-param><xsl:with-param name="value" select="@iškėlusi_partija"/></xsl:call-template>
                <xsl:if test="string(@iškėlusi_partija) != ''">
                    <xsl:call-template name="prop">
                        <xsl:with-param name="name">partijos_slug</xsl:with-param>
                        <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="@iškėlusi_partija"/></xsl:call-template></xsl:with-param>
                    </xsl:call-template>
                </xsl:if>
                <xsl:call-template name="prop"><xsl:with-param name="name">isrinkimo_budas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@išrinkimo_būdas)"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">kadenciju_skaicius</xsl:with-param><xsl:with-param name="value" select="@kadencijų_skaičius"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">biografijos_nuoroda</xsl:with-param><xsl:with-param name="value" select="@biografijos_nuoroda"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">kadencijos_id</xsl:with-param><xsl:with-param name="value" select="$kadencija"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">data_nuo</xsl:with-param><xsl:with-param name="value" select="@data_nuo"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">data_iki</xsl:with-param><xsl:with-param name="value" select="@data_iki"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">el_pastas</xsl:with-param><xsl:with-param name="value" select="normalize-space(Kontaktai[@rūšis='El. p.'][1]/@reikšmė)"/></xsl:call-template>
                <xsl:call-template name="prop"><xsl:with-param name="name">telefonas</xsl:with-param><xsl:with-param name="value" select="normalize-space(Kontaktai[@rūšis='Darbo telefonas'][1]/@reikšmė)"/></xsl:call-template>
            </rdf:Description>

            <xsl:for-each select="Pareigos">
                <rdf:Description rdf:nodeID="{generate-id()}">
                    <xsl:call-template name="prop"><xsl:with-param name="name">pareigos_asmens_id</xsl:with-param><xsl:with-param name="value" select="../@asmens_id"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">padalinio_id</xsl:with-param><xsl:with-param name="value" select="@padalinio_id"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">padalinio_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@padalinio_pavadinimas)"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">parlamentines_grupes_id</xsl:with-param><xsl:with-param name="value" select="@parlamentinės_grupės_id"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">parlamentines_grupes_pavadinimas</xsl:with-param><xsl:with-param name="value" select="normalize-space(@parlamentinės_grupės_pavadinimas)"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">pareigos</xsl:with-param><xsl:with-param name="value" select="normalize-space(@pareigos)"/></xsl:call-template>
                    <xsl:if test="string(@pareigos) != ''">
                        <xsl:call-template name="prop">
                            <xsl:with-param name="name">pareigu_slug</xsl:with-param>
                            <xsl:with-param name="value"><xsl:call-template name="slug"><xsl:with-param name="value" select="@pareigos"/></xsl:call-template></xsl:with-param>
                        </xsl:call-template>
                    </xsl:if>
                    <xsl:call-template name="prop"><xsl:with-param name="name">pareigos_nuo</xsl:with-param><xsl:with-param name="value" select="@data_nuo"/></xsl:call-template>
                    <xsl:call-template name="prop"><xsl:with-param name="name">pareigos_iki</xsl:with-param><xsl:with-param name="value" select="@data_iki"/></xsl:call-template>
                </rdf:Description>
            </xsl:for-each>
        </xsl:for-each>
    </rdf:RDF>
</xsl:template>

</xsl:stylesheet>
