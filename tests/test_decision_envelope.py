import pytest
from dataclasses import FrozenInstanceError
from audio_engine.decision_envelope import DecisionEnvelope

def test_envelope_preserves_trust_epoch():
    envelope = DecisionEnvelope(
        node_id="node_alpha_01",
        sequence_id=101,
        trust_epoch=15,
        decision_state="ESCALATE",
        effective_trust=0.92,
        trust_reason_codes=("TRUST_HEALTHY",),
        evidence_digest="sha256:abcdef..."
    )
    assert envelope.trust_epoch == 15
    assert envelope.node_id == "node_alpha_01"
    assert envelope.sequence_id == 101
    assert envelope.decision_state == "ESCALATE"
    assert envelope.effective_trust == 0.92
    assert envelope.trust_reason_codes == ("TRUST_HEALTHY",)
    assert envelope.evidence_digest == "sha256:abcdef..."

def test_envelope_is_immutable():
    envelope = DecisionEnvelope(
        node_id="node_alpha_01",
        sequence_id=101,
        trust_epoch=15,
        decision_state="NO_ACTION",
        effective_trust=1.0,
        trust_reason_codes=("TRUST_HEALTHY",),
        evidence_digest="sha256:123456..."
    )
    with pytest.raises(FrozenInstanceError):
        envelope.trust_epoch = 16
