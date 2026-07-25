"""WGS84 coordinates + geometry for LTLOD admin units → geo:lat/geo:long + gs:asWKT.

The AR spatial (`erdviniai duomenys`) models on get.data.gov.lt carry authoritative
polygons in LKS-94 / EPSG:3346 (projected metres). This tool reads such a CSV
(`{code},{WKT geometry}`) and, per unit, emits into the entity's own named graph:

    <admin-units/{code}/#this>
        geo:lat  "54.6817"^^xsd:decimal ;                 # representative point
        geo:long "25.2537"^^xsd:decimal ;
        gs:asWKT "POLYGON((25.2 54.6, …))"^^gs:wktLiteral. # simplified boundary (opt)

The graph name equals the entity document, so both merge on load (the alignments.trig
convention). LinkedDataHub plots a resource on a map from geo:lat+geo:long (a marker)
and/or gs:asWKT (a polygon) — both keyed off the resource's own DESCRIBE — so this is
what unlocks ac:MapMode for admin-unit listings. Point emit follows AutoGraph's
home-location wizard (geo:lat/geo:long xsd:decimal).

The WKT boundary is optional (`--simplify TOL`): the source polygon is Douglas–Peucker
simplified by TOL metres BEFORE reprojection (metric, latitude-independent tolerance),
reprojected, and written as BARE WGS84 lon-lat WKT (no CRS-URI prefix — OpenLayers'
ol.format.WKT can't parse one) typed gs:wktLiteral. Without --simplify, only the point
is emitted (e.g. the 20k-settlement layer stays point-only). LDH does no client-side
simplification, so keep TOL sane (a few tens of metres) for browser render cost.

Usage:
    ltlod-geo --base https://linkeddata.lt/ \
        --input graseniunija.csv --code-col sen_kodas --geom-col seniunijos \
        --simplify 50 --output elderships-geo.trig

The output is written absolute and relativized on write (etl/lib/relativize.sh), same
as reconcile.py. --base is the publicID the graph/entity IRIs are minted against.

⚠ EPSG:3346 axis order is (Northing, Easting): the WKT stores the ~6·10⁶ northing
first, the ~3–6·10⁵ easting second. shapely reads ordinates positionally (first→.x,
second→.y), so .x is the northing and .y is the easting; pyproj (always_xy=True) wants
(easting, northing) and returns (lon, lat) — hence the (pt.y, pt.x) / (y, x) swaps.
Every emitted point is bounds-checked against Lithuania's bounding box — a swapped
axis lands far outside and fails the run.
"""

from __future__ import annotations

import argparse
import csv
import sys

from pyproj import Transformer
from rdflib import Dataset, Literal, Namespace, URIRef
from rdflib.namespace import XSD
from shapely import to_wkt, wkt
from shapely.ops import transform as shapely_transform

GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
GSP = Namespace("http://www.opengis.net/ont/geosparql#")

DEFAULT_BASE = "https://linkeddata.lt/"
DEFAULT_SOURCE_CRS = "EPSG:3346"

# Lithuania bounding box (WGS84), with margin — a swapped/mis-projected axis lands
# far outside this and aborts the run rather than emitting garbage coordinates.
LAT_MIN, LAT_MAX = 53.5, 56.6
LON_MIN, LON_MAX = 20.5, 27.0

# CSV cells hold whole polygons/multipolygons; lift the field-size cap accordingly.
csv.field_size_limit(sys.maxsize)


def _reproject(geom, transformer: Transformer):
    """Reproject a source-CRS geometry to WGS84 lon-lat. Source ordinates are
    (northing=x, easting=y); always_xy transformer wants (easting, northing) → (lon, lat)."""
    return shapely_transform(lambda x, y: transformer.transform(y, x), geom)


def build_features(rows, code_col: str, geom_col: str, transformer: Transformer,
                   simplify: float | None) -> tuple[list[tuple], int]:
    """(code, lat, lon, wkt|None) per row with a non-empty valid geometry; count skipped."""
    features, skipped = [], 0
    for row in rows:
        code = (row.get(code_col) or "").strip()
        geom_wkt = (row.get(geom_col) or "").strip()
        if not code or not geom_wkt:
            skipped += 1
            continue
        try:
            geom = wkt.loads(geom_wkt)
        except Exception:
            skipped += 1
            continue
        if geom.is_empty:
            skipped += 1
            continue
        pt = geom.representative_point()          # inside even for concave/multipart
        lon, lat = transformer.transform(pt.y, pt.x)
        boundary = None
        if simplify is not None:
            simp = geom.simplify(simplify, preserve_topology=True)
            # bare WGS84 lon-lat WKT, ~0.1 m precision (trim trailing zeros)
            boundary = to_wkt(_reproject(simp, transformer), rounding_precision=6)
        features.append((code, round(lat, 6), round(lon, 6), boundary))
    return features, skipped


def check_bounds(features: list[tuple]) -> list[tuple]:
    return [f for f in features if not (LAT_MIN <= f[1] <= LAT_MAX and LON_MIN <= f[2] <= LON_MAX)]


def write_geo(features: list[tuple], base: str, output: str) -> None:
    ds = Dataset()
    ds.bind("geo", GEO, override=True, replace=True)
    ds.bind("gsp", GSP, override=True, replace=True)
    for code, lat, lon, boundary in features:
        entity = URIRef(f"{base}admin-units/{code}/#this")
        g = ds.graph(URIRef(f"{base}admin-units/{code}/"))
        g.add((entity, GEO.lat, Literal(f"{lat:.6f}", datatype=XSD.decimal)))
        g.add((entity, GEO.long, Literal(f"{lon:.6f}", datatype=XSD.decimal)))
        if boundary is not None:
            g.add((entity, GSP.asWKT, Literal(boundary, datatype=GSP.wktLiteral)))
    ds.serialize(destination=output, format="trig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="spatial CSV (code + WKT geometry)")
    parser.add_argument("--code-col", required=True, help="natural-key column (e.g. gyv_kodas)")
    parser.add_argument("--geom-col", required=True, help="WKT geometry column (e.g. gyv_vietoves)")
    parser.add_argument("--base", default=DEFAULT_BASE, help="publicID for minting graph/entity IRIs")
    parser.add_argument("--output", required=True, help="geo TriG output")
    parser.add_argument("--source-crs", default=DEFAULT_SOURCE_CRS, help="source CRS (default EPSG:3346)")
    parser.add_argument("--simplify", type=float, default=None, metavar="METRES",
                        help="also emit gs:asWKT, Douglas–Peucker simplified by this tolerance "
                             "(source-CRS metres) before reprojection; omit for point-only")
    args = parser.parse_args()

    transformer = Transformer.from_crs(args.source_crs, "EPSG:4326", always_xy=True)
    with open(args.input, newline="") as f:
        features, skipped = build_features(csv.DictReader(f), args.code_col, args.geom_col,
                                           transformer, args.simplify)

    if not features:
        print(f"ERROR: {args.input} yielded no coordinates", file=sys.stderr)
        sys.exit(1)

    out_of_bounds = check_bounds(features)
    if out_of_bounds:
        print(f"ERROR: {len(out_of_bounds)} point(s) outside Lithuania's bbox "
              f"(lat {LAT_MIN}–{LAT_MAX}, lon {LON_MIN}–{LON_MAX}) — likely an axis/CRS "
              f"mix-up. First few: {[f[:3] for f in out_of_bounds[:5]]}", file=sys.stderr)
        sys.exit(1)

    write_geo(features, args.base, args.output)
    kind = "points + geometry" if args.simplify is not None else "points"
    print(f"geocoded {len(features)} units [{kind}] ({skipped} skipped: no/invalid geometry) "
          f"-> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
