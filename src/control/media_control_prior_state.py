from dataclasses import dataclass
from math import isfinite

from src.control.media_control_capabilities import EqBandGain, EqPreset
from src.device_fabric.contracts import AuthorizedActionIntent, DeviceState, PhysicalSnapshot


@dataclass(frozen=True, slots=True, init=False)
class MediaControlPriorState:
    device_id: str
    volume_percent: int
    captions_enabled: bool | None
    eq_preset: EqPreset | None
    eq_bands: tuple[EqBandGain, ...] | None
    prior_state_digest: str
    prior_state_evidence_digest: str
    prior_state_epoch: int
    observed_at: float
    intent_id: str
    transaction_id: str
    authorization_digest: str
    capability_digest: str
    operation: str
    expected_post_state_digest: str

    def __init__(self) -> None:
        raise TypeError("prior state requires an authorized snapshot capture")

    @classmethod
    def from_authorized_snapshot(cls, snapshot: PhysicalSnapshot, authorized: AuthorizedActionIntent) -> "MediaControlPriorState":
        if type(snapshot) is not PhysicalSnapshot or type(authorized) is not AuthorizedActionIntent:
            raise ValueError("invalid prior capture input")
        lineage=(snapshot.device_id,snapshot.evidence_digest,authorized.device_id,authorized.intent_id,authorized.transaction_id,authorized.authorization_digest,authorized.capability_digest,authorized.operation)
        if any(type(value) is not str or not value.strip() for value in lineage):
            raise ValueError("incomplete prior capture lineage")
        if authorized.operation not in {"set_volume","set_captions_enabled","set_eq_preset","set_eq_bands"}:
            raise ValueError("unsupported prior capture operation")
        if snapshot.device_id != authorized.device_id:
            raise ValueError("prior capture device mismatch")
        if any(type(state) is not DeviceState for state in (snapshot.state,authorized.expected_pre_state,authorized.target_state)):
            raise ValueError("invalid prior capture device state")
        if type(snapshot.epoch) is not int or snapshot.epoch < 0:
            raise ValueError("invalid prior capture epoch")
        if type(snapshot.observed_at) not in (int,float) or not isfinite(snapshot.observed_at) or snapshot.observed_at < 0:
            raise ValueError("invalid prior capture observation time")
        volume=snapshot.state.volume
        if type(volume) is not int or not 0 <= volume <= 100:
            raise ValueError("invalid prior capture volume")
        custom=snapshot.state.custom_state
        if type(custom) is not dict:
            raise ValueError("invalid prior capture custom state")
        captions=None
        if "captions_enabled" in custom:
            captions=custom["captions_enabled"]
            if type(captions) is not bool:
                raise ValueError("invalid prior capture captions")
        has_preset="eq_preset" in custom
        has_bands="eq_bands" in custom
        if has_preset and has_bands:
            raise ValueError("prior capture combines EQ preset and bands")
        preset=None
        if has_preset:
            raw_preset=custom["eq_preset"]
            if type(raw_preset) is not str:
                raise ValueError("invalid prior capture EQ preset")
            try:
                preset=EqPreset(raw_preset)
            except ValueError as error:
                raise ValueError("invalid prior capture EQ preset") from error
        bands=None
        if has_bands:
            raw_bands=custom["eq_bands"]
            if type(raw_bands) is not list or not 1 <= len(raw_bands) <= 10:
                raise ValueError("invalid prior capture EQ bands")
            parsed=[]
            for raw_band in raw_bands:
                if type(raw_band) is not dict or set(raw_band) != {"frequency_hz","gain_db"}:
                    raise ValueError("invalid prior capture EQ band")
                parsed.append(EqBandGain(raw_band["frequency_hz"],raw_band["gain_db"]))
            bands=tuple(parsed)
            if any(left.frequency_hz >= right.frequency_hz for left,right in zip(bands,bands[1:])):
                raise ValueError("prior capture EQ bands must increase")
        digest=snapshot.state.state_digest
        if digest != authorized.expected_pre_state.state_digest:
            raise ValueError("prior capture pre-state mismatch")
        if authorized.operation == "set_volume":
            target_volume=authorized.target_state.volume
            if type(target_volume) is not int or not 0 <= target_volume <= 100:
                raise ValueError("invalid prior capture target volume")
            expected_target=DeviceState(power=snapshot.state.power,volume=target_volume,muted=snapshot.state.muted,input_source=snapshot.state.input_source,channel=snapshot.state.channel,custom_state=dict(custom),playback_position_seconds=snapshot.state.playback_position_seconds)
            if authorized.target_state.state_digest != expected_target.state_digest:
                raise ValueError("prior capture target does not match operation")
        elif authorized.operation == "set_captions_enabled":
            target_custom=authorized.target_state.custom_state
            if type(target_custom) is not dict or "captions_enabled" not in target_custom or type(target_custom["captions_enabled"]) is not bool:
                raise ValueError("invalid prior capture target captions")
            expected_custom=dict(custom)
            expected_custom["captions_enabled"]=target_custom["captions_enabled"]
            expected_target=DeviceState(power=snapshot.state.power,volume=snapshot.state.volume,muted=snapshot.state.muted,input_source=snapshot.state.input_source,channel=snapshot.state.channel,custom_state=expected_custom,playback_position_seconds=snapshot.state.playback_position_seconds)
            if authorized.target_state.state_digest != expected_target.state_digest:
                raise ValueError("prior capture target does not match operation")
        elif authorized.operation == "set_eq_preset":
            target_custom=authorized.target_state.custom_state
            if type(target_custom) is not dict or "eq_preset" not in target_custom or type(target_custom["eq_preset"]) is not str:
                raise ValueError("invalid prior capture target EQ preset")
            try:
                target_preset=EqPreset(target_custom["eq_preset"])
            except ValueError as error:
                raise ValueError("invalid prior capture target EQ preset") from error
            expected_custom=dict(custom)
            expected_custom["eq_preset"]=target_preset.value
            expected_custom.pop("eq_bands",None)
            expected_target=DeviceState(power=snapshot.state.power,volume=snapshot.state.volume,muted=snapshot.state.muted,input_source=snapshot.state.input_source,channel=snapshot.state.channel,custom_state=expected_custom,playback_position_seconds=snapshot.state.playback_position_seconds)
            if authorized.target_state.state_digest != expected_target.state_digest:
                raise ValueError("prior capture target does not match operation")
        elif authorized.operation == "set_eq_bands":
            target_custom=authorized.target_state.custom_state
            if type(target_custom) is not dict or "eq_bands" not in target_custom:
                raise ValueError("invalid prior capture target EQ bands")
            target_bands=target_custom["eq_bands"]
            if type(target_bands) is not list or not 1 <= len(target_bands) <= 10:
                raise ValueError("invalid prior capture target EQ bands")
            validated_target_bands=[]
            parsed_target_bands=[]
            for target_band in target_bands:
                if type(target_band) is not dict or set(target_band) != {"frequency_hz","gain_db"}:
                    raise ValueError("invalid prior capture target EQ band")
                parsed_target_bands.append(EqBandGain(target_band["frequency_hz"],target_band["gain_db"]))
                validated_target_bands.append({"frequency_hz":target_band["frequency_hz"],"gain_db":target_band["gain_db"]})
            if any(left.frequency_hz >= right.frequency_hz for left,right in zip(parsed_target_bands,parsed_target_bands[1:])):
                raise ValueError("prior capture target EQ bands must increase")
            expected_custom=dict(custom)
            expected_custom["eq_bands"]=validated_target_bands
            expected_custom.pop("eq_preset",None)
            expected_target=DeviceState(power=snapshot.state.power,volume=snapshot.state.volume,muted=snapshot.state.muted,input_source=snapshot.state.input_source,channel=snapshot.state.channel,custom_state=expected_custom,playback_position_seconds=snapshot.state.playback_position_seconds)
            if authorized.target_state.state_digest != expected_target.state_digest:
                raise ValueError("prior capture target does not match operation")
        values={"device_id":snapshot.device_id,"volume_percent":volume,"captions_enabled":captions,"eq_preset":preset,"eq_bands":bands,"prior_state_digest":digest,"prior_state_evidence_digest":snapshot.evidence_digest,"prior_state_epoch":snapshot.epoch,"observed_at":float(snapshot.observed_at),"intent_id":authorized.intent_id,"transaction_id":authorized.transaction_id,"authorization_digest":authorized.authorization_digest,"capability_digest":authorized.capability_digest,"operation":authorized.operation,"expected_post_state_digest":authorized.target_state.state_digest}
        result=object.__new__(cls)
        for name,value in values.items():
            object.__setattr__(result,name,value)
        return result
