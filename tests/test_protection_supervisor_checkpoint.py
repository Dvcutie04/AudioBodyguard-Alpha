import pytest
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from src.control.crypto_identity import KeyPair
from src.control.remote_controller_protocol import P256AuthorityKeyPair
from src.control.protection_supervisor import ProtectionState,ProtectionSupervisor
from src.control.protection_supervisor_checkpoint import AuthenticatedProtectionSupervisorCheckpointStore,ProtectionSupervisorCheckpoint,ProtectionSupervisorCheckpointCodec,ProtectionSupervisorCheckpointRestorer,ProtectionSupervisorCheckpointStore,RollbackProtectedProtectionSupervisorCheckpointStore,InMemoryCheckpointFreshnessAnchor,InMemoryCheckpointFreshnessWitness,WitnessedCheckpointFreshnessAnchor,CheckpointFreshnessAnchorUnavailable,SignedCheckpointFreshnessRecord,CheckpointFreshnessRecordDecision,CheckpointFreshnessRecordVerifier,VerifiedCheckpointFreshnessWitness,SigningCheckpointFreshnessWitness,DurableFileCheckpointFreshnessWitness


def test_historical_active_checkpoint_requires_fresh_revalidation_after_restart():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    restorer=ProtectionSupervisorCheckpointRestorer()
    state=restorer.restore(supervisor,checkpoint,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.state is ProtectionState.RECOVERY_REQUIRED
    assert status.reason=="HISTORICAL_ACTIVE_REQUIRES_REVALIDATION"
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_restart_boundary_requires_strictly_newer_evidence():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    restorer=ProtectionSupervisorCheckpointRestorer()
    assert restorer.restore(supervisor,checkpoint,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0) is ProtectionState.RECOVERY_REQUIRED
    replayed=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1002.0,now=1002.0,observed_monotonic=51.0,monotonic_now=52.0)
    assert replayed is ProtectionState.PAUSED
    assert supervisor.reason=="FRESH_VALIDATION_REQUIRED"
    assert supervisor.automation_allowed is False
    fresh=supervisor.validate(permission_granted=True,runtime_eligible=True,sensor_available=True,connected=True,authority_valid=True,protection_path_eligible=True,observed_at=1003.0,now=1003.0,observed_monotonic=52.0,monotonic_now=52.0)
    assert fresh is ProtectionState.ACTIVE
    assert supervisor.reason=="VALIDATED"
    assert supervisor.automation_allowed is True


def test_unknown_physical_checkpoint_dominates_restart_recovery():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1000.0,runtime_generation="generation-a")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    restorer=ProtectionSupervisorCheckpointRestorer()
    state=restorer.restore(supervisor,checkpoint,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_checkpoint_codec_has_canonical_versioned_round_trip():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    encoded=ProtectionSupervisorCheckpointCodec.encode(checkpoint)
    assert encoded==b'{"checkpoint_sequence":1,"observed_at":1000.0,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":2,"state":"ACTIVE"}'
    decoded=ProtectionSupervisorCheckpointCodec.decode(encoded)
    assert decoded==checkpoint


def test_checkpoint_codec_rejects_oversized_payload():
    oversized=("{\"observed_at\":1000.0,\"reason\":\""+("A"*5000)+"\",\"runtime_generation\":\"generation-a\",\"schema_version\":1,\"state\":\"ACTIVE\"}").encode("utf-8")
    with pytest.raises(ValueError,match="checkpoint payload is too large"):
        ProtectionSupervisorCheckpointCodec.decode(oversized)


def test_checkpoint_codec_refuses_to_encode_oversized_payload():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="A"*5000,observed_at=1000.0,runtime_generation="generation-a")
    with pytest.raises(ValueError,match="checkpoint payload is too large"):
        ProtectionSupervisorCheckpointCodec.encode(checkpoint)


def test_checkpoint_codec_rejects_untrusted_encodings():
    payloads=[b'\xff', b'{', b'{"observed_at":1000.0,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":2,"state":"ACTIVE"}', b'{"observed_at":1000.0,"reason":"VALIDATED","schema_version":1,"state":"ACTIVE"}', b'{"extra":true,"observed_at":1000.0,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":1,"state":"ACTIVE"}', b'{"observed_at":1000.0,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":1,"schema_version":1,"state":"ACTIVE"}', b'{"observed_at":NaN,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":1,"state":"ACTIVE"}', b'{"observed_at":true,"reason":"VALIDATED","runtime_generation":"generation-a","schema_version":1,"state":"ACTIVE"}']
    for encoded in payloads:
        with pytest.raises((TypeError,ValueError)):
            ProtectionSupervisorCheckpointCodec.decode(encoded)


def test_checkpoint_store_atomically_round_trips_checkpoint(tmp_path):
    path=tmp_path/"protection-supervisor.checkpoint"
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    store=ProtectionSupervisorCheckpointStore(path)
    store.save(checkpoint)
    assert store.load()==checkpoint
    assert path.read_bytes()==ProtectionSupervisorCheckpointCodec.encode(checkpoint)
    assert not path.with_suffix(path.suffix+".tmp").exists()


def test_corrupt_checkpoint_store_restores_fail_closed_without_claimed_evidence(tmp_path):
    path=tmp_path/"protection-supervisor.checkpoint"
    path.write_bytes(b"{")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    restorer=ProtectionSupervisorCheckpointRestorer()
    state=restorer.restore_from_store(supervisor,ProtectionSupervisorCheckpointStore(path),current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="CHECKPOINT_UNAVAILABLE_OR_INVALID"
    assert status.automation_allowed is False
    assert status.observed_at is None


def test_checkpoint_runtime_generation_cannot_be_reused():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore(supervisor,checkpoint,current_runtime_generation="generation-a",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="RUNTIME_GENERATION_REUSE"
    assert status.automation_allowed is False
    assert status.observed_at==1000.0


def test_unknown_physical_state_dominates_runtime_generation_reuse():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1000.0,runtime_generation="generation-a")
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore(supervisor,checkpoint,current_runtime_generation="generation-a",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.UNKNOWN_PHYSICAL_STATE
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="POST_CONDITION_UNOBSERVED"
    assert status.automation_allowed is False


def test_checkpoint_store_replaces_permissive_file_with_private_permissions(tmp_path):
    path=tmp_path/"protection-supervisor.checkpoint"
    path.write_bytes(b"legacy")
    path.chmod(0o644)
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a")
    ProtectionSupervisorCheckpointStore(path).save(checkpoint)
    assert path.stat().st_mode&0o777==0o600
    assert ProtectionSupervisorCheckpointStore(path).load()==checkpoint


def test_authenticated_checkpoint_store_rejects_tampering(tmp_path):
    path=tmp_path/"authenticated-protection-supervisor.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    store=AuthenticatedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier})
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1000.0,runtime_generation="generation-a")
    store.save(checkpoint)
    encoded=bytearray(path.read_bytes())
    encoded[len(encoded)//2]^=1
    path.write_bytes(encoded)
    with pytest.raises(ValueError,match="checkpoint authentication failed"):
        store.load()


def test_authenticated_checkpoint_tampering_restores_fail_closed(tmp_path):
    path=tmp_path/"authenticated-protection-supervisor.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    store=AuthenticatedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier})
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a")
    store.save(checkpoint)
    assert store.load()==checkpoint
    encoded=bytearray(path.read_bytes())
    encoded[len(encoded)//2]^=1
    path.write_bytes(encoded)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore_from_store(supervisor,store,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="CHECKPOINT_UNAVAILABLE_OR_INVALID"
    assert status.observed_at is None
    assert status.automation_allowed is False


def test_authenticated_checkpoint_store_requires_signing_key_verifier(tmp_path):
    signing_key=KeyPair("checkpoint-key",b"K"*32)
    wrong_key=KeyPair("wrong-key",b"W"*32)
    with pytest.raises(ValueError,match="signing key verifier is unavailable"):
        AuthenticatedProtectionSupervisorCheckpointStore(tmp_path/"checkpoint",signing_key=signing_key,verifiers={wrong_key.key_id:wrong_key.public_verifier})


def test_authenticated_checkpoint_store_rejects_mismatched_signing_key_material(tmp_path):
    signing_key=KeyPair("checkpoint-key",b"K"*32)
    mismatched_verifier=KeyPair("checkpoint-key",b"W"*32).public_verifier
    with pytest.raises(ValueError,match="signing key verifier is unavailable"):
        AuthenticatedProtectionSupervisorCheckpointStore(tmp_path/"checkpoint",signing_key=signing_key,verifiers={signing_key.key_id:mismatched_verifier})


def test_authenticated_checkpoint_store_supports_key_rotation(tmp_path):
    path=tmp_path/"authenticated-protection-supervisor.checkpoint"
    old_key=KeyPair("checkpoint-key-old",b"O"*32)
    new_key=KeyPair("checkpoint-key-new",b"N"*32)
    old_store=AuthenticatedProtectionSupervisorCheckpointStore(path,signing_key=old_key,verifiers={old_key.key_id:old_key.public_verifier})
    old_checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a")
    old_store.save(old_checkpoint)
    rotated_store=AuthenticatedProtectionSupervisorCheckpointStore(path,signing_key=new_key,verifiers={old_key.key_id:old_key.public_verifier,new_key.key_id:new_key.public_verifier})
    assert rotated_store.load()==old_checkpoint
    new_checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1001.0,runtime_generation="generation-b")
    rotated_store.save(new_checkpoint)
    assert rotated_store.load()==new_checkpoint
    with pytest.raises(ValueError,match="checkpoint authentication failed"):
        old_store.load()


def test_missing_checkpoint_store_restores_fail_closed_without_claimed_evidence(tmp_path):
    path=tmp_path/"missing-protection-supervisor.checkpoint"
    assert not path.exists()
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore_from_store(supervisor,ProtectionSupervisorCheckpointStore(path),current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="CHECKPOINT_UNAVAILABLE_OR_INVALID"
    assert status.observed_at is None
    assert status.automation_allowed is False


def test_checkpoint_sequence_is_cryptographically_bound_to_canonical_payload():
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=7)
    encoded=ProtectionSupervisorCheckpointCodec.encode(checkpoint)
    assert encoded==b"{\"checkpoint_sequence\":7,\"observed_at\":1000.0,\"reason\":\"VALIDATED\",\"runtime_generation\":\"generation-a\",\"schema_version\":2,\"state\":\"ACTIVE\"}"
    assert ProtectionSupervisorCheckpointCodec.decode(encoded)==checkpoint


class _MemoryCheckpointFreshnessAnchor:
    def __init__(self):
        self.record=None

    def read(self):
        return self.record

    def advance(self,sequence,digest):
        expected=1 if self.record is None else self.record[0]+1
        if sequence!=expected:
            raise ValueError("checkpoint sequence is not monotonic")
        self.record=(sequence,digest)

def test_rollback_protected_store_rejects_older_authentic_checkpoint(tmp_path):
    path=tmp_path/"rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(first)
    replay=path.read_bytes()
    second=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1001.0,runtime_generation="generation-b",checkpoint_sequence=2)
    store.save(second)
    assert store.load()==second
    path.write_bytes(replay)
    with pytest.raises(ValueError,match="checkpoint rollback detected"):
        store.load()


def test_detected_checkpoint_rollback_restores_with_explicit_fail_closed_reason(tmp_path):
    path=tmp_path/"rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(first)
    replay=path.read_bytes()
    second=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1001.0,runtime_generation="generation-b",checkpoint_sequence=2)
    store.save(second)
    path.write_bytes(replay)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore_from_store(supervisor,store,current_runtime_generation="generation-c",now=1002.0,monotonic_now=52.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1002.0,monotonic_now=52.0)
    assert status.reason=="CHECKPOINT_ROLLBACK_DETECTED"
    assert status.observed_at is None
    assert status.automation_allowed is False


def test_anchor_advance_before_failed_checkpoint_write_leaves_old_file_fail_closed(tmp_path):
    path=tmp_path/"rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(first)
    original_write=store._write_encoded
    def fail_write(encoded):
        raise OSError("simulated checkpoint write failure")
    store._write_encoded=fail_write
    second=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1001.0,runtime_generation="generation-b",checkpoint_sequence=2)
    with pytest.raises(OSError,match="simulated checkpoint write failure"):
        store.save(second)
    store._write_encoded=original_write
    assert anchor.read()[0]==2
    with pytest.raises(ValueError,match="checkpoint rollback detected"):
        store.load()


def test_missing_freshness_anchor_restores_with_explicit_fail_closed_reason(tmp_path):
    path=tmp_path/"rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(checkpoint)
    anchor.record=None
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore_from_store(supervisor,store,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="CHECKPOINT_FRESHNESS_ANCHOR_UNAVAILABLE"
    assert status.observed_at is None
    assert status.automation_allowed is False


def test_freshness_digest_rejects_different_authentic_checkpoint_at_same_sequence(tmp_path):
    protected_path=tmp_path/"rollback-protected.checkpoint"
    alternate_path=tmp_path/"alternate-authentic.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    protected=RollbackProtectedProtectionSupervisorCheckpointStore(protected_path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    original=ProtectionSupervisorCheckpoint(state=ProtectionState.UNKNOWN_PHYSICAL_STATE,reason="POST_CONDITION_UNOBSERVED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    protected.save(original)
    alternate=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    AuthenticatedProtectionSupervisorCheckpointStore(alternate_path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier}).save(alternate)
    protected_path.write_bytes(alternate_path.read_bytes())
    with pytest.raises(ValueError,match="checkpoint rollback detected"):
        protected.load()


@pytest.mark.parametrize("invalid_sequence",(True,0,-1,2**63,"1",1.0,None))
def test_checkpoint_sequence_rejects_non_monotonic_domain_values(invalid_sequence):
    with pytest.raises(ValueError,match="checkpoint_sequence must be a positive 63-bit integer"):
        ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=invalid_sequence)


def test_skipped_checkpoint_sequence_is_rejected_without_mutating_committed_state(tmp_path):
    path=tmp_path/"rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=_MemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(first)
    committed_bytes=path.read_bytes()
    skipped=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1002.0,runtime_generation="generation-c",checkpoint_sequence=3)
    with pytest.raises(ValueError,match="checkpoint freshness advance failed"):
        store.save(skipped)
    assert anchor.read()[0]==1
    assert path.read_bytes()==committed_bytes
    assert store.load()==first


def test_identical_freshness_advance_is_idempotent_but_same_sequence_fork_is_rejected():
    anchor=InMemoryCheckpointFreshnessAnchor()
    digest="a"*64
    anchor.advance(1,digest)
    anchor.advance(1,digest)
    assert anchor.read()==(1,digest)
    with pytest.raises(ValueError,match="checkpoint freshness conflict"):
        anchor.advance(1,"b"*64)
    assert anchor.read()==(1,digest)


def test_freshness_anchor_atomically_rejects_concurrent_same_sequence_fork():
    from concurrent.futures import ThreadPoolExecutor
    anchor=InMemoryCheckpointFreshnessAnchor()
    def attempt(digest):
        try:
            anchor.advance(1,digest)
            return ("advanced",digest)
        except ValueError as error:
            return ("rejected",str(error))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(attempt,("a"*64,"b"*64)))
    assert sorted(result[0] for result in results)==["advanced","rejected"]
    assert [result[1] for result in results if result[0]=="rejected"]==["checkpoint freshness conflict"]
    winning_digest=[result[1] for result in results if result[0]=="advanced"][0]
    assert anchor.read()==(1,winning_digest)


def test_identical_save_retry_recovers_anchor_first_write_failure(tmp_path):
    path=tmp_path/"retryable-rollback-protected.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    anchor=InMemoryCheckpointFreshnessAnchor()
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    second=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1001.0,runtime_generation="generation-b",checkpoint_sequence=2)
    store.save(first)
    original_write=store._write_encoded
    def fail_write(encoded):
        raise OSError("simulated checkpoint write failure")
    store._write_encoded=fail_write
    with pytest.raises(OSError,match="simulated checkpoint write failure"):
        store.save(second)
    with pytest.raises(ValueError,match="checkpoint rollback detected"):
        store.load()
    store._write_encoded=original_write
    store.save(second)
    assert anchor.read()[0]==2
    assert store.load()==second


def test_independent_witness_rejects_coherent_local_checkpoint_rollback(tmp_path):
    path=tmp_path/"witnessed.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    witness=InMemoryCheckpointFreshnessWitness()
    anchor=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-a")
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    first=ProtectionSupervisorCheckpoint(state=ProtectionState.PAUSED,reason="PERMISSION_DENIED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    store.save(first)
    replay=path.read_bytes()
    second=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1001.0,runtime_generation="generation-b",checkpoint_sequence=2)
    store.save(second)
    path.write_bytes(replay)
    restored_anchor=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-a")
    restored_store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=restored_anchor)
    with pytest.raises(ValueError,match="checkpoint rollback detected"):
        restored_store.load()


def test_unavailable_independent_witness_restores_with_explicit_fail_closed_reason(tmp_path):
    path=tmp_path/"witness-unavailable.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    witness=InMemoryCheckpointFreshnessWitness()
    healthy_anchor=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-a")
    healthy_store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=healthy_anchor)
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    healthy_store.save(checkpoint)
    class UnavailableWitness:
        def read(self,installation_id):
            raise OSError("simulated witness outage")
        def compare_and_advance(self,installation_id,sequence,digest):
            raise OSError("simulated witness outage")
    unavailable_anchor=WitnessedCheckpointFreshnessAnchor(UnavailableWitness(),installation_id="installation-a")
    unavailable_store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=unavailable_anchor)
    supervisor=ProtectionSupervisor(max_evidence_age=10.0)
    state=ProtectionSupervisorCheckpointRestorer().restore_from_store(supervisor,unavailable_store,current_runtime_generation="generation-b",now=1001.0,monotonic_now=51.0)
    assert state is ProtectionState.RECOVERY_REQUIRED
    status=supervisor.status(now=1001.0,monotonic_now=51.0)
    assert status.reason=="CHECKPOINT_FRESHNESS_ANCHOR_UNAVAILABLE"
    assert status.observed_at is None
    assert status.automation_allowed is False


def test_witness_freshness_history_is_isolated_per_installation():
    witness=InMemoryCheckpointFreshnessWitness()
    installation_a=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-a")
    installation_b=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-b")
    installation_a.advance(1,"a"*64)
    installation_b.advance(1,"b"*64)
    assert installation_a.read()==(1,"a"*64)
    assert installation_b.read()==(1,"b"*64)
    with pytest.raises(ValueError,match="checkpoint freshness conflict"):
        installation_a.advance(1,"c"*64)
    assert installation_a.read()==(1,"a"*64)
    assert installation_b.read()==(1,"b"*64)


@pytest.mark.parametrize("record",((0,"a"*64),(2**63,"a"*64),(1,"A"*64),(1,"a"*63)))
def test_malformed_witness_record_is_rejected_as_unavailable(record):
    class MalformedWitness:
        def read(self,installation_id):
            return record
        def compare_and_advance(self,installation_id,sequence,digest):
            return (sequence,digest)
    anchor=WitnessedCheckpointFreshnessAnchor(MalformedWitness(),installation_id="installation-a")
    with pytest.raises(ValueError,match="checkpoint witness response is invalid"):
        anchor.read()


def test_witness_advance_outage_is_typed_and_never_writes_checkpoint(tmp_path):
    path=tmp_path/"witness-advance-outage.checkpoint"
    key_pair=KeyPair("checkpoint-key",b"K"*32)
    class UnavailableWitness:
        def read(self,installation_id):
            raise OSError("simulated witness outage")
        def compare_and_advance(self,installation_id,sequence,digest):
            raise OSError("simulated witness outage")
    anchor=WitnessedCheckpointFreshnessAnchor(UnavailableWitness(),installation_id="installation-a")
    store=RollbackProtectedProtectionSupervisorCheckpointStore(path,signing_key=key_pair,verifiers={key_pair.key_id:key_pair.public_verifier},freshness_anchor=anchor)
    checkpoint=ProtectionSupervisorCheckpoint(state=ProtectionState.ACTIVE,reason="VALIDATED",observed_at=1000.0,runtime_generation="generation-a",checkpoint_sequence=1)
    with pytest.raises(CheckpointFreshnessAnchorUnavailable,match="checkpoint witness unavailable"):
        store.save(checkpoint)
    assert not path.exists()


@pytest.mark.parametrize(("sequence","digest"),((0,"a"*64),(True,"a"*64),(2**63,"a"*64),(1,"A"*64),(1,"a"*63)))
def test_witnessed_anchor_rejects_invalid_proposal_before_remote_call(sequence,digest):
    class RecordingWitness:
        def __init__(self):
            self.calls=0
        def read(self,installation_id):
            return None
        def compare_and_advance(self,installation_id,sequence,digest):
            self.calls+=1
            return (sequence,digest)
    witness=RecordingWitness()
    anchor=WitnessedCheckpointFreshnessAnchor(witness,installation_id="installation-a")
    with pytest.raises(ValueError):
        anchor.advance(sequence,digest)
    assert witness.calls==0


def test_signed_witness_record_rejects_tampered_digest():
    key_pair=P256AuthorityKeyPair.generate("witness-key")
    record=SignedCheckpointFreshnessRecord.issue(installation_id="installation-a",sequence=1,digest="a"*64,signing_key=key_pair)
    verifier=CheckpointFreshnessRecordVerifier({key_pair.key_id:key_pair.public_verifier})
    assert verifier.validate(record,installation_id="installation-a") is CheckpointFreshnessRecordDecision.ALLOW
    tampered=replace(record,digest="b"*64)
    assert verifier.validate(tampered,installation_id="installation-a") is CheckpointFreshnessRecordDecision.INVALID_SIGNATURE


def test_verified_witness_client_rejects_tampered_remote_record():
    key_pair=P256AuthorityKeyPair.generate("witness-key")
    genuine=SignedCheckpointFreshnessRecord.issue(installation_id="installation-a",sequence=1,digest="a"*64,signing_key=key_pair)
    class RemoteWitness:
        record=genuine
        def read(self,installation_id):
            return self.record
        def compare_and_advance(self,installation_id,sequence,digest):
            return self.record
    remote=RemoteWitness()
    verified=VerifiedCheckpointFreshnessWitness(remote,trusted_verifiers={key_pair.key_id:key_pair.public_verifier})
    anchor=WitnessedCheckpointFreshnessAnchor(verified,installation_id="installation-a")
    assert anchor.read()==(1,"a"*64)
    remote.record=replace(genuine,digest="b"*64)
    with pytest.raises(CheckpointFreshnessAnchorUnavailable):
        anchor.read()


def test_signing_and_verified_witness_complete_authenticated_round_trip():
    key_pair=P256AuthorityKeyPair.generate("witness-key")
    atomic_witness=InMemoryCheckpointFreshnessWitness()
    signing_witness=SigningCheckpointFreshnessWitness(atomic_witness,signing_key=key_pair)
    verified_witness=VerifiedCheckpointFreshnessWitness(signing_witness,trusted_verifiers={key_pair.key_id:key_pair.public_verifier})
    anchor=WitnessedCheckpointFreshnessAnchor(verified_witness,installation_id="installation-a")
    anchor.advance(1,"a"*64)
    assert anchor.read()==(1,"a"*64)
    with pytest.raises(ValueError,match="checkpoint freshness conflict"):
        anchor.advance(1,"b"*64)
    assert anchor.read()==(1,"a"*64)


def test_signed_witness_record_is_bound_to_installation_and_trusted_issuer():
    trusted=P256AuthorityKeyPair.generate("trusted-witness")
    untrusted=P256AuthorityKeyPair.generate("untrusted-witness")
    verifier=CheckpointFreshnessRecordVerifier({trusted.key_id:trusted.public_verifier})
    trusted_record=SignedCheckpointFreshnessRecord.issue(installation_id="installation-a",sequence=1,digest="a"*64,signing_key=trusted)
    assert verifier.validate(trusted_record,installation_id="installation-b") is CheckpointFreshnessRecordDecision.INSTALLATION_MISMATCH
    untrusted_record=SignedCheckpointFreshnessRecord.issue(installation_id="installation-a",sequence=1,digest="a"*64,signing_key=untrusted)
    assert verifier.validate(untrusted_record,installation_id="installation-a") is CheckpointFreshnessRecordDecision.UNKNOWN_ISSUER


def test_durable_witness_survives_restart_and_rejects_fork(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    first=DurableFileCheckpointFreshnessWitness(state_path)
    assert first.compare_and_advance("installation-a",1,"a"*64)==(1,"a"*64)
    restarted=DurableFileCheckpointFreshnessWitness(state_path)
    assert restarted.read("installation-a")== (1,"a"*64)
    with pytest.raises(ValueError,match="checkpoint freshness conflict"):
        restarted.compare_and_advance("installation-a",1,"b"*64)
    assert DurableFileCheckpointFreshnessWitness(state_path).read("installation-a")== (1,"a"*64)


def test_durable_witness_rejects_duplicate_state_keys(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    state_path.write_text("{\"version\":1,\"records\":{},\"records\":{\"installation-a\":[1,\""+"a"*64+"\"]}}",encoding="utf-8")
    with pytest.raises(ValueError,match="invalid checkpoint witness state"):
        DurableFileCheckpointFreshnessWitness(state_path)


def test_durable_witness_rejects_oversized_state_before_parsing(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    state_path.write_text("{\"version\":1,\"records\":{}}"+(" "*(1024*1024)),encoding="utf-8")
    with pytest.raises(ValueError,match="checkpoint witness state is too large"):
        DurableFileCheckpointFreshnessWitness(state_path)


def test_durable_witness_serializes_competing_instances(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    witnesses=(DurableFileCheckpointFreshnessWitness(state_path),DurableFileCheckpointFreshnessWitness(state_path))
    def attempt(arguments):
        witness,digest=arguments
        try:
            return ("committed",witness.compare_and_advance("installation-a",1,digest))
        except ValueError as error:
            return ("rejected",str(error))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(attempt,((witnesses[0],"a"*64),(witnesses[1],"b"*64))))
    assert sorted(result[0] for result in results)==["committed","rejected"]
    assert next(result[1] for result in results if result[0]=="rejected")=="checkpoint freshness conflict"
    assert DurableFileCheckpointFreshnessWitness(state_path).read("installation-a") in ((1,"a"*64),(1,"b"*64))


def test_durable_witness_never_commits_state_above_its_size_limit(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    witness=DurableFileCheckpointFreshnessWitness(state_path)
    witness._MAX_STATE_BYTES=100
    with pytest.raises(ValueError,match="checkpoint witness state is too large"):
        witness.compare_and_advance("installation-a",1,"a"*64)
    assert not state_path.exists()
    assert witness._records=={}


def test_durable_witness_replace_failure_never_publishes_candidate(tmp_path,monkeypatch):
    import src.control.protection_supervisor_checkpoint as checkpoint_module
    state_path=tmp_path/"checkpoint-witness.json"
    witness=DurableFileCheckpointFreshnessWitness(state_path)
    committed=witness.compare_and_advance("installation-a",1,"a"*64)
    committed_bytes=state_path.read_bytes()
    def fail_replace(source,destination):
        raise OSError("simulated replace failure")
    monkeypatch.setattr(checkpoint_module.os,"replace",fail_replace)
    with pytest.raises(OSError,match="simulated replace failure"):
        witness.compare_and_advance("installation-a",2,"b"*64)
    assert witness._records["installation-a"]==committed
    assert state_path.read_bytes()==committed_bytes
    assert list(tmp_path.glob("checkpoint-witness.json.*.tmp"))==[]


def test_durable_witness_rejects_truncated_state_without_discarding_committed_memory(tmp_path):
    state_path=tmp_path/"checkpoint-witness.json"
    witness=DurableFileCheckpointFreshnessWitness(state_path)
    committed=witness.compare_and_advance("installation-a",1,"a"*64)
    state_path.write_text("{\"version\":1,\"records\":{",encoding="utf-8")
    with pytest.raises(ValueError):
        witness.read("installation-a")
    assert witness._records["installation-a"]==committed


def test_signed_durable_witness_survives_restart_with_verified_record(tmp_path):
    key_pair=P256AuthorityKeyPair.generate("witness-key")
    state_path=tmp_path/"checkpoint-witness.json"
    signing=SigningCheckpointFreshnessWitness(DurableFileCheckpointFreshnessWitness(state_path),signing_key=key_pair)
    verified=VerifiedCheckpointFreshnessWitness(signing,trusted_verifiers={key_pair.key_id:key_pair.public_verifier})
    WitnessedCheckpointFreshnessAnchor(verified,installation_id="installation-a").advance(1,"a"*64)
    restarted_signing=SigningCheckpointFreshnessWitness(DurableFileCheckpointFreshnessWitness(state_path),signing_key=key_pair)
    restarted_verified=VerifiedCheckpointFreshnessWitness(restarted_signing,trusted_verifiers={key_pair.key_id:key_pair.public_verifier})
    restarted_anchor=WitnessedCheckpointFreshnessAnchor(restarted_verified,installation_id="installation-a")
    assert restarted_anchor.read()==(1,"a"*64)
    restarted_anchor.advance(2,"b"*64)
    assert restarted_anchor.read()==(2,"b"*64)
    with pytest.raises(ValueError,match="checkpoint freshness conflict"):
        restarted_anchor.advance(2,"c"*64)
