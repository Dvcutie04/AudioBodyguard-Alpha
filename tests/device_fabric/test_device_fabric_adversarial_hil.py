"""
AQSS-36-OMEGA
Physical Truth Runtime — Adversarial Hardware-in-the-Loop (HIL) Tests
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.device_fabric.contracts import (
    AuthorizedActionIntent,
    CapabilityLease,
    ContractViolation,
    DeviceState,
    DeviceType,
    VerificationStatus,
    verify_epoch_lock,
)
from src.device_fabric.mocks.mock_tv import MockTV, MockTVAdapter


def create_valid_lease(device_id: str = "tv_hil_target") -> CapabilityLease:
    """Helper to construct a contract-compliant CapabilityLease."""
    now = datetime.now(timezone.utc)
    return CapabilityLease(
        lease_id="lease_hil_001",
        subject_id="subject_hil_runner",
        device_id=device_id,
        capabilities=frozenset(["set_power", "set_volume", "set_muted", "set_input_source"]),
        valid_from=now - timedelta(seconds=5),
        expires_at=now + timedelta(seconds=35),
        authorized_epoch=100,
        max_world_state_age_ms=2000,
        max_clock_skew_ms=1000,
        nonce="nonce_hil_99823",
    )


def test_adversarial_lease_temporal_validation():
    """Verify that an expired capability lease correctly fails temporal validity checks."""
    now = datetime.now(timezone.utc)
    expired_lease = CapabilityLease(
        lease_id="lease_expired_001",
        subject_id="subject_hil_runner",
        device_id="tv_hil_target",
        capabilities=frozenset(["set_volume"]),
        valid_from=now - timedelta(seconds=60),
        expires_at=now - timedelta(seconds=10),
        authorized_epoch=100,
        max_world_state_age_ms=2000,
        max_clock_skew_ms=1000,
        nonce="nonce_expired_123",
    )

    assert not expired_lease.is_temporally_valid(now)


def test_adversarial_lease_permission_boundary():
    """Verify that a capability lease enforces strict permission limits."""
    lease = create_valid_lease()
    assert lease.permits("set_volume")
    assert not lease.permits("UNAUTHORIZED_ADMIN_COMMAND")


def test_adversarial_epoch_lock_tampering():
    """Verify that epoch mismatch between authorized state and observed physical world is rejected."""
    authorized_epoch = 100
    tampered_observed_epoch = 101

    res = verify_epoch_lock(
        authorized_epoch=authorized_epoch,
        observed_epoch=tampered_observed_epoch,
    )

    assert not res.allowed
    assert res.status == VerificationStatus.STATE_EPOCH_MISMATCH


@pytest.mark.asyncio
async def test_hil_adapter_actuation_lineage():
    """Verify that MockTVAdapter preserves lineage when executing an authorized intent."""
    adapter = MockTVAdapter("tv_hil_target")

    pre_state = DeviceState(
        power=True,
        volume=50.0,
        muted=False,
        input_source="HDMI_1",
    )
    target_state = DeviceState(
        power=True,
        volume=60.0,
        muted=False,
        input_source="HDMI_1",
    )

    intent = AuthorizedActionIntent(
        intent_id="intent_hil_001",
        device_id="tv_hil_target",
        operation="set_volume",
        target_state=target_state,
        expected_pre_state=pre_state,
        authorization_digest="auth_digest_hil_hash",
        deadline_at=datetime.now(timezone.utc).timestamp() + 10.0,
    )

    receipt = await adapter.execute_intent(
        intent=intent,
        transaction_digest="tx_digest_hil_test",
        capability_digest="cap_digest_hil_test",
    )

    assert receipt.action_id == "intent_hil_001"
    assert receipt.device_id == "tv_hil_target"
    assert receipt.transaction_digest == "tx_digest_hil_test"
    assert receipt.capability_digest == "cap_digest_hil_test"
    assert adapter.device.state.volume == 60.0
