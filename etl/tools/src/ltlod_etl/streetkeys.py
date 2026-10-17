"""Re-key AR street centrelines (GraGatve) to Address Register street codes.

The spatial model `gragatve/GraGatve` numbers its centrelines with its own
`gat_kodas` (16 036–69 832) — a code space disjoint from the register's
`gatve/Gatve` `gat_kodas` (1 122 775–…) that LTLOD street URIs are minted from,
and no crosswalk is published. Both do carry the settlement and the name, so this
joins on the natural key

    (gyvenamoji_vietove.gyv_kodas, "<pavadinimas> <tipo_santrumpa>")

GraGatve's `pavadinimas` already includes the type abbreviation ("Smukučių g."),
Gatve splits it ("Smukučių" + "g."). Only current register streets (empty
`gat_iki`) are candidates; a key that is ambiguous on either side is skipped, never
guessed. Output is `{gat_kodas},{geometry}` for `ltlod-geo`; unmatched centrelines
are reported on stderr.

Usage:
    ltlod-streetkeys --spatial streets-geo-raw.csv --streets streets.csv \
        --output streets-geo.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter

csv.field_size_limit(sys.maxsize)

SETTLEMENT_COL = "gyvenamoji_vietove.gyv_kodas"


def street_key(row: dict) -> tuple[str, str]:
    name = row["pavadinimas"].strip()
    abbr = row["tipo_santrumpa"].strip()
    return row[SETTLEMENT_COL].strip(), f"{name} {abbr}" if abbr else name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spatial", required=True,
                        help="GraGatve CSV (gat_kodas, pavadinimas, gyv_kodas, geometry)")
    parser.add_argument("--streets", required=True, help="Gatve CSV (the streets fetch)")
    parser.add_argument("--geom-col", default="gatves", help="WKT geometry column")
    parser.add_argument("--output", required=True, help="{gat_kodas},{geometry} CSV")
    args = parser.parse_args()

    with open(args.streets, newline="") as f:
        current = [r for r in csv.DictReader(f) if not (r.get("gat_iki") or "").strip()]
    street_counts = Counter(street_key(r) for r in current)
    codes = {street_key(r): r["gat_kodas"] for r in current}

    with open(args.spatial, newline="") as f:
        spatial = list(csv.DictReader(f))
    spatial_counts = Counter((r[SETTLEMENT_COL].strip(), r["pavadinimas"].strip())
                             for r in spatial)

    matched, unmatched = [], []
    for r in spatial:
        key = (r[SETTLEMENT_COL].strip(), r["pavadinimas"].strip())
        if street_counts.get(key) == 1 and spatial_counts[key] == 1:
            matched.append((codes[key], r[args.geom_col]))
        else:
            unmatched.append(key)

    if not matched:
        print(f"ERROR: no centreline in {args.spatial} matched a street", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gat_kodas", args.geom_col])
        w.writerows(matched)
    print(f"re-keyed {len(matched)} street centrelines ({len(unmatched)} unmatched"
          f"{': ' + str(unmatched[:10]) if unmatched else ''}) -> {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
