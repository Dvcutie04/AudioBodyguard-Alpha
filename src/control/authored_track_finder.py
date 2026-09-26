"""Owned-player authored-track discovery and proposal-only manual priority.

Player metadata/selection and callbacks are claims about a player. None of
these values certify caption visibility, acoustic delivery or user perception.
This module has no adapter or authority dependency and cannot select a track.
"""

import math
import re
from dataclasses import dataclass
from enum import Enum


_LANGUAGE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8}){0,5}\Z")


def _id(value: object, name: str) -> None:
    if type(value) is not str or not value.strip() or value != value.strip() or len(value) > 256:
        raise ValueError(f"invalid {name}")


def _time(value: object, name: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"invalid {name}")


class AuthoredTrackKind(Enum):
    SUBTITLES = "SUBTITLES"
    SDH = "SDH"
    AUDIO_DESCRIPTION = "AUDIO_DESCRIPTION"
    DUB = "DUB"


@dataclass(frozen=True, slots=True)
class AuthoredTrack:
    track_id: str
    kind: AuthoredTrackKind
    language: str
    selected_by_player: bool = False
    presentation_callback_reported: bool = False

    def __post_init__(self) -> None:
        _id(self.track_id, "track_id")
        if type(self.kind) is not AuthoredTrackKind:
            raise ValueError("invalid authored track kind")
        if type(self.language) is not str or _LANGUAGE.fullmatch(self.language) is None:
            raise ValueError("invalid language tag")
        if type(self.selected_by_player) is not bool or type(self.presentation_callback_reported) is not bool:
            raise ValueError("invalid player track report")
        if self.presentation_callback_reported and not self.selected_by_player:
            raise ValueError("presentation callback without selected track")


@dataclass(frozen=True, slots=True)
class OwnedTrackSnapshot:
    playback_session_id: str
    content_generation: int
    runtime_id: str
    clock_domain_id: str
    observed_monotonic: float
    expires_monotonic: float
    catalog_complete: bool
    tracks: tuple[AuthoredTrack, ...]

    def __post_init__(self) -> None:
        for name in ("playback_session_id", "runtime_id", "clock_domain_id"):
            _id(getattr(self, name), name)
        if type(self.content_generation) is not int or self.content_generation < 0:
            raise ValueError("invalid content generation")
        _time(self.observed_monotonic, "observed_monotonic")
        _time(self.expires_monotonic, "expires_monotonic")
        if self.expires_monotonic < self.observed_monotonic:
            raise ValueError("invalid catalog expiry")
        if type(self.catalog_complete) is not bool:
            raise ValueError("invalid catalog completeness")
        if type(self.tracks) is not tuple or len(self.tracks) > 256 or any(type(t) is not AuthoredTrack for t in self.tracks):
            raise ValueError("invalid authored tracks")
        ids = [track.track_id for track in self.tracks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate track identity")


@dataclass(frozen=True, slots=True)
class AuthoredTrackView:
    availability: str
    selection: str
    presentation: str
    physical_output_verified: bool = False


def _current(catalog: OwnedTrackSnapshot | None, *, runtime_id: str,
             clock_domain_id: str, now_monotonic: float) -> bool:
    _id(runtime_id, "runtime_id")
    _id(clock_domain_id, "clock_domain_id")
    _time(now_monotonic, "now_monotonic")
    return (type(catalog) is OwnedTrackSnapshot
            and catalog.runtime_id == runtime_id
            and catalog.clock_domain_id == clock_domain_id
            and catalog.observed_monotonic <= now_monotonic <= catalog.expires_monotonic)


def authored_track_view(catalog: OwnedTrackSnapshot | None, *, kind: AuthoredTrackKind,
                        language: str, runtime_id: str, clock_domain_id: str,
                        now_monotonic: float) -> AuthoredTrackView:
    if type(kind) is not AuthoredTrackKind or type(language) is not str or _LANGUAGE.fullmatch(language) is None:
        raise ValueError("invalid authored track query")
    if not _current(catalog, runtime_id=runtime_id, clock_domain_id=clock_domain_id,
                    now_monotonic=now_monotonic):
        return AuthoredTrackView("UNKNOWN", "UNKNOWN", "UNKNOWN")
    matches = [track for track in catalog.tracks if track.kind is kind and track.language.lower() == language.lower()]
    if not matches:
        return AuthoredTrackView("PLAYER_REPORTS_ABSENT" if catalog.catalog_complete else "UNKNOWN",
                                 "UNKNOWN", "UNKNOWN")
    selected = [track for track in matches if track.selected_by_player]
    callback = any(track.presentation_callback_reported for track in selected)
    return AuthoredTrackView("PLAYER_REPORTS_AVAILABLE",
                             "PLAYER_REPORTS_SELECTED" if selected else "NOT_REPORTED_SELECTED",
                             "PLAYER_CALLBACK_REPORTED" if callback else "NO_PRESENTATION_CALLBACK")


@dataclass(frozen=True, slots=True)
class ManualTrackChoice:
    playback_session_id: str
    content_generation: int
    track_id: str

    def __post_init__(self) -> None:
        _id(self.playback_session_id, "playback_session_id")
        _id(self.track_id, "track_id")
        if type(self.content_generation) is not int or self.content_generation < 0:
            raise ValueError("invalid content generation")


@dataclass(frozen=True, slots=True)
class TrackProposalView:
    status: str
    chosen_track_id: str | None = None
    can_actuate: bool = False


def proposed_track_choice(catalog: OwnedTrackSnapshot | None, *, suggested_track_id: str,
                          manual_choice: ManualTrackChoice | None, runtime_id: str,
                          clock_domain_id: str, now_monotonic: float) -> TrackProposalView:
    _id(suggested_track_id, "suggested_track_id")
    if manual_choice is not None and type(manual_choice) is not ManualTrackChoice:
        raise ValueError("invalid manual choice")
    if not _current(catalog, runtime_id=runtime_id, clock_domain_id=clock_domain_id,
                    now_monotonic=now_monotonic):
        return TrackProposalView("CATALOG_UNKNOWN")
    tracks = {track.track_id for track in catalog.tracks}
    if manual_choice is not None:
        if (manual_choice.playback_session_id != catalog.playback_session_id
                or manual_choice.content_generation != catalog.content_generation
                or manual_choice.track_id not in tracks):
            return TrackProposalView("MANUAL_CHOICE_REVALIDATION_REQUIRED")
        return TrackProposalView("MANUAL_CHOICE_PRIORITY", manual_choice.track_id)
    if suggested_track_id not in tracks:
        return TrackProposalView("TRACK_UNAVAILABLE")
    return TrackProposalView("PROPOSAL_ONLY", suggested_track_id)
