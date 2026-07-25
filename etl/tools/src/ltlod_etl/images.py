"""Image URL liveness — keep only depiction/logo URLs that actually resolve.

Wikidata reconciliation (P18/P94/P154) and the lrs.lt scraper can reference
images that have since been deleted, renamed or moved; emitting a dead
``foaf:depiction`` pollutes the dataset and renders downstream as a broken
image. Callers normalize URLs with :func:`to_https` and drop the unreachable
ones via :func:`live_images` / :func:`reachable` before writing the triples.

The check follows redirects — a Commons ``Special:FilePath`` URL 302-redirects
to ``upload.wikimedia.org`` — and falls back from HEAD to a 1-byte ranged GET
for hosts that reject HEAD (e.g. lrs.lt).
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor

import httpx

from .wikidata import USER_AGENT

# Shared, thread-safe client (httpx.Client is safe across ThreadPoolExecutor
# workers); short timeout since these are liveness pings, not downloads.
_client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=15, follow_redirects=True)

# Status codes that mean "HEAD unsupported here" — retry once with a ranged GET.
_HEAD_UNSUPPORTED = frozenset({403, 405, 501})


def to_https(url: str) -> str:
    """Upgrade http:// Wikimedia URLs to https://.

    WDQS returns Commons image URIs with an http:// scheme; the https:// form
    is what renders in browsers and GitHub's image proxy and matches
    ``wikidata.COMMONS_FILEPATH``. Non-Wikimedia URLs are returned unchanged.
    """
    if url.startswith("http://") and "wikimedia.org" in url:
        return "https://" + url[len("http://"):]
    return url


def reachable(url: str) -> bool:
    """True if the URL resolves to a non-error status (following redirects)."""
    for method in ("HEAD", "GET"):
        try:
            resp = _client.request(
                method, url,
                headers={"Range": "bytes=0-0"} if method == "GET" else {},
            )
        except httpx.HTTPError:
            return False
        if resp.status_code < 400:
            return True
        if resp.status_code not in _HEAD_UNSUPPORTED:
            return False
    return False


def live_images(urls, *, workers: int = 16) -> set[str]:
    """Return the reachable subset of ``urls``; log each dropped URL to stderr."""
    unique = sorted({str(u) for u in urls})
    if not unique:
        return set()
    live: set[str] = set()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for url, ok in zip(unique, pool.map(reachable, unique)):
            if ok:
                live.add(url)
            else:
                print(f"  dead image skipped: {url}", file=sys.stderr)
    print(f"image liveness: {len(live)}/{len(unique)} reachable", file=sys.stderr)
    return live
