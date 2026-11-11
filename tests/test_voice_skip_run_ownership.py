"""A delayed recognizer event must not own a newer listening session."""
from dataclasses import replace

import pytest

from src.voice.skip_command import OwnedPlayerState, OwnedVoiceSkipGate, SkipAction, SkipDecision


def player():
    return OwnedPlayerState('owned', 'episode-session', 'episode', 1, True, True, True, True)


@pytest.mark.parametrize('permission,foreground', [(False, True), (True, False)])
@pytest.mark.parametrize('action', [SkipAction.SKIP_INTRO, SkipAction.SKIP_RECAP])
def test_old_final_denial_cannot_stop_new_listening_run(permission, foreground, action):
    gate, state, calls = OwnedVoiceSkipGate(), player(), []
    assert gate.start('old', state)
    gate.stop()
    assert gate.start('new', state)
    phrase = 'Audio Bodyguard, skip ' + ('intro' if action is SkipAction.SKIP_INTRO else 'recap')
    def press(value):
        calls.append(value)
        return True
    assert gate.request_final(phrase, run_id='old', observed=state,
                              permission=permission, foreground=foreground,
                              press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == []
    assert gate.request_final(phrase, run_id='new', observed=state,
                              permission=True, foreground=True,
                              press_owned_button=press) is SkipDecision.REQUESTED
    assert calls == [action]
    assert gate.request_final(phrase, run_id='new', observed=state,
                              permission=True, foreground=True,
                              press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == [action]


@pytest.mark.parametrize('permission,foreground', [(False, True), (True, False)])
@pytest.mark.parametrize('bad_input', ['missing_proposal', 'changed_state'])
def test_current_denial_invalidates_run_before_other_rejections(permission, foreground, bad_input):
    gate, state, calls = OwnedVoiceSkipGate(), player(), []
    assert gate.start('current', state)
    proposal = gate.propose('Audio Bodyguard, skip intro', final=True,
                            run_id='current', observed=state)
    assert proposal is not None
    def press(value):
        calls.append(value)
        return True
    supplied = None if bad_input == 'missing_proposal' else proposal
    observed = replace(state, generation=2) if bad_input == 'changed_state' else state
    assert gate.request(supplied, run_id='current', observed=observed,
                        permission=permission, foreground=foreground,
                        press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == []
    # Restoring permission/state alone must never revive the pending proposal.
    assert gate.request(proposal, run_id='current', observed=state,
                        permission=True, foreground=True,
                        press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == []
    assert not gate.start('current', state)
    assert gate.start('fresh', state)
    assert gate.request_final('Audio Bodyguard, skip intro', run_id='fresh', observed=state,
                              permission=True, foreground=True,
                              press_owned_button=press) is SkipDecision.REQUESTED
    assert calls == [SkipAction.SKIP_INTRO]


@pytest.mark.parametrize('permission,foreground', [(False, True), (True, False)])
def test_old_split_request_cannot_stop_new_pending_proposal(permission, foreground):
    gate, state, calls = OwnedVoiceSkipGate(), player(), []
    assert gate.start('old', state)
    old = gate.propose('Audio Bodyguard, skip intro', final=True, run_id='old', observed=state)
    gate.stop()
    assert gate.start('new', state)
    new = gate.propose('Audio Bodyguard, skip recap', final=True, run_id='new', observed=state)
    def press(value):
        calls.append(value)
        return True
    assert gate.request(old, run_id='old', observed=state, permission=permission,
                        foreground=foreground, press_owned_button=press) is SkipDecision.UNAVAILABLE
    assert calls == []
    assert gate.request(new, run_id='new', observed=state, permission=True,
                        foreground=True, press_owned_button=press) is SkipDecision.REQUESTED
    assert calls == [SkipAction.SKIP_RECAP]
