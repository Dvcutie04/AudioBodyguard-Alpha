"""
AQSS-36-OMEGA
Tests for Physical Truth Runtime — Core Contracts
"""
from datetime import datetime, timedelta, timezone
import pytest

from contracts import (
    ActuationReceipt,
    ActuationStatus,
    AuthorizedActionIntent,
    CapabilityLease,
    CommittedState,
    ContractViolation,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceState,
    DeviceType,
    ObservedState,
    PhysicalCommitCertificate,
    PredictedState,
    PreconditionStatus,
    ReconciledState,
    TransactionState,
    VerificationResult,
    VerificationStatus,
    canonical_digest,
    utc_now,
    verify_epoch_lock,
)

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------
def make_valid_device_state() -> DeviceState:
    return DeviceState(
        power=True,
        volume=25.0,
        input_source="HDMI_1",
        payload={"hdr": True},
        muted=False,
    )

def make_valid_intent() -> AuthorizedActionIntent:
    state = make_valid_device_state()
    return AuthorizedActionIntent(
        intent_id="intent-101",
        device_id="dev-tv-01",
        operation="SET_VOLUME",
        target_state=state,
        expected_pre_state=state,
        authorization_digest="digest-auth-123",
        deadline_at=1000.0,
    )

def make_valid_committed_state() -> CommittedState:
    return CommittedState(
        device_id="dev-tv-01",
        transaction_id="tx-999",
        requested_state={"power": True},
        authorized_epoch=1,
        committed_at=utc_now(),
        command_digest="cmd-digest-1",
        authorization_digest="auth-digest-1",
    )

def make_valid_observed_state() -> ObservedState:
    return ObservedState(
        device_id="dev-tv-01",
        state={"power": True},
        observer_id="obs-sensor-01",
        observation_id="obs-777",
        observed_at=utc_now(),
        world_epoch=1,
        measurement_digest="meas-digest-1",
        uncertainty=0.01,
    )

def make_valid_lease() -> CapabilityLease:
    now = utc_now()
    return CapabilityLease(
        lease_id="lease-001",
        subject_id="sub-auth-1",
        device_id="dev-tv-01",
        capabilities=frozenset({"power", "volume"}),
        valid_from=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=5),
        authorized_epoch=1,
        max_world_state_age_ms=1000,
        max_clock_skew_ms=500,
        nonce="nonce-abc-123",
    )

# ---------------------------------------------------------------------------
# Core Utilities & Enums
# ---------------------------------------------------------------------------
def test_utc_now_returns_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc

def test_canonical_digest_determinism():
    d1 = canonical_digest("PART_A", 123, True)
    d2 = canonical_digest("PART_A", 123, True)
    d3 = canonical_digest("PART_B", 123, True)
    assert d1 == d2
    assert d1 != d3

def test_enum_members():
    assert DeviceType.TV.name == "TV"
    assert TransactionState.PENDING.name == "PENDING"
    assert PreconditionStatus.MATCH.name == "MATCH"
    assert ActuationStatus.EXECUTED.name == "EXECUTED"
    assert VerificationStatus.VERIFIED.name == "VERIFIED"

# ---------------------------------------------------------------------------
# DeviceState
# ---------------------------------------------------------------------------
def test_device_state_valid():
    ds = make_valid_device_state()
    assert ds.power is True
    assert ds.volume == 25.0
    assert ds.input_source == "HDMI_1"
    assert ds.state_digest != ""

def test_device_state_invalid_power():
    with pytest.raises(ContractViolation, match="power must be bool"):
        DeviceState(power="on", volume=10.0, input_source="HDMI_1")  # type: ignore

def test_device_state_invalid_volume():
    with pytest.raises(ContractViolation, match="volume cannot be negative"):
        DeviceState(power=True, volume=-1.0, input_source="HDMI_1")

def test_device_state_missing_input_source():
    with pytest.raises(ContractViolation, match="DeviceState requires input_source"):
        DeviceState(power=True, volume=10.0, input_source="")

def test_device_state_invalid_muted():
    with pytest.raises(ContractViolation, match="muted must be bool"):
        DeviceState(power=True, volume=10.0, input_source="HDMI_1", muted="no")  # type: ignore

# ---------------------------------------------------------------------------
# AuthorizedActionIntent
# ---------------------------------------------------------------------------
def test_authorized_action_intent_valid():
    intent = make_valid_intent()
    assert intent.intent_id == "intent-101"

@pytest.mark.parametrize(
    "field_name, invalid_val, match_msg",
    [
        ("intent_id", "", "intent_id required"),
        ("device_id", "", "device_id required"),
        ("operation", "", "operation required"),
        ("authorization_digest", "", "authorization_digest required"),
        ("deadline_at", 0.0, "deadline_at must be strictly positive"),
        ("deadline_at", -5.0, "deadline_at must be strictly positive"),
    ],
)
def test_authorized_action_intent_invariants(field_name, invalid_val, match_msg):
    kwargs = {
        "intent_id": "intent-101",
        "device_id": "dev-tv-01",
        "operation": "SET_VOLUME",
        "target_state": make_valid_device_state(),
        "expected_pre_state": make_valid_device_state(),
        "authorization_digest": "digest-auth-123",
        "deadline_at": 1000.0,
    }
    kwargs[field_name] = invalid_val
    with pytest.raises(ContractViolation, match=match_msg):
        AuthorizedActionIntent(**kwargs)

# ---------------------------------------------------------------------------
# Device Identity & Capabilities
# ---------------------------------------------------------------------------
def test_device_identity_valid():
    ident = DeviceIdentity("dev-1", DeviceType.TV, "Sony", "Bravia", "v1.0")
    assert ident.device_id == "dev-1"

def test_device_identity_invariants():
    with pytest.raises(ContractViolation, match="device_id required"):
        DeviceIdentity("", DeviceType.TV, "Sony", "Bravia", "v1.0")

def test_device_capabilities_valid():
    caps = DeviceCapabilities("dev-1", frozenset({"power", "mute"}))
    assert caps.device_id == "dev-1"

def test_device_capabilities_invariants():
    with pytest.raises(ContractViolation, match="capabilities must be a frozenset"):
        DeviceCapabilities("dev-1", ["power", "mute"])  # type: ignore

# ---------------------------------------------------------------------------
# ActuationReceipt
# ---------------------------------------------------------------------------
def test_actuation_receipt_valid():
    now = utc_now()
    receipt = ActuationReceipt(
        receipt_id="rcpt-1",
        action_id="act-1",
        device_id="dev-1",
        intent_digest="id-1",
        status=ActuationStatus.EXECUTED,
        timestamp=now,
        transaction_digest="td-1",
        capability_digest="cd-1",
        pre_state_digest="prd-1",
        post_state_digest="pod-1",
        physical_state_digest="psd-1",
        executed_at=now - timedelta(seconds=1),
    )
    assert receipt.receipt_digest != ""

def test_actuation_receipt_future_execution():
    now = utc_now()
    with pytest.raises(ContractViolation, match="executed_at cannot be later than receipt timestamp"):
        ActuationReceipt(
            receipt_id="rcpt-1",
            action_id="act-1",
            device_id="dev-1",
            intent_digest="id-1",
            status=ActuationStatus.EXECUTED,
            timestamp=now,
            transaction_digest="td-1",
            capability_digest="cd-1",
            pre_state_digest="prd-1",
            post_state_digest="pod-1",
            physical_state_digest="psd-1",
            executed_at=now + timedelta(seconds=10),
        )

# ---------------------------------------------------------------------------
# Epistemic States
# ---------------------------------------------------------------------------
def test_predicted_state_valid():
    ps = PredictedState(
        device_id="dev-1",
        state={"power": True},
        model_id="mod-1",
        model_version="1.0",
        confidence=0.95,
    )
    assert ps.epistemic_class == "PREDICTED"

def test_predicted_state_invalid_confidence():
    with pytest.raises(ContractViolation, match="confidence must be within \\[0.0, 1.0\\]"):
        PredictedState(
            device_id="dev-1",
            state={},
            model_id="m1",
            model_version="1",
            confidence=1.5,
        )

def test_observed_state_valid():
    obs = make_valid_observed_state()
    assert obs.epistemic_class == "OBSERVED"

def test_committed_state_valid():
    comm = make_valid_committed_state()
    assert comm.epistemic_class == "COMMITTED"

def test_reconciled_state_valid():
    comm = make_valid_committed_state()
    obs = make_valid_observed_state()
    rec = ReconciledState(
        device_id="dev-tv-01",
        transaction_id="tx-999",
        committed_state=comm,
        observed_state=obs,
        verified=True,
        divergence=False,
    )
    assert rec.epistemic_class == "RECONCILED"

def test_reconciled_state_divergent_and_verified_conflict():
    comm = make_valid_committed_state()
    obs = make_valid_observed_state()
    with pytest.raises(ContractViolation, match="A divergent state cannot be verified"):
        ReconciledState(
            device_id="dev-tv-01",
            transaction_id="tx-999",
            committed_state=comm,
            observed_state=obs,
            verified=True,
            divergence=True,
        )

def test_reconciled_state_invalid_type():
    comm = make_valid_committed_state()
    pred = PredictedState("dev-tv-01", {}, "m1", "1.0", 0.9)
    with pytest.raises(ContractViolation, match="observed_state must be an ObservedState"):
        ReconciledState(
            device_id="dev-tv-01",
            transaction_id="tx-999",
            committed_state=comm,
            observed_state=pred,  # type: ignore
            verified=False,
            divergence=True,
        )

# ---------------------------------------------------------------------------
# Capability Lease
# ---------------------------------------------------------------------------
def test_capability_lease_validity():
    lease = make_valid_lease()
    now = utc_now()
    assert lease.is_temporally_valid(now)
    assert lease.permits("power")
    assert not lease.permits("channel")

def test_capability_lease_expired():
    now = utc_now()
    lease = CapabilityLease(
        lease_id="l-1",
        subject_id="s-1",
        device_id="d-1",
        capabilities=frozenset({"power"}),
        valid_from=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),
        authorized_epoch=1,
        max_world_state_age_ms=1000,
        max_clock_skew_ms=500,
        nonce="nonce-1",
    )
    assert not lease.is_temporally_valid(now)

# ---------------------------------------------------------------------------
# Physical Commit Certificate & Epoch Verification
# ---------------------------------------------------------------------------
def test_verify_epoch_lock_match():
    res = verify_epoch_lock(authorized_epoch=5, observed_epoch=5)
    assert res.allowed
    assert res.status == VerificationStatus.VERIFIED

def test_verify_epoch_lock_mismatch():
    res = verify_epoch_lock(authorized_epoch=5, observed_epoch=6)
    assert not res.allowed
    assert res.status == VerificationStatus.STATE_EPOCH_MISMATCH

def test_physical_commit_certificate_valid():
    v_res = VerificationResult(
        status=VerificationStatus.VERIFIED,
        transaction_id="tx-123",
        authorized_epoch=2,
        observed_epoch=2,
        uncertainty_total=0.0,
        uncertainty_limit=0.05,
    )
    cert = PhysicalCommitCertificate(
        certificate_id="cert-1",
        transaction_id="tx-123",
        device_id="dev-1",
        intent_digest="id-1",
        authorization_digest="ad-1",
        capability_lease_digest="cld-1",
        pre_state_digest="prd-1",
        simulation_digest="sd-1",
        authorized_epoch=2,
        command_digest="cmd-1",
        execution_timestamp=utc_now(),
        observed_state_digest="obs-digest-1",
        verification=v_res,
        provenance_parent=None,
    )
    assert cert.physically_verified is True

def test_physical_commit_certificate_missing_observed_state():
    v_res = VerificationResult(
        status=VerificationStatus.VERIFIED,
        transaction_id="tx-123",
        authorized_epoch=2,
        observed_epoch=2,
        uncertainty_total=0.0,
        uncertainty_limit=0.05,
    )
    with pytest.raises(ContractViolation, match="Verified commit requires observed state digest"):
        PhysicalCommitCertificate(
            certificate_id="cert-1",
            transaction_id="tx-123",
            device_id="dev-1",
            intent_digest="id-1",
            authorization_digest="ad-1",
            capability_lease_digest="cld-1",
            pre_state_digest="prd-1",
            simulation_digest="sd-1",
            authorized_epoch=2,
            command_digest="cmd-1",
            execution_timestamp=utc_now(),
            observed_state_digest=None,
            verification=v_res,
            provenance_parent=None,
        )
