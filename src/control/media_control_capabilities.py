import json
from dataclasses import dataclass
from enum import Enum, unique
from hashlib import sha256
from math import isfinite
from types import MappingProxyType
from typing import Mapping


@unique
class CaptionCapability(Enum):
    NATIVE_TRACK = "NATIVE_TRACK"
    DEVICE_MODE = "DEVICE_MODE"
    PHONE_TRANSCRIPT = "PHONE_TRANSCRIPT"
    NONE = "NONE"


@unique
class EqCapability(Enum):
    BANDS = "BANDS"
    SEMANTIC_PRESETS = "SEMANTIC_PRESETS"
    VOLUME_ONLY = "VOLUME_ONLY"
    NONE = "NONE"


@unique
class EqPreset(Enum):
    DIALOGUE = "DIALOGUE"
    MUSIC = "MUSIC"
    NIGHT = "NIGHT"
    FLAT = "FLAT"


@dataclass(frozen=True, slots=True)
class EqBandGain:
    frequency_hz: float
    gain_db: float

    def __post_init__(self) -> None:
        for field_name in ("frequency_hz", "gain_db"):
            value = getattr(self, field_name)
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError(f"invalid {field_name}")
        if not 20.0 <= self.frequency_hz <= 20_000.0:
            raise ValueError("frequency_hz is out of range")
        if not -12.0 <= self.gain_db <= 12.0:
            raise ValueError("gain_db is out of range")
        object.__setattr__(self, "frequency_hz", float(self.frequency_hz))
        object.__setattr__(self, "gain_db", float(self.gain_db))


@unique
class VerificationStrength(Enum):
    OBSERVED = "OBSERVED"
    ACK_ONLY = "ACK_ONLY"
    NONE = "NONE"


@unique
class MediaControlOperation(Enum):
    SET_CAPTIONS_ENABLED = "SET_CAPTIONS_ENABLED"
    SET_EQ_PRESET = "SET_EQ_PRESET"
    SET_EQ_BANDS = "SET_EQ_BANDS"
    SET_VOLUME = "SET_VOLUME"


@unique
class MediaControlCapabilityDecision(Enum):
    ALLOW = "ALLOW"
    DEVICE_MISMATCH = "DEVICE_MISMATCH"
    PLAYBACK_SESSION_MISMATCH = "PLAYBACK_SESSION_MISMATCH"
    CONTENT_GENERATION_MISMATCH = "CONTENT_GENERATION_MISMATCH"
    MANIFEST_DIGEST_MISMATCH = "MANIFEST_DIGEST_MISMATCH"
    CAPABILITY_DENIED = "CAPABILITY_DENIED"


@dataclass(frozen=True, slots=True)
class MediaControlCapabilityManifest:
    device_id: str
    adapter_id: str
    playback_session_id: str
    content_generation: int
    caption_capability: CaptionCapability
    eq_capability: EqCapability
    verification_strength: VerificationStrength
    issued_monotonic: float
    expires_monotonic: float
    clock_domain_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "device_id",
            "adapter_id",
            "playback_session_id",
            "clock_domain_id",
        ):
            value = getattr(self, field_name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"invalid {field_name}")
        for field_name in ("issued_monotonic", "expires_monotonic"):
            value = getattr(self, field_name)
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"invalid {field_name}")
        if self.expires_monotonic <= self.issued_monotonic:
            raise ValueError("invalid monotonic validity interval")
        if type(self.content_generation) is not int or self.content_generation < 0:
            raise ValueError("invalid content_generation")
        if type(self.caption_capability) is not CaptionCapability:
            raise ValueError("invalid caption_capability")
        if type(self.eq_capability) is not EqCapability:
            raise ValueError("invalid eq_capability")
        if type(self.verification_strength) is not VerificationStrength:
            raise ValueError("invalid verification_strength")

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "device_id": self.device_id,
            "adapter_id": self.adapter_id,
            "playback_session_id": self.playback_session_id,
            "content_generation": self.content_generation,
            "caption_capability": self.caption_capability.value,
            "eq_capability": self.eq_capability.value,
            "verification_strength": self.verification_strength.value,
            "issued_monotonic": self.issued_monotonic,
            "expires_monotonic": self.expires_monotonic,
            "clock_domain_id": self.clock_domain_id,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class SignedMediaControlCapabilityManifest:
    manifest: MediaControlCapabilityManifest
    protocol_version: str
    issuer_id: str
    nonce: str
    signature: str = ""

    def __post_init__(self) -> None:
        if type(self.manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid manifest")
        for field_name in ("protocol_version", "issuer_id", "nonce"):
            value = getattr(self, field_name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"invalid {field_name}")
        if type(self.signature) is not str:
            raise ValueError("invalid signature")

    @property
    def canonical_bytes(self) -> bytes:
        payload = {
            "manifest_digest": self.manifest.digest,
            "protocol_version": self.protocol_version,
            "issuer_id": self.issuer_id,
            "nonce": self.nonce,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")


class MediaControlCapabilityManifestIssuer:
    __slots__ = ("_signer", "_protocol_version", "_issuer_id")

    def __init__(self, signer: object, *, protocol_version: str) -> None:
        issuer_id = getattr(signer, "key_id", None)
        sign = getattr(signer, "sign", None)
        if type(issuer_id) is not str or not issuer_id.strip():
            raise ValueError("invalid signer key_id")
        if not callable(sign):
            raise ValueError("invalid signer")
        if type(protocol_version) is not str or not protocol_version.strip():
            raise ValueError("invalid protocol_version")
        self._signer = signer
        self._protocol_version = protocol_version
        self._issuer_id = issuer_id

    def issue(
        self,
        *,
        manifest: MediaControlCapabilityManifest,
        nonce: str,
    ) -> SignedMediaControlCapabilityManifest:
        unsigned = SignedMediaControlCapabilityManifest(
            manifest=manifest,
            protocol_version=self._protocol_version,
            issuer_id=self._issuer_id,
            nonce=nonce,
            signature="",
        )
        signature = self._signer.sign(unsigned.canonical_bytes)
        if type(signature) is not str or not signature:
            raise ValueError("signer returned invalid signature")
        return SignedMediaControlCapabilityManifest(
            manifest=manifest,
            protocol_version=self._protocol_version,
            issuer_id=self._issuer_id,
            nonce=nonce,
            signature=signature,
        )


class MediaControlCapabilityManifestVerifier:
    __slots__ = (
        "_verifier",
        "_protocol_version",
        "_clock_domain_id",
        "_issuer_id",
    )

    def __init__(
        self,
        verifier: object,
        *,
        protocol_version: str,
        clock_domain_id: str,
    ) -> None:
        issuer_id = getattr(verifier, "key_id", None)
        verify = getattr(verifier, "verify", None)
        if type(issuer_id) is not str or not issuer_id.strip():
            raise ValueError("invalid verifier key_id")
        if not callable(verify):
            raise ValueError("invalid verifier")
        for field_name, value in (
            ("protocol_version", protocol_version),
            ("clock_domain_id", clock_domain_id),
        ):
            if type(value) is not str or not value.strip():
                raise ValueError(f"invalid {field_name}")
        self._verifier = verifier
        self._protocol_version = protocol_version
        self._clock_domain_id = clock_domain_id
        self._issuer_id = issuer_id

    def verify(
        self,
        signed: SignedMediaControlCapabilityManifest,
        *,
        now_monotonic: float,
    ) -> MediaControlCapabilityManifest:
        if type(signed) is not SignedMediaControlCapabilityManifest:
            raise ValueError("invalid signed manifest")
        if (
            type(now_monotonic) not in (int, float)
            or not isfinite(now_monotonic)
            or now_monotonic < 0
        ):
            raise ValueError("invalid now_monotonic")
        if signed.issuer_id != self._issuer_id:
            raise ValueError("untrusted manifest issuer")
        if self._verifier.verify(signed.canonical_bytes, signed.signature) is not True:
            raise ValueError("media capability manifest signature is invalid")
        if signed.protocol_version != self._protocol_version:
            raise ValueError("media capability manifest protocol mismatch")
        manifest = signed.manifest
        if manifest.clock_domain_id != self._clock_domain_id:
            raise ValueError("media capability manifest clock domain mismatch")
        if now_monotonic < manifest.issued_monotonic:
            raise ValueError("media capability manifest is not yet valid")
        if now_monotonic >= manifest.expires_monotonic:
            raise ValueError("media capability manifest is expired")
        return manifest


@dataclass(frozen=True, slots=True)
class MediaControlRequest:
    device_id: str
    playback_session_id: str
    content_generation: int
    operation: MediaControlOperation
    parameters: Mapping[str, object]
    capability_manifest_digest: str
    expected_pre_state_digest: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("device_id", "playback_session_id"):
            value = getattr(self, field_name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"invalid {field_name}")
        if type(self.content_generation) is not int or self.content_generation < 0:
            raise ValueError("invalid content_generation")
        if type(self.operation) is not MediaControlOperation:
            raise ValueError("invalid operation")
        if type(self.parameters) is not dict:
            raise ValueError("invalid parameters")
        if (
            type(self.capability_manifest_digest) is not str
            or len(self.capability_manifest_digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.capability_manifest_digest
            )
        ):
            raise ValueError("invalid capability_manifest_digest")
        if self.expected_pre_state_digest is not None and (type(self.expected_pre_state_digest) is not str or len(self.expected_pre_state_digest) != 64 or any(character not in "0123456789abcdef" for character in self.expected_pre_state_digest)):
            raise ValueError("invalid expected_pre_state_digest")
        if self.operation is MediaControlOperation.SET_CAPTIONS_ENABLED:
            if (
                set(self.parameters) != {"enabled"}
                or type(self.parameters.get("enabled")) is not bool
            ):
                raise ValueError("invalid caption parameters")
            normalized_parameters = dict(self.parameters)
        elif self.operation is MediaControlOperation.SET_EQ_PRESET:
            if (
                set(self.parameters) != {"preset"}
                or type(self.parameters.get("preset")) is not EqPreset
            ):
                raise ValueError("invalid EQ preset parameters")
            normalized_parameters = {
                "preset": self.parameters["preset"].value,
            }
        elif self.operation is MediaControlOperation.SET_EQ_BANDS:
            bands = self.parameters.get("bands")
            if (
                set(self.parameters) != {"bands"}
                or type(bands) is not tuple
                or not 1 <= len(bands) <= 10
                or any(type(band) is not EqBandGain for band in bands)
                or any(
                    left.frequency_hz >= right.frequency_hz
                    for left, right in zip(bands, bands[1:])
                )
            ):
                raise ValueError("invalid EQ band parameters")
            normalized_parameters = {"bands": bands}
        elif self.operation is MediaControlOperation.SET_VOLUME:
            volume_percent = self.parameters.get("volume_percent")
            if (
                set(self.parameters) != {"volume_percent"}
                or type(volume_percent) is not int
                or not 0 <= volume_percent <= 100
            ):
                raise ValueError("invalid volume parameters")
            normalized_parameters = {"volume_percent": volume_percent}
        else:
            raise ValueError("unsupported media control operation")
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(normalized_parameters),
        )

    @property
    def canonical_bytes(self) -> bytes:
        parameters = dict(self.parameters)
        if self.operation is MediaControlOperation.SET_EQ_BANDS:
            parameters = {
                "bands": [
                    {
                        "frequency_hz": band.frequency_hz,
                        "gain_db": band.gain_db,
                    }
                    for band in self.parameters["bands"]
                ],
            }
        payload = {
            "device_id": self.device_id,
            "playback_session_id": self.playback_session_id,
            "content_generation": self.content_generation,
            "operation": self.operation.value,
            "parameters": parameters,
            "capability_manifest_digest": self.capability_manifest_digest,
        }
        if self.expected_pre_state_digest is not None:
            payload["expected_pre_state_digest"]=self.expected_pre_state_digest
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


class MediaControlCapabilityGate:
    @staticmethod
    def evaluate(
        request: MediaControlRequest,
        manifest: MediaControlCapabilityManifest,
    ) -> MediaControlCapabilityDecision:
        if type(request) is not MediaControlRequest:
            raise ValueError("invalid media control request")
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if request.device_id != manifest.device_id:
            return MediaControlCapabilityDecision.DEVICE_MISMATCH
        if request.playback_session_id != manifest.playback_session_id:
            return MediaControlCapabilityDecision.PLAYBACK_SESSION_MISMATCH
        if request.content_generation != manifest.content_generation:
            return MediaControlCapabilityDecision.CONTENT_GENERATION_MISMATCH
        if request.capability_manifest_digest != manifest.digest:
            return MediaControlCapabilityDecision.MANIFEST_DIGEST_MISMATCH
        if request.operation is MediaControlOperation.SET_CAPTIONS_ENABLED:
            allowed = manifest.caption_capability is not CaptionCapability.NONE
        elif request.operation is MediaControlOperation.SET_EQ_PRESET:
            allowed = manifest.eq_capability is EqCapability.SEMANTIC_PRESETS
        elif request.operation is MediaControlOperation.SET_EQ_BANDS:
            allowed = manifest.eq_capability is EqCapability.BANDS
        elif request.operation is MediaControlOperation.SET_VOLUME:
            allowed = manifest.eq_capability is not EqCapability.NONE
        else:
            allowed = False
        if not allowed:
            return MediaControlCapabilityDecision.CAPABILITY_DENIED
        return MediaControlCapabilityDecision.ALLOW
