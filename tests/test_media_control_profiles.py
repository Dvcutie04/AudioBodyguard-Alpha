import sqlite3

import pytest

from src.control.media_control_capabilities import (
    CaptionCapability,
    EqBandGain,
    EqCapability,
    MediaControlCapabilityDecision,
    MediaControlCapabilityGate,
    MediaControlCapabilityManifest,
    MediaControlOperation,
    VerificationStrength,
)
from src.control.media_control_profiles import (
    MediaControlProfileKind,
    MediaControlProfileStore,
    MediaControlSettingsProfile,
)


def test_recommended_profile_rebinds_to_current_manifest():
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-8",
        content_generation=8,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.BANDS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=200.0,
        expires_monotonic=230.0,
        clock_domain_id="runtime-monotonic",
    )
    profile = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="Recommended",
        kind=MediaControlProfileKind.RECOMMENDED,
        volume_percent=42,
        captions_enabled=True,
        eq_bands=(EqBandGain(1000, 3),),
    )
    requests = profile.requests_for(manifest)
    assert tuple(request.operation for request in requests) == (
        MediaControlOperation.SET_CAPTIONS_ENABLED,
        MediaControlOperation.SET_EQ_BANDS,
        MediaControlOperation.SET_VOLUME,
    )
    assert all(request.playback_session_id == "session-8" for request in requests)
    assert all(request.content_generation == 8 for request in requests)
    assert all(request.capability_manifest_digest == manifest.digest for request in requests)
    assert all(MediaControlCapabilityGate.evaluate(request, manifest) is MediaControlCapabilityDecision.ALLOW for request in requests)


def test_saved_default_survives_reopen_and_resets_to_recommended(tmp_path):
    database_path = tmp_path / "media-control-defaults.sqlite3"
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
    store = MediaControlProfileStore(database_path)
    assert store.resolve("profile-1", recommended=recommended) == recommended

    store.save_my_default("profile-1", personal)
    reopened = MediaControlProfileStore(database_path)
    assert reopened.resolve("profile-1", recommended=recommended) == personal

    assert reopened.reset_my_default("profile-1", "living-room-tv") is True
    assert reopened.resolve("profile-1", recommended=recommended) == recommended
    assert reopened.reset_my_default("profile-1", "living-room-tv") is False


def test_corrupt_saved_default_fails_closed(tmp_path):
    database_path = tmp_path / "corrupt-media-control-defaults.sqlite3"
    store = MediaControlProfileStore(database_path)
    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT INTO media_control_user_defaults "
        "(user_profile_id, device_id, payload) VALUES (?, ?, ?)",
        ("profile-1", "living-room-tv", "corrupt"),
    )
    connection.commit()
    connection.close()
    recommended = MediaControlSettingsProfile(
        device_id="living-room-tv",
        name="Recommended",
        kind=MediaControlProfileKind.RECOMMENDED,
        volume_percent=42,
    )

    with pytest.raises(ValueError, match="invalid stored media control profile"):
        store.resolve("profile-1", recommended=recommended)
