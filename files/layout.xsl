<?xml version="1.0" encoding="UTF-8"?>
<!--

    Server-side layout override for the LTLOD end-user app.

    Two jobs:
    1. repoint the client-side XSLT bootstrap at our custom Saxon-JS stylesheet
       (files/client.xsl → client.xsl.sef.json) instead of the stock one
       (xhtml:Script below);
    2. import the shared files/overrides.xsl so the membership plumbing blocks
       are suppressed in the SERVER render too — otherwise the server emits them
       and the client removes them during CSR, causing a visible flash.

    Imports the base layout.xsl and overrides only the xhtml:Script template's
    client-stylesheet parameter.

    Mounted over the end-user app's ac:stylesheet target
    (static/xsl/layout.xsl, config/dataspaces.trig), so it applies to the
    end-user app only — the admin app uses static/xsl/admin/layout.xsl and is
    untouched. The xhtml:Script signature mirrors the pinned LDH image
    (docker-compose.yml), which matches on the lapp:origin() function.

-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY rdf    "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
]>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:rdf="&rdf;"
    xmlns:lapp="https://w3id.org/atomgraph/linkeddatahub/apps#"
    xmlns:srx="http://www.w3.org/2005/sparql-results#"
    exclude-result-prefixes="#all">

    <xsl:import href="../com/atomgraph/linkeddatahub/xsl/bootstrap/2.3.2/layout.xsl"/>
    <!-- imported last so its suppression templates take import precedence -->
    <xsl:import href="overrides.xsl"/>

    <!-- load our custom client SEF instead of the stock client.xsl.sef.json -->
    <xsl:template match="rdf:RDF[lapp:origin()] | srx:sparql[lapp:origin()]" mode="xhtml:Script">
        <xsl:param name="client-stylesheet" select="resolve-uri('static/com/ltlod/xsl/client.xsl.sef.json', lapp:origin())" as="xs:anyURI"/>

        <xsl:apply-imports>
            <xsl:with-param name="client-stylesheet" select="$client-stylesheet"/>
        </xsl:apply-imports>
    </xsl:template>

</xsl:stylesheet>
