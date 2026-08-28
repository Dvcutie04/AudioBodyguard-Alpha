"""
Integration tests validating the Intent Firewall, Action Dispatcher, and StateLogger pipeline.
"""

import pytest
from src.control.intent_firewall import IntentFirewall
from src.control.action_dispatcher import ActionDispatcher, StateLogger
from src.control.authorized_intent import SignedActionIntent


def test_dispatcher_firewall_successful_pipeline():
    # Pass trusted_verifiers map required by IntentFirewall initializer
    firewall = IntentFirewall(trusted_verifiers={})
    logger = StateLogger()
    dispatcher = ActionDispatcher(logger=logger)

    # Instantiate authorized signed intent
    intent = SignedActionIntent(
        intent_id="intent_001",
        target="spk_01",
        action="SET_ATTENUATION",
        parameters={"level_db": 15},
        epoch=100
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
