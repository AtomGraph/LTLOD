"""Thin Wikidata clients: WDQS SPARQL and the OpenRefine-spec reconciliation service.

The reconciliation flow follows AutoGraph's ReconcileWikidata operation
(../AutoGraph/src/com/atomgraph/auto_graph/operations/reconcile_wikidata.py),
lifted off the web-algebra framework onto plain httpx.
"""

from __future__ import annotations

import json
import time

import httpx

USER_AGENT = "LTLOD-ETL/0.1 (https://github.com/pumba-lt/lt-lod; martynas@atomgraph.com)"
WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
RECONCILE_ENDPOINT = "https://wikidata-reconciliation.wmcloud.org/{lang}/api"
COMMONS_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"

_client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)


def sparql(query: str, retries: int = 3) -> list[dict]:
    """Run a SELECT against WDQS, return bindings as a list of {var: value} dicts."""
    for attempt in range(retries):
        try:
            resp = _client.get(
                WDQS_ENDPOINT,
                params={"query": query},
                headers={"Accept": "application/sparql-results+json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {var: b[var]["value"] for var in b}
                for b in data["results"]["bindings"]
            ]
        except (httpx.HTTPError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    return []


def reconcile(query: str, type_qid: str | None = None, properties: list[dict] | None = None,
              lang: str = "lt", min_score: float = 70.0) -> str | None:
    """Label-based match via the Wikidata reconciliation service.

    Returns the entity URI (http://www.wikidata.org/entity/Q...) of the best
    candidate at or above min_score, or None. `properties` uses OpenRefine hint
    format, e.g. [{"pid": "P17", "v": {"id": "Q37"}}].
    """
    q: dict = {"query": query}
    if type_qid:
        q["type"] = type_qid
    if properties:
        q["properties"] = properties

    resp = _client.post(
        RECONCILE_ENDPOINT.format(lang=lang),
        data={"queries": json.dumps({"q0": q})},
    )
    resp.raise_for_status()
    candidates = resp.json().get("q0", {}).get("result", [])
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.get("score", 0))
    if best.get("score", 0) < min_score:
        return None
    return f"http://www.wikidata.org/entity/{best['id']}"


def commons_url(filename: str) -> str:
    """Turn a Commons file name into a stable Special:FilePath URL."""
    return COMMONS_FILEPATH + httpx.URL(path=filename.replace(" ", "_")).path.lstrip("/")
