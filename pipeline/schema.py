"""
pipeline/schema.py

Defines the canonical data shapes used across the whole pipeline:
scrapers -> cleaner -> verse_segmenter -> aligner -> metadata_tagger -> validator
-> embeddings -> retrieval -> api.

Every stage should import VerseRecord (or Citation) from here rather than
re-defining fields ad hoc. If a field needs to change, it changes once, here.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class VedaName(str, Enum):
    RIGVEDA = "rigveda"
    SAMAVEDA = "samaveda"
    YAJURVEDA_SHUKLA = "yajurveda_shukla"
    YAJURVEDA_KRISHNA = "yajurveda_krishna"
    ATHARVAVEDA = "atharvaveda"


class TextCategory(str, Enum):
    """Top-level scripture category — mirrors the Shruti/Smriti map we scoped earlier.
    Only VEDA_SAMHITA is populated in v1; the rest exist so later phases don't
    require a schema migration.
    """
    VEDA_SAMHITA = "veda_samhita"
    UPANISHAD = "upanishad"
    BRAHMANA = "brahmana"
    SMRITI = "smriti"
    ITIHASA = "itihasa"
    PURANA = "purana"
    GRIHYA_SUTRA = "grihya_sutra"


class SourceProvenance(BaseModel):
    """Where this record's text actually came from. This is what lets you answer
    'where did this verse come from' months from now, and what data_version /
    manifest.json point back into.
    """
    source_site: str  # e.g. "sacred-texts.com", "gretil"
    source_url: HttpUrl
    translator: Optional[str] = None  # e.g. "Griffith" — None for Sanskrit-only records
    translation_year: Optional[int] = None
    is_public_domain: bool = True
    license_note: Optional[str] = None
    retrieved_on: date
    data_version: str  # matches an entry in data/processed/manifest.json


class VerseRecord(BaseModel):
    """The canonical verse-level unit. One of these = one retrievable, citable
    chunk. Never store paragraph- or hymn-level chunks — verse level is what
    makes a citation like 'Rigveda 10.129.1' possible instead of 'somewhere in
    hymn 129'.
    """
    id: str  # stable synthetic key, e.g. "rigveda.10.129.1"

    category: TextCategory
    veda: Optional[VedaName] = None  # populated for veda_samhita category

    # Canonical addressing — the numbering scheme is per-text (see aligner.py
    # and configs/alignment_maps/ for how source numbering maps to this).
    book: int  # "Mandala" for Rigveda, "Kanda" for Atharvaveda, etc.
    hymn: int  # "Sukta" — chapter/hymn-equivalent
    verse: int

    sanskrit_devanagari: Optional[str] = None
    sanskrit_iast: Optional[str] = None  # romanized
    english: Optional[str] = None  # None only for the known Griffith gap-hymns

    # True when the English text was produced by our own LLM pipeline rather
    # than a public-domain human translation. Anything True here MUST also
    # carry review_status != "unreviewed" before it's allowed into the live
    # embedding index — enforced in validator.py, not here.
    is_llm_translated: bool = False
    review_status: Optional[str] = None  # "unreviewed" | "spot_checked" | "approved"

    provenance: SourceProvenance

    class Config:
        use_enum_values = True


class Citation(BaseModel):
    """What retrieval/verdict_generator.py hands back to the API layer —
    the minimal set of fields the frontend needs to render a verse card.
    Deliberately a subset of VerseRecord: the UI never needs provenance
    plumbing like data_version.
    """
    reference: str  # human-readable, e.g. "Rigveda 10.129.1"
    sanskrit_devanagari: Optional[str] = None
    english: Optional[str] = None
    translator: Optional[str] = None
    source_url: HttpUrl

    @classmethod
    def from_verse_record(cls, v: VerseRecord) -> "Citation":
        veda_label = v.veda.replace("_", " ").title() if v.veda else v.category
        return cls(
            reference=f"{veda_label} {v.book}.{v.hymn}.{v.verse}",
            sanskrit_devanagari=v.sanskrit_devanagari,
            english=v.english,
            translator=v.provenance.translator,
            source_url=v.provenance.source_url,
        )