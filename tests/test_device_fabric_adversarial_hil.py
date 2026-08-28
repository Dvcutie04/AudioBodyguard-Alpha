import time
import pytest

from src.device_fabric.contracts import (
    AuthorizedActionIntent, CapabilityLease, DeviceState, TransactionState
)
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin
from src.device_fabric.transaction import PhysicalTransactionManager
from src.device_fabric.mocks.mock_tv import MockTVAdapter


@pytest.fixture
def hil_env():
    adapter = MockTVAdapter("tv_hil_target")
    evaluator = PreconditionEvaluator(staleness_threshold_seconds=2.0)
    twin = DigitalTwin()
    
    # Register a strict HIL acoustic safety constraint (Max Vol 80)
    twin.register_constraint(
        "tv_hil_target", 
        lambda curr, target: target.volume <= 80.0
    )
    
    manager = PhysicalTransactionManager(adapter, evaluator, twin)
    
    # Base baseline intent
    pre_state = DeviceState(power=True, volume=50.0, input_source="HDMI_1")
    target = DeviceState(power=True, volume=44.0, input_source="HDMI_1", payload={"delta_db": 6.0})
    
    intent = AuthorizedActionIntent(
        intent_id="hil_act_001",
        device_id="tv_hil_target",
        operation="REDUCE_VOLUME",
        target_state=target,
        expected_pre_state=pre_state,
        authorization_digest="auth_hash_hil",
        deadline_at=time.time() + 5.0
    )
    
    lease = CapabilityLease(
        device_id="tv_hil_target",
        capability_digest="mock_cap_sha256_001",
        firmware_identity="1.0.0-mock",
        protocol_version="1.0",
        issued_at=time.time(),
        expires_at=time.time() + 30.0,
        nonce="nonce_hil",
        issuer="gov_1"
    )
    
    return manager, adapter, intent, lease


@pytest.mark.asyncio
async def test_hil_adversarial_stale_telemetry_rejection(hil_env, monkeypatch):
    manager, adapter, intent, lease = hil_env
    
    # ADVERSARIAL: Device network is lagging. Telemetry is 10 seconds old.
    async def stale_observe():
        return DeviceState(
            power=True, volume=50.0, input_source="HDMI_1", 
            observed_at=time.time() - 10.0  # Older than 2.0s threshold
        )
    monkeypatch.setattr(adapter, "observe_state", stale_observe)
    
    status, err = await manager.execute_transaction(intent, lease)
    
    assert status == TransactionState.FAILED_DRIFT
    assert "STALE" in err


@pytest.mark.asyncio
async def test_hil_adversarial_lease_replay_attack(hil_env):
    manager, adapter, intent, lease = hil_env
    
    # ADVERSARIAL: Malicious or buggy process tries to reuse a lease that expired 1 second ago
    expired_lease = CapabilityLease(
        device_id=lease.device_id,
        capability_digest=lease.capability_digest,
        firmware_identity=lease.firmware_identity,
        protocol_version=lease.protocol_version,
        issued_at=time.time() - 100,
        expires_at=time.time() - 1,  # Expired
        nonce="replayed_nonce",
        issuer="gov_1"
    )
    
    status, err = await manager.execute_transaction(intent, expired_lease)
    
    assert status == TransactionState.FAILED_VERIFICATION
    assert "expired" in err


@pytest.mark.asyncio
async def test_hil_adversarial_digital_twin_safety_trip(hil_env):
    manager, adapter, intent, lease = hil_env
    
    # ADVERSARIAL: AI hallucinated a dangerous acoustic target state (Vol 100)
    dangerous_target = DeviceState(power=True, volume=100.0, input_source="HDMI_1")
    dangerous_intent = AuthorizedActionIntent(
        intent_id="hil_act_danger",
        device_id="tv_hil_target",
        operation="SET_VOLUME",
        target_state=dangerous_target,
        expected_pre_state=intent.expected_pre_state,
        authorization_digest="auth_hash_hil",
        deadline_at=time.time() + 5.0
    )
    
    status, err = await manager.execute_transaction(dangerous_intent, lease)
    
    # Twin must intercept BEFORE physical execution
    assert status == TransactionState.FAILED_VERIFICATION
    assert "constraint violation" in err
    assert adapter.state.volume == 50.0  # Hardware untouched


@pytest.mark.asyncio
async def test_hil_adversarial_device_disappears_during_execution(hil_env, monkeypatch):
    manager, adapter, intent, lease = hil_env
    
    # ADVERSARIAL: Power cord gets yanked exactly as command is sent
    async def dead_execute(*args, **kwargs):
        raise TimeoutError("Device did not ACK command")
    monkeypatch.setattr(adapter, "execute", dead_execute)
    
    status, err = await manager.execute_transaction(intent, lease)
    
    # Because execution threw an exception, it triggers rollback.
    # Rollback succeeds (mock adapter state didn't actually change).
    assert status == TransactionState.ROLLED_BACK
    assert "Execution fault" in err


@pytest.mark.asyncio
async def test_hil_adversarial_catastrophic_recovery_required(hil_env, monkeypatch):
    manager, adapter, intent, lease = hil_env
    
    # ADVERSARIAL: 
    # 1. Execution succeeds but puts TV in wrong state.
    # 2. Verification catches the mismatch and triggers rollback.
    # 3. Network completely dies during rollback.
    
    # Force verification failure by returning a bizarre state
    async def broken_observe():
        return DeviceState(power=True, volume=99.0, input_source="UNKNOWN")
    
    # Network dies on rollback
    async def dead_rollback(*args, **kwargs):
        raise ConnectionError("Host Unreachable")
    
    monkeypatch.setattr(adapter, "observe_state", broken_observe)
    monkeypatch.setattr(adapter, "rollback", dead_rollback)
    
    status, err = await manager.execute_transaction(intent, lease)
    
    # The ultimate invariant check: If we don't know the physical state, we halt.
    assert status == TransactionState.RECOVERY_REQUIRED
    assert "CRITICAL" in err
