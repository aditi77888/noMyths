"""
pipeline/versioning.py

data_version answers one question, reproducibly: "given this string, what raw
content and what pipeline code produced the verses that carry it?"

It is NOT hand-bumped. It's computed as:

    data_version = f"{text_id}-{pipeline_version}-{content_hash[:10]}"

    content_hash  = sha256 of the SORTED, CONCATENATED bytes of every cached
                    raw HTML file for that text (sorted so file-order never
                    changes the hash — dict/filesystem iteration order isn't
                    guaranteed).
    pipeline_version = from configs/pipeline_version.yaml (see that file's
                    comment for when to bump it).

Why both matter, not just one:
  - content_hash alone can't distinguish "re-scraped, source site fixed a
    typo" from "re-parsed with a fixed regex, same raw HTML."
  - pipeline_version alone can't tell you if sacred-texts.com's content
    changed between two scrapes.
  - Together, any change in either input produces a different data_version,
    and manifest.json records exactly which raw files + pipeline_version
    went into it.

This module is called AFTER all pages for a text are fetched (see
base_scraper.fetch_pages()) and BEFORE parse_page() runs — parsing needs to
know its data_version up front, it can't be patched in after the fact.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import yaml

_MANIFEST_PATH = Path("data/processed/manifest.json")
_PIPELINE_VERSION_CONFIG = Path("configs/pipeline_version.yaml")


def get_pipeline_version() -> str:
    config = yaml.safe_load(_PIPELINE_VERSION_CONFIG.read_text(encoding="utf-8"))
    return config["version"]


def compute_content_hash(raw_html_paths: list[Path]) -> str:
    """Hash the sorted, concatenated contents of every raw HTML file that
    went into a text. Sorting by path ensures the hash is deterministic
    regardless of filesystem iteration order.
    """
    hasher = hashlib.sha256()
    for path in sorted(raw_html_paths, key=lambda p: p.name):
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def compute_data_version(text_id: str, raw_html_paths: list[Path]) -> str:
    """The single function everything else calls. text_id is the key used
    in sources.yaml (e.g. "rigveda").
    """
    pipeline_version = get_pipeline_version()
    content_hash = compute_content_hash(raw_html_paths)
    return f"{text_id}-{pipeline_version}-{content_hash[:10]}"


def record_manifest_entry(
    text_id: str,
    data_version: str,
    raw_html_paths: list[Path],
    verse_count: int,
) -> None:
    """Write/update this text's entry in data/processed/manifest.json.
    Called once per full scrape+parse run of a text, AFTER parsing succeeds
    (so a failed parse doesn't get recorded as if it produced this version).
    """
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if _MANIFEST_PATH.exists():
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    manifest[text_id] = {
        "data_version": data_version,
        "pipeline_version": get_pipeline_version(),
        "content_hash": data_version.rsplit("-", 1)[-1],
        "generated_on": date.today().isoformat(),
        "source_file_count": len(raw_html_paths),
        "verse_count": verse_count,
    }

    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def get_current_data_version(text_id: str) -> str | None:
    """Look up the last recorded data_version for a text, e.g. to compare
    against a freshly computed one and detect 'nothing actually changed.'
    Returns None if this text has never been processed.
    """
    if not _MANIFEST_PATH.exists():
        return None
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = manifest.get(text_id)
    return entry["data_version"] if entry else None