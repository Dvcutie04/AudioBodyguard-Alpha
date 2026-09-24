import time
import pytest
from src.control.crypto_identity import KeyPair
from src.control.capability_lease import SignedCapabilityLease
from src.control.authorized_intent import SignedActionIntent
from src.control.intent_firewall import IntentFirewall, AuthRejectionCode
from src.control.action_dispatcher import ActionDispatcher


@pytest.fixture
def dispatcher_env():
    governor_key = KeyPair.generate()
    verifier = governor_key.public_verifier
    firewall = IntentFirewall(trusted_verifiers={governor_key.key_id: verifier})
    dispatcher = ActionDispatcher(firewall=firewall)
    now = time.time()
    
    lease_data = {
        "device_id": "spk_01",
        "capability_digest": "cap_audio",
        "firmware_identity": "v1.0",
        "protocol_version": "1.0",
        "issued_at": now,
        "expires_at": now + 60.0,
        "nonce": "lease_nonce_01",
        "issuer_id": governor_key.key_id
    }
    lease_sig = governor_key.sign(SignedCapabilityLease(**lease_data, signature="").canonical_bytes)
    lease = SignedCapabilityLease(**lease_data, signature=lease_sig)
    
    intent_data = {
        "intent_id": "int_01",
        "device_id": "spk_01",
        "operation": "SET_ATTENUATION",
        "parameters": {"db": 15.0},
        "issuer_id": governor_key.key_id,
        "policy_digest": "policy_strict",
        "capability_lease_digest": lease.payload_digest,
        "created_at": now,
        "expires_at": now + 15.0,
        "nonce": "intent_nonce_01",
        "transaction_id": "tx_01",
        "protocol_version": "1.0"
    }
    intent_sig = governor_key.sign(SignedActionIntent(**intent_data, signature="").canonical_bytes)
    intent = SignedActionIntent(**intent_data, signature=intent_sig)
    
    return dispatcher, governor_key, lease, intent, intent_data


def test_dispatcher_executes_valid_intent(dispatcher_env):
    dispatcher, _, lease, intent, _ = dispatcher_env
    res = dispatcher.dispatch(intent, lease)
    assert res["status"] == "EXECUTED"
    assert res["intent_id"] == "int_01"


def test_dispatcher_rejects_invalid_signature(dispatcher_env):
    dispatcher, governor_key, lease, _, raw_intent = dispatcher_env
    tampered = {**raw_intent, "parameters": {"db": 99.0}}
    bad_intent = SignedActionIntent(**tampered, signature="bad_sig")
    res = dispatcher.dispatch(bad_intent, lease)
    assert res["status"] == "REJECTED"
    assert res["code"] == AuthRejectionCode.AUTH_SIGNATURE_INVALID.value


def test_dispatcher_handles_logger_exception(dispatcher_env):
    _, governor_key, lease, _, raw_intent = dispatcher_env
    class FaultyLogger:
        def log_event(self, data):
            raise RuntimeError("Database log failure")
    firewall = IntentFirewall(trusted_verifiers={governor_key.key_id: governor_key.public_verifier})
    dispatcher = ActionDispatcher(firewall=firewall, logger=FaultyLogger())
    tampered = {**raw_intent, "parameters": {"db": 99.0}}
    bad_intent = SignedActionIntent(**tampered, signature="bad_sig")
    res = dispatcher.dispatch(bad_intent, lease)
    assert res["status"] == "REJECTED"


def test_dispatcher_fallback_logger(dispatcher_env):
    _, governor_key, lease, _, raw_intent = dispatcher_env
    class FallbackLogger:
        def __init__(self):
            self.logged = False
        def log(self, data):
            self.logged = True
    
    logger = FallbackLogger()
    firewall = IntentFirewall(trusted_verifiers={governor_key.key_id: governor_key.public_verifier})
    dispatcher = ActionDispatcher(firewall=firewall, logger=logger)
    tampered = {**raw_intent, "parameters": {"db": 99.0}}
    bad_intent = SignedActionIntent(**tampered, signature="bad_sig")
    res = dispatcher.dispatch(bad_intent, lease)
    assert res["status"] == "REJECTED"
    assert logger.logged is True
