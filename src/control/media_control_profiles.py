import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path

from .media_control_capabilities import (
    EqBandGain,
    EqPreset,
    MediaControlCapabilityDecision,
    MediaControlCapabilityGate,
    MediaControlCapabilityManifest,
    MediaControlOperation,
    MediaControlRequest,
)


def _nonblank(value: object) -> bool:
    return type(value) is str and bool(value.strip()) and value == value.strip()


@unique
class MediaControlProfileKind(Enum):
    RECOMMENDED = "RECOMMENDED"
    USER_DEFAULT = "USER_DEFAULT"
    VERIFIED_UNDO = "VERIFIED_UNDO"


@dataclass(frozen=True, slots=True)
class MediaControlSettingsProfile:
    device_id: str
    name: str
    kind: MediaControlProfileKind
    volume_percent: int | None = None
    captions_enabled: bool | None = None
    eq_preset: EqPreset | None = None
    eq_bands: tuple[EqBandGain, ...] | None = None

    def __post_init__(self) -> None:
        if not _nonblank(self.device_id):
            raise ValueError("invalid profile device identifier")
        if not _nonblank(self.name):
            raise ValueError("invalid profile name")
        if type(self.kind) is not MediaControlProfileKind:
            raise ValueError("invalid profile kind")
        if all(
            value is None
            for value in (
                self.volume_percent,
                self.captions_enabled,
                self.eq_preset,
                self.eq_bands,
            )
        ):
            raise ValueError("media control profile cannot be empty")
        if self.volume_percent is not None and (
            type(self.volume_percent) is not int
            or not 0 <= self.volume_percent <= 100
        ):
            raise ValueError("invalid profile volume")
        if self.captions_enabled is not None and type(self.captions_enabled) is not bool:
            raise ValueError("invalid profile captions")
        if self.eq_preset is not None and type(self.eq_preset) is not EqPreset:
            raise ValueError("invalid profile EQ preset")
        if self.eq_bands is not None and (
            type(self.eq_bands) is not tuple
            or not 1 <= len(self.eq_bands) <= 10
            or any(type(band) is not EqBandGain for band in self.eq_bands)
            or any(
                left.frequency_hz >= right.frequency_hz
                for left, right in zip(self.eq_bands, self.eq_bands[1:])
            )
        ):
            raise ValueError("invalid profile EQ bands")
        if self.eq_preset is not None and self.eq_bands is not None:
            raise ValueError("profile cannot combine EQ preset and bands")


    def requests_for(
        self,
        manifest: MediaControlCapabilityManifest,
    ) -> tuple[MediaControlRequest, ...]:
        if type(manifest) is not MediaControlCapabilityManifest:
            raise ValueError("invalid capability manifest")
        if self.device_id != manifest.device_id:
            raise ValueError("profile device mismatch")
        requests: list[MediaControlRequest] = []

        def add(
            operation: MediaControlOperation,
            parameters: dict[str, object],
        ) -> None:
            requests.append(
                MediaControlRequest(
                    device_id=manifest.device_id,
                    playback_session_id=manifest.playback_session_id,
                    content_generation=manifest.content_generation,
                    operation=operation,
                    parameters=parameters,
                    capability_manifest_digest=manifest.digest,
                )
            )

        if self.captions_enabled is not None:
            add(
                MediaControlOperation.SET_CAPTIONS_ENABLED,
                {"enabled": self.captions_enabled},
            )
        if self.eq_preset is not None:
            add(
                MediaControlOperation.SET_EQ_PRESET,
                {"preset": self.eq_preset},
            )
        if self.eq_bands is not None:
            add(
                MediaControlOperation.SET_EQ_BANDS,
                {"bands": self.eq_bands},
            )
        if self.volume_percent is not None:
            add(
                MediaControlOperation.SET_VOLUME,
                {"volume_percent": self.volume_percent},
            )
        if any(
            MediaControlCapabilityGate.evaluate(request, manifest)
            is not MediaControlCapabilityDecision.ALLOW
            for request in requests
        ):
            raise ValueError("profile is incompatible with capability manifest")
        return tuple(requests)


class MediaControlProfileStore:
    __slots__ = ("_database_path",)

    _TABLE_SQL = (
        "CREATE TABLE IF NOT EXISTS media_control_user_defaults ("
        "user_profile_id TEXT NOT NULL,"
        "device_id TEXT NOT NULL,"
        "payload TEXT NOT NULL,"
        "PRIMARY KEY (user_profile_id, device_id)"
        ") WITHOUT ROWID"
    )

    def __init__(self, database_path: str | Path) -> None:
        if isinstance(database_path, bool) or not isinstance(database_path, (str, Path)):
            raise ValueError("invalid profile store path")
        path = Path(database_path)
        if not str(path).strip() or str(path) == ":memory:":
            raise ValueError("profile store requires a durable path")
        self._database_path = path
        try:
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(self._TABLE_SQL)
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise ValueError("profile store unavailable") from error

    @staticmethod
    def _validate_user_profile_id(user_profile_id: object) -> None:
        if not _nonblank(user_profile_id):
            raise ValueError("invalid user profile identifier")

    @staticmethod
    def _validate_device_id(device_id: object) -> None:
        if not _nonblank(device_id):
            raise ValueError("invalid device identifier")

    @staticmethod
    def _encode(profile: MediaControlSettingsProfile) -> str:
        return json.dumps(
            {
                "schema_version": 1,
                "device_id": profile.device_id,
                "name": profile.name,
                "kind": profile.kind.value,
                "volume_percent": profile.volume_percent,
                "captions_enabled": profile.captions_enabled,
                "eq_preset": (
                    None if profile.eq_preset is None else profile.eq_preset.value
                ),
                "eq_bands": (
                    None
                    if profile.eq_bands is None
                    else [
                        {
                            "frequency_hz": band.frequency_hz,
                            "gain_db": band.gain_db,
                        }
                        for band in profile.eq_bands
                    ]
                ),
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


    @staticmethod
    def _decode(payload: object) -> MediaControlSettingsProfile:
        expected_keys = {
            "schema_version",
            "device_id",
            "name",
            "kind",
            "volume_percent",
            "captions_enabled",
            "eq_preset",
            "eq_bands",
        }

        def reject_constant(value: str) -> object:
            raise ValueError(f"invalid numeric constant: {value}")

        try:
            if type(payload) is not str:
                raise ValueError("stored payload must be text")
            data = json.loads(payload, parse_constant=reject_constant)
            if type(data) is not dict or set(data) != expected_keys:
                raise ValueError("invalid stored schema")
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise ValueError("unsupported stored schema")

            raw_bands = data["eq_bands"]
            if raw_bands is None:
                bands = None
            else:
                if type(raw_bands) is not list:
                    raise ValueError("invalid stored EQ bands")
                parsed_bands: list[EqBandGain] = []
                for raw_band in raw_bands:
                    if (
                        type(raw_band) is not dict
                        or set(raw_band) != {"frequency_hz", "gain_db"}
                    ):
                        raise ValueError("invalid stored EQ band")
                    parsed_bands.append(
                        EqBandGain(
                            raw_band["frequency_hz"],
                            raw_band["gain_db"],
                        )
                    )
                bands = tuple(parsed_bands)

            raw_preset = data["eq_preset"]
            preset = None if raw_preset is None else EqPreset(raw_preset)
            profile = MediaControlSettingsProfile(
                device_id=data["device_id"],
                name=data["name"],
                kind=MediaControlProfileKind(data["kind"]),
                volume_percent=data["volume_percent"],
                captions_enabled=data["captions_enabled"],
                eq_preset=preset,
                eq_bands=bands,
            )
        except (
            json.JSONDecodeError,
            KeyError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            raise ValueError("invalid stored media control profile") from None
        if profile.kind is not MediaControlProfileKind.USER_DEFAULT:
            raise ValueError("stored profile is not a personal default")
        return profile


    def save_my_default(
        self,
        user_profile_id: str,
        profile: MediaControlSettingsProfile,
    ) -> None:
        self._validate_user_profile_id(user_profile_id)
        if type(profile) is not MediaControlSettingsProfile:
            raise ValueError("invalid media control profile")
        if profile.kind is not MediaControlProfileKind.USER_DEFAULT:
            raise ValueError("personal default must use USER_DEFAULT kind")
        payload = self._encode(profile)
        try:
            with closing(sqlite3.connect(self._database_path)) as connection:
                connection.execute(
                    "INSERT INTO media_control_user_defaults "
                    "(user_profile_id, device_id, payload) VALUES (?, ?, ?) "
                    "ON CONFLICT(user_profile_id, device_id) "
                    "DO UPDATE SET payload = excluded.payload",
                    (user_profile_id, profile.device_id, payload),
                )
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise ValueError("profile store unavailable") from error

    def get_my_default(
        self,
        user_profile_id: str,
        device_id: str,
    ) -> MediaControlSettingsProfile | None:
        self._validate_user_profile_id(user_profile_id)
        self._validate_device_id(device_id)
        try:
            with closing(sqlite3.connect(self._database_path)) as connection:
                row = connection.execute(
                    "SELECT payload FROM media_control_user_defaults "
                    "WHERE user_profile_id = ? AND device_id = ?",
                    (user_profile_id, device_id),
                ).fetchone()
        except (OSError, sqlite3.Error) as error:
            raise ValueError("profile store unavailable") from error
        if row is None:
            return None
        profile = self._decode(row[0])
        if profile.device_id != device_id:
            raise ValueError("stored profile device mismatch")
        return profile


    def resolve(
        self,
        user_profile_id: str,
        *,
        recommended: MediaControlSettingsProfile,
    ) -> MediaControlSettingsProfile:
        if type(recommended) is not MediaControlSettingsProfile:
            raise ValueError("invalid recommended profile")
        if recommended.kind is not MediaControlProfileKind.RECOMMENDED:
            raise ValueError("recommended profile must use RECOMMENDED kind")
        personal = self.get_my_default(user_profile_id, recommended.device_id)
        return recommended if personal is None else personal

    def reset_my_default(
        self,
        user_profile_id: str,
        device_id: str,
    ) -> bool:
        self._validate_user_profile_id(user_profile_id)
        self._validate_device_id(device_id)
        try:
            with closing(sqlite3.connect(self._database_path)) as connection:
                cursor = connection.execute(
                    "DELETE FROM media_control_user_defaults "
                    "WHERE user_profile_id = ? AND device_id = ?",
                    (user_profile_id, device_id),
                )
                connection.commit()
                removed = cursor.rowcount
        except (OSError, sqlite3.Error) as error:
            raise ValueError("profile store unavailable") from error
        return removed == 1
