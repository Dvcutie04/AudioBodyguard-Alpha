"""
AQSS-36-OMEGA
Physical Truth Runtime — Device Fabric Integration Tests
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.device_fabric.contracts import (
    ActuationReceipt,
    ActuationStatus,
    AuthorizedActionIntent,
    CapabilityLease,
    ContractViolation,
    DeviceIdentity,
    DeviceState,
    DeviceType,
)
from src.device_fabric.mocks.mock_tv import MockTV, MockTVAdapter


@pytest.fixture
def target_device_id() -> str:
    return "tv_integration_node_1"


@pytest.fixture
def mock_lease(target_device_id: str) -> CapabilityLease:
    now = datetime.now(timezone.utc)
    return CapabilityLease(
        lease_id="lease_int_101",
        subject_id="tx_manager_integration",
        device_id=target_device_id,
        capabilities=frozenset(["set_power", "set_volume", "set_muted", "set_input_source"]),
        valid_from=now - timedelta(seconds=2),
        expires_at=now + timedelta(seconds=60),
        authorized_epoch=42,
        max_world_state_age_ms=5000,
        max_clock_skew_ms=2000,
        nonce="nonce_int_fixed_seed",
    )


def test_mock_tv_identity_and_capabilities(target_device_id: str):
    """Verify MockTV initializes with valid DeviceIdentity and DeviceCapabilities."""
    tv = MockTV(target_device_id)

    assert tv.identity.device_id == target_device_id
    assert tv.identity.device_type == DeviceType.TV
    assert tv.identity.vendor == "MockCorp"
    assert tv.capabilities.device_id == target_device_id
    assert "set_volume" in tv.capabilities.capabilities


def test_mock_tv_state_digest_stability():
    """Verify DeviceState generates stable, deterministic state digests."""
    state_a = DeviceState(
        power=True,
        volume=25.0,
        muted=False,
        input_source="HDMI_2",
    )
    state_b = DeviceState(
        power=True,
        volume=25.0,
        muted=False,
        input_source="HDMI_2",
    )

    assert state_a.state_digest == state_b.state_digest


@pytest.mark.asyncio
async def test_full_actuation_flow_via_adapter(
    target_device_id: str,
    mock_lease: CapabilityLease,
):
    """Verify end-to-end execution of an AuthorizedActionIntent through the MockTVAdapter."""
    adapter = MockTVAdapter(target_device_id)

    expected_pre = adapter.device.state
    target = DeviceState(
        power=True,
        volume=75.0,
        muted=False,
        input_source="HDMI_1",
    )

    now_ts = datetime.now(timezone.utc).timestamp()
    intent = AuthorizedActionIntent(
        intent_id="intent_integration_99",
        device_id=target_device_id,
        operation="set_volume",
        target_state=target,
        expected_pre_state=expected_pre,
        authorization_digest="auth_digest_int_99",
        deadline_at=now_ts + 30.0,
    )

    # Verify authorization lease permits the operation
    assert mock_lease.permits(intent.operation)

    # Execute intent through adapter boundary
    receipt = await adapter.execute_intent(
        intent=intent,
        transaction_digest="tx_digest_integration_flow",
        capability_digest=mock_lease.lease_digest or "cap_digest_mock",
    )

    assert isinstance(receipt, ActuationReceipt)
    assert receipt.status == ActuationStatus.EXECUTED
    assert receipt.device_id == target_device_id
    assert adapter.device.state.volume == 75.0


@pytest.mark.asyncio
async def test_duplicate_intent_absorption(target_device_id: str):
    """Verify that duplicate intents are absorbed idempotently."""
    adapter = MockTVAdapter(target_device_id)

    target = DeviceState(
        power=True,
        volume=30.0,
        muted=False,
        input_source="HDMI_1",
    )

    intent = AuthorizedActionIntent(
        intent_id="intent_duplicate_id",
        device_id=target_device_id,
        operation="set_volume",
        target_state=target,
        expected_pre_state=adapter.device.state,
        authorization_digest="auth_digest_dup",
        deadline_at=datetime.now(timezone.utc).timestamp() + 30.0,
    )

    receipt1 = await adapter.execute_intent(intent)
    assert receipt1.status == ActuationStatus.EXECUTED

    receipt2 = await adapter.execute_intent(intent)
    assert receipt2.status == ActuationStatus.DUPLICATE_ABSORBED
