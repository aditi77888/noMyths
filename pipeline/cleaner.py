"""
pipeline/cleaner.py

Runs BEFORE verse_segmenter.py. Scraped HTML->text is rarely clean enough to
split on verse numbers reliably — footnote markers, editorial brackets, and
inconsistent Unicode normalization all interfere with regex matching. This
stage exists so verse_segmenter.py can assume clean input and focus only on
"where are the verse boundaries," not "is this text well-formed."

Order matters: clean_page_text() runs on the FULL hymn-page text (before
verse splitting), because footnote markers often sit mid-verse and would
otherwise break verse_segmenter's boundary detection.
"""

from __future__ import annotations

import re
import unicodedata

# sacred-texts.com footnote markers appear inline as bracketed numbers,
# e.g. "...the golden germ.[1]..." — these are NOT part of the verse text
# and must be stripped before segmentation, or "[1]" can be mistaken for
# a verse-number boundary.
_FOOTNOTE_MARKER_RE = re.compile(r"\[\d+\]")

# Editorial insertions sacred-texts sometimes embeds in translations, e.g.
# "[i.e. the sun]" — these ARE part of the translator's rendering (Griffith
# uses brackets for implied words), so we do NOT strip these; only bare
# numeric footnote markers above are noise.

# Collapse any run of whitespace (including the newlines BeautifulSoup's
# get_text() introduces between HTML block elements) into a single space,
# EXCEPT we don't want to accidentally merge two separate verses if a page
# has no numbering between them — verse_segmenter runs on this already-
# collapsed text, so this must run first, not the other way round.
_WHITESPACE_RE = re.compile(r"\s+")


def clean_page_text(raw_text: str) -> str:
    """Clean a full hymn-page's extracted text, before verse segmentation."""
    text = unicodedata.normalize("NFC", raw_text)
    text = _FOOTNOTE_MARKER_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def clean_verse_text(verse_text: str) -> str:
    """Clean a single already-segmented verse's text. Lighter-touch than
    clean_page_text since whitespace collapsing already happened — this
    mainly handles per-verse trimming and stray punctuation left over from
    splitting (e.g. a leading period from '1. Then was...' -> '. Then was...').
    """
    text = verse_text.strip()
    text = re.sub(r"^[.\s]+", "", text)  # strip leftover leading punctuation from the split
    return text


def clean_sanskrit_text(text: str, script: str) -> str:
    """Sanskrit needs its own path: Devanagari and IAST have different
    normalization concerns.
    - devanagari: NFC normalization is critical — combining vowel signs
      (matras) can be represented in multiple equivalent byte sequences,
      and inconsistent normalization will make identical verses fail
      string-equality checks in validator.py's dedup logic.
    - iast: normalize NFC too (diacritics like ā, ī, ṛ are combining
      characters in some source encodings), then collapse whitespace.
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()