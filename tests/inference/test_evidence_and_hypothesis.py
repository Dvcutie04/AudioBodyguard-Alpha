import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.inference.evidence_envelope import EvidenceEnvelope


def test_evidence_envelope_creation():
    envelope = EvidenceEnvelope()
    assert envelope is not None
