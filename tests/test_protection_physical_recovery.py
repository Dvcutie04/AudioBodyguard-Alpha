import hashlib
import json
from dataclasses import replace
from src.control.protection_physical_recovery import PhysicalTransportFinalityEvidence, PhysicalTransportFinalityOutcome, ProtectionPhysicalRecoveryCoordinator
from src.control.protection_supervisor import ProtectionState, ProtectionSupervisor
from src.control.remote_controller_protocol import P256AuthorityKeyPair
from src.device_fabric.physical_recovery_store import PhysicalRecoveryRecord, PhysicalRecoveryStatus, PhysicalRecoveryStore


class _TrustedFinalitySource:
    def __init__(self,outcomes):
        self._outcomes=dict(outcomes)
        self._signing_key=P256AuthorityKeyPair.generate("endpoint-finality-test-key")
        self.endpoint_verifiers={self._signing_key.key_id:self._signing_key.public_verifier}
        self._evidence={}

    def terminal_evidence(self,record,*,query_nonce):
        outcome=self._outcomes.get(record.transaction_id)
        if outcome is None:
            return None
        cached=self._evidence.get((record.transaction_id,query_nonce))
        if cached is not None:
            return cached
        report=json.dumps({"algorithm":self._signing_key.algorithm,"authorization_digest":record.authorization_digest,"capability_digest":record.capability_digest,"device_id":record.device_id,"endpoint_key_id":self._signing_key.key_id,"intent_id":record.intent_id,"operation":record.operation,"outcome":outcome.name,"query_nonce":query_nonce,"transaction_id":record.transaction_id},sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        evidence=PhysicalTransportFinalityEvidence(transaction_id=record.transaction_id,intent_id=record.intent_id,device_id=record.device_id,operation=record.operation,authorization_digest=record.authorization_digest,capability_digest=record.capability_digest,outcome=outcome,query_nonce=query_nonce,report_bytes=report,report_digest=hashlib.sha256(report).hexdigest(),endpoint_key_id=self._signing_key.key_id,algorithm=self._signing_key.algorithm,signature=self._signing_key.sign(report))
        self._evidence[(record.transaction_id,query_nonce)]=evidence
        return evidence


def _coordinator_with_finality(supervisor,store,outcomes):
    source=_TrustedFinalitySource(outcomes)
    return ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=source,endpoint_verifiers=source.endpoint_verifiers)


def test_verified_applied_transaction_clears_matching_unknown_latch_to_paused(tmp_path):
    transaction_id="tx-protection-recovery-001"
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=1001.0,monotonic_now=51.0,physical_state_known=False,physical_transaction_id=transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-protection-recovery-001",device_id="tv-protection-recovery-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=1001.0,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)
    assert store.record(record) is True
    resolved=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    assert resolved.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    coordinator=_coordinator_with_finality(supervisor,store,{transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.PAUSED
    status=supervisor.status(now=1002.0,monotonic_now=52.0)
    assert status.reason=="FRESH_VALIDATION_REQUIRED"
    assert status.automation_allowed is False


def _recovery_record(transaction_id,recorded_at=1001.0):
    return PhysicalRecoveryRecord(transaction_id=transaction_id,intent_id="intent-"+transaction_id,device_id="tv-protection-recovery-001",operation="set_volume",target_state_digest="a"*64,expected_pre_state_digest="b"*64,authorization_digest="c"*64,capability_digest="d"*64,recorded_at=recorded_at,status=PhysicalRecoveryStatus.RECOVERY_REQUIRED)


def _unknown_supervisor(*transaction_ids):
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1000.0,now=1000.0,observed_monotonic=50.0,monotonic_now=50.0)
    for offset,transaction_id in enumerate(transaction_ids,1):
        supervisor.interrupt("POST_CONDITION_UNOBSERVED",now=1000.0+offset,monotonic_now=50.0+offset,physical_state_known=False,physical_transaction_id=transaction_id)
    return supervisor


def test_unresolved_or_ambiguous_recovery_cannot_clear_unknown_state(tmp_path):
    transaction_id="tx-ambiguous-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    store.record(record)
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    ambiguous=store.reconcile_observation(transaction_id,observed_state_digest="e"*64,observed_at=1002.0)
    assert ambiguous.status is PhysicalRecoveryStatus.MANUAL_REVIEW_REQUIRED
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False


def test_verified_different_transaction_cannot_clear_matching_unknown_latch(tmp_path):
    unresolved="tx-unresolved-001"
    different="tx-different-001"
    supervisor=_unknown_supervisor(unresolved)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(different)
    store.record(record)
    store.reconcile_observation(different,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    coordinator=_coordinator_with_finality(supervisor,store,{different:PhysicalTransportFinalityOutcome.APPLIED})
    assert coordinator.resolve(different,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False


def test_each_outstanding_transaction_requires_its_own_verified_recovery(tmp_path):
    first="tx-multiple-001"
    second="tx-multiple-002"
    supervisor=_unknown_supervisor(first,second)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    first_record=_recovery_record(first,1001.0)
    second_record=_recovery_record(second,1002.0)
    store.record(first_record)
    store.record(second_record)
    store.reconcile_observation(first,observed_state_digest=first_record.target_state_digest,observed_at=1003.0)
    store.reconcile_observation(second,observed_state_digest=second_record.expected_pre_state_digest,observed_at=1004.0)
    coordinator=_coordinator_with_finality(supervisor,store,{first:PhysicalTransportFinalityOutcome.APPLIED,second:PhysicalTransportFinalityOutcome.NOT_APPLIED})
    assert coordinator.resolve(first,now=1003.0,monotonic_now=53.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False
    assert coordinator.resolve(second,now=1004.0,monotonic_now=54.0) is ProtectionState.PAUSED
    assert supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    assert supervisor.automation_allowed is False


def test_verified_recovery_requires_newer_protection_evidence_before_active(tmp_path):
    transaction_id="tx-revalidation-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    store.record(record)
    store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    coordinator=_coordinator_with_finality(supervisor,store,{transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.PAUSED
    same_boundary=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1002.0,now=1002.0,observed_monotonic=52.0,monotonic_now=52.0)
    assert same_boundary is ProtectionState.PAUSED
    assert supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    newer=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=53.0,monotonic_now=53.0)
    assert newer is ProtectionState.ACTIVE
    assert supervisor.reason=="VALIDATED"
    assert supervisor.automation_allowed is True


def test_pending_recovery_rehydrates_unknown_state_after_restart(tmp_path):
    transaction_id="tx-restart-pending-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    store.record(_recovery_record(transaction_id))
    restarted_store=PhysicalRecoveryStore(path)
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1002.0,now=1002.0,observed_monotonic=52.0,monotonic_now=52.0)
    assert restarted_supervisor.state is ProtectionState.ACTIVE
    coordinator=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,restarted_store)
    assert coordinator.restore_pending(now=1003.0,monotonic_now=53.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    status=restarted_supervisor.status(now=1003.0,monotonic_now=53.0)
    assert status.reason=="PENDING_PHYSICAL_RECOVERY"
    assert status.automation_allowed is False
    still_unknown=restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1004.0,now=1004.0,observed_monotonic=54.0,monotonic_now=54.0)
    assert still_unknown is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert restarted_supervisor.automation_allowed is False


def test_matching_observation_without_transport_finality_cannot_clear_unknown_state(tmp_path):
    transaction_id="tx-no-transport-finality-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    store.record(record)
    reconciled=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    assert reconciled.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False


def test_mismatched_transport_finality_lineage_cannot_clear_unknown_state(tmp_path):
    transaction_id="tx-finality-lineage-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    store.record(record)
    resolved=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    valid=_TrustedFinalitySource({transaction_id:PhysicalTransportFinalityOutcome.APPLIED}).terminal_evidence(resolved,query_nonce="a"*64)
    mutations=(replace(valid,transaction_id="tx-attacker"),replace(valid,intent_id="intent-attacker"),replace(valid,device_id="tv-attacker"),replace(valid,operation="set_power"),replace(valid,authorization_digest="e"*64),replace(valid,capability_digest="f"*64),replace(valid,outcome=PhysicalTransportFinalityOutcome.NOT_APPLIED))
    class StaticSource:
        def __init__(self,evidence):
            self.evidence=evidence
        def terminal_evidence(self,record,*,query_nonce):
            return self.evidence
    for forged in mutations:
        coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=StaticSource(forged),query_nonce_factory=lambda:"a"*64)
        assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
        assert supervisor.automation_allowed is False


def test_malformed_recovery_identifier_fails_closed_without_finality_query(tmp_path):
    supervisor=_unknown_supervisor("tx-valid-recovery-001")
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    class CountingSource:
        def __init__(self):
            self.calls=0
        def terminal_evidence(self,record,*,query_nonce):
            self.calls+=1
            raise AssertionError("invalid transaction must not query finality")
    source=CountingSource()
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=source)
    assert coordinator.resolve("",now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert source.calls==0
    assert supervisor.automation_allowed is False


def test_observation_without_finality_remains_unresolved_after_restart(tmp_path):
    transaction_id="tx-restart-without-finality-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    assert observed.status is PhysicalRecoveryStatus.VERIFIED_APPLIED
    restarted_store=PhysicalRecoveryStore(path)
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=53.0,monotonic_now=53.0) is ProtectionState.ACTIVE
    coordinator=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,restarted_store)
    assert coordinator.restore_pending(now=1004.0,monotonic_now=54.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert restarted_supervisor.automation_allowed is False
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1005.0,now=1005.0,observed_monotonic=55.0,monotonic_now=55.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert restarted_supervisor.automation_allowed is False


def test_transport_finality_resolution_remains_closed_after_restart(tmp_path):
    transaction_id="tx-durable-finality-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    supervisor=_unknown_supervisor(transaction_id)
    coordinator=_coordinator_with_finality(supervisor,store,{transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.PAUSED
    restarted_store=PhysicalRecoveryStore(path)
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=53.0,monotonic_now=53.0) is ProtectionState.ACTIVE
    restarted=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,restarted_store)
    assert restarted.restore_pending(now=1004.0,monotonic_now=54.0) is ProtectionState.ACTIVE
    assert restarted_supervisor.automation_allowed is True


def test_finality_persistence_failure_cannot_release_unknown_latch(tmp_path):
    transaction_id="tx-finality-persistence-failure-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    class FailingFinalityStore(PhysicalRecoveryStore):
        def confirm_finality(self,record,*,report_digest,report_bytes,endpoint_key_id,algorithm,signature):
            raise OSError("simulated finality persistence failure")
    failing_store=FailingFinalityStore(path)
    supervisor=_unknown_supervisor(transaction_id)
    coordinator=_coordinator_with_finality(supervisor,failing_store,{transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False
    persisted=store.get(transaction_id)
    assert persisted.finality_closed is False
    assert store.unresolved()==(persisted,)


def test_persisted_finality_can_retry_after_supervisor_release_interruption(tmp_path,monkeypatch):
    import pytest
    transaction_id="tx-interrupted-release-retry-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    coordinator=_coordinator_with_finality(supervisor,store,{transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    real_resolve=ProtectionSupervisor.resolve_physical_transaction
    interrupted=[]
    def interrupt_once(self,transaction_id,*,now,monotonic_now=None):
        if self is supervisor and not interrupted:
            interrupted.append(transaction_id)
            raise OSError("simulated supervisor release interruption")
        return real_resolve(self,transaction_id,now=now,monotonic_now=monotonic_now)
    monkeypatch.setattr(ProtectionSupervisor,"resolve_physical_transaction",interrupt_once)
    with pytest.raises(OSError,match="simulated supervisor release interruption"):
        coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0)
    persisted=store.get(transaction_id)
    assert persisted.finality_closed is True
    assert store.unresolved()==()
    assert supervisor.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert coordinator.resolve(transaction_id,now=1003.0,monotonic_now=53.0) is ProtectionState.PAUSED
    assert supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    assert supervisor.automation_allowed is False


def test_committed_finality_rehydrates_release_barrier_after_restart(tmp_path):
    transaction_id="tx-restarted-release-barrier-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    source=_TrustedFinalitySource({transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    evidence=source.terminal_evidence(observed,query_nonce="a"*64)
    closed=store.confirm_finality(observed,report_digest=evidence.report_digest,report_bytes=evidence.report_bytes,endpoint_key_id=evidence.endpoint_key_id,algorithm=evidence.algorithm,signature=evidence.signature)
    assert closed.finality_closed is True
    assert store.unresolved()==()
    restarted_store=PhysicalRecoveryStore(path)
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=53.0,monotonic_now=53.0) is ProtectionState.ACTIVE
    coordinator=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,restarted_store,endpoint_verifiers=source.endpoint_verifiers)
    assert coordinator.restore_pending(now=1004.0,monotonic_now=54.0) is ProtectionState.PAUSED
    assert restarted_supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    assert restarted_supervisor.automation_allowed is False


def test_malformed_release_state_fails_closed_during_restore(tmp_path):
    from contextlib import closing
    import sqlite3
    transaction_id="tx-malformed-release-restore-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    assert store.record(_recovery_record(transaction_id)) is True
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute("UPDATE physical_recovery_records SET supervisor_release_completed = 2 WHERE transaction_id = ?",(transaction_id,))
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1002.0,now=1002.0,observed_monotonic=52.0,monotonic_now=52.0) is ProtectionState.ACTIVE
    coordinator=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,PhysicalRecoveryStore(path))
    assert coordinator.restore_pending(now=1003.0,monotonic_now=53.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert restarted_supervisor.reason=="PHYSICAL_RECOVERY_RESTORE_FAILURE"
    assert restarted_supervisor.automation_allowed is False


def test_finality_report_digest_mismatch_cannot_clear_unknown_state(tmp_path):
    import json
    transaction_id="tx-finality-report-digest-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    resolved=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    report=json.dumps({"authorization_digest":record.authorization_digest,"capability_digest":record.capability_digest,"device_id":record.device_id,"intent_id":record.intent_id,"operation":record.operation,"outcome":"APPLIED","query_nonce":"a"*64,"transaction_id":record.transaction_id},sort_keys=True,separators=(",",":")).encode("utf-8")
    evidence=PhysicalTransportFinalityEvidence(transaction_id=record.transaction_id,intent_id=record.intent_id,device_id=record.device_id,operation=record.operation,authorization_digest=record.authorization_digest,capability_digest=record.capability_digest,outcome=PhysicalTransportFinalityOutcome.APPLIED,query_nonce="a"*64,report_bytes=report,report_digest="0"*64,endpoint_key_id="endpoint-finality-digest-test",algorithm="ECDSA_P256_SHA256",signature="invalid-signature")
    class StaticSource:
        def terminal_evidence(self,record,*,query_nonce):
            return evidence
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=StaticSource(),query_nonce_factory=lambda:"a"*64)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False
    assert store.get(transaction_id).finality_closed is False


def test_finality_report_with_untrusted_endpoint_signature_cannot_clear_unknown_state(tmp_path):
    from src.control.remote_controller_protocol import P256AuthorityKeyPair
    transaction_id="tx-finality-endpoint-signature-001"
    supervisor=_unknown_supervisor(transaction_id)
    store=PhysicalRecoveryStore(tmp_path/"physical_recovery.sqlite3")
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    trusted=P256AuthorityKeyPair.generate("endpoint-finality-trusted-001")
    rogue=P256AuthorityKeyPair.generate("endpoint-finality-rogue-001")
    report=json.dumps({"algorithm":trusted.algorithm,"authorization_digest":record.authorization_digest,"capability_digest":record.capability_digest,"device_id":record.device_id,"endpoint_key_id":trusted.key_id,"intent_id":record.intent_id,"operation":record.operation,"outcome":"APPLIED","query_nonce":"a"*64,"transaction_id":record.transaction_id},sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    evidence=PhysicalTransportFinalityEvidence(transaction_id=record.transaction_id,intent_id=record.intent_id,device_id=record.device_id,operation=record.operation,authorization_digest=record.authorization_digest,capability_digest=record.capability_digest,outcome=PhysicalTransportFinalityOutcome.APPLIED,query_nonce="a"*64,report_bytes=report,report_digest=hashlib.sha256(report).hexdigest(),endpoint_key_id=trusted.key_id,algorithm=trusted.algorithm,signature=rogue.sign(report))
    class StaticSource:
        def terminal_evidence(self,record,*,query_nonce):
            return evidence
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=StaticSource(),endpoint_verifiers={trusted.key_id:trusted.public_verifier},query_nonce_factory=lambda:"a"*64)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False
    assert store.get(transaction_id).finality_closed is False


def test_authenticated_finality_persists_report_digest_with_closure(tmp_path):
    transaction_id="tx-finality-report-commitment-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    supervisor=_unknown_supervisor(transaction_id)
    source=_TrustedFinalitySource({transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    evidence=source.terminal_evidence(observed,query_nonce="a"*64)
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=source,endpoint_verifiers=source.endpoint_verifiers,query_nonce_factory=lambda:"a"*64)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.PAUSED
    persisted=PhysicalRecoveryStore(path).get(transaction_id)
    assert persisted.finality_closed is True
    assert persisted.finality_report_digest==evidence.report_digest
    assert persisted.finality_report_bytes==evidence.report_bytes
    assert persisted.finality_endpoint_key_id==evidence.endpoint_key_id
    assert persisted.finality_algorithm==evidence.algorithm
    assert persisted.finality_signature==evidence.signature


def test_restart_cannot_release_finality_without_trusted_endpoint_verifier(tmp_path):
    transaction_id="tx-restart-finality-trust-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    source=_TrustedFinalitySource({transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    evidence=source.terminal_evidence(observed,query_nonce="a"*64)
    closed=store.confirm_finality(observed,report_digest=evidence.report_digest,report_bytes=evidence.report_bytes,endpoint_key_id=evidence.endpoint_key_id,algorithm=evidence.algorithm,signature=evidence.signature)
    assert closed.finality_closed is True
    restarted_supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    assert restarted_supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=53.0,monotonic_now=53.0) is ProtectionState.ACTIVE
    coordinator=ProtectionPhysicalRecoveryCoordinator(restarted_supervisor,PhysicalRecoveryStore(path))
    assert coordinator.restore_pending(now=1004.0,monotonic_now=54.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert restarted_supervisor.automation_allowed is False
    assert PhysicalRecoveryStore(path).get(transaction_id).supervisor_release_completed is False


def test_previously_signed_finality_report_cannot_answer_fresh_query(tmp_path):
    transaction_id="tx-finality-fresh-query-001"
    path=tmp_path/"physical_recovery.sqlite3"
    store=PhysicalRecoveryStore(path)
    record=_recovery_record(transaction_id)
    assert store.record(record) is True
    observed=store.reconcile_observation(transaction_id,observed_state_digest=record.target_state_digest,observed_at=1002.0)
    supervisor=_unknown_supervisor(transaction_id)
    source=_TrustedFinalitySource({transaction_id:PhysicalTransportFinalityOutcome.APPLIED})
    replayed=source.terminal_evidence(observed,query_nonce="a"*64)
    assert replayed is not None
    class ReplaySource:
        def terminal_evidence(self,record,*,query_nonce):
            return replayed
    coordinator=ProtectionPhysicalRecoveryCoordinator(supervisor,store,finality_source=ReplaySource(),endpoint_verifiers=source.endpoint_verifiers,query_nonce_factory=lambda:"b"*64)
    assert coordinator.resolve(transaction_id,now=1002.0,monotonic_now=52.0) is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert supervisor.automation_allowed is False
    assert PhysicalRecoveryStore(path).get(transaction_id).finality_closed is False
