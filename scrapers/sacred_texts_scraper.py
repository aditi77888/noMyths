"""
scrapers/sacred_texts_scraper.py

Concrete scraper for sacred-texts.com, covering:
  - English translations (Griffith et al.) — one HTML page per hymn
  - Rigveda Sanskrit ("rvsan") — one HTML page per VERSE

IMPORTANT — read before running:
This environment has no network access, so the selectors below are built
from the page structure we confirmed via search snippets (index pages,
book/hymn listing, and one sample verse page), NOT from fetching and
inspecting the live DOM byte-for-byte. Treat the regex/selectors here as a
strong first draft: run this against one real hymn page first, print the
parsed output, and adjust `_VERSE_SPLIT_RE` / `_HYMN_HEADING_RE` if the
actual markup differs. This is exactly why base_scraper caches raw HTML —
you can re-run parsing against the cache without re-hitting the site.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from pipeline.cleaner import clean_page_text, clean_verse_text
from pipeline.schema import SourceProvenance, TextCategory, VedaName, VerseRecord
from pipeline.verse_segmenter import split_numbered_verses
from scrapers.base_scraper import BaseScraper

# Matches "Rig-Veda, Book 10: HYMN CXXIX. Creation." style headings, or the
# simpler "HYMN CXXIX. Creation." fragment — captures the roman-numeral hymn
# number and (optionally) the book number.
_HYMN_HEADING_RE = re.compile(
    r"(?:Book\s+(?P<book>\d+).*?)?HYMN\s+(?P<hymn_roman>[IVXLCDM]+)\.?\s*(?P<deity>[^.]*)",
    re.IGNORECASE,
)

# NOTE: verse-splitting regex has moved to pipeline/verse_segmenter.py as
# "griffith_inline" — validated against a real page (Rigveda 10.129, all 7
# verses confirmed correct). Kept here only as a named reference so it's
# obvious which pattern this scraper depends on.
_VERSE_SPLIT_PATTERN_NAME = "griffith_inline"


def _roman_to_int(roman: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(roman.upper()):
        val = values[ch]
        total += -val if val < prev else val
        prev = val
    return total


class SacredTextsScraper(BaseScraper):
    def __init__(self, raw_data_dir):
        super().__init__(raw_data_dir, source_site="sacred-texts.com")

    # ------------------------------------------------------------------

    def list_page_urls(self, base_url: str) -> Iterable[str]:
        """Fetch the text's index page and return every hymn-page link found
        in the main content area. sacred-texts index pages are a flat list
        of <a href="rvBBHHH.htm">Rig-Veda Book N: HYMN ...</a> links.
        """
        index_html = self._fetch(base_url)
        soup = BeautifulSoup(index_html, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Skip navigation links (index, previous, next) — real hymn
            # pages on this site follow a rvBBHHH.htm-style naming pattern.
            if re.search(r"\.htm$", href) and "index" not in href.lower():
                urls.append(urljoin(base_url, href))
        return urls

    def parse_page(self, url: str, raw_html: str, data_version: str) -> list[VerseRecord]:
        soup = BeautifulSoup(raw_html, "html.parser")
        page_text = clean_page_text(soup.get_text("\n"))

        heading_match = _HYMN_HEADING_RE.search(page_text)
        if not heading_match:
            # Not a hymn page (e.g. a book-index sub-page) — nothing to parse.
            return []

        book = int(heading_match.group("book")) if heading_match.group("book") else self._book_from_url(url)
        hymn = _roman_to_int(heading_match.group("hymn_roman"))

        # Isolate the body text after the heading for verse splitting.
        body_start = heading_match.end()
        body_text = page_text[body_start:]

        verses = split_numbered_verses(body_text, pattern_name=_VERSE_SPLIT_PATTERN_NAME)

        records = []
        for verse_num, verse_text in verses.items():
            records.append(
                VerseRecord(
                    id=f"rigveda.{book}.{hymn}.{verse_num}",
                    category=TextCategory.VEDA_SAMHITA,
                    veda=VedaName.RIGVEDA,
                    book=book,
                    hymn=hymn,
                    verse=verse_num,
                    english=clean_verse_text(verse_text),
                    provenance=SourceProvenance(
                        source_site=self.source_site,
                        source_url=url,
                        translator="Griffith",
                        translation_year=1896,
                        is_public_domain=True,
                        retrieved_on=date.today(),
                        data_version=data_version,
                    ),
                )
            )
        return records

    # ------------------------------------------------------------------

    @staticmethod
    def _book_from_url(url: str) -> int:
        """Fallback book-number extraction from filename, e.g. rv10129.htm
        -> book 10. Only used if the heading text itself didn't state the
        book number (some hymn pages only restate it on the index page).
        """
        match = re.search(r"rv(\d{1,2})\d{3}\.htm", url)
        return int(match.group(1)) if match else 0