"""
pipeline/verse_segmenter.py

Splits a cleaned hymn/chapter's body text into {verse_number: verse_text}.

This logic used to live inline in sacred_texts_scraper.py as a private
method. Now that it's been validated against a real page (Rigveda 10.129,
confirmed all 7 verses split correctly), it's pulled out here so:
  1. sacred_texts_scraper.py's OTHER Vedas (Samaveda, Yajurveda, Atharvaveda)
     can reuse the same splitter if their pages follow the same
     "N followed by verse text" convention.
  2. gretil_scraper.py / sanskritdocuments_scraper.py can reuse it too, or
     register their own SPLIT_PATTERNS entry if their source formats a
     verse boundary differently.
  3. If we ever need to fix verse splitting, there's one place to fix it,
     not one copy per scraper.

Each source format gets its own named pattern in SPLIT_PATTERNS rather than
one "smart" universal regex — verse-numbering conventions genuinely differ
across texts (inline "1 text" vs "||1||" danda-style markers vs separate
line-per-verse), and a single regex trying to handle all of them invites
silent mis-splits on the ones it wasn't tested against.
"""

from __future__ import annotations

import re

# Validated against sacred-texts.com Griffith Rigveda pages (confirmed
# correct on 10.129, all 7 verses). Matches an inline verse number followed
# by the start of the verse text, e.g. "1 THEN was not..." "2 Death was..."
GRIFFITH_INLINE_NUMBER = re.compile(r"(?:^|\s)(\d{1,3})[.\s]+(?=[A-ZŚṚĀĪŪ])")

# Sanskrit texts using traditional double-danda verse-end markers, e.g.
# "...śive te santu panthānaḥ ||1||" — the number sits AFTER the verse text,
# not before it. NOT YET VALIDATED — placeholder for when we scrape
# sanskritdocuments.org / GRETIL sources for the other 3 Vedas.
DANDA_TRAILING_NUMBER = re.compile(r"\|\|(\d{1,3})\|\|")

SPLIT_PATTERNS = {
    "griffith_inline": GRIFFITH_INLINE_NUMBER,
    "danda_trailing": DANDA_TRAILING_NUMBER,
}


def split_numbered_verses(body_text: str, pattern_name: str = "griffith_inline") -> dict[int, str]:
    """Split body_text into {verse_number: verse_text} using the named
    pattern from SPLIT_PATTERNS. Raises KeyError on an unknown pattern name
    deliberately — silently falling back to a default would risk applying
    the wrong convention to a text that needs a different one.
    """
    pattern = SPLIT_PATTERNS[pattern_name]

    if pattern_name == "griffith_inline":
        return _split_leading_number(body_text, pattern)
    elif pattern_name == "danda_trailing":
        return _split_trailing_number(body_text, pattern)
    raise NotImplementedError(f"No split strategy wired up for pattern '{pattern_name}'")


def _split_leading_number(body_text: str, pattern: re.Pattern) -> dict[int, str]:
    """For patterns where the verse number PRECEDES the verse text."""
    parts = pattern.split(body_text)
    verses: dict[int, str] = {}
    it = iter(parts[1:])  # parts[0] is whatever precedes the first verse number
    for num_str, text in zip(it, it):
        verses[int(num_str)] = text.strip()
    return verses


def _split_trailing_number(body_text: str, pattern: re.Pattern) -> dict[int, str]:
    """For patterns where the verse number FOLLOWS the verse text (e.g.
    danda-style ||N|| markers). Splitting strategy is inverted relative to
    the leading-number case: the text comes first in each pair, not the number.
    """
    matches = list(pattern.finditer(body_text))
    verses: dict[int, str] = {}
    prev_end = 0
    for m in matches:
        verse_text = body_text[prev_end : m.start()].strip()
        verse_num = int(m.group(1))
        verses[verse_num] = verse_text
        prev_end = m.end()
    return verses