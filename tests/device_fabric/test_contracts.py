"""
Adversarial test suite enforcing the epistemic invariants of the Physical Truth Runtime.
"""
import pytest
from datetime import datetime, timedelta, timezone
from src.device_fabric.contracts import (
    ContractViolation,
    PredictedState,
    ObservedState,
    CommittedState,
    ReconciledState,
    CapabilityLease,
    VerificationStatus,
    VerificationResult,
    PhysicalCommitCertificate,
    verify_epoch_lock,
    utc_now
)


@pytest.fixture
def base_time():
    return utc_now()


def test_epistemic_separation(base_time):
    # 1. PredictedState cannot satisfy an observation requirement
    pred = PredictedState("dev1", {"vol": 20}, "m1", "v1", 0.9, base_time, 100)
    assert pred.epistemic_class == "PREDICTED"
    
    # 2. CommittedState cannot be treated as physical truth
    comm = CommittedState("dev1", "tx1", {"vol": 20}, 100, base_time, "cmd_dig", "auth_dig")
    assert comm.epistemic_class == "COMMITTED"
    
    obs = ObservedState("dev1", {"vol": 22}, "obs1", "obs_id1", base_time, 100, "meas_dig", 0.05)
    
    # Type checking enforces strict separation. You cannot build a ReconciledState with a PredictedState
    with pytest.raises(AttributeError):
        # Python type hinting and runtime checks prevent mixing predicted and observed
        ReconciledState("dev1", "tx1", comm, pred, False, True)


def test_epoch_lock_drift_enforcement():
    # 3. authorized_epoch != observed_epoch -> PRECONDITION_DRIFT (Mismatch)
    res = verify_epoch_lock(authorized_epoch=100, observed_epoch=101)
    assert res.status == VerificationStatus.STATE_EPOCH_MISMATCH
    assert res.allowed is False


def test_capability_lease_temporal_bounds(base_time):
    # 4. Expired lease
    expired_lease = CapabilityLease(
        "L1", "sub1", "dev1", frozenset(["SET_VOL"]), 
        valid_from=base_time - timedelta(minutes=10),
        expires_at=base_time - timedelta(minutes=1),
        authorized_epoch=100, max_world_state_age_ms=5000, max_clock_skew_ms=1000, nonce="n1"
    )
    assert expired_lease.is_temporally_valid(now=base_time) is False

    # 5. Future lease
    future_lease = CapabilityLease(
        "L1", "sub1", "dev1", frozenset(["SET_VOL"]), 
        valid_from=base_time + timedelta(minutes=1),
        expires_at=base_time + timedelta(minutes=10),
        authorized_epoch=100, max_world_state_age_ms=5000, max_clock_skew_ms=1000, nonce="n1"
    )
    assert future_lease.is_temporally_valid(now=base_time) is False


def test_reconciled_state_invariants(base_time):
    comm = CommittedState("dev1", "tx1", {"vol": 20}, 100, base_time, "cmd", "auth")
    obs = ObservedState("dev1", {"vol": 25}, "obs1", "id1", base_time, 100, "meas", 0.01)
    
    # 8. Divergent physical state cannot be marked verified
    with pytest.raises(ContractViolation, match="divergent state cannot be verified"):
        ReconciledState("dev1", "tx1", comm, obs, verified=True, divergence=True)
        
    # 11. Device identity mismatch -> hard rejection
    obs_wrong_dev = ObservedState("dev2", {"vol": 25}, "obs1", "id1", base_time, 100, "meas", 0.01)
    with pytest.raises(ContractViolation, match="ObservedState device mismatch"):
        ReconciledState("dev1", "tx1", comm, obs_wrong_dev, verified=False, divergence=True)


def test_commit_certificate_invariants(base_time):
    valid_ver = VerificationResult(
        status=VerificationStatus.VERIFIED, transaction_id="tx1", 
        authorized_epoch=100, observed_epoch=100, uncertainty_total=0.01, uncertainty_limit=0.1
    )
    
    # 7. Missing post-observation -> no VERIFIED certificate
    # 10. Verified certificate must contain an observed-state digest
    with pytest.raises(ContractViolation, match="Verified commit requires observed state digest"):
        PhysicalCommitCertificate(
            certificate_id="cert1", transaction_id="tx1", device_id="dev1",
            intent_digest="int", authorization_digest="auth", capability_lease_digest="cap",
            pre_state_digest="pre", simulation_digest="sim", authorized_epoch=100,
            command_digest="cmd", execution_timestamp=base_time,
            observed_state_digest=None,  # Missing!
            verification=valid_ver, provenance_parent=None
        )


def test_lease_requires_nonce_for_replay_protection(base_time):
    # 12. Replayed lease/transaction nonce -> hard rejection (Contract level requires field)
    with pytest.raises(ContractViolation, match="requires nonce"):
        CapabilityLease(
            "L1", "sub1", "dev1", frozenset(["SET"]), 
            base_time, base_time + timedelta(minutes=5), 
            100, 5000, 1000, nonce=""
        )
