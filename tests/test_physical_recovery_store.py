import pytest

from src.device_fabric.physical_recovery_store import (
    PhysicalRecoveryRecord,
    PhysicalRecoveryStatus,
    PhysicalRecoveryStore,
)


def test_recovery_record_persists_once_across_store_reopen(tmp_path):
    path = tmp_path / "physical_recovery.sqlite3"
    record = PhysicalRecoveryRecord(
        transaction_id="tx-recovery-001",
        intent_id="intent-recovery-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=1234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.record(record) is True
    assert store.record(record) is False
    reopened = PhysicalRecoveryStore(path)
    assert reopened.get(record.transaction_id) == record
    assert reopened.pending() == (record,)


def test_recovery_store_rejects_conflicting_transaction_lineage(tmp_path):
    store = PhysicalRecoveryStore(tmp_path / "physical_recovery.sqlite3")
    original = PhysicalRecoveryRecord(
        transaction_id="tx-conflict-001",
        intent_id="intent-original",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=1234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    conflicting = PhysicalRecoveryRecord(
        transaction_id=original.transaction_id,
        intent_id="intent-conflicting",
        device_id=original.device_id,
        operation=original.operation,
        target_state_digest=original.target_state_digest,
        expected_pre_state_digest=original.expected_pre_state_digest,
        authorization_digest=original.authorization_digest,
        capability_digest=original.capability_digest,
        recorded_at=original.recorded_at,
        status=original.status,
    )
    assert store.record(original) is True
    with pytest.raises(ValueError, match="conflicting physical recovery record"):
        store.record(conflicting)
    assert store.get(original.transaction_id) == original


def test_target_observation_reconciles_recovery_as_verified_applied(tmp_path):
    path = tmp_path / "physical_recovery.sqlite3"
    record = PhysicalRecoveryRecord(
        transaction_id="tx-reconcile-applied-001",
        intent_id="intent-reconcile-applied-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=1234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.record(record) is True
    resolved = store.reconcile_observation(
        record.transaction_id,
        observed_state_digest=record.target_state_digest,
        observed_at=1235.0,
    )
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    assert resolved.observed_state_digest == record.target_state_digest
    assert resolved.observed_at == 1235.0
    assert store.pending() == ()
    assert PhysicalRecoveryStore(path).get(record.transaction_id) == resolved


def test_pre_state_observation_reconciles_recovery_as_verified_not_applied(tmp_path):
    path = tmp_path / "physical_recovery.sqlite3"
    record = PhysicalRecoveryRecord(
        transaction_id="tx-reconcile-not-applied-001",
        intent_id="intent-reconcile-not-applied-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=2234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.record(record) is True
    resolved = store.reconcile_observation(
        record.transaction_id,
        observed_state_digest=record.expected_pre_state_digest,
        observed_at=2235.0,
    )
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_NOT_APPLIED
    assert resolved.observed_state_digest == record.expected_pre_state_digest
    assert resolved.observed_at == 2235.0
    assert store.pending() == ()
    assert PhysicalRecoveryStore(path).get(record.transaction_id) == resolved


def test_unexpected_observation_requires_manual_review_and_remains_pending(tmp_path):
    path = tmp_path / "physical_recovery.sqlite3"
    record = PhysicalRecoveryRecord(
        transaction_id="tx-reconcile-manual-001",
        intent_id="intent-reconcile-manual-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=3234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.record(record) is True
    unexpected_digest = "e" * 64
    resolved = store.reconcile_observation(
        record.transaction_id,
        observed_state_digest=unexpected_digest,
        observed_at=3235.0,
    )
    assert resolved.status is PhysicalRecoveryStatus.MANUAL_REVIEW_REQUIRED
    assert resolved.observed_state_digest == unexpected_digest
    assert resolved.observed_at == 3235.0
    assert store.pending() == (resolved,)
    assert PhysicalRecoveryStore(path).get(record.transaction_id) == resolved


def test_reconciliation_replay_is_idempotent_and_conflict_cannot_overwrite(tmp_path):
    path = tmp_path / "physical_recovery.sqlite3"
    record = PhysicalRecoveryRecord(
        transaction_id="tx-reconcile-replay-001",
        intent_id="intent-reconcile-replay-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=4234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.record(record) is True
    first = store.reconcile_observation(
        record.transaction_id,
        observed_state_digest=record.target_state_digest,
        observed_at=4235.0,
    )
    replay = store.reconcile_observation(
        record.transaction_id,
        observed_state_digest=record.target_state_digest,
        observed_at=4235.0,
    )
    assert replay == first
    with pytest.raises(ValueError, match="physical recovery record already reconciled"):
        store.reconcile_observation(
            record.transaction_id,
            observed_state_digest=record.expected_pre_state_digest,
            observed_at=4236.0,
        )
    assert PhysicalRecoveryStore(path).get(record.transaction_id) == first


def test_existing_recovery_database_migrates_without_losing_pending_record(tmp_path):
    import sqlite3

    path = tmp_path / "physical_recovery.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE physical_recovery_records (transaction_id TEXT PRIMARY KEY NOT NULL, intent_id TEXT NOT NULL, device_id TEXT NOT NULL, operation TEXT NOT NULL, target_state_digest TEXT NOT NULL, expected_pre_state_digest TEXT NOT NULL, authorization_digest TEXT NOT NULL, capability_digest TEXT NOT NULL, recorded_at REAL NOT NULL, status TEXT NOT NULL)")
    connection.execute("INSERT INTO physical_recovery_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("tx-legacy-001", "intent-legacy-001", "tv-recovery-001", "set_volume", "a" * 64, "b" * 64, "c" * 64, "d" * 64, 5234.5, PhysicalRecoveryStatus.RECOVERY_REQUIRED.value))
    connection.commit()
    connection.close()
    expected = PhysicalRecoveryRecord(
        transaction_id="tx-legacy-001",
        intent_id="intent-legacy-001",
        device_id="tv-recovery-001",
        operation="set_volume",
        target_state_digest="a" * 64,
        expected_pre_state_digest="b" * 64,
        authorization_digest="c" * 64,
        capability_digest="d" * 64,
        recorded_at=5234.5,
        status=PhysicalRecoveryStatus.RECOVERY_REQUIRED,
    )
    store = PhysicalRecoveryStore(path)
    assert store.get(expected.transaction_id) == expected
    assert store.pending() == (expected,)
    resolved = store.reconcile_observation(expected.transaction_id, observed_state_digest=expected.target_state_digest, observed_at=5235.0)
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    assert PhysicalRecoveryStore(path).get(expected.transaction_id) == resolved


def test_concurrent_record_change_cannot_persist_finality_closure(tmp_path,monkeypatch):
    from contextlib import closing
    import sqlite3
    import pytest
    import src.device_fabric.physical_recovery_store as recovery_module
    transaction_id="tx-concurrent-finality-001"
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-concurrent-finality-001",device_id="tv-concurrent-finality-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=1001.0,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    real_connect=sqlite3.connect
    injected=[]
    class InterleavedConnection(sqlite3.Connection):
        def execute(self,sql,parameters=()):
            if sql.startswith("UPDATE physical_recovery_records SET finality_closed = 1") and not injected:
                injected.append(True)
                with closing(real_connect(store.path)) as competing:
                    with competing:
                        competing.execute("UPDATE physical_recovery_records SET authorization_digest = ? WHERE transaction_id = ?",("e"*64,transaction_id))
            return super().execute(sql,parameters)
    def instrumented_connect(path):
        return real_connect(path,factory=InterleavedConnection)
    monkeypatch.setattr(recovery_module.sqlite3,"connect",instrumented_connect)
    with pytest.raises((ValueError,sqlite3.OperationalError)):
        store.confirm_finality(observed,report_digest=__import__("hashlib").sha256(b"test-finality-report").hexdigest(),report_bytes=b"test-finality-report",endpoint_key_id="test-endpoint",algorithm="TEST",signature="test-signature")
    assert injected==[True]
    persisted=store.get(transaction_id)
    assert persisted.finality_closed is False
    assert store.unresolved()==(persisted,)


def test_unresolved_rejects_malformed_finality_flag(tmp_path):
    from contextlib import closing
    import sqlite3
    import pytest
    transaction_id="tx-malformed-finality-flag-001"
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-malformed-finality-flag-001",device_id="tv-malformed-finality-flag-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=1001.0,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)
    assert store.record(record) is True
    with closing(sqlite3.connect(store.path)) as connection:
        with connection:
            connection.execute("UPDATE physical_recovery_records SET finality_closed = 2 WHERE transaction_id = ?",(transaction_id,))
    with pytest.raises(ValueError,match="invalid stored physical recovery finality state"):
        store.unresolved()


def test_confirm_finality_accepts_freshly_reloaded_closed_record(tmp_path):
    transaction_id="tx-reloaded-finality-retry-001"
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-reloaded-finality-retry-001",device_id="tv-reloaded-finality-retry-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=1001.0,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    closed=store.confirm_finality(observed,report_digest=__import__("hashlib").sha256(b"test-finality-report").hexdigest(),report_bytes=b"test-finality-report",endpoint_key_id="test-endpoint",algorithm="TEST",signature="test-signature")
    reloaded=PhysicalRecoveryStore(store.path).get(transaction_id)
    assert reloaded==closed
    assert store.confirm_finality(reloaded,report_digest=__import__("hashlib").sha256(b"test-finality-report").hexdigest(),report_bytes=b"test-finality-report",endpoint_key_id="test-endpoint",algorithm="TEST",signature="test-signature")==closed
    assert store.unresolved()==()


def test_confirm_finality_rejects_changed_report_digest(tmp_path):
    import pytest
    transaction_id="tx-finality-report-immutability-001"
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-finality-report-immutability-001",device_id="tv-finality-report-immutability-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=1001.0,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    committed_bytes=b"committed-finality-report"
    committed_digest=__import__("hashlib").sha256(committed_bytes).hexdigest()
    closed=store.confirm_finality(observed,report_digest=committed_digest,report_bytes=committed_bytes,endpoint_key_id="test-endpoint",algorithm="TEST",signature="test-signature")
    assert closed.finality_report_digest==committed_digest
    changed_bytes=b"changed-finality-report"
    with pytest.raises(ValueError,match="physical recovery finality report evidence changed"):
        store.confirm_finality(closed,report_digest=__import__("hashlib").sha256(changed_bytes).hexdigest(),report_bytes=changed_bytes,endpoint_key_id="test-endpoint",algorithm="TEST",signature="test-signature")
    with pytest.raises(ValueError,match="physical recovery finality report evidence changed"):
        store.confirm_finality(closed,report_digest=committed_digest,report_bytes=committed_bytes,endpoint_key_id="test-endpoint",algorithm="TEST",signature="changed-signature")
    persisted=PhysicalRecoveryStore(store.path).get(transaction_id)
    assert persisted==closed
    assert persisted.finality_report_digest==committed_digest
