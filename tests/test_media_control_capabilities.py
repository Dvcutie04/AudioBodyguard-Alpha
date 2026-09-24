from dataclasses import FrozenInstanceError

import pytest

from src.control.media_control_capabilities import (
    CaptionCapability,
    EqCapability,
    EqPreset,
    EqBandGain,
    MediaControlCapabilityManifest,
    MediaControlCapabilityManifestIssuer,
    MediaControlCapabilityManifestVerifier,
    MediaControlOperation,
    MediaControlRequest,
    MediaControlCapabilityDecision,
    MediaControlCapabilityGate,
    SignedMediaControlCapabilityManifest,
    VerificationStrength,
)


def test_media_capability_taxonomy_is_closed_and_truthful():
    assert tuple(member.value for member in CaptionCapability) == (
        "NATIVE_TRACK",
        "DEVICE_MODE",
        "PHONE_TRANSCRIPT",
        "NONE",
    )
    assert tuple(member.value for member in EqCapability) == (
        "BANDS",
        "SEMANTIC_PRESETS",
        "VOLUME_ONLY",
        "NONE",
    )
    assert tuple(member.value for member in VerificationStrength) == (
        "OBSERVED",
        "ACK_ONLY",
        "NONE",
    )


def test_media_capability_manifest_binds_device_adapter_and_playback_generation():
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    assert manifest.device_id == "living-room-tv"
    assert manifest.adapter_id == "aqss-tv-adapter"
    assert manifest.playback_session_id == "session-7"
    assert manifest.content_generation == 7
    with pytest.raises(FrozenInstanceError):
        manifest.content_generation = 8


@pytest.mark.parametrize(("field", "value"), (
    ("device_id", ""),
    ("device_id", "   "),
    ("device_id", None),
    ("adapter_id", ""),
    ("adapter_id", 7),
    ("playback_session_id", ""),
    ("playback_session_id", None),
    ("content_generation", True),
    ("content_generation", -1),
    ("content_generation", 1.0),
    ("caption_capability", "NATIVE_TRACK"),
    ("eq_capability", "BANDS"),
    ("verification_strength", "OBSERVED"),
))
def test_media_capability_manifest_rejects_malformed_scope_and_untyped_capabilities(field, value):
    values = {
        "device_id": "living-room-tv",
        "adapter_id": "aqss-tv-adapter",
        "playback_session_id": "session-7",
        "content_generation": 7,
        "caption_capability": CaptionCapability.NATIVE_TRACK,
        "eq_capability": EqCapability.SEMANTIC_PRESETS,
        "verification_strength": VerificationStrength.OBSERVED,
        "issued_monotonic": 100.0,
        "expires_monotonic": 100.5,
        "clock_domain_id": "process:trusted-test-domain",
    }
    values[field] = value
    with pytest.raises(ValueError):
        MediaControlCapabilityManifest(**values)


def test_media_capability_manifest_requires_strictly_increasing_monotonic_validity():
    with pytest.raises(ValueError):
        MediaControlCapabilityManifest(
            device_id="living-room-tv",
            adapter_id="aqss-tv-adapter",
            playback_session_id="session-7",
            content_generation=7,
            caption_capability=CaptionCapability.NATIVE_TRACK,
            eq_capability=EqCapability.SEMANTIC_PRESETS,
            verification_strength=VerificationStrength.OBSERVED,
            issued_monotonic=100.0,
            expires_monotonic=100.0,
            clock_domain_id="process:trusted-test-domain",
        )


@pytest.mark.parametrize(("field", "value"), (
    ("issued_monotonic", True),
    ("issued_monotonic", -0.1),
    ("issued_monotonic", float("nan")),
    ("issued_monotonic", float("inf")),
    ("expires_monotonic", True),
    ("expires_monotonic", -0.1),
    ("expires_monotonic", float("nan")),
    ("expires_monotonic", float("inf")),
    ("expires_monotonic", 100.0),
    ("expires_monotonic", 99.9),
    ("clock_domain_id", ""),
    ("clock_domain_id", "   "),
    ("clock_domain_id", None),
    ("clock_domain_id", 7),
))
def test_media_capability_manifest_rejects_malformed_monotonic_validity_and_clock_domain(field, value):
    values = {
        "device_id": "living-room-tv",
        "adapter_id": "aqss-tv-adapter",
        "playback_session_id": "session-7",
        "content_generation": 7,
        "caption_capability": CaptionCapability.NATIVE_TRACK,
        "eq_capability": EqCapability.SEMANTIC_PRESETS,
        "verification_strength": VerificationStrength.OBSERVED,
        "issued_monotonic": 100.0,
        "expires_monotonic": 100.5,
        "clock_domain_id": "process:trusted-test-domain",
    }
    values[field] = value
    with pytest.raises(ValueError):
        MediaControlCapabilityManifest(**values)


def test_media_capability_manifest_has_exact_canonical_bytes_and_digest():
    from hashlib import sha256

    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    expected = b'{"adapter_id":"aqss-tv-adapter","caption_capability":"NATIVE_TRACK","clock_domain_id":"process:trusted-test-domain","content_generation":7,"device_id":"living-room-tv","eq_capability":"SEMANTIC_PRESETS","expires_monotonic":100.5,"issued_monotonic":100.0,"playback_session_id":"session-7","verification_strength":"OBSERVED"}'
    assert manifest.canonical_bytes == expected
    assert manifest.digest == sha256(expected).hexdigest()


@pytest.mark.parametrize(("field", "value"), (
    ("device_id", "bedroom-tv"),
    ("adapter_id", "replacement-adapter"),
    ("playback_session_id", "session-8"),
    ("content_generation", 8),
    ("caption_capability", CaptionCapability.DEVICE_MODE),
    ("eq_capability", EqCapability.BANDS),
    ("verification_strength", VerificationStrength.ACK_ONLY),
    ("issued_monotonic", 99.9),
    ("expires_monotonic", 100.6),
    ("clock_domain_id", "process:other-domain"),
))
def test_media_capability_manifest_digest_binds_every_field(field, value):
    from dataclasses import replace

    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    changed = replace(manifest, **{field: value})
    assert changed.canonical_bytes != manifest.canonical_bytes
    assert changed.digest != manifest.digest


def test_signed_media_capability_manifest_binds_manifest_and_authority():
    from dataclasses import replace

    from src.control.crypto_identity import KeyPair

    key = KeyPair.generate("media-capability-authority")
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    unsigned = SignedMediaControlCapabilityManifest(
        manifest=manifest,
        protocol_version="AQSS-1",
        issuer_id=key.key_id,
        nonce="media-manifest-7",
        signature="",
    )
    signed = replace(unsigned, signature=key.sign(unsigned.canonical_bytes))
    assert key.public_verifier.verify(signed.canonical_bytes, signed.signature)
    tampered = replace(
        signed,
        manifest=replace(manifest, content_generation=8),
    )
    assert not key.public_verifier.verify(
        tampered.canonical_bytes,
        tampered.signature,
    )


@pytest.mark.parametrize(("field", "value"), (
    ("manifest", None),
    ("manifest", {}),
    ("protocol_version", ""),
    ("protocol_version", "   "),
    ("protocol_version", None),
    ("issuer_id", ""),
    ("issuer_id", None),
    ("nonce", ""),
    ("nonce", None),
    ("signature", None),
    ("signature", b"not-text"),
))
def test_signed_media_capability_manifest_rejects_malformed_envelope(field, value):
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    values = {
        "manifest": manifest,
        "protocol_version": "AQSS-1",
        "issuer_id": "media-capability-authority",
        "nonce": "media-manifest-7",
        "signature": "",
    }
    values[field] = value
    with pytest.raises(ValueError):
        SignedMediaControlCapabilityManifest(**values)


def test_media_capability_manifest_issuer_owns_authority_metadata_and_signature():
    from src.control.crypto_identity import KeyPair

    key = KeyPair.generate("media-capability-authority")
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    issuer = MediaControlCapabilityManifestIssuer(
        key,
        protocol_version="AQSS-1",
    )
    signed = issuer.issue(
        manifest=manifest,
        nonce="media-manifest-7",
    )
    assert signed.manifest is manifest
    assert signed.protocol_version == "AQSS-1"
    assert signed.issuer_id == key.key_id
    assert signed.nonce == "media-manifest-7"
    assert signed.signature
    assert key.public_verifier.verify(
        signed.canonical_bytes,
        signed.signature,
    )


@pytest.mark.parametrize(("field", "value"), (
    ("manifest", None),
    ("manifest", {}),
    ("nonce", ""),
    ("nonce", "   "),
    ("nonce", None),
    ("nonce", 7),
))
def test_media_capability_manifest_issuer_rejects_invalid_request_before_signing(field, value):
    calls = []

    class RecordingSigner:
        key_id = "media-capability-authority"

        def sign(self, data):
            calls.append(data)
            return "unexpected-signature"

    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    issuer = MediaControlCapabilityManifestIssuer(
        RecordingSigner(),
        protocol_version="AQSS-1",
    )
    values = {"manifest": manifest, "nonce": "media-manifest-7"}
    values[field] = value
    with pytest.raises(ValueError):
        issuer.issue(**values)
    assert calls == []


def test_media_capability_manifest_verifier_accepts_current_trusted_manifest():
    from src.control.crypto_identity import KeyPair

    key = KeyPair.generate("media-capability-authority")
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    signed = MediaControlCapabilityManifestIssuer(
        key,
        protocol_version="AQSS-1",
    ).issue(manifest=manifest, nonce="media-manifest-7")
    verifier = MediaControlCapabilityManifestVerifier(
        key.public_verifier,
        protocol_version="AQSS-1",
        clock_domain_id="process:trusted-test-domain",
    )
    assert verifier.verify(
        signed,
        now_monotonic=100.25,
    ) is manifest


def test_media_capability_manifest_verifier_rejects_untrusted_or_noncurrent_evidence():
    from dataclasses import replace

    from src.control.crypto_identity import KeyPair

    key = KeyPair.generate("media-capability-authority")
    other_key = KeyPair.generate("untrusted-media-authority")
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="aqss-tv-adapter",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.SEMANTIC_PRESETS,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=100.5,
        clock_domain_id="process:trusted-test-domain",
    )
    signed = MediaControlCapabilityManifestIssuer(
        key,
        protocol_version="AQSS-1",
    ).issue(manifest=manifest, nonce="media-manifest-7")
    verifier = MediaControlCapabilityManifestVerifier(
        key.public_verifier,
        protocol_version="AQSS-1",
        clock_domain_id="process:trusted-test-domain",
    )
    with pytest.raises(ValueError, match="signature is invalid"):
        verifier.verify(
            replace(signed, signature="forged-signature"),
            now_monotonic=100.25,
        )
    untrusted = MediaControlCapabilityManifestIssuer(
        other_key,
        protocol_version="AQSS-1",
    ).issue(manifest=manifest, nonce="media-manifest-7")
    with pytest.raises(ValueError, match="untrusted manifest issuer"):
        verifier.verify(untrusted, now_monotonic=100.25)
    wrong_protocol = MediaControlCapabilityManifestIssuer(
        key,
        protocol_version="AQSS-2",
    ).issue(manifest=manifest, nonce="media-manifest-7")
    with pytest.raises(ValueError, match="protocol mismatch"):
        verifier.verify(wrong_protocol, now_monotonic=100.25)
    wrong_clock_manifest = replace(
        manifest,
        clock_domain_id="process:other-domain",
    )
    wrong_clock = MediaControlCapabilityManifestIssuer(
        key,
        protocol_version="AQSS-1",
    ).issue(manifest=wrong_clock_manifest, nonce="media-manifest-7")
    with pytest.raises(ValueError, match="clock domain mismatch"):
        verifier.verify(wrong_clock, now_monotonic=100.25)
    with pytest.raises(ValueError, match="not yet valid"):
        verifier.verify(signed, now_monotonic=99.9)
    with pytest.raises(ValueError, match="is expired"):
        verifier.verify(signed, now_monotonic=100.5)


def test_media_control_operation_taxonomy_is_closed_and_excludes_pitch():
    assert tuple(member.value for member in MediaControlOperation) == (
        "SET_CAPTIONS_ENABLED",
        "SET_EQ_PRESET",
        "SET_EQ_BANDS",
        "SET_VOLUME",
    )
    assert all("PITCH" not in member.value for member in MediaControlOperation)


def test_media_control_request_binds_caption_operation_to_manifest_scope():
    parameters = {"enabled": True}
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_CAPTIONS_ENABLED,
        parameters=parameters,
        capability_manifest_digest="a" * 64,
    )
    parameters["enabled"] = False
    assert request.device_id == "living-room-tv"
    assert request.playback_session_id == "session-7"
    assert request.content_generation == 7
    assert request.operation is MediaControlOperation.SET_CAPTIONS_ENABLED
    assert dict(request.parameters) == {"enabled": True}
    assert request.capability_manifest_digest == "a" * 64
    with pytest.raises(TypeError):
        request.parameters["enabled"] = False



def test_media_control_request_canonical_bytes_bind_scope_operation_and_parameters():
    import json
    from hashlib import sha256

    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_CAPTIONS_ENABLED,
        parameters={"enabled": True},
        capability_manifest_digest="a" * 64,
    )
    expected = json.dumps(
        {
            "device_id": "living-room-tv",
            "playback_session_id": "session-7",
            "content_generation": 7,
            "operation": "SET_CAPTIONS_ENABLED",
            "parameters": {"enabled": True},
            "capability_manifest_digest": "a" * 64,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert request.canonical_bytes == expected
    assert request.digest == sha256(expected).hexdigest()


def test_media_control_request_canonical_bytes_bind_expected_pre_state_digest():
    import json
    from hashlib import sha256

    request=MediaControlRequest(device_id="living-room-tv",playback_session_id="session-undo",content_generation=8,operation=MediaControlOperation.SET_VOLUME,parameters={"volume_percent":21},capability_manifest_digest="a" * 64,expected_pre_state_digest="b" * 64)
    expected=json.dumps({"device_id":"living-room-tv","playback_session_id":"session-undo","content_generation":8,"operation":"SET_VOLUME","parameters":{"volume_percent":21},"capability_manifest_digest":"a" * 64,"expected_pre_state_digest":"b" * 64},sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    assert request.expected_pre_state_digest=="b" * 64
    assert request.canonical_bytes==expected
    assert request.digest==sha256(expected).hexdigest()


@pytest.mark.parametrize(("field", "value"), (
    ("device_id", ""),
    ("device_id", "   "),
    ("device_id", None),
    ("playback_session_id", ""),
    ("playback_session_id", None),
    ("content_generation", -1),
    ("content_generation", True),
    ("content_generation", 7.0),
    ("operation", "SET_CAPTIONS_ENABLED"),
    ("parameters", None),
    ("parameters", {}),
    ("parameters", {"enabled": 1}),
    ("parameters", {"enabled": "true"}),
    ("parameters", {"enabled": True, "extra": False}),
    ("capability_manifest_digest", ""),
    ("capability_manifest_digest", "a" * 63),
    ("capability_manifest_digest", "A" * 64),
    ("capability_manifest_digest", "g" * 64),
    ("capability_manifest_digest", None),
    ("expected_pre_state_digest", ""),
    ("expected_pre_state_digest", "b" * 63),
    ("expected_pre_state_digest", "B" * 64),
    ("expected_pre_state_digest", "g" * 64),
    ("expected_pre_state_digest", 7),
))
def test_media_control_request_rejects_malformed_caption_request(field, value):
    values = {
        "device_id": "living-room-tv",
        "playback_session_id": "session-7",
        "content_generation": 7,
        "operation": MediaControlOperation.SET_CAPTIONS_ENABLED,
        "parameters": {"enabled": True},
        "capability_manifest_digest": "a" * 64,
    }
    values[field] = value
    with pytest.raises(ValueError):
        MediaControlRequest(**values)


def test_eq_preset_taxonomy_is_closed_and_excludes_pitch():
    assert tuple(member.value for member in EqPreset) == (
        "DIALOGUE",
        "MUSIC",
        "NIGHT",
        "FLAT",
    )
    assert all("PITCH" not in member.value for member in EqPreset)



def test_media_control_request_accepts_typed_eq_preset_and_normalizes_value():
    import json

    parameters = {"preset": EqPreset.DIALOGUE}
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_EQ_PRESET,
        parameters=parameters,
        capability_manifest_digest="a" * 64,
    )
    parameters["preset"] = EqPreset.MUSIC
    assert dict(request.parameters) == {"preset": "DIALOGUE"}
    assert json.loads(request.canonical_bytes)["parameters"] == {
        "preset": "DIALOGUE",
    }


@pytest.mark.parametrize("parameters", (
    {},
    {"preset": None},
    {"preset": "DIALOGUE"},
    {"preset": 1},
    {"preset": MediaControlOperation.SET_EQ_PRESET},
    {"preset": EqPreset.DIALOGUE, "extra": True},
))
def test_media_control_request_rejects_malformed_eq_preset_parameters(parameters):
    with pytest.raises(ValueError, match="invalid EQ preset parameters"):
        MediaControlRequest(
            device_id="living-room-tv",
            playback_session_id="session-7",
            content_generation=7,
            operation=MediaControlOperation.SET_EQ_PRESET,
            parameters=parameters,
            capability_manifest_digest="a" * 64,
        )


def test_eq_band_gain_is_typed_bounded_and_immutable():
    from dataclasses import FrozenInstanceError

    band = EqBandGain(frequency_hz=1000, gain_db=3)
    assert band.frequency_hz == 1000.0
    assert band.gain_db == 3.0
    with pytest.raises(FrozenInstanceError):
        band.gain_db = 4.0


@pytest.mark.parametrize(("field", "value"), (
    ("frequency_hz", True),
    ("frequency_hz", "1000"),
    ("frequency_hz", None),
    ("frequency_hz", float("nan")),
    ("frequency_hz", float("inf")),
    ("frequency_hz", 19.999),
    ("frequency_hz", 20000.001),
    ("gain_db", True),
    ("gain_db", "3"),
    ("gain_db", None),
    ("gain_db", float("nan")),
    ("gain_db", float("inf")),
    ("gain_db", -12.001),
    ("gain_db", 12.001),
))
def test_eq_band_gain_rejects_invalid_values(field, value):
    values = {"frequency_hz": 1000.0, "gain_db": 3.0}
    values[field] = value
    with pytest.raises(ValueError):
        EqBandGain(**values)


def test_media_control_request_accepts_ordered_typed_eq_bands():
    import json

    bands = (
        EqBandGain(frequency_hz=100, gain_db=-1.5),
        EqBandGain(frequency_hz=1000, gain_db=3.0),
        EqBandGain(frequency_hz=8000, gain_db=-2.0),
    )
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_EQ_BANDS,
        parameters={"bands": bands},
        capability_manifest_digest="a" * 64,
    )
    assert request.parameters["bands"] == bands
    assert json.loads(request.canonical_bytes)["parameters"] == {
        "bands": [
            {"frequency_hz": 100.0, "gain_db": -1.5},
            {"frequency_hz": 1000.0, "gain_db": 3.0},
            {"frequency_hz": 8000.0, "gain_db": -2.0},
        ],
    }


@pytest.mark.parametrize("parameters", (
    {},
    {"bands": None},
    {"bands": []},
    {"bands": ()},
    {"bands": ({"frequency_hz": 1000.0, "gain_db": 3.0},)},
    {"bands": (EqBandGain(1000, 3),), "extra": True},
    {"bands": tuple(EqBandGain(100 + index, 0) for index in range(11))},
    {"bands": (EqBandGain(100, 0), EqBandGain(100, 1))},
    {"bands": (EqBandGain(1000, 0), EqBandGain(100, 1))},
))
def test_media_control_request_rejects_malformed_eq_band_parameters(parameters):
    with pytest.raises(ValueError, match="invalid EQ band parameters"):
        MediaControlRequest(
            device_id="living-room-tv",
            playback_session_id="session-7",
            content_generation=7,
            operation=MediaControlOperation.SET_EQ_BANDS,
            parameters=parameters,
            capability_manifest_digest="a" * 64,
        )


def test_media_control_request_accepts_integer_volume_percent():
    import json

    parameters = {"volume_percent": 42}
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_VOLUME,
        parameters=parameters,
        capability_manifest_digest="a" * 64,
    )
    parameters["volume_percent"] = 99
    assert dict(request.parameters) == {"volume_percent": 42}
    assert json.loads(request.canonical_bytes)["parameters"] == {
        "volume_percent": 42,
    }


@pytest.mark.parametrize("volume_percent", (0, 100))
def test_media_control_request_accepts_volume_percent_boundaries(volume_percent):
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_VOLUME,
        parameters={"volume_percent": volume_percent},
        capability_manifest_digest="a" * 64,
    )
    assert dict(request.parameters) == {"volume_percent": volume_percent}


@pytest.mark.parametrize("parameters", (
    {},
    {"volume_percent": None},
    {"volume_percent": True},
    {"volume_percent": 42.0},
    {"volume_percent": "42"},
    {"volume_percent": -1},
    {"volume_percent": 101},
    {"volume_percent": 42, "extra": True},
))
def test_media_control_request_rejects_malformed_volume_parameters(parameters):
    with pytest.raises(ValueError, match="invalid volume parameters"):
        MediaControlRequest(
            device_id="living-room-tv",
            playback_session_id="session-7",
            content_generation=7,
            operation=MediaControlOperation.SET_VOLUME,
            parameters=parameters,
            capability_manifest_digest="a" * 64,
        )


def test_media_control_capability_decision_taxonomy_is_closed():
    assert tuple(member.value for member in MediaControlCapabilityDecision) == (
        "ALLOW",
        "DEVICE_MISMATCH",
        "PLAYBACK_SESSION_MISMATCH",
        "CONTENT_GENERATION_MISMATCH",
        "MANIFEST_DIGEST_MISMATCH",
        "CAPABILITY_DENIED",
    )


def test_media_control_capability_gate_allows_bound_caption_request():
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.NONE,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=130.0,
        clock_domain_id="runtime-monotonic",
    )
    request = MediaControlRequest(
        device_id="living-room-tv",
        playback_session_id="session-7",
        content_generation=7,
        operation=MediaControlOperation.SET_CAPTIONS_ENABLED,
        parameters={"enabled": True},
        capability_manifest_digest=manifest.digest,
    )
    assert (
        MediaControlCapabilityGate.evaluate(request, manifest)
        is MediaControlCapabilityDecision.ALLOW
    )


@pytest.mark.parametrize(("field", "value", "expected"), (
    ("device_id", "bedroom-tv", MediaControlCapabilityDecision.DEVICE_MISMATCH),
    (
        "playback_session_id",
        "session-8",
        MediaControlCapabilityDecision.PLAYBACK_SESSION_MISMATCH,
    ),
    (
        "content_generation",
        8,
        MediaControlCapabilityDecision.CONTENT_GENERATION_MISMATCH,
    ),
    (
        "capability_manifest_digest",
        "b" * 64,
        MediaControlCapabilityDecision.MANIFEST_DIGEST_MISMATCH,
    ),
))
def test_media_control_capability_gate_rejects_scope_and_digest_mismatch(
    field,
    value,
    expected,
):
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=CaptionCapability.NATIVE_TRACK,
        eq_capability=EqCapability.NONE,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=130.0,
        clock_domain_id="runtime-monotonic",
    )
    values = {
        "device_id": manifest.device_id,
        "playback_session_id": manifest.playback_session_id,
        "content_generation": manifest.content_generation,
        "operation": MediaControlOperation.SET_CAPTIONS_ENABLED,
        "parameters": {"enabled": True},
        "capability_manifest_digest": manifest.digest,
    }
    values[field] = value
    request = MediaControlRequest(**values)
    assert MediaControlCapabilityGate.evaluate(request, manifest) is expected


@pytest.mark.parametrize(("operation", "parameters", "caption_capability", "eq_capability", "expected"), (
    (MediaControlOperation.SET_CAPTIONS_ENABLED, {"enabled": True}, CaptionCapability.NATIVE_TRACK, EqCapability.NONE, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_CAPTIONS_ENABLED, {"enabled": True}, CaptionCapability.DEVICE_MODE, EqCapability.NONE, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_CAPTIONS_ENABLED, {"enabled": True}, CaptionCapability.PHONE_TRANSCRIPT, EqCapability.NONE, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_CAPTIONS_ENABLED, {"enabled": True}, CaptionCapability.NONE, EqCapability.BANDS, MediaControlCapabilityDecision.CAPABILITY_DENIED),
    (MediaControlOperation.SET_EQ_PRESET, {"preset": EqPreset.DIALOGUE}, CaptionCapability.NONE, EqCapability.SEMANTIC_PRESETS, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_EQ_PRESET, {"preset": EqPreset.DIALOGUE}, CaptionCapability.NONE, EqCapability.BANDS, MediaControlCapabilityDecision.CAPABILITY_DENIED),
    (MediaControlOperation.SET_EQ_BANDS, {"bands": (EqBandGain(1000, 3),)}, CaptionCapability.NONE, EqCapability.BANDS, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_EQ_BANDS, {"bands": (EqBandGain(1000, 3),)}, CaptionCapability.NONE, EqCapability.SEMANTIC_PRESETS, MediaControlCapabilityDecision.CAPABILITY_DENIED),
    (MediaControlOperation.SET_VOLUME, {"volume_percent": 42}, CaptionCapability.NONE, EqCapability.BANDS, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_VOLUME, {"volume_percent": 42}, CaptionCapability.NONE, EqCapability.SEMANTIC_PRESETS, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_VOLUME, {"volume_percent": 42}, CaptionCapability.NONE, EqCapability.VOLUME_ONLY, MediaControlCapabilityDecision.ALLOW),
    (MediaControlOperation.SET_VOLUME, {"volume_percent": 42}, CaptionCapability.NONE, EqCapability.NONE, MediaControlCapabilityDecision.CAPABILITY_DENIED),
))
def test_media_control_capability_gate_enforces_operation_capability_matrix(
    operation,
    parameters,
    caption_capability,
    eq_capability,
    expected,
):
    manifest = MediaControlCapabilityManifest(
        device_id="living-room-tv",
        adapter_id="matter-tv",
        playback_session_id="session-7",
        content_generation=7,
        caption_capability=caption_capability,
        eq_capability=eq_capability,
        verification_strength=VerificationStrength.OBSERVED,
        issued_monotonic=100.0,
        expires_monotonic=130.0,
        clock_domain_id="runtime-monotonic",
    )
    request = MediaControlRequest(
        device_id=manifest.device_id,
        playback_session_id=manifest.playback_session_id,
        content_generation=manifest.content_generation,
        operation=operation,
        parameters=parameters,
        capability_manifest_digest=manifest.digest,
    )
    assert MediaControlCapabilityGate.evaluate(request, manifest) is expected
