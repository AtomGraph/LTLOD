<?xml version="1.0" encoding="UTF-8"?>
<!--

    Server-side layout override for the LTLOD end-user app.

    Five jobs:
    1. repoint the client-side XSLT bootstrap at our custom Saxon-JS stylesheet
       (files/client.xsl → client.xsl.sef.json) instead of the stock one
       (xhtml:Script below);
    2. import the shared files/overrides.xsl so the membership plumbing blocks
       are suppressed in the SERVER render too — otherwise the server emits them
       and the client removes them during CSR, causing a visible flash;
    3. restyle the header wordmark (ldh:Brand) with the same Lithuanian-tricolour
       mark as the footer one, so header and footer brand match (the text is the
       dataspace dct:title in config/dataspaces*.trig — keep it "linkeddata.lt",
       the footer wordmark's text). Server-rendered only, like the footer;
    4. social-preview image: og:image / twitter:image from the page's primary
       topic (coat of arms, portrait) when the document has none, else the
       linkeddata.lt card files/og-image.png (source: files/og-image.html), so a
       shared link always unfurls with a picture;
    5. replace the stock LinkedDataHub footer (ac:Footer) with the LTLOD one —
       our own wordmark, dataset shortcuts, source attribution and licence.
       The footer is server-rendered ONLY (layout.xsl applies ac:Footer once,
       client.xsl never re-renders it), so it lives here and not in
       overrides.xsl — no SEF rebuild needed after editing it.

    Imports the base layout.xsl and overrides only the xhtml:Script template's
    client-stylesheet parameter.

    Mounted over the end-user app's ac:stylesheet target
    (static/xsl/layout.xsl, config/dataspaces.trig), so it applies to the
    end-user app only — the admin app uses static/xsl/admin/layout.xsl and is
    untouched. The xhtml:Script signature mirrors the pinned LDH image
    (docker-compose.yml), which matches on the lds:origin() function.

-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY rdf    "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
]>
<xsl:stylesheet version="3.0"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:rdf="&rdf;"
    xmlns:ac="https://w3id.org/atomgraph/client#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:ldh="https://w3id.org/atomgraph/linkeddatahub#"
    xmlns:lds="https://w3id.org/atomgraph/linkeddatahub/dataspaces#"
    xmlns:srx="http://www.w3.org/2005/sparql-results#"
    exclude-result-prefixes="#all">

    <xsl:import href="../com/atomgraph/linkeddatahub/xsl/layout.xsl"/>
    <!-- imported last so its suppression templates take import precedence -->
    <xsl:import href="overrides.xsl"/>

    <!-- load our custom client SEF instead of the stock client.xsl.sef.json -->
    <xsl:template match="rdf:RDF[lds:origin()] | srx:sparql[lds:origin()]" mode="xhtml:Script">
        <xsl:param name="client-stylesheet" select="resolve-uri('static/lt/linkeddata/xsl/client.xsl.sef.json', lds:origin())" as="xs:anyURI"/>

        <xsl:apply-imports>
            <xsl:with-param name="client-stylesheet" select="$client-stylesheet"/>
        </xsl:apply-imports>
    </xsl:template>

    <!-- META: the stock og:/twitter: tags carry an image only when the page DOCUMENT has one (ac:image -
         foaf:img > foaf:logo > foaf:depiction), which ETL documents never do: the coat of arms or portrait
         hangs off its foaf:primaryTopic (#this). Use the topic's image when the document has none, else
         the linkeddata.lt card (frontpage, containers, entities without an image) -->
    <xsl:template match="rdf:RDF | srx:sparql" mode="xhtml:Meta">
        <xsl:variable name="doc" select="key('resources', ac:absolute-path(ldh:base-uri(.)))" as="element()*"/>

        <xsl:apply-imports/>

        <xsl:if test="not($doc[ac:image(.)])">
            <xsl:variable name="topic-image-raw" select="(($doc/foaf:primaryTopic/@rdf:resource/key('resources', ., root(.))) ! ac:image(.))[1] ! xs:anyURI(.)" as="xs:anyURI?"/>
            <!-- link unfurlers (Slack, Facebook, X) do not render SVG, which is what most coats of arms are;
                 Commons' Special:FilePath serves a PNG thumbnail when given ?width= -->
            <xsl:variable name="topic-image" select="if (ends-with(lower-case($topic-image-raw), '.svg') and contains($topic-image-raw, '/Special:FilePath/')) then xs:anyURI($topic-image-raw || '?width=630') else $topic-image-raw" as="xs:anyURI?"/>
            <xsl:variable name="image" select="($topic-image, resolve-uri('static/lt/linkeddata/og-image.png', lds:base()))[1]" as="xs:anyURI"/>

            <meta property="og:image" content="{$image}"/>
            <xsl:if test="empty($topic-image)">
                <meta property="og:image:width" content="1200"/>
                <meta property="og:image:height" content="630"/>
                <meta property="og:image:alt" content="linkeddata.lt — Lietuvos susietieji atvirieji duomenys"/>
            </xsl:if>
            <meta name="twitter:image" content="{$image}"/>
        </xsl:if>
    </xsl:template>

    <!-- HEADER wordmark: the stock ldh:Brand with the tricolour .mark of the footer wordmark below
         (end-user app only, so the stock template's admin-class branch is dropped) -->
    <xsl:template match="rdf:RDF[lds:dataspace-description()] | srx:sparql[lds:dataspace-description()]" mode="ldh:Brand" priority="1">
        <a class="ldh-wordmark" href="{lds:base()}">
            <span class="mark" style="background: linear-gradient(135deg, #FDB913 0%, #006A44 55%, #C1272D 100%);"></span>
            <span>
                <xsl:apply-templates select="lds:dataspace-description()" mode="ac:label"/>
            </span>
        </a>
    </xsl:template>

    <!-- FOOTER

         Same markup contract as the stock footer (app.css: .ldh-footer > .cols
         is a `1.4fr repeat(4, 1fr)` grid, so exactly one .brand-col plus FOUR
         .col children; each column is a .ftitle followed by bare <a> children;
         .legal holds two spans laid out space-between) — only the content is
         ours, so the LDH design system styles it with no extra CSS.

         The one visual deviation is the wordmark .mark, whose stock blue→violet
         gradient is restyled inline to the Lithuanian tricolour; the class keeps
         the size, radius, inset ring and the two dots.

         Content is end-user first: what the data is, where it came from, who
         owns it. Developer entry points (SPARQL endpoint, example queries, raw
         dataset downloads, the namespace ontology) live in one column here
         instead of on the frontpage.

         Elements are written unprefixed, like the stock template: the stylesheet
         declares XHTML as the default element namespace (xmlns on xsl:stylesheet
         above), so they land in the XHTML namespace like the surrounding markup —
         without it the serialiser emits a stray xmlns="" reset on the footer.
         Footer links are excluded from the client-side click interceptor
         (client.xsl's ixsl:onclick match skips ancestor .ldh-footer), so internal
         ones do a normal page load rather than CSR. -->

    <xsl:template match="rdf:RDF | srx:sparql" mode="ac:Footer">
        <div class="ldh-footer" role="contentinfo">
            <div class="cols">
                <div class="col brand-col">
                    <a class="ldh-wordmark" href="{lds:base()}">
                        <span class="mark" style="background: linear-gradient(135deg, #FDB913 0%, #006A44 55%, #C1272D 100%);"></span>
                        <span>linkeddata.lt</span>
                    </a>
                    <p>Lietuvos susietieji atvirieji duomenys: oficialių registrų duomenys vienoje vietoje — susieti tarpusavyje ir laisvai naudojami.</p>
                </div>
                <div class="col">
                    <p class="ftitle">Duomenys</p>
                    <a href="{resolve-uri('admin-units/', lds:base())}">Administraciniai vienetai</a>
                    <a href="{resolve-uri('persons/', lds:base())}">Seimo nariai</a>
                    <a href="{resolve-uri('parties/', lds:base())}">Partijos</a>
                    <a href="{resolve-uri('legal-entities/', lds:base())}">Juridiniai asmenys</a>
                    <a href="{resolve-uri('taxonomies/', lds:base())}">Klasifikatoriai</a>
                </div>
                <div class="col">
                    <p class="ftitle">Šaltiniai</p>
                    <a href="https://www.registrucentras.lt/" target="_blank">Registrų centras</a>
                    <a href="https://get.data.gov.lt/" target="_blank">get.data.gov.lt</a>
                    <a href="https://www.lrs.lt/" target="_blank">Seimo kanceliarija</a>
                    <a href="https://www.wikidata.org/" target="_blank">Wikidata</a>
                </div>
                <div class="col">
                    <p class="ftitle">Kūrėjams</p>
                    <a href="{resolve-uri('sparql', lds:base())}">SPARQL užklausos</a>
                    <a href="https://github.com/AtomGraph/LTLOD/blob/master/queries/EXAMPLES.md" target="_blank">Užklausų pavyzdžiai</a>
                    <a href="https://github.com/AtomGraph/LTLOD/tree/master/datasets/current" target="_blank">Atsisiųsti duomenis</a>
                    <a href="{resolve-uri('ns', lds:base())}">Vardų erdvė</a>
                </div>
                <div class="col">
                    <p class="ftitle">Projektas</p>
                    <a href="https://github.com/AtomGraph/LTLOD" target="_blank">Apie projektą</a>
                    <a href="https://github.com/AtomGraph/LTLOD/issues" target="_blank">Pranešti apie klaidą</a>
                    <a href="https://creativecommons.org/licenses/by/4.0/deed.lt" target="_blank">Licencija CC BY 4.0</a>
                    <a href="https://linkeddatahub.com" target="_blank">Sukurta su LinkedDataHub</a>
                </div>
            </div>
            <div class="legal">
                <span>© <xsl:value-of select="format-date(current-date(), '[Y]')"/> · Duomenys © Registrų centras, Seimo kanceliarija · CC BY 4.0</span>
                <span><xsl:value-of select="lds:base()"/></span>
            </div>
        </div>
    </xsl:template>

</xsl:stylesheet>
