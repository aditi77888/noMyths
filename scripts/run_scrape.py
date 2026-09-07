"""
scripts/run_scrape.py

Deliberately narrow test harness — NOT the full pipeline runner yet.
Purpose: fetch ONE real hymn page, run it through SacredTextsScraper.parse_page(),
and print the resulting VerseRecords so you can eyeball whether the verse
split landed on real verse boundaries before we build cleaner/verse_segmenter
on top of it.

Usage:
    python scripts/run_scrape.py https://sacred-texts.com/hin/rigveda/rv10129.htm

If the output looks wrong (verses merged together, numbers misplaced,
missing verses), paste this script's output back and we fix
_HYMN_HEADING_RE / _VERSE_SPLIT_RE in sacred_texts_scraper.py together —
don't move on to cleaner.py against a scraper we haven't validated.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the project root importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.sacred_texts_scraper import SacredTextsScraper  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_scrape.py <hymn_page_url>")
        sys.exit(1)

    url = sys.argv[1]
    raw_dir = Path("data/raw/vedas/rigveda")
    scraper = SacredTextsScraper(raw_data_dir=raw_dir)

    print(f"Fetching (or reading from cache): {url}")
    raw_html = scraper._fetch(url)  # noqa: SLF001 — deliberate, this is a debug harness

    print("Parsing...")
    # Single-page debug run — NOT a real data_version. Real versions are
    # computed from the FULL text's fetched content by
    # pipeline/versioning.py, via scripts/run_pipeline.py. Using an obviously
    # fake version here so nobody mistakes debug output for a real run.
    debug_data_version = "DEBUG-single-page-not-a-real-version"
    records = scraper.parse_page(url, raw_html, debug_data_version)

    if not records:
        print(
            "\n⚠️  No VerseRecords produced. Likely causes:\n"
            "   - _HYMN_HEADING_RE didn't match this page's heading text\n"
            "   - This page isn't actually a hymn page (check the URL)\n"
            "Print raw_html (or open the cached .html file under data/raw/) to inspect.\n"
        )
        return

    print(f"\n✅ Parsed {len(records)} verse(s):\n")
    for r in records:
        print(f"--- {r.id} ---")
        print(f"Book {r.book}, Hymn {r.hymn}, Verse {r.verse}")
        print(f"English: {r.english[:200] if r.english else '(none)'}")
        print()

    # Dump full JSON too, in case a verse LOOKS right printed above but has
    # a subtle issue (trailing whitespace, wrong id, etc.) only visible raw.
    out_path = Path("data/interim/_debug_last_scrape.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Full JSON written to {out_path} for closer inspection.")


if __name__ == "__main__":
    main()