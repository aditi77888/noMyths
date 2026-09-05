"""Pydantic models for API request/response payloads."""
from pydantic import BaseModel
from typing import List, Optional

class ClaimRequest(BaseModel):
    claim: str

class EvidenceItem(BaseModel):
    canonical_citation: str
    sanskrit_text: Optional[str] = None
    english_translation: Optional[str] = None
    source_name: str

class VerdictResponse(BaseModel):
    claim: str
    verdict: str
    confidence: float
    explanation: str
    evidence: List[EvidenceItem]
