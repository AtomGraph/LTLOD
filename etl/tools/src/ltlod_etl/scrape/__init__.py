"""Fallback scraper framework — used ONLY where no structured source exists.

A Scraper subclass declares how to enumerate items and extract fields from
each page; the base class handles polite fetching and RDF emission so
individual scrapers stay declarative.
"""

from __future__ import annotations

import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator

import httpx
from rdflib import Dataset, URIRef

USER_AGENT = "LTLOD-ETL/0.1 (martynas@atomgraph.com)"


class Scraper(ABC):
    """Base class: subclasses implement items() and triples()."""

    delay_seconds: float = 1.0

    def __init__(self) -> None:
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT},
                                   timeout=60, follow_redirects=True)

    def fetch(self, url: str) -> httpx.Response:
        resp = self.client.get(url)
        resp.raise_for_status()
        time.sleep(self.delay_seconds)
        return resp

    @abstractmethod
    def items(self) -> Iterator[dict]:
        """Yield work items, e.g. {"id": ..., "url": ...}."""

    @abstractmethod
    def triples(self, item: dict) -> Iterator[tuple[URIRef, URIRef, URIRef, object]]:
        """Yield (graph, subject, predicate, object) quads for one item."""

    def run(self, output: str) -> None:
        ds = Dataset()
        count = 0
        for item in self.items():
            try:
                for graph, s, p, o in self.triples(item):
                    ds.graph(graph).add((s, p, o))
                count += 1
            except httpx.HTTPError as e:
                print(f"skip {item}: {e}", file=sys.stderr)
        ds.serialize(destination=output, format="trig")
        print(f"scraped {count} items -> {output}", file=sys.stderr)
