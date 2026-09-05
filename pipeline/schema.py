"""Data schemas for processed verses and manifest records."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class VerseRecord(BaseModel):
    id: str
    text_corpus: str
    canonical_citation: str
    sanskrit_text: Optional[str] = None
    transliteration: Optional[str] = None
    english_translation: Optional[str] = None
    translator: Optional[str] = None
    metadata: Dict[str, Any] = {}
