"""Fail-closed voice proposals for an *owned* player with authored Skip controls.

This is not a remote-control adapter, microphone implementation or physical proof.
A final on-device transcript proposes an action; the gate checks an actively
consented listening session and a fresh, exactly bound player/affordance before
invoking a single owned-button callback. A successful callback means REQUESTED,
not that any TV or external streaming service actually skipped anything.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Callable

GRAMMAR_VERSION = "voice-skip-v1"
MAX_TRANSCRIPT_LENGTH = 96
_PHRASE = re.compile(r"audio\s+bodyguard\s*,?\s*skip\s+(intro|recap)[.!?]?", re.ASCII)


class SkipAction(str, Enum):
    SKIP_INTRO = "SKIP_INTRO"
    SKIP_RECAP = "SKIP_RECAP"


class SkipDecision(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    REQUESTED = "REQUESTED"
    CALL_FAILED = "CALL_FAILED"


def parse_skip_command(text: str, *, final: bool) -> SkipAction | None:
    """Only the two complete English phrases; no fuzzy or partial matching."""
    if type(text) is not str or type(final) is not bool or not final or not (1 <= len(text) <= MAX_TRANSCRIPT_LENGTH) or any(not (32 <= ord(ch) <= 126) for ch in text):
        return None
    match = _PHRASE.fullmatch(text.strip().lower())
    if match is None:
        return None
    return SkipAction.SKIP_INTRO if match.group(1) == "intro" else SkipAction.SKIP_RECAP


def _identifier(value: object) -> bool:
    return type(value) is str and 1 <= len(value) <= 96 and value == value.strip() and all(
        ch.isascii() and (ch.isalnum() or ch in "._:-") for ch in value
    )


@dataclass(frozen=True, slots=True)
class OwnedPlayerState:
    """Fresh, app-owned control state; not a discovered or authenticated TV."""
    player_id: str
    playback_session_id: str
    content_id: str
    generation: int
    intro_visible: bool
    intro_enabled: bool
    recap_visible: bool
    recap_enabled: bool

    def __post_init__(self) -> None:
        if not all(_identifier(v) for v in (self.player_id, self.playback_session_id, self.content_id)):
            raise ValueError("invalid owned player identity")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("invalid control generation")
        if not all(type(v) is bool for v in (
            self.intro_visible, self.intro_enabled, self.recap_visible, self.recap_enabled
        )):
            raise ValueError("invalid control availability")

    def offers(self, action: SkipAction) -> bool:
        if action is SkipAction.SKIP_INTRO:
            return self.intro_visible and self.intro_enabled
        if action is SkipAction.SKIP_RECAP:
            return self.recap_visible and self.recap_enabled
        return False


@dataclass(frozen=True, slots=True)
class SkipProposal:
    listening_run_id: str
    action: SkipAction
    player_state: OwnedPlayerState
    grammar_version: str = GRAMMAR_VERSION


class OwnedVoiceSkipGate:
    """Single-utterance admission and one callback at most per explicit Start.

    Not a production authorization replacement. The owning native controller
    must supply fresh visible/enabled controls and remain on the foreground.
    An external target additionally needs authenticated authority and Physical
    Commit verification; those are deliberately *absent* from this fixture.
    """

    def __init__(self) -> None:
        self._run_id: str | None = None
        self._player: OwnedPlayerState | None = None
        self._proposal: SkipProposal | None = None
        self._used = False
        self._last_run_id: str | None = None

    def start(self, run_id: str, selected_player: OwnedPlayerState) -> bool:
        if self._run_id is not None or not _identifier(run_id) or run_id == self._last_run_id:
            return False
        if not isinstance(selected_player, OwnedPlayerState):
            return False
        self._run_id = run_id
        self._last_run_id = run_id
        self._player = selected_player
        self._proposal = None
        self._used = False
        return True

    def stop(self) -> None:
        self._run_id = None
        self._player = None
        self._proposal = None
        self._used = False

    def propose(self, text: str, *, final: bool, run_id: str,
                observed: OwnedPlayerState) -> SkipProposal | None:
        if self._run_id is None or run_id != self._run_id or self._used or self._proposal is not None:
            return None
        if observed != self._player:
            return None
        action = parse_skip_command(text, final=final)
        if action is None or not observed.offers(action):
            return None
        self._proposal = SkipProposal(run_id, action, observed)
        return self._proposal

    def request(self, proposal: SkipProposal, *, run_id: str,
                observed: OwnedPlayerState, permission: bool, foreground: bool,
                press_owned_button: Callable[[SkipAction], bool]) -> SkipDecision:
        # A retired callback cannot revoke a newer run. For the current run,
        # loss of consent must invalidate even an otherwise rejected request.
        if self._run_id is None or run_id != self._run_id:
            return SkipDecision.UNAVAILABLE
        if permission is not True or foreground is not True:
            self.stop()
            return SkipDecision.UNAVAILABLE
        if (self._used or
            proposal is not self._proposal or not isinstance(proposal, SkipProposal) or
            proposal.grammar_version != GRAMMAR_VERSION or
            observed != self._player or observed != proposal.player_state or
            not observed.offers(proposal.action) or not callable(press_owned_button)):
            return SkipDecision.UNAVAILABLE
        # Consumed before the callback: an exception or reentrant callback can
        # never turn the same recognized utterance into a second press.
        self._used = True
        self._proposal = None
        try:
            accepted = press_owned_button(proposal.action)
        except Exception:
            return SkipDecision.CALL_FAILED
        return SkipDecision.REQUESTED if accepted is True else SkipDecision.CALL_FAILED

    def request_final(self, text: str | None, *, run_id: str, observed: OwnedPlayerState,
                      permission: bool, foreground: bool,
                      press_owned_button: Callable[[SkipAction], bool]) -> SkipDecision:
        """Apply final recognition through the same one-shot owned-button policy."""
        if self._run_id is None or run_id != self._run_id:
            return SkipDecision.UNAVAILABLE
        if permission is not True or foreground is not True:
            self.stop()
            return SkipDecision.UNAVAILABLE
        proposal = self.propose(text, final=True, run_id=run_id, observed=observed)
        if proposal is None:
            return SkipDecision.UNAVAILABLE
        return self.request(proposal, run_id=run_id, observed=observed,
                            permission=permission, foreground=foreground,
                            press_owned_button=press_owned_button)
