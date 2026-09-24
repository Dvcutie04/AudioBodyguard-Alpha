from src.device_fabric.contracts import CapabilityLease, PhysicalSnapshot, PhysicalVerificationRecord


def test_physical_verification_record_has_world_state_provenance_without_minting_authority():
    record=PhysicalVerificationRecord(
        world_state_evidence_digest="sha256:observed-world-state-evidence",
    )

    assert record.world_state_evidence_digest=="sha256:observed-world-state-evidence"
    assert "world_state_evidence_digest" not in CapabilityLease.__dataclass_fields__
    assert "world_state_evidence_digest" not in PhysicalSnapshot.__dataclass_fields__

def test_physical_verification_record_binds_world_state_epoch_without_minting_authority():
    record=PhysicalVerificationRecord(
        world_state_evidence_digest="sha256:epoch-bound-evidence",
        world_state_epoch=73,
    )
    assert record.world_state_evidence_digest=="sha256:epoch-bound-evidence"
    assert record.world_state_epoch==73
    assert "world_state_epoch" not in CapabilityLease.__dataclass_fields__
    assert "world_state_epoch" not in PhysicalSnapshot.__dataclass_fields__


def test_physical_verification_record_preserves_distinct_authorization_and_observation_evidence():
    record=PhysicalVerificationRecord(
        world_state_evidence_digest="sha256:authorization-observation",
        observed_state_evidence_digest="sha256:post-state-observation",
    )
    assert record.world_state_evidence_digest=="sha256:authorization-observation"
    assert record.observed_state_evidence_digest=="sha256:post-state-observation"
    assert "observed_state_evidence_digest" not in CapabilityLease.__dataclass_fields__
    assert "observed_state_evidence_digest" not in PhysicalSnapshot.__dataclass_fields__
