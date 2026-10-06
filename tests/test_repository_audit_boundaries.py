"""Adversarial boundary cases found during the September repository audit."""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from src.control.device_fabric_bridge import Gen3DeviceFabricBridge
from src.control.protection_supervisor import ProtectionState, ProtectionSupervisor
from src.device_fabric.contracts import CapabilityLease, PhysicalSnapshot
from src.device_fabric.physical_recovery_store import PhysicalRecoveryStore
from src.inference.sensor_gate import SensorQualityGate
from tests.test_device_fabric_bridge import env


def physical_context(bridge, intent):
    state = bridge.adapter.device.state
    lease = CapabilityLease(device_id=intent.device_id, capabilities={intent.operation.lower()}, authorized_epoch=0)
    snapshot = PhysicalSnapshot(device_id=intent.device_id, state=state, epoch=0, observed_at=time.time())
    return lease, snapshot, state


@pytest.mark.asyncio
@pytest.mark.parametrize("operation,parameters", [
    ("SET_POWER", {"power": "false"}),
    ("SET_POWER", {"power": 1}),
    ("SET_MUTED", {"muted": "false"}),
    ("SET_MUTED", {"muted": None}),
    ("SET_VOLUME", {"volume": float("nan")}),
    ("SET_VOLUME", {"volume": float("inf")}),
    ("SET_VOLUME", {"volume": -1}),
    ("SET_VOLUME", {"volume": 101}),
    ("SET_VOLUME", {"volume": True}),
    ("SET_INPUT_SOURCE", {"input_source": None}),
    ("SET_CHANNEL", {"channel": []}),
])
async def test_malformed_signed_controls_never_call_adapter(env, operation, parameters):
    bridge, intent, lease, key = env
    intent.operation, intent.parameters = operation, parameters
    intent.signature = key.sign(intent.canonical_bytes)
    bridge.adapter.execute_intent = AsyncMock(wraps=bridge.adapter.execute_intent)
    result = await bridge.authorize_and_commit(intent, lease, *physical_context(bridge, intent))
    assert result.status == "REJECTED"
    bridge.adapter.execute_intent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["commit", "legacy"])
@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_interrupted_transport_persists_uncertainty_and_blocks_followup(env, tmp_path, path, failure):
    base, intent, lease, _ = env
    supervisor = ProtectionSupervisor(max_evidence_age=30)
    wall, mono = time.time(), time.monotonic()
    supervisor.validate(permission_granted=True, runtime_eligible=True, sensor_available=True,
                        connected=True, authority_valid=True, protection_path_eligible=True,
                        observed_at=wall, now=wall, observed_monotonic=mono, monotonic_now=mono)
    store = PhysicalRecoveryStore(tmp_path / "recovery.sqlite3")
    bridge = Gen3DeviceFabricBridge(base.firewall, base.adapter, protection_supervisor=supervisor, recovery_store=store)
    before = bridge.adapter.device.state

    async def applied_then_failed(intent, **kwargs):
        bridge.adapter.device.state = intent.target_state
        raise failure("completion lost after submission")

    bridge.adapter.execute_intent = AsyncMock(side_effect=applied_then_failed)
    async def submit():
        if path == "commit":
            return await bridge.authorize_and_commit(intent, lease, *physical_context(bridge, intent))
        return await bridge.authorize_and_execute(intent, lease, before)

    if failure is asyncio.CancelledError:
        with pytest.raises(asyncio.CancelledError):
            await submit()
    else:
        assert (await submit()).status == "FAILED"
    assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert not supervisor.automation_allowed
    assert len(store.pending()) == 1
    assert store.pending()[0].transaction_id == intent.transaction_id
    assert store.pending()[0].authorization_digest == bridge._authorization_digest(intent)
    assert store.pending()[0].capability_digest == lease.payload_digest
    assert (await submit()).status == "REJECTED"
    assert bridge.adapter.execute_intent.call_count == 1


@pytest.mark.parametrize("field", ["clipping_ratio", "acoustic_energy"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "bad", None])
def test_invalid_sensor_statistics_do_not_report_good_quality(field, value):
    assert SensorQualityGate().validate({field: value}) is False


@pytest.mark.asyncio
@pytest.mark.parametrize('path,fault', [('commit', fault) for fault in ('receipt_mismatch', 'failed_receipt', 'observer_error', 'observer_cancelled', 'observer_mismatch')] + [('legacy', fault) for fault in ('receipt_mismatch', 'failed_receipt')])
async def test_post_submission_failures_require_recovery(env, tmp_path, path, fault):
    from dataclasses import replace
    from src.device_fabric.contracts import ActuationStatus
    base, intent, lease, _ = env
    supervisor = ProtectionSupervisor(max_evidence_age=30)
    wall, mono = time.time(), time.monotonic()
    supervisor.validate(permission_granted=True, runtime_eligible=True, sensor_available=True,
                        connected=True, authority_valid=True, protection_path_eligible=True,
                        observed_at=wall, now=wall, observed_monotonic=mono, monotonic_now=mono)
    store = PhysicalRecoveryStore(tmp_path / 'recovery.sqlite3')
    bridge = Gen3DeviceFabricBridge(base.firewall, base.adapter, protection_supervisor=supervisor, recovery_store=store)
    original = base.adapter.execute_intent
    context = physical_context(bridge, intent)

    async def transport(**kwargs):
        receipt = await original(**kwargs)
        if fault == 'receipt_mismatch':
            return replace(receipt, intent_id='wrong-intent')
        if fault == 'failed_receipt':
            return replace(receipt, status=ActuationStatus.FAILED)
        return receipt

    async def observe(device_id):
        if fault == 'observer_cancelled':
            raise asyncio.CancelledError()
        if fault == 'observer_error':
            raise RuntimeError('observation unavailable')
        return PhysicalSnapshot(device_id=device_id, state=context[2], epoch=1, observed_at=time.time())

    bridge.adapter.execute_intent = AsyncMock(side_effect=transport)
    if fault == 'observer_cancelled':
        with pytest.raises(asyncio.CancelledError):
            await bridge.authorize_and_commit(intent, lease, *context, post_state_observer=observe)
    else:
        if path == 'legacy':
            result = await bridge.authorize_and_execute(intent, lease, context[2])
        else:
            result = await bridge.authorize_and_commit(intent, lease, *context, post_state_observer=observe)
        assert result.status == 'FAILED'
    assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert not supervisor.automation_allowed
    assert len(store.pending()) == 1
    assert store.pending()[0].transaction_id == intent.transaction_id


def test_unimplemented_causal_validator_cannot_certify_freshness():
    from src.core.causal_freshness import CausalFreshnessValidator
    validator = CausalFreshnessValidator()
    for evidence in ({}, {'timestamp': float('nan')}, {'sequence': 1, 'signature': 'forged'}):
        assert validator.validate(**evidence).is_fresh is False


@pytest.mark.asyncio
@pytest.mark.parametrize('parameters', [None, [], {'db': float('nan')}, {'db': float('inf')}])
async def test_malformed_attenuation_cannot_escape_parameter_validation(env, parameters):
    bridge, intent, lease, key = env
    intent.operation = 'SET_ATTENUATION'
    intent.parameters = parameters
    intent.signature = key.sign(intent.canonical_bytes)
    bridge.adapter.execute_intent = AsyncMock(wraps=bridge.adapter.execute_intent)
    result = await bridge.authorize_and_commit(intent, lease, *physical_context(bridge, intent))
    assert result.status == 'REJECTED'
    bridge.adapter.execute_intent.assert_not_called()
