import pytest

from src.control.media_control_prior_state import MediaControlPriorState
from src.control.media_control_undo_candidate import MediaControlUndoCandidate
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.device_fabric.contracts import AuthorizedActionIntent, DeviceState, PhysicalSnapshot, PhysicalVerificationRecord, VerificationStatus


def test_verified_change_creates_transaction_bound_volume_undo_candidate():
    prior_device_state=DeviceState(volume=21)
    post_device_state=DeviceState(volume=37)
    prior_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior_device_state,epoch=7,observed_at=100.0,evidence_digest="prior-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-undo-1",device_id="living-room-tv",operation="set_volume",target_state=post_device_state,expected_pre_state=prior_device_state,authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    prior=MediaControlPriorState.from_authorized_snapshot(prior_snapshot,authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_device_state,epoch=8,observed_at=101.0,evidence_digest="post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-undo-1",device_id="living-room-tv",receipt_id="receipt-1",expected_state_digest=post_device_state.state_digest,observed_state_digest=post_device_state.state_digest,authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1",observed_state_evidence_digest="post-evidence",world_state_epoch=7,observed_state_epoch=8,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(post_snapshot,verification)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,verified)
    assert candidate.device_id=="living-room-tv"
    assert candidate.operation=="set_volume"
    assert dict(candidate.parameters)=={"volume_percent":21}
    assert candidate.expected_current_state_digest==post_device_state.state_digest
    assert candidate.prior_state_digest==prior_device_state.state_digest
    assert candidate.source_intent_id=="intent-undo-1"
    assert candidate.source_transaction_id=="transaction-1"
    assert candidate.authorization_digest=="authorization-1"
    assert candidate.capability_digest=="capability-1"
    with pytest.raises(TypeError):
        MediaControlUndoCandidate()


def test_verified_captions_change_restores_prior_boolean():
    prior_device_state=DeviceState(volume=21,custom_state={"captions_enabled":False})
    post_device_state=DeviceState(volume=21,custom_state={"captions_enabled":True})
    prior_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior_device_state,epoch=9,observed_at=102.0,evidence_digest="captions-prior-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-undo-captions",device_id="living-room-tv",operation="set_captions_enabled",target_state=post_device_state,expected_pre_state=prior_device_state,authorization_digest="authorization-captions",transaction_id="transaction-captions",capability_digest="capability-captions")
    prior=MediaControlPriorState.from_authorized_snapshot(prior_snapshot,authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_device_state,epoch=10,observed_at=103.0,evidence_digest="captions-post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-undo-captions",device_id="living-room-tv",receipt_id="receipt-captions",expected_state_digest=post_device_state.state_digest,observed_state_digest=post_device_state.state_digest,authorization_digest="authorization-captions",transaction_id="transaction-captions",capability_digest="capability-captions",observed_state_evidence_digest="captions-post-evidence",world_state_epoch=9,observed_state_epoch=10,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(post_snapshot,verification)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,verified)
    assert candidate.operation=="set_captions_enabled"
    assert dict(candidate.parameters)=={"enabled":False}


def test_verified_eq_bands_change_restores_prior_preset():
    prior_device_state=DeviceState(volume=21,custom_state={"eq_preset":"DIALOGUE"})
    post_device_state=DeviceState(volume=21,custom_state={"eq_bands":[{"frequency_hz":1000.0,"gain_db":3.0}]})
    prior_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior_device_state,epoch=11,observed_at=104.0,evidence_digest="eq-prior-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-undo-eq",device_id="living-room-tv",operation="set_eq_bands",target_state=post_device_state,expected_pre_state=prior_device_state,authorization_digest="authorization-eq",transaction_id="transaction-eq",capability_digest="capability-eq")
    prior=MediaControlPriorState.from_authorized_snapshot(prior_snapshot,authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_device_state,epoch=12,observed_at=105.0,evidence_digest="eq-post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-undo-eq",device_id="living-room-tv",receipt_id="receipt-eq",expected_state_digest=post_device_state.state_digest,observed_state_digest=post_device_state.state_digest,authorization_digest="authorization-eq",transaction_id="transaction-eq",capability_digest="capability-eq",observed_state_evidence_digest="eq-post-evidence",world_state_epoch=11,observed_state_epoch=12,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(post_snapshot,verification)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,verified)
    assert candidate.operation=="set_eq_preset"
    assert dict(candidate.parameters)=={"preset":"DIALOGUE"}


def test_verified_eq_preset_change_restores_prior_bands_immutably():
    prior_bands=[{"frequency_hz":500.0,"gain_db":-2.0},{"frequency_hz":1000.0,"gain_db":3.0}]
    prior_device_state=DeviceState(volume=21,custom_state={"eq_bands":prior_bands})
    post_device_state=DeviceState(volume=21,custom_state={"eq_preset":"MUSIC"})
    prior_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior_device_state,epoch=13,observed_at=106.0,evidence_digest="bands-prior-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-undo-bands",device_id="living-room-tv",operation="set_eq_preset",target_state=post_device_state,expected_pre_state=prior_device_state,authorization_digest="authorization-bands",transaction_id="transaction-bands",capability_digest="capability-bands")
    prior=MediaControlPriorState.from_authorized_snapshot(prior_snapshot,authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_device_state,epoch=14,observed_at=107.0,evidence_digest="bands-post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-undo-bands",device_id="living-room-tv",receipt_id="receipt-bands",expected_state_digest=post_device_state.state_digest,observed_state_digest=post_device_state.state_digest,authorization_digest="authorization-bands",transaction_id="transaction-bands",capability_digest="capability-bands",observed_state_evidence_digest="bands-post-evidence",world_state_epoch=13,observed_state_epoch=14,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(post_snapshot,verification)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,verified)
    assert candidate.operation=="set_eq_bands"
    assert dict(candidate.parameters)=={"bands":({"frequency_hz":500.0,"gain_db":-2.0},{"frequency_hz":1000.0,"gain_db":3.0})}
    with pytest.raises(TypeError):
        candidate.parameters["bands"][0]["gain_db"]=9.0


def test_undo_candidate_rejects_cross_transaction_verified_state():
    prior_state=DeviceState(volume=21)
    post_state=DeviceState(volume=37)
    prior=MediaControlPriorState.from_authorized_snapshot(PhysicalSnapshot(device_id="living-room-tv",state=prior_state,epoch=15,observed_at=108.0,evidence_digest="lineage-prior-evidence"),AuthorizedActionIntent(intent_id="intent-lineage",device_id="living-room-tv",operation="set_volume",target_state=post_state,expected_pre_state=prior_state,authorization_digest="authorization-lineage",transaction_id="transaction-prior",capability_digest="capability-lineage"))
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_state,epoch=16,observed_at=109.0,evidence_digest="lineage-post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-lineage",device_id="living-room-tv",receipt_id="receipt-lineage",expected_state_digest=post_state.state_digest,observed_state_digest=post_state.state_digest,authorization_digest="authorization-lineage",transaction_id="transaction-other",capability_digest="capability-lineage",observed_state_evidence_digest="lineage-post-evidence",world_state_epoch=15,observed_state_epoch=16,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    with pytest.raises(ValueError,match="undo candidate lineage mismatch"):
        MediaControlUndoCandidate.from_verified_change(prior,verified)


def test_undo_candidate_rejects_unrelated_verified_post_state():
    prior_state=DeviceState(volume=21)
    authorized_post_state=DeviceState(volume=37)
    unrelated_post_state=DeviceState(volume=38)
    prior=MediaControlPriorState.from_authorized_snapshot(PhysicalSnapshot(device_id="living-room-tv",state=prior_state,epoch=17,observed_at=110.0,evidence_digest="post-match-prior-evidence"),AuthorizedActionIntent(intent_id="intent-post-match",device_id="living-room-tv",operation="set_volume",target_state=authorized_post_state,expected_pre_state=prior_state,authorization_digest="authorization-post-match",transaction_id="transaction-post-match",capability_digest="capability-post-match"))
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=unrelated_post_state,epoch=18,observed_at=111.0,evidence_digest="post-match-observed-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-post-match",device_id="living-room-tv",receipt_id="receipt-post-match",expected_state_digest=unrelated_post_state.state_digest,observed_state_digest=unrelated_post_state.state_digest,authorization_digest="authorization-post-match",transaction_id="transaction-post-match",capability_digest="capability-post-match",observed_state_evidence_digest="post-match-observed-evidence",world_state_epoch=17,observed_state_epoch=18,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    with pytest.raises(ValueError,match="undo candidate post-state mismatch"):
        MediaControlUndoCandidate.from_verified_change(prior,verified)
