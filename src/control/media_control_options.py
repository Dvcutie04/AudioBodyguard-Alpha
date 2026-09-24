from dataclasses import dataclass
from enum import Enum, unique

from .media_control_capabilities import (
    CaptionCapability,
    EqCapability,
    MediaControlCapabilityManifest,
)


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value.strip()) and value == value.strip()


@unique
class MediaControlOptionKey(Enum):
    VOLUME = "VOLUME"
    CAPTIONS = "CAPTIONS"
    EQ_PRESET = "EQ_PRESET"
    EQ_BANDS = "EQ_BANDS"


@unique
class MediaControlRecoveryActionKey(Enum):
    APPLY_RECOMMENDED = "APPLY_RECOMMENDED"
    SAVE_MY_DEFAULT = "SAVE_MY_DEFAULT"
    RESTORE_MY_DEFAULT = "RESTORE_MY_DEFAULT"
    UNDO_LAST_CHANGE = "UNDO_LAST_CHANGE"
    RESET_DEVICE_PREFERENCES = "RESET_DEVICE_PREFERENCES"


@dataclass(frozen=True, slots=True)
class DeviceDisplayMetadata:
    device_id: str
    display_name: str
    brand: str | None = None
    model: str | None = None
    metadata_verified: bool = False

    def __post_init__(self) -> None:
        if not _nonblank(self.device_id):
            raise ValueError("invalid device identifier")
        if not _nonblank(self.display_name):
            raise ValueError("invalid device display name")
        if type(self.metadata_verified) is not bool:
            raise ValueError("invalid device metadata verification")
        if any(value is not None and not _nonblank(value) for value in (self.brand, self.model)):
            raise ValueError("invalid device metadata")
        if self.metadata_verified and (self.brand is None or self.model is None):
            raise ValueError("verified device metadata requires brand and model")
        if not self.metadata_verified and (self.brand is not None or self.model is not None):
            raise ValueError("unverified brand or model cannot be displayed")


@dataclass(frozen=True, slots=True)
class MediaControlOption:
    key: MediaControlOptionKey
    title: str
    description: str
    example: str
    available: bool
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.key) is not MediaControlOptionKey:
            raise ValueError("invalid media control option key")
        if not all(_nonblank(value) for value in (self.title, self.description, self.example)):
            raise ValueError("invalid media control option text")
        if not self.example.startswith("Example:"):
            raise ValueError("media control example must be labeled")
        if type(self.available) is not bool:
            raise ValueError("invalid media control availability")
        if self.available and self.unavailable_reason is not None:
            raise ValueError("available option cannot have an unavailable reason")
        if not self.available and not _nonblank(self.unavailable_reason):
            raise ValueError("unavailable option requires a reason")


@dataclass(frozen=True, slots=True)
class MediaControlRecoveryState:
    has_recommended_profile: bool
    has_saved_default: bool
    can_undo: bool
    can_save_current: bool = False

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.has_recommended_profile,
                self.has_saved_default,
                self.can_undo,
                self.can_save_current,
            )
        ):
            raise ValueError("invalid recovery state")


@dataclass(frozen=True, slots=True)
class MediaControlRecoveryAction:
    key: MediaControlRecoveryActionKey
    label: str
    description: str
    available: bool = True
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.key) is not MediaControlRecoveryActionKey:
            raise ValueError("invalid recovery action key")
        if not _nonblank(self.label) or not _nonblank(self.description):
            raise ValueError("invalid recovery action text")
        if type(self.available) is not bool:
            raise ValueError("invalid recovery action availability")
        if self.available and self.unavailable_reason is not None:
            raise ValueError("available recovery action cannot have an unavailable reason")
        if not self.available and not _nonblank(self.unavailable_reason):
            raise ValueError("unavailable recovery action requires a reason")


@dataclass(frozen=True, slots=True)
class MediaControlOptionsMenu:
    device_heading: str
    device_detail: str
    items: tuple[MediaControlOption, ...]
    recovery_actions: tuple[MediaControlRecoveryAction, ...]

    def item(self, key: MediaControlOptionKey) -> MediaControlOption:
        if type(key) is not MediaControlOptionKey:
            raise ValueError("invalid media control option key")
        return next(item for item in self.items if item.key is key)

    def action(
        self,
        key: MediaControlRecoveryActionKey,
    ) -> MediaControlRecoveryAction:
        if type(key) is not MediaControlRecoveryActionKey:
            raise ValueError("invalid recovery action key")
        return next(action for action in self.recovery_actions if action.key is key)

    @classmethod
    def for_manifest(
        cls,
        manifest: MediaControlCapabilityManifest,
        *,
        device: DeviceDisplayMetadata,
        recovery: MediaControlRecoveryState = MediaControlRecoveryState(False, False, False),
    ) -> "MediaControlOptionsMenu":
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if type(device) is not DeviceDisplayMetadata:
            raise ValueError("invalid device display metadata")
        if type(recovery) is not MediaControlRecoveryState:
            raise ValueError("invalid recovery state")
        if device.device_id != manifest.device_id:
            raise ValueError("device metadata mismatch")
        device_detail = (
            f"{device.brand} • {device.model}"
            if device.metadata_verified
            else "Brand and model unavailable"
        )

        def option(
            key: MediaControlOptionKey,
            title: str,
            description: str,
            example: str,
            available: bool,
        ) -> MediaControlOption:
            return MediaControlOption(
                key=key,
                title=title,
                description=description,
                example=example,
                available=available,
                unavailable_reason=None if available else "Not supported by this device",
            )

        items = (
            option(
                MediaControlOptionKey.VOLUME,
                "Volume",
                "Set this device volume from 0 to 100 percent.",
                "Example: Set the Living Room TV volume to 42 percent.",
                manifest.eq_capability is not EqCapability.NONE,
            ),
            option(
                MediaControlOptionKey.CAPTIONS,
                "Captions",
                "Turn available captions on or off for the current playback session.",
                "Example: Turn on the TV native caption track.",
                manifest.caption_capability is not CaptionCapability.NONE,
            ),
            option(
                MediaControlOptionKey.EQ_PRESET,
                "Sound Preset",
                "Choose Dialogue, Music, Night, or Flat when presets are supported.",
                "Example: Use Dialogue to make speech easier to understand.",
                manifest.eq_capability is EqCapability.SEMANTIC_PRESETS,
            ),
            option(
                MediaControlOptionKey.EQ_BANDS,
                "Custom Equalizer",
                "Adjust supported frequency bands without changing playback pitch.",
                "Example: Raise 1 kHz by 3 dB to emphasize speech.",
                manifest.eq_capability is EqCapability.BANDS,
            ),
        )
        def recovery_action(
            key: MediaControlRecoveryActionKey,
            label: str,
            description: str,
            available: bool,
            unavailable_reason: str,
        ) -> MediaControlRecoveryAction:
            return MediaControlRecoveryAction(
                key,
                label,
                description,
                available,
                None if available else unavailable_reason,
            )

        recovery_actions = (
            recovery_action(
                MediaControlRecoveryActionKey.APPLY_RECOMMENDED,
                "Apply Recommended",
                "Reapply the verified device-compatible baseline.",
                recovery.has_recommended_profile,
                "No recommended profile available",
            ),
            recovery_action(
                MediaControlRecoveryActionKey.SAVE_MY_DEFAULT,
                "Save Current as My Default",
                "Save the current confirmed settings for this device.",
                recovery.can_save_current and any(item.available for item in items),
                (
                    "No verified current settings to save"
                    if not recovery.can_save_current
                    else "No supported settings to save"
                ),
            ),
            recovery_action(
                MediaControlRecoveryActionKey.RESTORE_MY_DEFAULT,
                "Restore My Default",
                "Reapply the last saved confirmed settings.",
                recovery.has_saved_default,
                "Save a personal default first",
            ),
            recovery_action(
                MediaControlRecoveryActionKey.UNDO_LAST_CHANGE,
                "Undo Last Change",
                "Restore the last physically verified device state.",
                recovery.can_undo,
                "No verified change to undo",
            ),
            recovery_action(
                MediaControlRecoveryActionKey.RESET_DEVICE_PREFERENCES,
                "Reset Device Preferences",
                "Remove the personal default and return to Recommended.",
                recovery.has_saved_default,
                "No personal default to reset",
            ),
        )
        return cls(device.display_name, device_detail, items, recovery_actions)
