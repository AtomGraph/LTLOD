<?xml version="1.0" encoding="UTF-8"?>
<!--

    Client-side (Saxon-JS) XSLT overrides for the LTLOD end-user app.

    Imports LinkedDataHub's stock client.xsl plus the shared files/overrides.xsl
    (the property-centric membership-block suppression, shared with the
    server-side files/layout.xsl so the blocks never render — no flash).
    Compiled to client.xsl.sef.json by `make sef` and mounted into the LDH
    container; activated by files/layout.xsl (which repoints the client
    bootstrap at our SEF). See CLAUDE.md "Client-side XSLT overrides".

    This file additionally holds the CLIENT-ONLY tidying of the memberships
    table that the ontology-defined view (:Memberships in app/ns.ttl,
    ac:TableMode) renders in place of the suppressed blocks — the table is
    loaded and rendered client-side, so these overrides need not run server-side.

-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY ldh    "https://w3id.org/atomgraph/linkeddatahub#">
    <!ENTITY ac     "https://w3id.org/atomgraph/client#">
    <!ENTITY rdf    "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <!ENTITY org    "http://www.w3.org/ns/org#">
    <!ENTITY time   "http://www.w3.org/2006/time#">
    <!ENTITY foaf   "http://xmlns.com/foaf/0.1/">
    <!ENTITY xsd    "http://www.w3.org/2001/XMLSchema#">
]>
<xsl:stylesheet version="3.0"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:ldh="&ldh;"
    xmlns:ac="&ac;"
    xmlns:rdf="&rdf;"
    xmlns:json="http://www.w3.org/2005/xpath-functions"
    xmlns:foaf="&foaf;"
    xmlns:org="&org;"
    xmlns:time="&time;"
    exclude-result-prefixes="#all">

    <xsl:import href="../com/atomgraph/linkeddatahub/xsl/client.xsl"/>
    <!-- imported last so its templates take import precedence over the base -->
    <xsl:import href="overrides.xsl"/>
    <!-- the ltlod:CalendarMode view layout (month grids); client-only, see the file header -->
    <xsl:import href="calendar-mode.xsl"/>

    <!--
        Override LDH's default geo-map modal query (the stock ldh:geo-resources-string
        global param declared in navigation.xsl, fed into the "modal modal-geo"
        element and wrapped in DESCRIBE * by ldh:GeoResourcesLoad). The stock query
        DESCRIBEs EVERY geo:lat/geo:long resource — here ~21k, all 20,880 point-only
        settlements included — yielding a ~21 MB response that exceeds LDH's
        MAX_CONTENT_LENGTH (4 MB, .env), so LDH returns 502 Bad Gateway.

        Restrict to admin unit boundaries: FILTER EXISTS on cv:AdminUnit + gsp:asWKT
        keeps exactly the 606 counties/municipalities/elderships → ~3.1 MB / 200
        (settlements are point-only; the ~22.5k streets carry centreline WKT but are
        dct:Location, not cv:AdminUnit — without the type they would blow the limit).
        The filter is host-agnostic (no base URI), and the projected variable
        stays ?resource (navigation.xsl requires initial-var-name='resource'). This
        param has higher import precedence than the included navigation.xsl copy, so
        it wins. Scoped map views (:SubUnits, the frontpage counties map) use their
        own spin:query and are unaffected — settlement points remain mappable there.
    -->
    <xsl:param name="ldh:geo-resources-string" as="xs:string"><![CDATA[
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX gsp: <http://www.opengis.net/ont/geosparql#>
PREFIX cv:  <http://data.europa.eu/m8g/>

SELECT DISTINCT ?resource
WHERE
  { GRAPH ?graph
      { ?resource  geo:lat   ?lat ;
                   geo:long  ?long
        FILTER EXISTS { ?resource a cv:AdminUnit ; gsp:asWKT ?wkt }
        OPTIONAL
          { ?resource  a  ?type }
        OPTIONAL
          { ?resource  dct:title  ?title }
      }
  }
ORDER BY ?title
]]></xsl:param>

    <!--
        Tidy the memberships table (rendered by the :Memberships ldh:View in
        ac:TableMode). LDH DESCRIBEs each membership and tables it by predicate,
        which by default yields a Resource-URI anchor column plus rdf:type,
        org:member (redundant — always this person), org:memberDuring,
        org:organization and org:role columns.

        We restrict the columns to Pareigos (org:role) | Organizacija
        (org:organization) | Laikotarpis (org:memberDuring) and drop the anchor
        column, then hand the table back to the stock emitter with xsl:next-match.
        The stock table is the SAME mode this template matches in, so next-match
        is what reaches it — an apply-templates in ac:ResultsTable would re-enter
        this template forever. This reuses all the base table machinery; removing
        this one template reverts to the busier but functional stock table.
    -->
    <xsl:template match="rdf:RDF[*/rdf:type/@rdf:resource = '&org;Membership']"
                  mode="ac:ResultsTable" priority="5">
        <xsl:variable name="predicates" as="element()*"
            select="(*/org:role)[1], (*/org:organization)[1], (*/org:memberDuring)[1]"/>

        <xsl:next-match>
            <xsl:with-param name="predicates" select="$predicates"/>
            <xsl:with-param name="anchor-column" select="false()" tunnel="yes"/>
        </xsl:next-match>
    </xsl:template>

    <!--
        Render the Laikotarpis (org:memberDuring) cell as the period text only —
        no link. The interval is suppressed plumbing, so a hyperlink to it is
        pointless; the useful value is its dct:title period. ac:object-label
        resolves the interval URI's label from the object-metadata the table
        already loads (tunnel), so this prints e.g. "2024-11-14 – dabar" as a
        plain literal instead of an anchor to the interval resource.
    -->
    <xsl:template match="*[@rdf:about or @rdf:nodeID]/org:memberDuring" mode="ac:ResultsTableDataCell" priority="5">
        <td>
            <xsl:apply-templates select="@rdf:resource" mode="ac:object-label"/>
        </td>
    </xsl:template>

    <!--
        Show ONE image per foaf:depiction table cell.

        The design system's cell rule is that every value of a property shares the
        one cell the first value opens, stacked in a `div.values` that caps its own
        height (ldh.css: `.ldh-results-table td > .values { max-height: 12em;
        overflow-y: auto }`). That is right for literals, but a stack of portraits
        turns every row into a ~180px scroll box, and the second portrait carries no
        information the first does not — Seimas members legitimately have more than
        one depiction (Wikidata P18 plus the scraped lrs.lt portrait, see CLAUDE.md).

        So this keeps the design system's markup exactly — `div.values > div.value`,
        so the cell padding, the `~ .value` separator rule and the height cap all
        still apply — and simply feeds it a single value. With one value the cap
        never engages and the separator never draws.

        Matched on the cell-opening depiction (the one without a preceding
        foaf:depiction sibling), which is the same node the stock priority-1
        ac:ResultsTableDataCell template matches; the stock empty template still
        swallows the rest. Removing this template reverts to the stacked cell.

        https: is preferred over http: when both forms of the same image are
        present: Wikimedia Commons URLs served over http do not render in browsers
        (which is why the reconciler https-normalises them), so picking one blindly
        could show a knowingly-broken image. After a clean store rebuild no http
        Commons URL survives and the predicate is a no-op.
    -->
    <xsl:template match="*[@rdf:about or @rdf:nodeID]/foaf:depiction[not(preceding-sibling::foaf:depiction)]"
                  mode="ac:ResultsTableDataCell" priority="5">
        <xsl:variable name="depictions" select="../foaf:depiction" as="element()*"/>

        <td>
            <div class="values">
                <xsl:apply-templates select="($depictions[starts-with(@rdf:resource, 'https:')], $depictions)[1]"
                                     mode="ac:ResultsTableDataCellValue"/>
            </div>
        </td>
    </xsl:template>

</xsl:stylesheet>
