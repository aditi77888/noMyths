"""
scrapers/base_scraper.py

Every concrete scraper (sacred_texts_scraper.py, gretil_scraper.py,
sanskritdocuments_scraper.py) implements this interface. Why bother with an
abstract base for what's "just HTTP + parsing":

1. run_scrape.py (the CLI entrypoint) can loop over every text in
   sources.yaml and dispatch to the right scraper by name, without knowing
   anything about that site's HTML structure.
2. Rate-limiting, retry, and raw-HTML caching are handled ONCE here, so a
   site-specific scraper only has to implement "what does this page look
   like" — not "how do I not get rate-limited."
3. Every scraper writes raw HTML to data/raw/ before parsing, unconditionally.
   If a parser has a bug, you re-run parsing against cached HTML instead of
   re-hitting the website.
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.schema import VerseRecord


class BaseScraper(ABC):
    """Subclass this for each source site. See sacred_texts_scraper.py for
    a concrete example.
    """

    # Seconds to wait between requests to the same site — be a polite
    # scraper, these are volunteer-run archives, not commercial APIs.
    REQUEST_DELAY_SECONDS: float = 1.0

    def __init__(self, raw_data_dir: Path, source_site: str):
        self.raw_data_dir = raw_data_dir
        self.source_site = source_site
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Shared machinery — do not override in subclasses.
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
    def _fetch(self, url: str) -> str:
        """GET a URL with retry/backoff, then cache the raw response to disk
        keyed by a hash of the URL. Returns the raw HTML/text either way —
        from cache if present, from the network if not.
        """
        cache_path = self._cache_path_for(url)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        time.sleep(self.REQUEST_DELAY_SECONDS)
        resp = requests.get(url, headers={"User-Agent": "NoMyths research bot (contact: <your-email>)"}, timeout=20)
        resp.raise_for_status()
        cache_path.write_text(resp.text, encoding="utf-8")
        return resp.text

    def _cache_path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.raw_data_dir / f"{digest}.html"

    # ------------------------------------------------------------------
    # Subclasses must implement these two — everything else is inherited.
    # ------------------------------------------------------------------

    @abstractmethod
    def list_page_urls(self, base_url: str) -> Iterable[str]:
        """Given a text's base/index URL (from sources.yaml), return every
        page URL that needs to be fetched (e.g. one URL per hymn).
        """
        raise NotImplementedError

    @abstractmethod
    def parse_page(self, url: str, raw_html: str, data_version: str) -> list[VerseRecord]:
        """Parse one fetched page into zero or more VerseRecords, stamping
        each with the given data_version. Zero results is valid — e.g. a
        table-of-contents page that isn't itself verse content.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Orchestration. Split into two phases on purpose:
    #   1. fetch_pages() — hits the network (or cache), populates
    #      data/raw/.../*.html for every page of this text.
    #   2. parse_all() — computes data_version from what's now cached,
    #      THEN parses. Parsing can't know its own data_version until
    #      fetching is done, since the version is a hash of the fetched
    #      content (see pipeline/versioning.py).
    # ------------------------------------------------------------------

    def fetch_pages(self, base_url: str) -> list[tuple[str, str, Path]]:
        """Fetch every page for this text. Returns (url, raw_html, cache_path)
        tuples — cache_path is what versioning.py hashes to compute
        data_version, so callers need it even though parse_page() doesn't.
        """
        results = []
        for page_url in self.list_page_urls(base_url):
            raw_html = self._fetch(page_url)
            results.append((page_url, raw_html, self._cache_path_for(page_url)))
        return results

    def parse_all(self, fetched_pages: list[tuple[str, str, Path]], data_version: str) -> list[VerseRecord]:
        """Parse already-fetched pages, stamping every record with the given
        data_version. Call compute_data_version() on the fetched pages'
        cache paths BEFORE calling this — see scripts/run_pipeline.py for
        the full sequence.
        """
        records: list[VerseRecord] = []
        for url, raw_html, _cache_path in fetched_pages:
            records.extend(self.parse_page(url, raw_html, data_version))
        return records