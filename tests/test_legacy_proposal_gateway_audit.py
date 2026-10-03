import pytest
from src.actuation.gateway import ActuatorGateway
from src.crypto.attestation import ActionAttestor

def test_authenticated_proposal_does_not_claim_physical_execution():
    key = b"k" * 32
    evidence = ActionAttestor(key).generate_attestation("ALLOW", 0.8, "state-1")
    assert ActuatorGateway(key).process_action_proposal(evidence) == (True, "AUTHENTICATED_PROPOSAL_ALLOW")

@pytest.mark.parametrize("evidence", [None, {}, {"payload": {"sequence_num": []}}, {"payload": {}, "signature": "é"}])
def test_malformed_proposal_rejected_without_crash(evidence):
    assert ActuatorGateway(b"k" * 32).process_action_proposal(evidence)[0] is False

def test_interlock_does_not_consume_unauthenticated_sequence():
    key = b"k" * 32
    gateway = ActuatorGateway(key)
    gateway.set_hardware_interlock(True)
    gateway.process_action_proposal({"payload": {"sequence_num": 1}, "signature": "forged"})
    gateway.set_hardware_interlock(False)
    signed = ActionAttestor(key).generate_attestation("ALLOW", 0.8, "state-1")
    assert gateway.process_action_proposal(signed)[0] is True

def test_nonfinite_attestation_is_not_authenticated():
    key = b"k" * 32
    signed = ActionAttestor(key).generate_attestation("ALLOW", float("nan"), "state-1")
    assert ActionAttestor.verify_attestation(signed, key) is False
