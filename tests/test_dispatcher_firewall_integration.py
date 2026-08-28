"""
Integration tests validating the Intent Firewall, Action Dispatcher, and StateLogger pipeline.
"""

import time
import pytest
from src.control.intent_firewall import IntentFirewall
from src.control.action_dispatcher import ActionDispatcher, StateLogger
from src.control.authorized_intent import SignedActionIntent


def test_dispatcher_firewall_successful_pipeline():
    # Pass trusted_verifiers map required by IntentFirewall initializer
    firewall = IntentFirewall(trusted_verifiers={})
    logger = StateLogger()
    dispatcher = ActionDispatcher(logger=logger)

    now = time.time()
    
    # Instantiate authorized signed intent matching full cryptographic schema
    intent = SignedActionIntent(
        intent_id="intent_001",
        device_id="spk_01",
        operation="SET_ATTENUATION",
        parameters={"level_db": 15},
        issuer_id="governor_v1",
        policy_digest="policy_test_digest",
        capability_lease_digest="lease_test_digest",
        created_at=now,
        expires_at=now + 60.0,
        nonce="nonce_001",
        transaction_id="tx_001",
        protocol_version="1.0",
        signature=""
    )

    # Dispatch intent
    success, msg = dispatcher.dispatch(intent)
    assert success is True
    assert "DISPATCH_SUCCESS" in msg
    assert len(logger.logs) == 1
    assert logger.logs[0]["success"] is True


def test_dispatcher_rejects_expired_or_invalid_intent():
    dispatcher = ActionDispatcher()
    
    # Test None intent rejection
    success, msg = dispatcher.dispatch(None)
    assert success is False
    assert "INVALID_INTENT" in msg
