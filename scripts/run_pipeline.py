from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from pipeline.versioning import (  # noqa: E402
    compute_data_version,
    get_current_data_version,
    record_manifest_entry,
)
from scrapers.sacred_texts_scraper import SacredTextsScraper  # noqa: E402

SOURCES_CONFIG = Path("configs/sources.yaml")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_pipeline.py <text_id>   (e.g. rigveda)")
        sys.exit(1)

    text_id = sys.argv[1]
    sources = yaml.safe_load(SOURCES_CONFIG.read_text(encoding="utf-8"))["texts"]

    if text_id not in sources:
        print(f"'{text_id}' not found in {SOURCES_CONFIG}")
        sys.exit(1)

    text_config = sources[text_id]
    if text_config.get("status") != "v1_active":
        print(
            f"⚠️  '{text_id}' is marked '{text_config.get('status')}', not 'v1_active'.\n"
            f"   Only Rigveda is validated end-to-end so far — proceeding anyway, "
            f"but expect scraper/alignment gaps for other texts."
        )

    base_url = text_config["english"]["base_url"]
    raw_dir = Path(f"data/raw/vedas/{text_id}")

    print(f"[1/4] Fetching all pages for '{text_id}' from {base_url} ...")
    scraper = SacredTextsScraper(raw_data_dir=raw_dir)
    fetched_pages = scraper.fetch_pages(base_url)
    print(f"      Fetched {len(fetched_pages)} page(s) (cache: {raw_dir})")

    print("[2/4] Computing data_version from fetched content...")
    cache_paths = [cache_path for _, _, cache_path in fetched_pages]
    new_version = compute_data_version(text_id, cache_paths)
    old_version = get_current_data_version(text_id)
    if old_version == new_version:
        print(f"      data_version unchanged ({new_version}) — no new content or code changes since last run.")
    else:
        print(f"      data_version: {old_version or '(none yet)'} -> {new_version}")

    print("[3/4] Parsing all fetched pages...")
    records = scraper.parse_all(fetched_pages, data_version=new_version)
    print(f"      Produced {len(records)} VerseRecord(s)")

    print("[4/4] Recording manifest entry...")
    record_manifest_entry(text_id, new_version, cache_paths, verse_count=len(records))

    out_path = Path(f"data/processed/vedas/{text_id}/_all_verses.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n✅ Done. {len(records)} verses written to {out_path}")
    print(f"   data_version: {new_version}  (see data/processed/manifest.json)")


if __name__ == "__main__":
    main()