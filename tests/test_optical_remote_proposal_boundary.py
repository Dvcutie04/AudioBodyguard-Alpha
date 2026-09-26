import math

import pytest

from src.control.optical_remote import ButtonExtraction, OpticalRemoteMapper, RemoteHypothesis
from src.omotenashi.graceful_degradation import TrustGradient


def test_confidence_never_authorizes_an_optical_command():
    mapper = OpticalRemoteMapper()
    for score in (0.4, 0.7, 0.85, 0.9, 1.0):
        hypothesis = RemoteHypothesis("unknown", "media", "IR", "volume", score)
        result = mapper.verify_command(hypothesis)
        assert result["trust_verdict"]["action_type"] == "propose_for_review"
        assert result["trust_verdict"]["requires_confirmation"] is True
        assert result["execution_status"] == "NOT_EXECUTED"
        assert result["proposal_status"] == "REVIEW_REQUIRED"


def test_weak_evidence_does_not_create_an_executable_proposal():
    result = OpticalRemoteMapper().verify_command(
        RemoteHypothesis("unknown", "media", "unknown", "unknown", 0.35)
    )
    assert result["trust_verdict"]["action_type"] == "do_not_act"
    assert result["execution_status"] == "NOT_EXECUTED"
    assert result["proposal_status"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("bad", [True, None, "0.9", -0.01, 1.01, math.nan, math.inf, -math.inf])
def test_invalid_confidence_rejects_instead_of_entering_any_execution_path(bad):
    with pytest.raises(ValueError, match="confidence"):
        TrustGradient().evaluate_confidence(bad)


def test_inferred_remote_button_remains_a_proposal():
    mapper = OpticalRemoteMapper()
    hypothesis = mapper.generate_hypothesis(
        [ButtonExtraction("vol_up", "round", 0.1, 0.2)], ir_emitter_detected=True
    )
    result = mapper.verify_command(hypothesis)
    assert hypothesis.confidence_score == 0.85
    assert result["execution_status"] == "NOT_EXECUTED"
    assert result["proposal_status"] == "REVIEW_REQUIRED"
