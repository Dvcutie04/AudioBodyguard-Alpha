from dataclasses import replace

import pytest

from src.control.media_control_capabilities import (
    CaptionCapability,
    EqBandGain,
    EqCapability,
    MediaControlCapabilityManifest,
    MediaControlOperation,
    VerificationStrength,
)
from src.control.media_control_options import (
    DeviceDisplayMetadata,
    MediaControlRecoveryActionKey,
)
from src.control.media_control_options_page import MediaControlOptionsPageBuilder
from src.control.media_control_verified_state import VerifiedMediaControlState
from src.control.media_control_prior_state import MediaControlPriorState
from src.control.media_control_undo_candidate import MediaControlUndoCandidate
from src.device_fabric.contracts import AuthorizedActionIntent, DeviceState, PhysicalSnapshot, PhysicalVerificationRecord, VerificationStatus
from src.control.media_control_profiles import (
    MediaControlProfileKind,
    MediaControlProfileStore,
    MediaControlSettingsProfile,
)


def test_page_derives_recovery_actions_from_durable_defaults(tmp_path):
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-9",
        content_generation=9,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.BANDS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=300.0,
        expires_monotonic=330.0,
        clock_domain_id="runtime-monotonic",
    )
    device = DeviceDisplayMetadata(
        device_id="living-room-tv",
        display_name="Living Room TV",
        brand="Samsung",
        model="QN90D",
        metadata_verified=True,
    )
    recommended = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="Recommended",
        kind=MediaControlProfileKind.RECOMMENDED,
        volume_percent=42,
        captions_enabled=True,
        eq_bands=(EqBandGain(1000, 3),),
    )
    personal = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="My Default",
        kind=MediaControlProfileKind.USER_DEFAULT,
        volume_percent=30,
        captions_enabled=False,
        eq_bands=(EqBandGain(1000, 1),),
    )
    store = MediaControlProfileStore(tmp_path / "page-defaults.sqlite3")
    page = MediaControlOptionsPageBuilder(store)

    menu = page.build_menu(
        manifest,
        device=device,
        user_profile_id="profile-1",
        recommended=recommended,
    )
    assert menu.action(MediaControlRecoveryActionKey.APPLY_RECOMMENDED).available is True
    save = menu.action(MediaControlRecoveryActionKey.SAVE_MY_DEFAULT)
    assert save.available is False
    assert save.unavailable_reason == "No verified current settings to save"
    assert menu.action(MediaControlRecoveryActionKey.RESTORE_MY_DEFAULT).available is False
    assert menu.action(MediaControlRecoveryActionKey.RESET_DEVICE_PREFERENCES).available is False
    assert menu.action(MediaControlRecoveryActionKey.UNDO_LAST_CHANGE).available is False

    store.save_my_default("profile-1", personal)
    menu = page.build_menu(
        manifest,
        device=device,
        user_profile_id="profile-1",
        recommended=recommended,
    )
    assert menu.action(MediaControlRecoveryActionKey.RESTORE_MY_DEFAULT).available is True
    assert menu.action(MediaControlRecoveryActionKey.RESET_DEVICE_PREFERENCES).available is True
    undo = menu.action(MediaControlRecoveryActionKey.UNDO_LAST_CHANGE)
    assert undo.available is False
    assert undo.unavailable_reason == "No verified change to undo"


def test_page_actions_create_fresh_proposals_for_current_manifest(tmp_path):
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-10",
        content_generation=10,
        caption_capability=CaptionCapability.NONE,
        eq_capability=EqCapability.VOLUME_ONLY,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=400.0,
        expires_monotonic=430.0,
        clock_domain_id="runtime-monotonic",
    )
    recommended = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="Recommended",
        kind=MediaControlProfileKind.RECOMMENDED,
        volume_percent=42,
    )
    personal = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="My Default",
        kind=MediaControlProfileKind.USER_DEFAULT,
        volume_percent=30,
    )
    store = MediaControlProfileStore(tmp_path / "page-proposals.sqlite3")
    store.save_my_default("profile-1", personal)
    page = MediaControlOptionsPageBuilder(store)

    recommended_requests = page.propose_recommended(
        manifest,
        recommended=recommended,
    )
    restored_requests = page.propose_restore_my_default(
        manifest,
        user_profile_id="profile-1",
    )

    assert tuple(request.operation for request in recommended_requests) == (
        MediaControlOperation.SET_VOLUME,
    )
    assert dict(recommended_requests[0].parameters) == {"volume_percent": 42}
    assert dict(restored_requests[0].parameters) == {"volume_percent": 30}
    for request in recommended_requests + restored_requests:
        assert request.playback_session_id == "session-10"
        assert request.content_generation == 10
        assert request.capability_manifest_digest == manifest.digest


def test_reset_device_preferences_removes_saved_default(tmp_path):
    personal = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="My Default",
        kind=MediaControlProfileKind.USER_DEFAULT,
        volume_percent=30,
    )
    store = MediaControlProfileStore(tmp_path / "page-reset.sqlite3")
    store.save_my_default("profile-1", personal)
    page = MediaControlOptionsPageBuilder(store)

    assert page.reset_device_preferences(
        user_profile_id="profile-1",
        device_id="living-room-tv",
    ) is True
    assert store.get_my_default("profile-1", "living-room-tv") is None
    assert page.reset_device_preferences(
        user_profile_id="profile-1",
        device_id="living-room-tv",
    ) is False


def test_page_enables_save_for_verified_current_settings(tmp_path):
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-save",content_generation=12,caption_capability=CaptionCapability.NONE,eq_capability=EqCapability.VOLUME_ONLY,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=500.0,expires_monotonic=530.0,clock_domain_id="runtime-monotonic")
    device=DeviceDisplayMetadata(device_id="living-room-tv",display_name="Living Room TV",brand="Samsung",model="QN90D",metadata_verified=True)
    recommended=MediaControlSettingsProfile(device_id="living-room-tv",name="Recommended",kind=MediaControlProfileKind.RECOMMENDED,volume_percent=42)
    state=DeviceState(volume=37)
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=8,observed_at=501.0,evidence_digest="save-current-observation")
    verification=PhysicalVerificationRecord(intent_id="intent-save-current",device_id="living-room-tv",receipt_id="receipt-save-current",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest="authorization-save-current",transaction_id="transaction-save-current",capability_digest="capability-save-current",observed_state_evidence_digest="save-current-observation",world_state_epoch=7,observed_state_epoch=8,verification_status=VerificationStatus.VERIFIED)
    verified=VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    store=MediaControlProfileStore(tmp_path / "page-save-current.sqlite3")
    page=MediaControlOptionsPageBuilder(store)
    menu=page.build_menu(manifest,device=device,user_profile_id="profile-1",recommended=recommended,verified_state=verified)
    assert menu.action(MediaControlRecoveryActionKey.SAVE_MY_DEFAULT).available is True
    page.save_verified_current_as_my_default(manifest,user_profile_id="profile-1",verified_state=verified)
    saved=store.get_my_default("profile-1","living-room-tv")
    assert saved is not None
    assert saved.kind is MediaControlProfileKind.USER_DEFAULT
    assert saved.volume_percent==37


def test_save_verified_current_failures_never_overwrite_existing_default(tmp_path):
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-fail-closed",content_generation=13,caption_capability=CaptionCapability.NONE,eq_capability=EqCapability.VOLUME_ONLY,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=600.0,expires_monotonic=630.0,clock_domain_id="runtime-monotonic")
    unsupported_manifest=replace(manifest,eq_capability=EqCapability.NONE)
    incompatible_manifest=replace(manifest,device_id="bedroom-tv")
    baseline=MediaControlSettingsProfile(device_id="living-room-tv",name="Existing Default",kind=MediaControlProfileKind.USER_DEFAULT,volume_percent=21)
    store=MediaControlProfileStore(tmp_path / "page-save-fail-closed.sqlite3")
    store.save_my_default("profile-1",baseline)
    page=MediaControlOptionsPageBuilder(store)
    def verified_for(device_id):
        state=DeviceState(volume=37)
        evidence=f"evidence-{device_id}"
        snapshot=PhysicalSnapshot(device_id=device_id,state=state,epoch=8,observed_at=601.0,evidence_digest=evidence)
        verification=PhysicalVerificationRecord(intent_id=f"intent-{device_id}",device_id=device_id,receipt_id=f"receipt-{device_id}",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest=f"authorization-{device_id}",transaction_id=f"transaction-{device_id}",capability_digest=f"capability-{device_id}",observed_state_evidence_digest=evidence,world_state_epoch=7,observed_state_epoch=8,verification_status=VerificationStatus.VERIFIED)
        return VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    verified=verified_for("living-room-tv")
    wrong_device=verified_for("bedroom-tv")
    attempts=((manifest,wrong_device,"My Default"),(unsupported_manifest,verified,"My Default"),(manifest,object(),"My Default"),(manifest,None,"My Default"),(manifest,verified," "),(incompatible_manifest,verified,"My Default"))
    for attempted_manifest,attempted_state,name in attempts:
        with pytest.raises(ValueError):
            page.save_verified_current_as_my_default(attempted_manifest,user_profile_id="profile-1",verified_state=attempted_state,name=name)
        assert store.get_my_default("profile-1","living-room-tv")==baseline


def test_page_save_eligibility_is_derived_only_from_matching_verified_state(tmp_path):
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-menu-gate",content_generation=14,caption_capability=CaptionCapability.NONE,eq_capability=EqCapability.VOLUME_ONLY,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=700.0,expires_monotonic=730.0,clock_domain_id="runtime-monotonic")
    unsupported_manifest=replace(manifest,eq_capability=EqCapability.NONE,caption_capability=CaptionCapability.NATIVE_TRACK)
    device=DeviceDisplayMetadata(device_id="living-room-tv",display_name="Living Room TV",brand="Samsung",model="QN90D",metadata_verified=True)
    recommended=MediaControlSettingsProfile(device_id="living-room-tv",name="Recommended",kind=MediaControlProfileKind.RECOMMENDED,volume_percent=42)
    def verified_for(device_id):
        state=DeviceState(volume=37)
        evidence=f"menu-evidence-{device_id}"
        snapshot=PhysicalSnapshot(device_id=device_id,state=state,epoch=9,observed_at=701.0,evidence_digest=evidence)
        verification=PhysicalVerificationRecord(intent_id=f"menu-intent-{device_id}",device_id=device_id,receipt_id=f"menu-receipt-{device_id}",expected_state_digest=state.state_digest,observed_state_digest=state.state_digest,authorization_digest=f"menu-authorization-{device_id}",transaction_id=f"menu-transaction-{device_id}",capability_digest=f"menu-capability-{device_id}",observed_state_evidence_digest=evidence,world_state_epoch=8,observed_state_epoch=9,verification_status=VerificationStatus.VERIFIED)
        return VerifiedMediaControlState.from_physical_verification(snapshot,verification)
    page=MediaControlOptionsPageBuilder(MediaControlProfileStore(tmp_path / "page-menu-gate.sqlite3"))
    verified=verified_for("living-room-tv")
    for attempted_manifest,attempted_state in ((manifest,None),(manifest,object()),(manifest,verified_for("bedroom-tv")),(unsupported_manifest,verified)):
        compatible_recommended=replace(recommended,volume_percent=None,captions_enabled=True) if attempted_manifest is unsupported_manifest else recommended
        menu=page.build_menu(attempted_manifest,device=device,user_profile_id="profile-1",recommended=compatible_recommended,verified_state=attempted_state)
        save=menu.action(MediaControlRecoveryActionKey.SAVE_MY_DEFAULT)
        assert save.available is False
        assert save.unavailable_reason=="No verified current settings to save"
    with pytest.raises(TypeError):
        page.build_menu(manifest,device=device,user_profile_id="profile-1",recommended=recommended,can_save_current=True)


def test_page_undo_creates_fresh_precondition_bound_proposal(tmp_path):
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-undo-current",content_generation=20,caption_capability=CaptionCapability.NONE,eq_capability=EqCapability.VOLUME_ONLY,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=800.0,expires_monotonic=830.0,clock_domain_id="runtime-monotonic")
    device=DeviceDisplayMetadata(device_id="living-room-tv",display_name="Living Room TV",brand="Samsung",model="QN90D",metadata_verified=True)
    recommended=MediaControlSettingsProfile(device_id="living-room-tv",name="Recommended",kind=MediaControlProfileKind.RECOMMENDED,volume_percent=42)
    prior_state=DeviceState(volume=21)
    post_state=DeviceState(volume=37)
    authorized=AuthorizedActionIntent(intent_id="intent-page-undo",device_id="living-room-tv",operation="set_volume",target_state=post_state,expected_pre_state=prior_state,authorization_digest="authorization-page-undo",transaction_id="transaction-page-undo",capability_digest="capability-page-undo")
    prior=MediaControlPriorState.from_authorized_snapshot(PhysicalSnapshot(device_id="living-room-tv",state=prior_state,epoch=19,observed_at=801.0,evidence_digest="page-undo-prior-evidence"),authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_state,epoch=20,observed_at=802.0,evidence_digest="page-undo-post-evidence")
    verification=PhysicalVerificationRecord(intent_id="intent-page-undo",device_id="living-room-tv",receipt_id="receipt-page-undo",expected_state_digest=post_state.state_digest,observed_state_digest=post_state.state_digest,authorization_digest="authorization-page-undo",transaction_id="transaction-page-undo",capability_digest="capability-page-undo",observed_state_evidence_digest="page-undo-post-evidence",world_state_epoch=19,observed_state_epoch=20,verification_status=VerificationStatus.VERIFIED)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,VerifiedMediaControlState.from_physical_verification(post_snapshot,verification))
    page=MediaControlOptionsPageBuilder(MediaControlProfileStore(tmp_path / "page-undo.sqlite3"))
    menu=page.build_menu(manifest,device=device,user_profile_id="profile-1",recommended=recommended,undo_candidate=candidate)
    assert menu.action(MediaControlRecoveryActionKey.UNDO_LAST_CHANGE).available is True
    request=page.propose_undo(manifest,undo_candidate=candidate)
    assert request.operation is MediaControlOperation.SET_VOLUME
    assert dict(request.parameters)=={"volume_percent":21}
    assert request.playback_session_id=="session-undo-current"
    assert request.content_generation==20
    assert request.capability_manifest_digest==manifest.digest
    assert request.expected_pre_state_digest==post_state.state_digest


def test_page_undo_fails_closed_when_current_manifest_denies_operation(tmp_path):
    manifest=MediaControlCapabilityManifest(device_id="living-room-tv",adapter_id="matter-tv",playback_session_id="session-undo-denied",content_generation=21,caption_capability=CaptionCapability.NATIVE_TRACK,eq_capability=EqCapability.NONE,verification_strength=VerificationStrength.OBSERVED,issued_monotonic=900.0,expires_monotonic=930.0,clock_domain_id="runtime-monotonic")
    device=DeviceDisplayMetadata(device_id="living-room-tv",display_name="Living Room TV",brand="Samsung",model="QN90D",metadata_verified=True)
    recommended=MediaControlSettingsProfile(device_id="living-room-tv",name="Recommended",kind=MediaControlProfileKind.RECOMMENDED,captions_enabled=True)
    prior_state=DeviceState(volume=21)
    post_state=DeviceState(volume=37)
    authorized=AuthorizedActionIntent(intent_id="intent-page-undo-denied",device_id="living-room-tv",operation="set_volume",target_state=post_state,expected_pre_state=prior_state,authorization_digest="authorization-page-undo-denied",transaction_id="transaction-page-undo-denied",capability_digest="capability-page-undo-denied")
    prior=MediaControlPriorState.from_authorized_snapshot(PhysicalSnapshot(device_id="living-room-tv",state=prior_state,epoch=20,observed_at=901.0,evidence_digest="page-undo-denied-prior"),authorized)
    post_snapshot=PhysicalSnapshot(device_id="living-room-tv",state=post_state,epoch=21,observed_at=902.0,evidence_digest="page-undo-denied-post")
    verification=PhysicalVerificationRecord(intent_id="intent-page-undo-denied",device_id="living-room-tv",receipt_id="receipt-page-undo-denied",expected_state_digest=post_state.state_digest,observed_state_digest=post_state.state_digest,authorization_digest="authorization-page-undo-denied",transaction_id="transaction-page-undo-denied",capability_digest="capability-page-undo-denied",observed_state_evidence_digest="page-undo-denied-post",world_state_epoch=20,observed_state_epoch=21,verification_status=VerificationStatus.VERIFIED)
    candidate=MediaControlUndoCandidate.from_verified_change(prior,VerifiedMediaControlState.from_physical_verification(post_snapshot,verification))
    page=MediaControlOptionsPageBuilder(MediaControlProfileStore(tmp_path / "page-undo-denied.sqlite3"))
    menu=page.build_menu(manifest,device=device,user_profile_id="profile-1",recommended=recommended,undo_candidate=candidate)
    undo=menu.action(MediaControlRecoveryActionKey.UNDO_LAST_CHANGE)
    assert undo.available is False
    assert undo.unavailable_reason=="No verified change to undo"
    with pytest.raises(ValueError,match="undo operation is not supported by capability manifest"):
        page.propose_undo(manifest,undo_candidate=candidate)
