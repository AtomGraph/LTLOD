<?xml version="1.0" encoding="UTF-8"?>
<!--

    ltlod:CalendarMode: a generic calendar layout mode for ldh:View blocks
    (client-side, Saxon-JS). Imported by files/client.xsl, compiled into the SEF.

    A view in this mode draws its results as month grids (Monday-first weeks):
    every result resource is placed on a date, and one grid is drawn per month
    the dates span: a full-size grid listing the items when there is one month,
    a compact year-style grid otherwise. The date of a resource is the value of
    the view's ORDER BY variable's predicate (from LDH's $var-predicates; may be
    an untyped "yyyy-mm-dd…" string such as dct:identifier), else its first
    xsd:date / xsd:dateTime literal. Resources with no date are left out. The
    mode does not page (LDH draws the pager for list/table/grid only): in it the
    view's request goes out unpaged, up to $ltlod:calendar-limit results.

    A result that IS the calendar day (an LTLOD calendar time:DateTimeInterval)
    turns its cell's day number into a link to it, and the cell shows its public
    holidays (dct:type labels from LDH's object metadata). Month titles link to
    the LTLOD calendar month document.

    Wiring into LDH (atomgraph/linkeddatahub image), whose view modes are a
    closed list in several places:
    - $ldh:class-modes (CSS class <-> mode, read back off the active switcher
      item by every view handler) and $ldh:mode-icons get a calendar entry;
    - the switcher item list (template rule) is wrapped with xsl:next-match and
      gets a Calendar item appended;
    - the named templates ldh:ViewModeSwitcher, ldh:ViewModeChoice and ldh:RenderView are
      COPIED from the image's client/block/view.xsl (named templates have no
      next-match) with one change each, marked "LTLOD:": the mode description
      lookup falls back to $ltlod:view-modes, the mode choice gets the calendar
      branch, and the results request drops paging in calendar mode only. Re-sync both on an LDH image upgrade;
    - the stock switcher click handler looks the picked mode up in the ac:
      ontology only, so for the calendar item it is followed by a re-render of
      the switcher (xsl:next-match, then replace-content).

-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY ldh    "https://w3id.org/atomgraph/linkeddatahub#">
    <!ENTITY ac     "https://w3id.org/atomgraph/client#">
    <!ENTITY rdf    "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <!ENTITY rdfs   "http://www.w3.org/2000/01/rdf-schema#">
    <!ENTITY xsd    "http://www.w3.org/2001/XMLSchema#">
    <!ENTITY time   "http://www.w3.org/2006/time#">
    <!ENTITY dct    "http://purl.org/dc/terms/">
    <!ENTITY foaf   "http://xmlns.com/foaf/0.1/">
    <!ENTITY ltlod  "http://linkeddata.lt/ns#">
]>
<xsl:stylesheet version="3.0"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:map="http://www.w3.org/2005/xpath-functions/map"
    xmlns:json="http://www.w3.org/2005/xpath-functions"
    xmlns:ixsl="http://saxonica.com/ns/interactiveXSLT"
    xmlns:ldh="&ldh;"
    xmlns:lds="https://w3id.org/atomgraph/linkeddatahub/dataspaces#"
    xmlns:ac="&ac;"
    xmlns:rdf="&rdf;"
    xmlns:rdfs="&rdfs;"
    xmlns:time="&time;"
    xmlns:dct="&dct;"
    xmlns:foaf="&foaf;"
    xmlns:ltlod="&ltlod;"
    extension-element-prefixes="ixsl"
    exclude-result-prefixes="#all">

    <!-- MODE REGISTRATION -->

    <!-- the stock entries (image client/block/view.xsl) + calendar-mode -->
    <xsl:param name="ldh:class-modes" as="map(xs:string, xs:anyURI)">
        <xsl:map>
            <xsl:map-entry key="'read-mode'" select="xs:anyURI('&ac;ReadMode')"/>
            <xsl:map-entry key="'list-mode'" select="xs:anyURI('&ac;ListMode')"/>
            <xsl:map-entry key="'table-mode'" select="xs:anyURI('&ac;TableMode')"/>
            <xsl:map-entry key="'grid-mode'" select="xs:anyURI('&ac;GridMode')"/>
            <xsl:map-entry key="'chart-mode'" select="xs:anyURI('&ac;ChartMode')"/>
            <xsl:map-entry key="'map-mode'" select="xs:anyURI('&ac;MapMode')"/>
            <xsl:map-entry key="'graph-mode'" select="xs:anyURI('&ac;GraphMode')"/>
            <xsl:map-entry key="'calendar-mode'" select="xs:anyURI('&ltlod;CalendarMode')"/>
        </xsl:map>
    </xsl:param>

    <!-- the stock glyphs (image resource.xsl) + calendar_month -->
    <xsl:variable name="ldh:mode-icons" as="map(xs:string, xs:string)" select="map{
        '&ldh;ContentMode': 'view_module',
        '&ac;ReadMode': 'visibility',
        '&ac;ListMode': 'view_list',
        '&ac;TableMode': 'table',
        '&ac;GridMode': 'grid_view',
        '&ac;MapMode': 'map',
        '&ac;ChartMode': 'bar_chart',
        '&ac;GraphMode': 'hub',
        '&ltlod;CalendarMode': 'calendar_month'
    }"/>

    <!-- descriptions of the modes LDH's ac: ontology does not have -->
    <xsl:variable name="ltlod:view-modes" as="document-node()">
        <xsl:document>
            <rdf:RDF>
                <rdf:Description rdf:about="&ltlod;CalendarMode">
                    <rdfs:label xml:lang="en">Calendar</rdfs:label>
                    <rdfs:label xml:lang="lt">Kalendorius</rdfs:label>
                </rdf:Description>
            </rdf:RDF>
        </xsl:document>
    </xsl:variable>

    <xsl:function name="ltlod:mode-resource" as="element()?">
        <xsl:param name="mode" as="xs:anyURI"/>
        <xsl:sequence select="(key('resources', $mode, document(ac:document-uri('&ac;'))), key('resources', $mode, $ltlod:view-modes))[1]"/>
    </xsl:function>

    <!-- SWITCHER -->

    <!-- copied from the image's client/block/view.xsl (named template, no next-match) -->
    <xsl:template name="ldh:ViewModeSwitcher">
        <xsl:param name="active-mode" as="xs:anyURI"/>
        <xsl:param name="id" select="'view-modes'" as="xs:string?"/>

        <div class="ldh-mode sz-sm ac-menu-anchor">
            <!-- LTLOD: the ac: ontology or $ltlod:view-modes -->
            <xsl:apply-templates select="ltlod:mode-resource($active-mode)" mode="ldh:ViewModeSwitcher">
                <xsl:with-param name="id" select="$id"/>
            </xsl:apply-templates>
        </div>
    </xsl:template>

    <!-- the stock trigger + items, with a Calendar item appended to the items -->
    <xsl:template match="*[@rdf:about]" mode="ldh:ViewModeSwitcher" priority="1">
        <xsl:variable name="active-mode" select="xs:anyURI(@rdf:about)" as="xs:anyURI"/>
        <xsl:variable name="stock" as="node()*">
            <xsl:next-match/>
        </xsl:variable>

        <xsl:apply-templates select="$stock" mode="ltlod:AddCalendarModeItem">
            <xsl:with-param name="active-mode" select="$active-mode" tunnel="yes"/>
        </xsl:apply-templates>
    </xsl:template>

    <xsl:mode name="ltlod:AddCalendarModeItem" on-no-match="shallow-copy"/>

    <xsl:template match="xhtml:div[contains-token(@class, 'view-mode-list')]" mode="ltlod:AddCalendarModeItem">
        <xsl:param name="active-mode" as="xs:anyURI" tunnel="yes"/>
        <xsl:variable name="active" select="$active-mode = '&ltlod;CalendarMode'" as="xs:boolean"/>

        <xsl:copy>
            <xsl:apply-templates select="@* | node()" mode="#current"/>
            <xsl:apply-templates select="key('resources', '&ltlod;CalendarMode', $ltlod:view-modes)" mode="ac:ModeSwitcherItem">
                <xsl:with-param name="active" select="$active"/>
                <xsl:with-param name="href" select="()"/>
                <xsl:with-param name="class" select="'calendar-mode' || (if ($active) then ' is-active' else ())"/>
            </xsl:apply-templates>
        </xsl:copy>
    </xsl:template>

    <!-- picking Calendar: the stock handler switches the view, but re-renders the switcher from the ac: ontology
         alone, which has no calendar mode - so the switcher is re-rendered once more afterwards -->
    <xsl:template match="div[@typeof = '&ldh;View']//*[contains-token(@class, 'view-mode-list')]/*[contains-token(@class, 'mi')][contains-token(@class, 'calendar-mode')][not(contains-token(@class, 'is-active'))]" mode="ixsl:onclick" priority="1">
        <xsl:variable name="anchor" select="ancestor::*[contains-token(@class, 'ac-menu-anchor')][1]" as="element()?"/>
        <xsl:variable name="id" select="($anchor/*[contains-token(@class, 'drop-toggle')]/@id)[1]!string()" as="xs:string?"/>

        <xsl:next-match/>

        <xsl:for-each select="$anchor">
            <xsl:result-document href="?." method="ixsl:replace-content">
                <xsl:apply-templates select="ltlod:mode-resource(xs:anyURI('&ltlod;CalendarMode'))" mode="ldh:ViewModeSwitcher">
                    <xsl:with-param name="id" select="$id"/>
                </xsl:apply-templates>
            </xsl:result-document>
        </xsl:for-each>
    </xsl:template>

    <!-- MODE CHOICE -->

    <!-- copied from the image's client/block/view.xsl (named template, no next-match); LTLOD: the calendar branch -->
    <xsl:template name="ldh:ViewModeChoice">
        <xsl:param name="container-id" as="xs:string"/>
        <xsl:param name="select-xml" as="document-node()?"/>
        <xsl:param name="endpoint" as="xs:anyURI"/>
        <xsl:param name="local-endpoint" as="xs:anyURI?"/>
        <xsl:param name="results" as="document-node()"/>
        <xsl:param name="object-metadata" as="document-node()?"/>
        <xsl:param name="active-mode" as="xs:anyURI"/>
        <xsl:param name="total-count" as="xs:integer?"/>
        <xsl:param name="var-predicates" as="map(xs:string, xs:anyURI*)?"/>
        <xsl:param name="order-by-var-name" select="$select-xml/json:map/json:array[@key = 'order']/json:map[1]/json:string[@key = 'expression']/substring-after(., '?')" as="xs:string?"/>
        <xsl:param name="order-by-desc" select="$select-xml/json:map/json:array[@key = 'order']/json:map[1]/json:boolean[@key = 'descending']" as="xs:boolean?"/>

        <xsl:variable name="remote-endpoint" select="if (not($endpoint = $local-endpoint)) then $endpoint else ()" as="xs:anyURI?"/>

        <xsl:choose>
            <!-- LTLOD: the calendar mode -->
            <xsl:when test="$active-mode = '&ltlod;CalendarMode'">
                <xsl:apply-templates select="$results" mode="ltlod:CalendarViewBlock">
                    <xsl:with-param name="container-id" select="$container-id"/>
                    <xsl:with-param name="total-count" select="$total-count"/>
                    <xsl:with-param name="object-metadata" select="$object-metadata"/>
                    <xsl:with-param name="var-predicates" select="$var-predicates"/>
                    <xsl:with-param name="order-by-var-name" select="$order-by-var-name"/>
                    <xsl:with-param name="order-by-desc" select="$order-by-desc"/>
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;ListMode'">
                <xsl:apply-templates select="$results" mode="ldh:ListViewBlock">
                    <xsl:with-param name="container-id" select="$container-id"/>
                    <xsl:with-param name="total-count" select="$total-count"/>
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;TableMode'">
                <xsl:apply-templates select="$results" mode="ldh:TableViewBlock">
                    <xsl:with-param name="container-id" select="$container-id"/>
                    <xsl:with-param name="total-count" select="$total-count"/>
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                    <xsl:with-param name="object-metadata" select="$object-metadata" tunnel="yes"/>
                    <xsl:with-param name="var-predicates" select="$var-predicates" tunnel="yes"/>
                    <xsl:with-param name="order-by-var-name" select="$order-by-var-name" tunnel="yes"/>
                    <xsl:with-param name="order-by-desc" select="$order-by-desc" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;GridMode'">
                <xsl:apply-templates select="$results" mode="ldh:GridViewBlock">
                    <xsl:with-param name="container-id" select="$container-id"/>
                    <xsl:with-param name="total-count" select="$total-count"/>
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;ChartMode'">
                <xsl:apply-templates select="$results" mode="ldh:Chart">
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="canvas-id" select="$container-id || '-chart-canvas'"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                    <xsl:with-param name="collapsed" select="true()"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;MapMode'">
                <xsl:apply-templates select="$results" mode="ac:Map">
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="id" select="$container-id || '-map-canvas'"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="$active-mode = '&ac;GraphMode'">
                <xsl:apply-templates select="$results" mode="ac:Graph">
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="canvas-id" select="$container-id || '-graph-canvas'"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:otherwise>
                <xsl:apply-templates select="$results">
                    <xsl:with-param name="show-edit-button" select="false()" tunnel="yes"/>
                    <xsl:with-param name="endpoint" select="$remote-endpoint" tunnel="yes"/>
                    <xsl:with-param name="object-metadata" select="$object-metadata" tunnel="yes"/>
                </xsl:apply-templates>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- REQUEST -->

    <!-- results drawn in calendar mode, at most -->
    <xsl:variable name="ltlod:calendar-limit" select="1000" as="xs:integer"/>

    <!-- copied from the image's client/block/view.xsl (named template, no next-match; its comments dropped);
         LTLOD: $request-select-xml -->
    <xsl:template name="ldh:RenderView">
        <xsl:param name="container" as="element()"/>
        <xsl:param name="select-string" as="xs:string"/>
        <xsl:param name="select-xml" as="document-node()"/>
        <xsl:param name="endpoint" select="xs:anyURI"/>
        <xsl:param name="initial-var-name" as="xs:string"/>
        <xsl:param name="focus-var-name" select="ldh:first-var-name($select-xml/json:map)" as="xs:string"/>
        <xsl:param name="active-mode" as="xs:anyURI"/>
        <xsl:param name="refresh-content" as="xs:boolean?"/>
        <xsl:param name="cache" as="item()"/>
        <xsl:param name="form-actions" as="element()?"/>
        <xsl:sequence select="ldh:begin-view-refresh($container)"/>
        <xsl:if test="ixsl:contains($cache, 'result-count')">
            <ixsl:remove-property name="result-count" object="$cache"/>
        </xsl:if>
        <!-- LTLOD: the calendar mode has no pager and draws whole months, so in it the request goes out without the
             page's LIMIT/OFFSET (capped at $ltlod:calendar-limit). Only the request: the returned (cached) select-xml
             keeps its paging, so switching back to a paged mode pages as before -->
        <xsl:variable name="request-select-xml" as="document-node()">
            <xsl:choose>
                <xsl:when test="$active-mode = '&ltlod;CalendarMode'">
                    <xsl:variable name="unpaged" as="document-node()">
                        <xsl:document>
                            <xsl:apply-templates select="$select-xml" mode="ldh:replace-limit">
                                <xsl:with-param name="limit" select="$ltlod:calendar-limit" tunnel="yes"/>
                            </xsl:apply-templates>
                        </xsl:document>
                    </xsl:variable>
                    <xsl:document>
                        <xsl:apply-templates select="$unpaged" mode="ldh:replace-offset"/>
                    </xsl:document>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:sequence select="$select-xml"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="query-xml" as="element()">
            <xsl:apply-templates select="$request-select-xml" mode="ldh:wrap-describe"/>
        </xsl:variable>
        <xsl:variable name="query-json-string" select="xml-to-json($query-xml)" as="xs:string"/>
        <xsl:variable name="query-json" select="ixsl:call(ixsl:get(ixsl:window(), 'JSON'), 'parse', [ $query-json-string ])"/>
        <xsl:variable name="query-string" select="ixsl:call($ldh:sparql-generator, 'stringify', [ $query-json ])" as="xs:string"/>
        <xsl:variable name="request-uri" select="ldh:href($endpoint, map{})" as="xs:anyURI"/>
        <xsl:variable name="headers" as="map(xs:string, xs:string)">
            <xsl:map>
                <xsl:map-entry key="'Accept'" select="'application/rdf+xml'"/>

                <xsl:if test="$refresh-content">
                    <xsl:map-entry key="'Cache-Control'" select="'no-cache, no-store, must-revalidate'"/>
                </xsl:if>
            </xsl:map>
        </xsl:variable>
        <xsl:variable name="request" select="map{ 'method': 'POST', 'href': $request-uri, 'media-type': 'application/sparql-query', 'body': $query-string, 'headers': $headers }" as="map(*)"/>
        <xsl:variable name="container-id" select="($container/@data-view-id/string(), generate-id($container))[1]" as="xs:string"/>
        <xsl:for-each select="$container[empty(@data-view-id)]">
            <ixsl:set-attribute name="data-view-id" select="$container-id"/>
        </xsl:for-each>
        <xsl:sequence select="           map{             'request': $request,             'container': $container,             'container-id': $container-id,             'active-mode': $active-mode,             'select-string': $select-string,             'select-xml': $select-xml,             'initial-var-name': $initial-var-name,             'focus-var-name': $focus-var-name,             'endpoint': $endpoint,             'form-actions': $form-actions,             'cache': $cache           }"/>
    </xsl:template>

    <!-- CALENDAR RENDERING -->

    <xsl:variable name="ltlod:month-names" as="xs:string+" select="('sausis', 'vasaris', 'kovas', 'balandis', 'gegužė', 'birželis', 'liepa', 'rugpjūtis', 'rugsėjis', 'spalis', 'lapkritis', 'gruodis')"/>
    <xsl:variable name="ltlod:weekday-names" as="xs:string+" select="('Pr', 'An', 'Tr', 'Kt', 'Pn', 'Š', 'Sk')"/>
    <!-- items listed in a full-size day cell before "+N" -->
    <xsl:variable name="ltlod:calendar-cell-items" select="3" as="xs:integer"/>

    <!-- the date a result resource is placed on: its value of the ORDER BY predicate(s) (a "yyyy-mm-dd…" string
         of any datatype), else its first xsd:date / xsd:dateTime literal -->
    <xsl:function name="ltlod:calendar-date" as="xs:date?">
        <xsl:param name="resource" as="element()"/>
        <xsl:param name="predicates" as="xs:anyURI*"/>

        <xsl:variable name="ordered" select="$resource/*[not(@rdf:resource or @rdf:nodeID)][namespace-uri() || local-name() = $predicates]" as="element()*"/>
        <xsl:variable name="typed" select="$resource/*[@rdf:datatype = ('&xsd;date', '&xsd;dateTime')]" as="element()*"/>
        <xsl:sequence select="(($ordered, $typed) ! substring(normalize-space(.), 1, 10)[matches(., '^\d{4}-\d{2}-\d{2}$')][. castable as xs:date] ! xs:date(.))[1]"/>
    </xsl:function>

    <!-- 0 = Monday … 6 = Sunday (1990-01-01 was a Monday) -->
    <xsl:function name="ltlod:weekday" as="xs:integer">
        <xsl:param name="date" as="xs:date"/>
        <xsl:variable name="days" select="xs:integer(($date - xs:date('1990-01-01')) div xs:dayTimeDuration('P1D'))" as="xs:integer"/>
        <xsl:sequence select="(($days mod 7) + 7) mod 7"/>
    </xsl:function>

    <!-- an LTLOD calendar day/month/year itself, rather than something that happened on it -->
    <xsl:function name="ltlod:is-calendar-unit" as="xs:boolean">
        <xsl:param name="resource" as="element()"/>
        <xsl:sequence select="$resource/rdf:type/@rdf:resource = '&time;DateTimeInterval'"/>
    </xsl:function>

    <xsl:template match="rdf:RDF" mode="ltlod:CalendarViewBlock">
        <xsl:param name="container-id" as="xs:string?"/>
        <xsl:param name="total-count" as="xs:integer?"/>
        <xsl:param name="object-metadata" as="document-node()?"/>
        <xsl:param name="var-predicates" as="map(xs:string, xs:anyURI*)?"/>
        <xsl:param name="order-by-var-name" as="xs:string?"/>
        <xsl:param name="order-by-desc" as="xs:boolean?"/>

        <xsl:variable name="predicates" select="if (exists($var-predicates) and $order-by-var-name and map:contains($var-predicates, $order-by-var-name)) then $var-predicates($order-by-var-name) else ()" as="xs:anyURI*"/>
        <!-- the results, not the documents DESCRIBEd along with them -->
        <xsl:variable name="resources" select="rdf:Description[@rdf:about][not(foaf:primaryTopic/@rdf:resource = ../rdf:Description/@rdf:about)]" as="element()*"/>
        <xsl:variable name="dated" select="for $r in $resources return let $d := ltlod:calendar-date($r, $predicates) return if (exists($d)) then map{ 'date': $d, 'resource': $r } else ()" as="map(*)*"/>
        <xsl:variable name="months" select="sort(distinct-values($dated ! format-date(?date, '[Y0001]-[M01]')))" as="xs:string*"/>

        <xsl:choose>
            <xsl:when test="empty($dated)">
                <xsl:apply-templates select="." mode="ldh:ViewBlockBlank">
                    <xsl:with-param name="container-id" select="$container-id"/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:otherwise>
                <xsl:variable name="compact" select="count($months) gt 1" as="xs:boolean"/>
                <div class="ltlod-cal{if ($compact) then ' compact' else ()}">
                    <xsl:call-template name="ltlod:CalendarStyle"/>
                    <xsl:for-each select="if ($order-by-desc) then reverse($months) else $months">
                        <xsl:call-template name="ltlod:CalendarMonth">
                            <xsl:with-param name="month" select="."/>
                            <xsl:with-param name="dated" select="$dated"/>
                            <xsl:with-param name="compact" select="$compact"/>
                            <xsl:with-param name="object-metadata" select="$object-metadata"/>
                        </xsl:call-template>
                    </xsl:for-each>
                </div>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template name="ltlod:CalendarMonth">
        <xsl:param name="month" as="xs:string"/>
        <xsl:param name="dated" as="map(*)*"/>
        <xsl:param name="compact" as="xs:boolean"/>
        <xsl:param name="object-metadata" as="document-node()?"/>

        <xsl:variable name="first" select="xs:date($month || '-01')" as="xs:date"/>
        <xsl:variable name="length" select="day-from-date($first + xs:yearMonthDuration('P1M') - xs:dayTimeDuration('P1D'))" as="xs:integer"/>
        <xsl:variable name="lead" select="ltlod:weekday($first)" as="xs:integer"/>
        <xsl:variable name="today" select="xs:date(format-date(current-date(), '[Y0001]-[M01]-[D01]'))" as="xs:date"/>

        <section class="ltlod-cal-month">
            <h3 class="ltlod-cal-title">
                <!-- the LTLOD calendar month document (calendar/{yyyy}/{mm}/) -->
                <a href="{lds:base()}calendar/{substring($month, 1, 4)}/{substring($month, 6, 2)}/">
                    <xsl:variable name="month-number" select="xs:integer(substring($month, 6, 2))" as="xs:integer"/>
                    <xsl:value-of select="substring($month, 1, 4) || ' m. ' || subsequence($ltlod:month-names, $month-number, 1)"/>
                </a>
            </h3>
            <table class="ltlod-cal-grid">
                <thead>
                    <tr>
                        <xsl:for-each select="$ltlod:weekday-names">
                            <th scope="col"><xsl:value-of select="."/></th>
                        </xsl:for-each>
                    </tr>
                </thead>
                <tbody>
                    <xsl:for-each select="0 to xs:integer(ceiling(($lead + $length) div 7)) - 1">
                        <xsl:variable name="week" select="." as="xs:integer"/>
                        <tr>
                            <xsl:for-each select="1 to 7">
                                <xsl:variable name="day" select="$week * 7 + . - $lead" as="xs:integer"/>
                                <xsl:choose>
                                    <xsl:when test="$day ge 1 and $day le $length">
                                        <xsl:variable name="date" select="$first + xs:dayTimeDuration('P' || ($day - 1) || 'D')" as="xs:date"/>
                                        <xsl:call-template name="ltlod:CalendarDay">
                                            <xsl:with-param name="date" select="$date"/>
                                            <xsl:with-param name="resources" select="$dated[?date = $date] ! ?resource"/>
                                            <xsl:with-param name="compact" select="$compact"/>
                                            <xsl:with-param name="today" select="$date = $today"/>
                                            <xsl:with-param name="weekend" select=". ge 6"/>
                                            <xsl:with-param name="object-metadata" select="$object-metadata"/>
                                        </xsl:call-template>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <td class="pad"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:for-each>
                        </tr>
                    </xsl:for-each>
                </tbody>
            </table>
        </section>
    </xsl:template>

    <xsl:template name="ltlod:CalendarDay">
        <xsl:param name="date" as="xs:date"/>
        <xsl:param name="resources" as="element()*"/>
        <xsl:param name="compact" as="xs:boolean"/>
        <xsl:param name="today" as="xs:boolean"/>
        <xsl:param name="weekend" as="xs:boolean"/>
        <xsl:param name="object-metadata" as="document-node()?"/>

        <xsl:variable name="day" select="$resources[ltlod:is-calendar-unit(.)][1]" as="element()?"/>
        <xsl:variable name="events" select="$resources except $day" as="element()*"/>
        <xsl:variable name="holidays" select="$day/dct:type/@rdf:resource ! (if (exists($object-metadata)) then key('resources', ., $object-metadata) else ())" as="element()*"/>
        <xsl:variable name="holiday-labels" select="$holidays ! ac:label(.)" as="xs:string*"/>
        <xsl:variable name="number" select="string(day-from-date($date))" as="xs:string"/>

        <td class="{string-join(('day', 'weekend'[$weekend], 'today'[$today], 'holiday'[exists($day/dct:type)], 'busy'[exists($events)]), ' ')}">
            <xsl:if test="$compact and exists(($holiday-labels, $events))">
                <xsl:attribute name="title" select="string-join(($holiday-labels, $events ! ac:label(.)), '; ')"/>
            </xsl:if>

            <xsl:choose>
                <xsl:when test="$day">
                    <a class="dnum" href="{$day/@rdf:about}"><xsl:value-of select="$number"/></a>
                </xsl:when>
                <xsl:when test="$compact and count($events) eq 1">
                    <a class="dnum" href="{$events/@rdf:about}"><xsl:value-of select="$number"/></a>
                </xsl:when>
                <!-- several: the LTLOD calendar day page lists them all -->
                <xsl:when test="$compact and exists($events)">
                    <a class="dnum" href="{lds:base()}calendar/{replace(string($date), '-', '/')}/"><xsl:value-of select="$number"/></a>
                </xsl:when>
                <xsl:otherwise>
                    <span class="dnum"><xsl:value-of select="$number"/></span>
                </xsl:otherwise>
            </xsl:choose>

            <xsl:choose>
                <xsl:when test="$compact">
                    <xsl:if test="count($events) gt 1">
                        <span class="count"><xsl:value-of select="count($events)"/></span>
                    </xsl:if>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:for-each select="$holiday-labels">
                        <span class="hol"><xsl:value-of select="."/></span>
                    </xsl:for-each>
                    <xsl:if test="exists($events)">
                        <ul class="items">
                            <xsl:for-each select="$events[position() le $ltlod:calendar-cell-items]">
                                <li><a href="{@rdf:about}" title="{ac:label(.)}"><xsl:value-of select="ac:label(.)"/></a></li>
                            </xsl:for-each>
                            <xsl:if test="count($events) gt $ltlod:calendar-cell-items">
                                <!-- the rest are on the LTLOD calendar day page -->
                                <li class="more"><a href="{lds:base()}calendar/{replace(string($date), '-', '/')}/">+<xsl:value-of select="count($events) - $ltlod:calendar-cell-items"/></a></li>
                            </xsl:if>
                        </ul>
                    </xsl:if>
                </xsl:otherwise>
            </xsl:choose>
        </td>
    </xsl:template>

    <xsl:template name="ltlod:CalendarStyle">
        <style>
.ltlod-cal { display: grid; gap: 1.5rem; grid-template-columns: 1fr; }
.ltlod-cal.compact { grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); }
.ltlod-cal-title { font-size: 1rem; font-weight: 600; margin: 0 0 .4rem; }
.ltlod-cal-title a { color: inherit; text-decoration: none; }
.ltlod-cal-grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ltlod-cal-grid th { font-size: .7rem; font-weight: 600; opacity: .6; text-align: left; padding: .2rem .3rem; }
.ltlod-cal-grid td { vertical-align: top; border: 1px solid rgba(127, 127, 127, .18); padding: .25rem .3rem; height: 6.5rem; font-size: .8rem; overflow: hidden; }
.ltlod-cal.compact .ltlod-cal-grid td { height: 2rem; font-size: .75rem; }
.ltlod-cal-grid td.pad { border-color: transparent; }
.ltlod-cal-grid td.weekend { background: rgba(127, 127, 127, .06); }
.ltlod-cal-grid td.today { box-shadow: inset 0 0 0 2px #2f6fde; }
.ltlod-cal-grid .dnum { font-weight: 600; text-decoration: none; }
.ltlod-cal-grid td.holiday .dnum { color: #b3261e; }
.ltlod-cal-grid td.busy:not(.holiday) .dnum { color: #2f6fde; }
.ltlod-cal-grid .hol { display: block; color: #b3261e; font-size: .7rem; line-height: 1.2; margin-top: .15rem; }
.ltlod-cal-grid .count { display: inline-block; margin-left: .2rem; font-size: .6rem; line-height: 1.3; padding: 0 .25rem; border-radius: .6rem; background: rgba(47, 111, 222, .15); vertical-align: 1px; }
.ltlod-cal-grid .items { list-style: none; margin: .2rem 0 0; padding: 0; }
.ltlod-cal-grid .items li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: .72rem; line-height: 1.35; }
        </style>
    </xsl:template>

</xsl:stylesheet>
