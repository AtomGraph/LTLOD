"""Scrape current member photos from lrs.lt biography pages.

Example of the scraper framework; supplements Wikidata P18 photos (which cover
only ~half of current members) with the official portraits. Emits
foaf:depiction quads into each person's named graph.

Usage:
    uv run python -m ltlod_etl.scrape.seimas_photos \
        <persons.trig> <base-uri> <output.trig>
"""

from __future__ import annotations

import sys
from collections.abc import Iterator

from rdflib import Dataset, URIRef
from rdflib.namespace import FOAF

from .. import images
from . import Scraper

# The portrait: <div class="sn_narys_foto"><div class="foto"><img src="…/sn_foto/…">
PHOTO_XPATH = ("//div[contains(concat(' ', normalize-space(@class), ' '), ' sn_narys_foto ')]"
               "//img/@src")


class SeimasPhotoScraper(Scraper):
    def __init__(self, persons_trig: str, base: str):
        super().__init__()
        self.base = base
        self.ds = Dataset()
        # persons.trig is base-relative; resolve its graph/entity IRIs against the
        # base so the emitted photo quads land in the canonical named graphs.
        self.ds.parse(persons_trig, format="trig", publicID=base)

    def items(self) -> Iterator[dict]:
        for graph in self.ds.graphs():
            doc = graph.identifier
            person = graph.value(doc, FOAF.primaryTopic)
            if person is None:
                continue
            bio = graph.value(person, FOAF.isPrimaryTopicOf)
            if bio:
                yield {"doc": doc, "person": person, "url": str(bio)}

    def triples(self, item: dict) -> Iterator[tuple]:
        srcs = self.fetch_html(item["url"]).xpath(PHOTO_XPATH)
        if srcs:
            url = images.to_https(str(srcs[0]))
            if images.reachable(url):
                yield (item["doc"], item["person"], FOAF.depiction, URIRef(url))
            else:
                print(f"  dead portrait skipped: {url}", file=sys.stderr)


def main() -> None:
    persons_trig, base, output = sys.argv[1:4]
    SeimasPhotoScraper(persons_trig, base).run(output)


if __name__ == "__main__":
    main()
