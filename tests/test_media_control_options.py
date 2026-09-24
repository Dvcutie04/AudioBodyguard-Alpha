import pytest

from src.control.media_control_capabilities import (
    CaptionCapability,
    EqCapability,
    MediaControlCapabilityManifest,
    VerificationStrength,
)
from src.control.media_control_options import (
    DeviceDisplayMetadata,
    MediaControlOptionKey,
    MediaControlOptionsMenu,
    MediaControlRecoveryActionKey,
    MediaControlRecoveryState,
)


def test_options_menu_identifies_device_and_explains_every_control():
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.BANDS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=130.0,
        clock_domain_id="runtime-monotonic",
    )
    menu = MediaControlOptionsMenu.for_manifest(
        manifest,
        device=DeviceDisplayMetadata(
            device_id="living-room-tv",
            display_name="Living Room TV",
            brand="Samsung",
            model="QN90D",
            metadata_verified=True,
        ),
        recovery=MediaControlRecoveryState(
            has_recommended_profile=True,
            has_saved_default=False,
            can_undo=False,
        ),
    )

    assert menu.device_heading == "Living Room TV"
    assert menu.device_detail == "Samsung • QN90D"
    assert tuple(item.key for item in menu.items) == (
        MediaControlOptionKey.VOLUME,
        MediaControlOptionKey.CAPTIONS,
        MediaControlOptionKey.EQ_PRESET,
        MediaControlOptionKey.EQ_BANDS,
    )
    assert all(item.description.strip() for item in menu.items)
    assert all(item.example.strip().startswith("Example:") for item in menu.items)
    assert menu.item(MediaControlOptionKey.VOLUME).available is True
    assert menu.item(MediaControlOptionKey.CAPTIONS).available is True
    assert menu.item(MediaControlOptionKey.EQ_PRESET).available is False
    assert menu.item(MediaControlOptionKey.EQ_BANDS).available is True
    assert tuple(action.label for action in menu.recovery_actions) == (
        "Apply Recommended",
        "Save Current as My Default",
        "Restore My Default",
        "Undo Last Change",
        "Reset Device Preferences",
    )
    assert menu.action(MediaControlRecoveryActionKey.APPLY_RECOMMENDED).available is True
    restore = menu.action(MediaControlRecoveryActionKey.RESTORE_MY_DEFAULT)
    assert restore.available is False
    assert restore.unavailable_reason == "Save a personal default first"
    undo = menu.action(MediaControlRecoveryActionKey.UNDO_LAST_CHANGE)
    assert undo.available is False
    assert undo.unavailable_reason == "No verified change to undo"
    reset = menu.action(MediaControlRecoveryActionKey.RESET_DEVICE_PREFERENCES)
    assert reset.available is False
    assert reset.unavailable_reason == "No personal default to reset"


def test_options_menu_rejects_metadata_for_another_device():
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.BANDS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=130.0,
        clock_domain_id="runtime-monotonic",
    )
    metadata = DeviceDisplayMetadata(
        device_id="bedroom-tv",
        display_name="Bedroom TV",
        brand="Samsung",
        model="QN90D",
        metadata_verified=True,
    )

    with pytest.raises(ValueError, match="device metadata mismatch"):
        MediaControlOptionsMenu.for_manifest(manifest, device=metadata)
