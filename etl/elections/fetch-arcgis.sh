#!/usr/bin/env bash
# Fetch every feature of one VRK ArcGIS Online feature layer as Esri JSON.
# VRK publishes its election results map (rinkimai-vrk.opendata.arcgis.com) as public
# feature services; vrk.lt and its Spinta instance (atviriduomenys.vrk.lt) sit behind a
# Cloudflare bot challenge, these services do not. One feature per constituency (71), so
# a single page (maxRecordCount 2000) is the whole layer.
# Usage: fetch-arcgis.sh <service-name> <output.json> [geometry]
#   geometry  also return the polygons, in LKS-94 (EPSG:3346, easting/northing metres)
set -euo pipefail

service="$1"
out="$2"
geometry="${3:-}"

url="https://services5.arcgis.com/1eJSoE398Vejvs53/arcgis/rest/services/${service}/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
if [ -n "$geometry" ]; then
    url="${url}&returnGeometry=true&outSR=3346"
else
    url="${url}&returnGeometry=false"
fi

mkdir -p "$(dirname "$out")"
curl -fsSL --retry 3 --max-time 300 "$url" -o "${out}.tmp"

# ArcGIS reports errors with HTTP 200 and an "error" member; fail loudly on those and
# on empty layers (renamed/withdrawn services)
if jq -e '.error' "${out}.tmp" > /dev/null; then
    echo "ERROR: ${service}: $(jq -c '.error' "${out}.tmp")" >&2
    rm -f "${out}.tmp"
    exit 1
fi
n=$(jq '.features | length' "${out}.tmp")
if [ "$n" -eq 0 ]; then
    echo "ERROR: ${service} returned no features" >&2
    rm -f "${out}.tmp"
    exit 1
fi

mv "${out}.tmp" "$out"
echo "fetched ${service}: ${n} features -> ${out}" >&2
