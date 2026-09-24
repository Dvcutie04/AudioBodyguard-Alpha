from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .media_control_prior_state import MediaControlPriorState
from .media_control_verified_state import VerifiedMediaControlState


@dataclass(frozen=True, slots=True, init=False)
class MediaControlUndoCandidate:
    device_id: str
    operation: str
    parameters: Mapping[str, object]
    expected_current_state_digest: str
    prior_state_digest: str
    source_intent_id: str
    source_transaction_id: str
    authorization_digest: str
    capability_digest: str
    prior_state_epoch: int
    verified_state_epoch: int

    def __init__(self) -> None:
        raise TypeError("undo candidate requires a verified physical change")

    @classmethod
    def from_verified_change(cls, prior: MediaControlPriorState, verified: VerifiedMediaControlState) -> "MediaControlUndoCandidate":
        if type(prior) is not MediaControlPriorState or type(verified) is not VerifiedMediaControlState:
            raise ValueError("invalid undo candidate input")
        prior_lineage=(prior.device_id,prior.intent_id,prior.transaction_id,prior.authorization_digest,prior.capability_digest)
        verified_lineage=(verified.device_id,verified.intent_id,verified.transaction_id,verified.authorization_digest,verified.capability_digest)
        if prior_lineage != verified_lineage:
            raise ValueError("undo candidate lineage mismatch")
        if prior.expected_post_state_digest != verified.observed_state_digest:
            raise ValueError("undo candidate post-state mismatch")
        if verified.observed_state_epoch <= prior.prior_state_epoch or verified.observed_at < prior.observed_at:
            raise ValueError("undo candidate observation order invalid")
        if prior.operation == "set_volume":
            operation="set_volume"
            parameters=MappingProxyType({"volume_percent":prior.volume_percent})
        elif prior.operation == "set_captions_enabled" and type(prior.captions_enabled) is bool:
            operation="set_captions_enabled"
            parameters=MappingProxyType({"enabled":prior.captions_enabled})
        elif prior.operation in ("set_eq_bands","set_eq_preset") and prior.eq_preset is not None:
            operation="set_eq_preset"
            parameters=MappingProxyType({"preset":prior.eq_preset.value})
        elif prior.operation in ("set_eq_bands","set_eq_preset") and prior.eq_bands is not None:
            operation="set_eq_bands"
            bands=tuple(MappingProxyType({"frequency_hz":band.frequency_hz,"gain_db":band.gain_db}) for band in prior.eq_bands)
            parameters=MappingProxyType({"bands":bands})
        else:
            raise ValueError("unsupported undo operation")
        values={"device_id":prior.device_id,"operation":operation,"parameters":parameters,"expected_current_state_digest":verified.observed_state_digest,"prior_state_digest":prior.prior_state_digest,"source_intent_id":prior.intent_id,"source_transaction_id":prior.transaction_id,"authorization_digest":prior.authorization_digest,"capability_digest":prior.capability_digest,"prior_state_epoch":prior.prior_state_epoch,"verified_state_epoch":verified.observed_state_epoch}
        result=object.__new__(cls)
        for name,value in values.items():
            object.__setattr__(result,name,value)
        return result
