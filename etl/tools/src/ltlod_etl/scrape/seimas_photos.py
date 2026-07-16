"""Scrape current member photos from lrs.lt biography pages.

Example of the scraper framework; supplements Wikidata P18 photos (which cover
only ~half of current members) with the official portraits. Emits
foaf:depiction quads into each person's named graph.

Usage:
    uv run python -m ltlod_etl.scrape.seimas_photos \
        <persons.trig> <base-uri> <output.trig>
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator

from rdflib import Dataset, URIRef
from rdflib.namespace import FOAF

from . import Scraper

PHOTO_RE = re.compile(r'<img[^>]+src="(https?://[^"]*(?:seimo_nariu_foto|sn_foto|nuotraukos)[^"]*)"', re.I)


class SeimasPhotoScraper(Scraper):
    def __init__(self, persons_trig: str, base: str):
        super().__init__()
        self.base = base
        self.ds = Dataset()
        self.ds.parse(persons_trig, format="trig")

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
        html = self.fetch(item["url"]).text
        match = PHOTO_RE.search(html)
        if match:
            yield (item["doc"], item["person"], FOAF.depiction, URIRef(match.group(1)))


def main() -> None:
    persons_trig, base, output = sys.argv[1:4]
    SeimasPhotoScraper(persons_trig, base).run(output)


if __name__ == "__main__":
    main()
