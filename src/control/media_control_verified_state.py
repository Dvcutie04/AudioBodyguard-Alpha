from dataclasses import dataclass
from math import isfinite

from .media_control_capabilities import CaptionCapability, EqBandGain, EqCapability, EqPreset, MediaControlCapabilityManifest
from .media_control_profiles import MediaControlProfileKind, MediaControlSettingsProfile
from src.device_fabric.contracts import DeviceState, PhysicalSnapshot, PhysicalVerificationRecord, VerificationStatus


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value.strip())


@dataclass(frozen=True, slots=True, init=False)
class VerifiedMediaControlState:
    device_id: str
    volume_percent: int
    captions_enabled: bool | None
    eq_preset: EqPreset | None
    eq_bands: tuple[EqBandGain, ...] | None
    observed_state_digest: str
    observed_state_evidence_digest: str
    observed_state_epoch: int
    observed_at: float
    intent_id: str
    receipt_id: str
    authorization_digest: str
    transaction_id: str
    capability_digest: str

    def __init__(self) -> None:
        raise TypeError("verified media state requires physical verification")

    @classmethod
    def from_physical_verification(cls, snapshot: PhysicalSnapshot, verification: PhysicalVerificationRecord) -> "VerifiedMediaControlState":
        if type(snapshot) is not PhysicalSnapshot or type(verification) is not PhysicalVerificationRecord:
            raise ValueError("invalid physical verification input")
        if verification.verification_status is not VerificationStatus.VERIFIED:
            raise ValueError("physical state is not verified")
        lineage=(snapshot.device_id,verification.device_id,verification.intent_id,verification.receipt_id,verification.authorization_digest,verification.transaction_id,verification.capability_digest,verification.expected_state_digest,verification.observed_state_digest,verification.observed_state_evidence_digest,snapshot.evidence_digest)
        if not all(_nonblank(value) for value in lineage):
            raise ValueError("incomplete physical verification lineage")
        if snapshot.device_id != verification.device_id:
            raise ValueError("verified device mismatch")
        if type(snapshot.state) is not DeviceState:
            raise ValueError("invalid observed device state")
        digest=snapshot.state.state_digest
        if digest != verification.observed_state_digest or digest != verification.expected_state_digest:
            raise ValueError("verified state digest mismatch")
        if snapshot.evidence_digest != verification.observed_state_evidence_digest:
            raise ValueError("verified evidence mismatch")
        if type(snapshot.epoch) is not int or snapshot.epoch < 0 or type(verification.observed_state_epoch) is not int or verification.observed_state_epoch != snapshot.epoch:
            raise ValueError("verified observation epoch mismatch")
        if type(verification.world_state_epoch) is not int or verification.world_state_epoch < 0 or verification.world_state_epoch > snapshot.epoch:
            raise ValueError("invalid verified world-state epoch")
        if type(snapshot.observed_at) not in (int,float) or not isfinite(snapshot.observed_at) or snapshot.observed_at < 0:
            raise ValueError("invalid verified observation time")
        state=snapshot.state
        if type(state.volume) is not int or not 0 <= state.volume <= 100:
            raise ValueError("invalid verified volume")
        if type(state.custom_state) is not dict:
            raise ValueError("invalid verified custom state")
        custom=state.custom_state
        if "captions_enabled" in custom:
            captions=custom["captions_enabled"]
            if type(captions) is not bool:
                raise ValueError("invalid verified captions")
        else:
            captions=None
        has_preset="eq_preset" in custom
        has_bands="eq_bands" in custom
        if has_preset and has_bands:
            raise ValueError("verified state combines EQ preset and bands")
        preset=None
        if has_preset:
            raw_preset=custom["eq_preset"]
            if type(raw_preset) is not str:
                raise ValueError("invalid verified EQ preset")
            try:
                preset=EqPreset(raw_preset)
            except ValueError as error:
                raise ValueError("invalid verified EQ preset") from error
        bands=None
        if has_bands:
            raw_bands=custom["eq_bands"]
            if type(raw_bands) is not list or not 1 <= len(raw_bands) <= 10:
                raise ValueError("invalid verified EQ bands")
            parsed=[]
            for raw_band in raw_bands:
                if type(raw_band) is not dict or set(raw_band) != {"frequency_hz","gain_db"}:
                    raise ValueError("invalid verified EQ band")
                parsed.append(EqBandGain(raw_band["frequency_hz"],raw_band["gain_db"]))
            bands=tuple(parsed)
            if any(left.frequency_hz >= right.frequency_hz for left,right in zip(bands,bands[1:])):
                raise ValueError("verified EQ bands must increase")
        result=object.__new__(cls)
        values={"device_id":snapshot.device_id,"volume_percent":state.volume,"captions_enabled":captions,"eq_preset":preset,"eq_bands":bands,"observed_state_digest":digest,"observed_state_evidence_digest":snapshot.evidence_digest,"observed_state_epoch":snapshot.epoch,"observed_at":float(snapshot.observed_at),"intent_id":verification.intent_id,"receipt_id":verification.receipt_id,"authorization_digest":verification.authorization_digest,"transaction_id":verification.transaction_id,"capability_digest":verification.capability_digest}
        for name,value in values.items(): object.__setattr__(result,name,value)
        return result

    def to_user_default_profile(self, manifest: MediaControlCapabilityManifest, *, name: str) -> MediaControlSettingsProfile:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if manifest.device_id != self.device_id:
            raise ValueError("verified state device mismatch")
        volume=self.volume_percent if manifest.eq_capability is not EqCapability.NONE else None
        captions=self.captions_enabled if manifest.caption_capability is not CaptionCapability.NONE else None
        preset=self.eq_preset if manifest.eq_capability is EqCapability.SEMANTIC_PRESETS else None
        bands=self.eq_bands if manifest.eq_capability is EqCapability.BANDS else None
        if all(value is None for value in (volume,captions,preset,bands)):
            raise ValueError("no verified settings supported by capability manifest")
        profile=MediaControlSettingsProfile(device_id=self.device_id,name=name,kind=MediaControlProfileKind.USER_DEFAULT,volume_percent=volume,captions_enabled=captions,eq_preset=preset,eq_bands=bands)
        profile.requests_for(manifest)
        return profile
