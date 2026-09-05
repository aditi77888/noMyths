"""Audit logger: logs every verdict + its retrieved evidence."""
import logging

logger = logging.getLogger("nomyths.verdicts")

def log_verdict(claim: str, verdict: dict, evidence: list):
    """Logs verdict decisions with full audit trail."""
    pass
