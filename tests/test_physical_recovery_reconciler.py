import pytest

from src.device_fabric.contracts import DeviceState, PhysicalSnapshot
from src.device_fabric.physical_recovery_reconciler import PhysicalRecoveryReconciler
from src.device_fabric.physical_recovery_store import PhysicalRecoveryRecord, PhysicalRecoveryStatus, PhysicalRecoveryStore


def test_snapshot_device_mismatch_cannot_reconcile_recovery(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-bound-reconcile-001",
        intent_id="intent-bound-reconcile-001",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=6234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    assert store.record(record) is True
    snapshot = PhysicalSnapshot(device_id="bedroom-tv", state=target, epoch=11, observed_at=6235.0)
    reconciler = PhysicalRecoveryReconciler(store)
    with pytest.raises(ValueError, match="snapshot device does not match recovery record"):
        reconciler.reconcile(record.transaction_id, snapshot)
    assert store.get(record.transaction_id) == record
    assert store.pending() == (record,)


def test_matching_snapshot_reconciles_target_state(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-bound-reconcile-002",
        intent_id="intent-bound-reconcile-002",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=7234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
        precondition_epoch=11,
    )
    assert store.record(record) is True
    snapshot = PhysicalSnapshot(device_id=record.device_id, state=target, epoch=12, observed_at=7235.0)
    resolved = PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, snapshot)
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    assert resolved.observed_state_digest == snapshot.state_digest
    assert resolved.observed_at == snapshot.observed_at
    assert store.pending() == ()


def test_duck_typed_snapshot_cannot_reconcile_recovery(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-bound-reconcile-003",
        intent_id="intent-bound-reconcile-003",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=8234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    assert store.record(record) is True
    class ForgedSnapshot:
        device_id = record.device_id
        state_digest = target.state_digest
        observed_at = 8235.0
    with pytest.raises(TypeError, match="snapshot must be PhysicalSnapshot"):
        PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, ForgedSnapshot())
    assert store.get(record.transaction_id) == record
    assert store.pending() == (record,)


def test_equal_epoch_snapshot_cannot_reconcile_epoch_bound_recovery(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-epoch-reconcile-001",
        intent_id="intent-epoch-reconcile-001",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=9234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
        precondition_epoch=40,
    )
    assert store.record(record) is True
    replay = PhysicalSnapshot(device_id=record.device_id, state=target, epoch=40, observed_at=9235.0)
    with pytest.raises(ValueError, match="snapshot epoch is not newer than recovery precondition"):
        PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, replay)
    assert store.get(record.transaction_id) == record
    assert store.pending() == (record,)


def test_newer_epoch_snapshot_reconciles_epoch_bound_recovery(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-epoch-reconcile-002",
        intent_id="intent-epoch-reconcile-002",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=10234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
        precondition_epoch=40,
    )
    assert store.record(record) is True
    snapshot = PhysicalSnapshot(device_id=record.device_id, state=target, epoch=41, observed_at=10235.0)
    resolved = PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, snapshot)
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    assert resolved.precondition_epoch == 40
    assert resolved.observed_state_digest == snapshot.state_digest
    assert store.pending() == ()


def test_missing_precondition_epoch_cannot_use_typed_reconciliation(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-epoch-reconcile-003",
        intent_id="intent-epoch-reconcile-003",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=11234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    assert store.record(record) is True
    snapshot = PhysicalSnapshot(device_id=record.device_id, state=target, epoch=41, observed_at=11235.0)
    with pytest.raises(ValueError, match="recovery record lacks precondition epoch"):
        PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, snapshot)
    assert store.get(record.transaction_id) == record
    assert store.pending() == (record,)


def test_boolean_snapshot_epoch_cannot_reconcile_recovery(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    target = DeviceState(power=True, volume=25)
    record = PhysicalRecoveryRecord(
        transaction_id="tx-epoch-reconcile-004",
        intent_id="intent-epoch-reconcile-004",
        device_id="living-room-tv",
        operation="set_volume",
        target_state_digest=target.state_digest,
        expected_pre_state_digest=DeviceState(power=True, volume=10).state_digest,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=12234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
        precondition_epoch=0,
    )
    assert store.record(record) is True
    forged = PhysicalSnapshot(device_id=record.device_id, state=target, epoch=True, observed_at=12235.0)
    with pytest.raises(ValueError, match="invalid snapshot epoch"):
        PhysicalRecoveryReconciler(store).reconcile(record.transaction_id, forged)
    assert store.get(record.transaction_id) == record
    assert store.pending() == (record,)


def test_nonfinite_snapshot_observation_time_never_reads_recovery_store():
    class ReadDetectingStore:
        def __init__(self):
            self.calls = 0

        def get(self, transaction_id):
            self.calls += 1
            raise AssertionError("invalid observation time must fail before recovery-store read")

    store = ReadDetectingStore()
    snapshot = PhysicalSnapshot(device_id="living-room-tv", state=DeviceState(power=True), epoch=1, observed_at=float("nan"))
    with pytest.raises(ValueError, match="invalid snapshot observation time"):
        PhysicalRecoveryReconciler(store).reconcile("tx-observation-time-001", snapshot)
    assert store.calls == 0


def test_forged_nested_state_never_reads_recovery_store():
    class ForgedState:
        state_digest = "a" * 64

    class ReadDetectingStore:
        def __init__(self):
            self.calls = 0

        def get(self, transaction_id):
            self.calls += 1
            raise AssertionError("forged snapshot state must fail before recovery-store read")

    store = ReadDetectingStore()
    snapshot = PhysicalSnapshot(device_id="living-room-tv", state=ForgedState(), epoch=1, observed_at=13235.0)
    with pytest.raises(TypeError, match="snapshot state must be DeviceState"):
        PhysicalRecoveryReconciler(store).reconcile("tx-nested-state-001", snapshot)
    assert store.calls == 0
