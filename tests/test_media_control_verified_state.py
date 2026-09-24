from dataclasses import replace

import pytest

from src.control.media_control_capabilities import CaptionCapability, EqBandGain, EqCapability, MediaControlCapabilityManifest, VerificationStrength
from src.control.media_control_profiles import MediaControlProfileKind
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.device_fabric.contracts import DeviceState, PhysicalSnapshot, PhysicalVerificationRecord, VerificationStatus


def test_verified_media_state_creates_user_default_from_observation():
    state=DeviceState(volume=42,custom_state={"captions_enabled":True,"eq_bands":[{"frequency_hz":1000.0,"gain_db":3.0}]})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-1",device_id="living-room-tv",receipt_id="receipt-1",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-1",content_generation=11,caption_capability=CaptionCapability.NATIVE_TRACK,eq_capability=EqCapability.BANDS,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=90.0,expires_monotonic=120.0,clock_domain_id="runtime-monotonic")
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    profile=verified.to_user_default_profile(manifest,name="My Default")
    assert verified.device_id=="living-room-tv"
    assert verified.observed_state_digest==state.state_digest
    assert profile.kind is MediaControlProfileKind.USER_DEFAULT
    assert profile.volume_percent==42
    assert profile.captions_enabled is True
    assert profile.eq_bands==(EqBandGain(1000,3),)


def test_verified_media_state_rejects_direct_construction_and_tampering():
    with pytest.raises(TypeError):
        VerifiedMediaControlState()
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-2",device_id="living-room-tv",receipt_id="receipt-2",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-2",transaction_id="transaction-2",capability_digest="capability-2",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    with pytest.raises(ValueError,match="digest mismatch"):
        VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,observed_state_digest="tampered"))


def test_verified_media_state_rejects_unverified_status_and_device_mismatch():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-3",device_id="living-room-tv",receipt_id="receipt-3",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-3",transaction_id="transaction-3",capability_digest="capability-3",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for status in (VerificationStatus.PENDING,VerificationStatus.FAILED):
        with pytest.raises(ValueError,match="not verified"):
            VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,verification_status=status))
    with pytest.raises(ValueError,match="device mismatch"):
        VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,device_id="bedroom-tv"))


def test_verified_media_state_rejects_incomplete_lineage():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-4",device_id="living-room-tv",receipt_id="receipt-4",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-4",transaction_id="transaction-4",capability_digest="capability-4",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for field in ("device_id","intent_id","receipt_id","expected_state_digest","observed_state_digest","authorization_digest","transaction_id","capability_digest","observed_state_evidence_digest"):
        for invalid in ("", "   ", None):
            with pytest.raises(ValueError,match="incomplete physical verification lineage"):
                VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,**{field:invalid}))
    for field in ("device_id","evidence_digest"):
        for invalid in ("", "   ", None):
            with pytest.raises(ValueError,match="incomplete physical verification lineage"):
                VerifiedMediaControlState.from_physical_verification(replace(snapshot,**{field:invalid}),verification)


def test_verified_media_state_rejects_digest_and_evidence_mismatches():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-5",device_id="living-room-tv",receipt_id="receipt-5",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-5",transaction_id="transaction-5",capability_digest="capability-5",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    with pytest.raises(ValueError,match="digest mismatch"):
        VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,expected_state_digest="tampered"))
    with pytest.raises(ValueError,match="evidence mismatch"):
        VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,observed_state_evidence_digest="different-evidence"))
    state.volume=43
    with pytest.raises(ValueError,match="digest mismatch"):
        VerifiedMediaControlState.from_physical_verification(snapshot,verification)


def test_verified_media_state_rejects_invalid_epochs():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-6",device_id="living-room-tv",receipt_id="receipt-6",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-6",transaction_id="transaction-6",capability_digest="capability-6",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (True,-1,7.0,"7",None):
        with pytest.raises(ValueError,match="observation epoch mismatch"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,epoch=invalid),verification)
    for invalid in (True,-1,7.0,"7",None,8):
        with pytest.raises(ValueError,match="observation epoch mismatch"):
            VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,observed_state_epoch=invalid))
    for invalid in (True,-1,6.0,"6",None,8):
        with pytest.raises(ValueError,match="world-state epoch"):
            VerifiedMediaControlState.from_physical_verification(snapshot,replace(verification,world_state_epoch=invalid))


def test_verified_media_state_rejects_invalid_observation_time():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-7",device_id="living-room-tv",receipt_id="receipt-7",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-7",transaction_id="transaction-7",capability_digest="capability-7",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (True,-1.0,float("nan"),float("inf"),float("-inf"),"100",None):
        with pytest.raises(ValueError,match="observation time"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,observed_at=invalid),verification)


def test_verified_media_state_rejects_invalid_volume():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-8",device_id="living-room-tv",receipt_id="receipt-8",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-8",transaction_id="transaction-8",capability_digest="capability-8",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (True,42.0,-1,101):
        invalid_state=DeviceState(volume=invalid)
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified volume"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_invalid_captions():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-9",device_id="living-room-tv",receipt_id="receipt-9",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-9",transaction_id="transaction-9",capability_digest="capability-9",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (None,1,0,"true",[]):
        invalid_state=DeviceState(volume=42,custom_state={"captions_enabled":invalid})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified captions"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_non_dict_custom_state():
    class DictSubclass(dict):
        pass
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-10",device_id="living-room-tv",receipt_id="receipt-10",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-10",transaction_id="transaction-10",capability_digest="capability-10",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in ([],DictSubclass()):
        invalid_state=DeviceState(volume=42,custom_state=invalid)
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified custom state"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_invalid_eq_preset():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-11",device_id="living-room-tv",receipt_id="receipt-11",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-11",transaction_id="transaction-11",capability_digest="capability-11",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (None,True,1,"UNKNOWN",[]):
        invalid_state=DeviceState(volume=42,custom_state={"eq_preset":invalid})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified EQ preset"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_eq_conflict_and_invalid_band_container():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-12",device_id="living-room-tv",receipt_id="receipt-12",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-12",transaction_id="transaction-12",capability_digest="capability-12",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    conflict_state=DeviceState(volume=42,custom_state={"eq_preset":"DIALOGUE","eq_bands":[{"frequency_hz":1000.0,"gain_db":3.0}]})
    conflict_verification=replace(verification,expected_state_digest=conflict_state.state_digest,observed_state_digest=conflict_state.state_digest)
    with pytest.raises(ValueError,match="combines EQ preset and bands"):
        VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=conflict_state),conflict_verification)
    invalid_containers=(None,(),[],[{"frequency_hz":float(index+20),"gain_db":0.0} for index in range(11)])
    for invalid in invalid_containers:
        invalid_state=DeviceState(volume=42,custom_state={"eq_bands":invalid})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified EQ bands"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_invalid_eq_band_shape_and_order():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-13",device_id="living-room-tv",receipt_id="receipt-13",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-13",transaction_id="transaction-13",capability_digest="capability-13",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    invalid_shapes=([None],[{"frequency_hz":1000.0}],[{"gain_db":3.0}],[{"frequency_hz":1000.0,"gain_db":3.0,"extra":True}])
    for invalid in invalid_shapes:
        invalid_state=DeviceState(volume=42,custom_state={"eq_bands":invalid})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="invalid verified EQ band"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)
    for invalid in (({"frequency_hz":1000.0,"gain_db":1.0},{"frequency_hz":1000.0,"gain_db":2.0}),({"frequency_hz":2000.0,"gain_db":1.0},{"frequency_hz":1000.0,"gain_db":2.0})):
        invalid_state=DeviceState(volume=42,custom_state={"eq_bands":list(invalid)})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError,match="must increase"):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_invalid_eq_band_values():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-14",device_id="living-room-tv",receipt_id="receipt-14",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-14",transaction_id="transaction-14",capability_digest="capability-14",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    for invalid in (True,"1000",None,float("nan"),float("inf"),float("-inf"),19.99,20000.01):
        invalid_state=DeviceState(volume=42,custom_state={"eq_bands":[{"frequency_hz":invalid,"gain_db":0.0}]})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)
    for invalid in (True,"3",None,float("nan"),float("inf"),float("-inf"),-12.01,12.01):
        invalid_state=DeviceState(volume=42,custom_state={"eq_bands":[{"frequency_hz":1000.0,"gain_db":invalid}]})
        invalid_verification=replace(verification,expected_state_digest=invalid_state.state_digest,observed_state_digest=invalid_state.state_digest)
        with pytest.raises(ValueError):
            VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=invalid_state),invalid_verification)


def test_verified_media_state_rejects_invalid_profile_projection():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-15",device_id="living-room-tv",receipt_id="receipt-15",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-15",transaction_id="transaction-15",capability_digest="capability-15",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-15",content_generation=15,caption_capability=CaptionCapability.NONE,eq_capability=EqCapability.NONE,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=90.0,expires_monotonic=120.0,clock_domain_id="runtime-monotonic")
    with pytest.raises(ValueError,match="invalid capability manifest"):
        verified.to_user_default_profile(object(),name="My Default")
    with pytest.raises(ValueError,match="device mismatch"):
        verified.to_user_default_profile(replace(manifest,device_id="bedroom-tv"),name="My Default")
    with pytest.raises(ValueError,match="no verified settings supported"):
        verified.to_user_default_profile(manifest,name="My Default")


def test_verified_media_state_is_immutable_and_snapshot_isolated():
    bands=[{"frequency_hz":1000.0,"gain_db":3.0}]
    custom={"captions_enabled":True,"eq_bands":bands}
    state=DeviceState(volume=42,custom_state=custom)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-16",device_id="living-room-tv",receipt_id="receipt-16",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-16",transaction_id="transaction-16",capability_digest="capability-16",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    state.volume=99
    custom["captions_enabled"]=False
    bands[0]["frequency_hz"]=2000.0
    bands[0]["gain_db"]=-3.0
    assert verified.volume_percent==42
    assert verified.captions_enabled is True
    assert verified.eq_bands==(EqBandGain(1000,3),)
    with pytest.raises(AttributeError):
        verified.volume_percent=99


def test_verified_media_state_rejects_invalid_physical_input_types():
    state=DeviceState(volume=42)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="observed-media-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-17",device_id="living-room-tv",receipt_id="receipt-17",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-17",transaction_id="transaction-17",capability_digest="capability-17",observed_state_evidence_digest="observed-media-evidence",world_state_epoch=6,observed_state_epoch=7,verification_status=VerificationStatus.VERIFIED)
    with pytest.raises(ValueError,match="invalid physical verification input"):
        VerifiedMediaControlState.from_physical_verification(object(),verification)
    with pytest.raises(ValueError,match="invalid physical verification input"):
        VerifiedMediaControlState.from_physical_verification(snapshot,object())
    with pytest.raises(ValueError,match="invalid observed device state"):
        VerifiedMediaControlState.from_physical_verification(replace(snapshot,state=object()),verification)
