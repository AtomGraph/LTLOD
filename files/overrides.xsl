<?xml version="1.0" encoding="UTF-8"?>
<!--

    Shared XSLT overrides for the LTLOD end-user app, imported by BOTH
    files/client.xsl (client-side, compiled into the SEF for CSR) and
    files/layout.xsl (server-side render). Keeping the block suppression in both
    trees means the n-ary membership plumbing never renders in the first place —
    no "server renders the blocks, then CSR removes them" flash.

    Suppression is PROPERTY-CENTRIC, not type-centric: a resource is hidden only
    when it is a rendered target of the :Memberships 1:N view (app/ns.ttl) on the
    CURRENT page — identified by its incoming property via
    key('predicates-by-object', …) / the org:member link to this page's primary
    topic — never by bare rdf:type. So an org:Membership / time:Interval /
    time:Instant is hidden when it hangs off the person whose page this is, and
    stays visible anywhere it is the subject in its own right.

    key('resources', …), key('predicates-by-object', …), ldh:request-uri() and
    ac:absolute-path() all come from the imported LDH/Web-Client stylesheets and
    are available in both the server (Saxon) and client (Saxon-JS) contexts.

-->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY rdf    "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <!ENTITY org    "http://www.w3.org/ns/org#">
    <!ENTITY time   "http://www.w3.org/2006/time#">
    <!ENTITY foaf   "http://xmlns.com/foaf/0.1/">
]>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="&rdf;"
    xmlns:org="&org;"
    xmlns:time="&time;"
    xmlns:foaf="&foaf;"
    xmlns:ac="https://w3id.org/atomgraph/client#"
    xmlns:ldh="https://w3id.org/atomgraph/linkeddatahub#"
    xmlns:bs2="http://graphity.org/xsl/bootstrap/2.3.2"
    exclude-result-prefixes="#all">

    <!-- membership block: its org:member points to the current page's primary
         topic — exactly the :Memberships view relationship (org:member $about) -->
    <xsl:template match="*[@rdf:about]
                          [org:member/@rdf:resource = key('resources', ac:absolute-path(ldh:request-uri()))/foaf:primaryTopic/@rdf:resource]"
                  mode="bs2:Row" priority="10"/>

    <!-- interval block: object of a membership's org:memberDuring (self-scoping —
         only memberships carry org:memberDuring) -->
    <xsl:template match="*[@rdf:about][key('predicates-by-object', @rdf:about)/self::org:memberDuring]"
                  mode="bs2:Row" priority="10"/>

    <!-- instant block: object of an interval's time:hasBeginning / time:hasEnd -->
    <xsl:template match="*[@rdf:about][key('predicates-by-object', @rdf:about)/(self::time:hasBeginning | self::time:hasEnd)]"
                  mode="bs2:Row" priority="10"/>

</xsl:stylesheet>
