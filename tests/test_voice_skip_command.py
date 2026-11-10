import dataclasses
import pytest

from src.voice.skip_command import (
    GRAMMAR_VERSION, OwnedPlayerState, OwnedVoiceSkipGate,
    SkipAction, SkipDecision, SkipProposal, parse_skip_command,
)


def player(**overrides):
    state = dict(player_id="owned-player", playback_session_id="session-1",
                 content_id="episode-1", generation=7, intro_visible=True,
                 intro_enabled=True, recap_visible=True, recap_enabled=True)
    state.update(overrides)
    return OwnedPlayerState(**state)


@pytest.mark.parametrize("phrase,kind", [
    ("Audio Bodyguard, skip intro", SkipAction.SKIP_INTRO),
    ("audio bodyguard skip recap", SkipAction.SKIP_RECAP),
    (" AUDIO BODYGUARD, SKIP RECAP. ", SkipAction.SKIP_RECAP),
    ("Audio  Bodyguard skip intro!", SkipAction.SKIP_INTRO),
])
def test_exact_final_phrases(phrase, kind):
    assert parse_skip_command(phrase, final=True) is kind
    assert parse_skip_command(phrase, final=False) is None


@pytest.mark.parametrize("phrase", [
    "skip intro", "Audio Bodyguard skip", "Audio Bodyguard skip ads",
    "Don't Audio Bodyguard skip intro", "Audio Bodyguard don't skip intro",
    "Audio Bodyguard skip intro please", "Audio Bodyguard skip recap then skip intro",
    "Audio Bodyguard skip next", "Audio Bodyguard skip intro? yes",
    "Audio Bodyguard skip intro " * 10, "Audio Bodyguard skip recap\x00",
    "Audio Bodyguard\nskip intro", "Audio Bodyguard\tskip recap",
    "\nAudio Bodyguard skip intro\n", "Audio Bodyguard skip intro\r",
    "Audio Bodyguard skip rеcap",  # visually similar non-ASCII character
    "\u00a0Audio Bodyguard skip intro",  # Unicode trim must not bypass native ASCII policy
    "Audio Bodyguard skip recap\u00a0",
])
def test_no_ambiguous_negated_or_broad_commands(phrase):
    assert parse_skip_command(phrase, final=True) is None


def test_invalid_recognition_types_or_player_states():
    assert parse_skip_command(None, final=True) is None
    assert parse_skip_command("Audio Bodyguard skip intro", final=1) is None
    for override in ({"player_id": ""}, {"content_id": "../other"},
                     {"generation": True}, {"recap_enabled": 1}):
        with pytest.raises(ValueError):
            player(**override)


@pytest.mark.parametrize("command,expected", [
    ("Audio Bodyguard skip intro", SkipAction.SKIP_INTRO),
    ("Audio Bodyguard skip recap", SkipAction.SKIP_RECAP),
])
def test_one_matching_owned_button_acted_on_once(command, expected):
    gate, current, calls = OwnedVoiceSkipGate(), player(), []
    assert gate.start("listen-1", current)
    proposal = gate.propose(command, final=True, run_id="listen-1", observed=current)
    assert proposal and proposal.action is expected and proposal.grammar_version == GRAMMAR_VERSION
    assert gate.request(proposal, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=lambda kind: calls.append(kind) or True) is SkipDecision.REQUESTED
    assert calls == [expected]
    assert gate.request(proposal, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=lambda kind: calls.append(kind) or True) is SkipDecision.UNAVAILABLE
    assert gate.propose(command, final=True, run_id="listen-1", observed=current) is None
    assert calls == [expected]


@pytest.mark.parametrize("change", [
    {"player_id": "other-player"}, {"playback_session_id": "session-2"},
    {"content_id": "episode-2"}, {"generation": 8},
    {"intro_visible": False}, {"intro_enabled": False},
])
def test_stale_player_content_and_manual_button_change_never_dispatch(change):
    gate, before, calls = OwnedVoiceSkipGate(), player(), []
    assert gate.start("listen-1", before)
    proposal = gate.propose("Audio Bodyguard skip intro", final=True,
                            run_id="listen-1", observed=before)
    assert proposal
    assert gate.request(proposal, run_id="listen-1", observed=player(**change),
                        permission=True, foreground=True,
                        press_owned_button=lambda a: calls.append(a) or True) is SkipDecision.UNAVAILABLE
    assert calls == []


@pytest.mark.parametrize("changed", [
    {"intro_visible": False}, {"intro_enabled": False},
    {"recap_visible": False, "intro_enabled": False},
])
def test_unavailable_intro_does_not_fall_back_to_recap_or_next(changed):
    current = player(**changed)
    gate = OwnedVoiceSkipGate()
    assert gate.start("listen-1", current)
    assert gate.propose("Audio Bodyguard skip intro", final=True,
                        run_id="listen-1", observed=current) is None


def test_recaps_need_their_own_available_button():
    current = player(recap_visible=False)
    gate = OwnedVoiceSkipGate()
    assert gate.start("listen-1", current)
    assert gate.propose("Audio Bodyguard skip recap", final=True,
                        run_id="listen-1", observed=current) is None
    assert gate.propose("Audio Bodyguard skip intro", final=True,
                        run_id="listen-1", observed=current).action is SkipAction.SKIP_INTRO


def test_stop_background_permission_and_old_run_reject_without_press():
    current = player()
    gate, calls = OwnedVoiceSkipGate(), []
    assert gate.start("listen-1", current)
    proposal = gate.propose("Audio Bodyguard skip intro", final=True,
                            run_id="listen-1", observed=current)
    for permission, foreground in [(False, True), (True, False)]:
        assert gate.request(proposal, run_id="listen-1", observed=current,
                            permission=permission, foreground=foreground,
                            press_owned_button=lambda kind: calls.append(kind) or True) is SkipDecision.UNAVAILABLE
    gate.stop()
    assert gate.request(proposal, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=lambda kind: calls.append(kind) or True) is SkipDecision.UNAVAILABLE
    assert not gate.start("listen-1", current)  # no immediate reuse of prior run ID
    assert gate.start("listen-2", current)
    assert gate.propose("Audio Bodyguard skip intro", final=True,
                        run_id="listen-1", observed=current) is None
    assert calls == []


def test_no_partial_repeat_proposal_and_forgery():
    current = player()
    gate, calls = OwnedVoiceSkipGate(), []
    assert gate.start("listen-1", current)
    assert gate.propose("Audio Bodyguard skip intro", final=False,
                        run_id="listen-1", observed=current) is None
    p = gate.propose("Audio Bodyguard skip intro", final=True,
                     run_id="listen-1", observed=current)
    assert p is not None
    assert gate.propose("Audio Bodyguard skip recap", final=True,
                        run_id="listen-1", observed=current) is None
    forged = dataclasses.replace(p)
    assert gate.request(forged, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=lambda kind: calls.append(kind) or True) is SkipDecision.UNAVAILABLE
    assert calls == []


def test_one_failing_owned_button_callback_is_never_retried():
    current, gate, calls = player(), OwnedVoiceSkipGate(), []
    assert gate.start("listen-1", current)
    p = gate.propose("Audio Bodyguard skip recap", final=True,
                     run_id="listen-1", observed=current)
    def fails(kind):
        calls.append(kind)
        raise RuntimeError("fixture button disappeared")
    assert gate.request(p, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=fails) is SkipDecision.CALL_FAILED
    assert gate.request(p, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=fails) is SkipDecision.UNAVAILABLE
    assert calls == [SkipAction.SKIP_RECAP]



@pytest.mark.parametrize("permission,foreground", [(False, True), (True, False)])
def test_permission_or_foreground_loss_closes_pending_run(permission, foreground):
    state, gate, calls = player(), OwnedVoiceSkipGate(), []
    assert gate.start("listen-1", state)
    proposal = gate.propose("Audio Bodyguard skip intro", final=True,
                            run_id="listen-1", observed=state)
    press = lambda action: calls.append(action) or True
    assert gate.request(proposal, run_id="listen-1", observed=state,
                        permission=permission, foreground=foreground,
                        press_owned_button=press) is SkipDecision.UNAVAILABLE
    # Recovered permission/focus cannot replay a final transcript from the lost run.
    assert gate.request(proposal, run_id="listen-1", observed=state,
                        permission=True, foreground=True,
                        press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert gate.propose("Audio Bodyguard skip recap", final=True,
                        run_id="listen-1", observed=state) is None
    assert not gate.start("listen-1", state)
    assert gate.start("listen-2", state)
    assert calls == []

def test_requested_is_not_physical_verification():
    current, gate = player(), OwnedVoiceSkipGate()
    assert gate.start("listen-1", current)
    p = gate.propose("Audio Bodyguard skip intro", final=True,
                     run_id="listen-1", observed=current)
    assert gate.request(p, run_id="listen-1", observed=current,
                        permission=True, foreground=True,
                        press_owned_button=lambda _: True) is SkipDecision.REQUESTED
    assert "VERIFIED" not in {state.value for state in SkipDecision}

@pytest.mark.parametrize("phrase,kind", [
    ("Audio Bodyguard skip intro", SkipAction.SKIP_INTRO),
    ("Audio Bodyguard skip recap", SkipAction.SKIP_RECAP),
])
def test_final_event_entry_point_one_matching_button(phrase, kind):
    state, gate, calls = player(), OwnedVoiceSkipGate(), []
    press = lambda action: calls.append(action) or True
    assert gate.start("listen-1", state)
    assert gate.request_final(phrase, run_id="listen-1", observed=state, permission=True,
                              foreground=True, press_owned_button=press) is SkipDecision.REQUESTED
    assert gate.request_final(phrase, run_id="listen-1", observed=state, permission=True,
                              foreground=True, press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == [kind]


@pytest.mark.parametrize("phrase,changed,permission,foreground", [
    ("Audio Bodyguard skip intro please", {}, True, True),
    ("Audio Bodyguard skip recap", {"recap_enabled": False}, True, True),
    ("Audio Bodyguard skip intro", {"generation": 8}, True, True),
    ("Audio Bodyguard skip intro", {}, False, True),
    ("Audio Bodyguard skip intro", {}, True, False),
])
def test_final_event_entry_point_rejects_without_callbacks(phrase, changed, permission, foreground):
    state, gate, calls = player(), OwnedVoiceSkipGate(), []
    assert gate.start("listen-1", state)
    press = lambda action: calls.append(action) or True
    assert gate.request_final(phrase, run_id="listen-1", observed=player(**changed),
                              permission=permission, foreground=foreground,
                              press_owned_button=press) is SkipDecision.UNAVAILABLE
    if not permission or not foreground:
        assert gate.request_final("Audio Bodyguard skip recap", run_id="listen-1",
                                  observed=state, permission=True, foreground=True,
                                  press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == []
