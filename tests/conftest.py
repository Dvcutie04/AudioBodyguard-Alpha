import pytest
from unittest.mock import MagicMock
from src.device_fabric.transaction import PhysicalTransactionManager
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin
from src.control.authorized_intent import AuthorizedActionIntent
from src.control.capability_lease import CapabilityLease
from src.device_fabric.contracts import DeviceState


@pytest.fixture
def hil_env():
    """Hardware-In-the-Loop test environment fixture."""
    adapter = MagicMock(name="HILAdapter")
    evaluator = PreconditionEvaluator(staleness_threshold_seconds=2.0)
    twin = DigitalTwin()
    manager = PhysicalTransactionManager(adapter, evaluator, twin)

    pre_state = DeviceState(power=True, volume=50.0, input_source="HDMI_1")
    target_state = DeviceState(power=True, volume=40.0, input_source="HDMI_1")

    intent = AuthorizedActionIntent(
        intent_id="req_capstone_test",
        device_id="tv_living_room",
        operation="REDUCE_VOLUME",
        expected_pre_state=pre_state,
        target_state=target_state,
        authorization_digest="auth_digest_mock",
        nonce="test-nonce-123"
    )

    lease = CapabilityLease(
        device_id="tv_living_room",
        lease_id="lease_capstone",
        subject_id="subj_test",
        capabilities=frozenset(["REDUCE_VOLUME"]),
        authorization_digest="auth_digest_mock",
        firmware_identity="omega-v1.0",
        protocol_version="1.0",
        nonce="test-nonce-123"
    )

    return manager, adapter, intent, lease
