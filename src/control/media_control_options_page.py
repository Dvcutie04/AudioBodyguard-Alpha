from .media_control_capabilities import (
    EqBandGain,
    EqPreset,
    MediaControlCapabilityDecision,
    MediaControlCapabilityGate,
    MediaControlCapabilityManifest,
    MediaControlOperation,
    MediaControlRequest,
)
from .media_control_options import (
    DeviceDisplayMetadata,
    MediaControlOptionsMenu,
    MediaControlRecoveryState,
)
from .media_control_verified_state import VerifiedMediaControlState
from .media_control_undo_candidate import MediaControlUndoCandidate
from .media_control_profiles import (
    MediaControlProfileKind,
    MediaControlProfileStore,
    MediaControlSettingsProfile,
)


class MediaControlOptionsPageBuilder:
    __slots__ = ("_store",)

    def __init__(self, store: MediaControlProfileStore) -> None:
        if type(store) is not MediaControlProfileStore:
            raise ValueError("invalid media control profile store")
        self._store = store

    def build_menu(
        self,
        manifest: MediaControlCapabilityManifest,
        *,
        device: DeviceDisplayMetadata,
        user_profile_id: str,
        recommended: MediaControlSettingsProfile,
        verified_state: VerifiedMediaControlState | None = None,
        undo_candidate: MediaControlUndoCandidate | None = None,
    ) -> MediaControlOptionsMenu:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if type(device) is not DeviceDisplayMetadata:
            raise ValueError("invalid device display metadata")
        if type(recommended) is not MediaControlSettingsProfile:
            raise ValueError("invalid recommended profile")
        if recommended.kind is not MediaControlProfileKind.RECOMMENDED:
            raise ValueError("recommended profile must use RECOMMENDED kind")
        if recommended.device_id != manifest.device_id:
            raise ValueError("recommended profile device mismatch")

        recommended.requests_for(manifest)
        can_save_current=False
        if type(verified_state) is VerifiedMediaControlState:
            try:
                verified_state.to_user_default_profile(manifest,name="My Default")
            except ValueError:
                pass
            else:
                can_save_current=True
        can_undo=False
        if type(undo_candidate) is MediaControlUndoCandidate:
            try:
                self.propose_undo(manifest,undo_candidate=undo_candidate)
            except ValueError:
                pass
            else:
                can_undo=True
        personal = self._store.get_my_default(
            user_profile_id,
            manifest.device_id,
        )
        recovery = MediaControlRecoveryState(
            has_recommended_profile=True,
            has_saved_default=personal is not None,
            can_undo=can_undo,
            can_save_current=can_save_current,
        )
        return MediaControlOptionsMenu.for_manifest(
            manifest,
            device=device,
            recovery=recovery,
        )


    def save_verified_current_as_my_default(
        self,
        manifest: MediaControlCapabilityManifest,
        *,
        user_profile_id: str,
        verified_state: VerifiedMediaControlState,
        name: str = "My Default",
    ) -> None:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if type(verified_state) is not VerifiedMediaControlState:
            raise ValueError("verified current settings required")
        profile=verified_state.to_user_default_profile(manifest,name=name)
        self._store.save_my_default(user_profile_id,profile)


    def propose_recommended(
        self,
        manifest: MediaControlCapabilityManifest,
        *,
        recommended: MediaControlSettingsProfile,
    ) -> tuple[MediaControlRequest, ...]:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if type(recommended) is not MediaControlSettingsProfile:
            raise ValueError("invalid recommended profile")
        if recommended.kind is not MediaControlProfileKind.RECOMMENDED:
            raise ValueError("recommended profile must use RECOMMENDED kind")
        if recommended.device_id != manifest.device_id:
            raise ValueError("recommended profile device mismatch")
        return recommended.requests_for(manifest)

    def propose_restore_my_default(
        self,
        manifest: MediaControlCapabilityManifest,
        *,
        user_profile_id: str,
    ) -> tuple[MediaControlRequest, ...]:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        personal = self._store.get_my_default(
            user_profile_id,
            manifest.device_id,
        )
        if personal is None:
            raise ValueError("personal default not found")
        return personal.requests_for(manifest)


    def propose_undo(
        self,
        manifest: MediaControlCapabilityManifest,
        *,
        undo_candidate: MediaControlUndoCandidate,
    ) -> MediaControlRequest:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if type(undo_candidate) is not MediaControlUndoCandidate:
            raise ValueError("verified undo candidate required")
        if undo_candidate.device_id != manifest.device_id:
            raise ValueError("undo candidate device mismatch")
        if undo_candidate.operation == "set_volume":
            operation=MediaControlOperation.SET_VOLUME
            parameters=dict(undo_candidate.parameters)
        elif undo_candidate.operation == "set_captions_enabled":
            operation=MediaControlOperation.SET_CAPTIONS_ENABLED
            parameters=dict(undo_candidate.parameters)
        elif undo_candidate.operation == "set_eq_preset":
            operation=MediaControlOperation.SET_EQ_PRESET
            parameters={"preset":EqPreset(undo_candidate.parameters["preset"])}
        elif undo_candidate.operation == "set_eq_bands":
            operation=MediaControlOperation.SET_EQ_BANDS
            parameters={"bands":tuple(EqBandGain(band["frequency_hz"],band["gain_db"]) for band in undo_candidate.parameters["bands"])}
        else:
            raise ValueError("unsupported undo operation")
        request=MediaControlRequest(device_id=manifest.device_id,playback_session_id=manifest.playback_session_id,content_generation=manifest.content_generation,operation=operation,parameters=parameters,capability_manifest_digest=manifest.digest,expected_pre_state_digest=undo_candidate.expected_current_state_digest)
        if MediaControlCapabilityGate.evaluate(request,manifest) is not MediaControlCapabilityDecision.ALLOW:
            raise ValueError("undo operation is not supported by capability manifest")
        return request

    def reset_device_preferences(
        self,
        *,
        user_profile_id: str,
        device_id: str,
    ) -> bool:
        return self._store.reset_my_default(user_profile_id, device_id)
