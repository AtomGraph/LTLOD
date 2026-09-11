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

    <!--
        Override LDH's default geo-map modal query (the stock geo-resources-string
        global param declared in navigation.xsl, fed into the "modal modal-geo"
        element and wrapped in DESCRIBE * by ldh:GeoResourcesLoad). The stock query
        DESCRIBEs EVERY geo:lat/geo:long resource — here ~21k, all 20,880 point-only
        settlements included — yielding a ~21 MB response that exceeds LDH's
        MAX_CONTENT_LENGTH (4 MB, .env), so LDH returns 502 Bad Gateway.

        Restrict to admin units: they are the only geo resources carrying a
        gsp:asWKT boundary polygon (settlements are point-only), so FILTER EXISTS on
        asWKT keeps exactly the 606 counties/municipalities/elderships → ~3.1 MB /
        200. The filter is host-agnostic (no base URI), and the projected variable
        stays ?resource (navigation.xsl requires initial-var-name='resource'). This
        param has higher import precedence than the included navigation.xsl copy, so
        it wins. Scoped map views (:SubUnits, the frontpage counties map) use their
        own spin:query and are unaffected — settlement points remain mappable there.
    -->
    <xsl:param name="geo-resources-string" as="xs:string"><![CDATA[
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX gsp: <http://www.opengis.net/ont/geosparql#>

SELECT DISTINCT ?resource
WHERE
  { GRAPH ?graph
      { ?resource  geo:lat   ?lat ;
                   geo:long  ?long
        FILTER EXISTS { ?resource gsp:asWKT ?wkt }
        OPTIONAL
          { ?resource  a  ?type }
        OPTIONAL
          { ?resource  dct:title  ?title }
      }
  }
ORDER BY ?title
]]></xsl:param>

    <!--
        The label predicates the facet-value-count override below filters on, in the
        order LDH's own alternative path lists them - so the SAMPLE(?label) a filter
        pill displays is unchanged. See that template for why the path became a FILTER.
    -->
    <xsl:param name="ldh:label-predicates" as="xs:string+" select="(
        'http://www.w3.org/2000/01/rdf-schema#label',
        'http://purl.org/dc/elements/1.1/title',
        'http://purl.org/dc/terms/title',
        'http://xmlns.com/foaf/0.1/name',
        'http://xmlns.com/foaf/0.1/givenName',
        'http://xmlns.com/foaf/0.1/familyName',
        'http://rdfs.org/sioc/ns#name',
        'http://www.w3.org/2004/02/skos/core#prefLabel')"/>

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

    <!--
        Facet value loading: replace the label lookup that LDH appends to the
        facet-value-count query (ldh:bgp-value-counts in the stock
        client/query-transforms.xsl).

        To label the values of a filter pill, LDH appends

            OPTIONAL { { ?value <alt-path> ?label }
                       UNION { GRAPH ?g { ?value <alt-path> ?label } } }

        where <alt-path> is a nested 7-way alternative property path over
        rdfs:label | dc:title | dct:title | foaf:name | foaf:givenName |
        foaf:familyName | sioc:name | skos:prefLabel. ARQ does not resolve an
        alternative path through the quad indexes when it sits inside a GRAPH
        block: it walks the graphs, and this dataspace has ~117k named graphs
        (one document per entity), so opening a single pill took ~104 s —
        past every timeout in front of Fuseki, i.e. a 500 in the browser.

        This override emits the semantically identical

            OPTIONAL { { ?value ?labelProp ?label }
                       UNION { GRAPH ?g { ?value ?labelProp ?label } }
                       FILTER (?labelProp IN (rdfs:label, …, skos:prefLabel)) }

        A variable predicate with a bound subject IS an index lookup, so the same
        pill loads in ~10-30 ms. The FILTER-IN-over-label-properties idiom is the
        one LDH itself uses for object metadata. Same label predicates, same
        order, so the SAMPLE(?label) a pill displays is unchanged.

        Structure mirrors the stock template: it is matched on the parent of a
        bgp and only fires for the group that binds the facet's object variable.
    -->
    <xsl:template match="json:map[json:string[@key = 'type'] = 'bgp']/.." mode="ldh:bgp-value-counts" priority="2">
        <xsl:param name="object-var-name" as="xs:string" tunnel="yes"/>
        <xsl:param name="label-var-name" as="xs:string" tunnel="yes"/>
        <xsl:param name="label-graph-var-name" select="$label-var-name || 'graph'" as="xs:string" tunnel="yes"/>
        <xsl:variable name="label-prop-var-name" select="$label-var-name || 'prop'" as="xs:string"/>

        <xsl:copy>
            <xsl:apply-templates select="@* | node()" mode="#current"/>

            <xsl:if test="json:map[json:string[@key = 'type'] = 'bgp']/json:array[@key = 'triples']/json:map/json:string[@key = 'object'] = '?' || $object-var-name">
                <json:map>
                    <json:string key="type">optional</json:string>
                    <json:array key="patterns">
                        <json:map>
                            <json:string key="type">union</json:string>
                            <json:array key="patterns">
                                <!-- default graph -->
                                <json:map>
                                    <json:string key="type">bgp</json:string>
                                    <json:array key="triples">
                                        <xsl:call-template name="ldh:LabelTriple">
                                            <xsl:with-param name="object-var-name" select="$object-var-name"/>
                                            <xsl:with-param name="label-prop-var-name" select="$label-prop-var-name"/>
                                            <xsl:with-param name="label-var-name" select="$label-var-name"/>
                                        </xsl:call-template>
                                    </json:array>
                                </json:map>
                                <!-- named graphs -->
                                <json:map>
                                    <json:string key="type">graph</json:string>
                                    <json:array key="patterns">
                                        <json:map>
                                            <json:string key="type">bgp</json:string>
                                            <json:array key="triples">
                                                <xsl:call-template name="ldh:LabelTriple">
                                                    <xsl:with-param name="object-var-name" select="$object-var-name"/>
                                                    <xsl:with-param name="label-prop-var-name" select="$label-prop-var-name"/>
                                                    <xsl:with-param name="label-var-name" select="$label-var-name"/>
                                                </xsl:call-template>
                                            </json:array>
                                        </json:map>
                                    </json:array>
                                    <json:string key="name"><xsl:text>?</xsl:text><xsl:value-of select="$label-graph-var-name"/></json:string>
                                </json:map>
                            </json:array>
                        </json:map>

                        <json:map>
                            <json:string key="type">filter</json:string>
                            <json:map key="expression">
                                <json:string key="type">operation</json:string>
                                <json:string key="operator">in</json:string>
                                <json:array key="args">
                                    <json:string><xsl:text>?</xsl:text><xsl:value-of select="$label-prop-var-name"/></json:string>
                                    <json:array>
                                        <xsl:for-each select="$ldh:label-predicates">
                                            <json:string><xsl:value-of select="."/></json:string>
                                        </xsl:for-each>
                                    </json:array>
                                </json:array>
                            </json:map>
                        </json:map>
                    </json:array>
                </json:map>
            </xsl:if>
        </xsl:copy>
    </xsl:template>

    <xsl:template name="ldh:LabelTriple">
        <xsl:param name="object-var-name" as="xs:string"/>
        <xsl:param name="label-prop-var-name" as="xs:string"/>
        <xsl:param name="label-var-name" as="xs:string"/>

        <json:map>
            <json:string key="subject"><xsl:text>?</xsl:text><xsl:value-of select="$object-var-name"/></json:string>
            <json:string key="predicate"><xsl:text>?</xsl:text><xsl:value-of select="$label-prop-var-name"/></json:string>
            <json:string key="object"><xsl:text>?</xsl:text><xsl:value-of select="$label-var-name"/></json:string>
        </json:map>
    </xsl:template>

</xsl:stylesheet>
