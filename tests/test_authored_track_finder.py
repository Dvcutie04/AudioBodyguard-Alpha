"""Authored options, player selection and presentation are separate facts."""

from dataclasses import replace

import pytest

from src.control.authored_track_finder import (
    AuthoredTrack,
    AuthoredTrackKind,
    ManualTrackChoice,
    OwnedTrackSnapshot,
    authored_track_view,
    proposed_track_choice,
)


def snapshot(*tracks):
    return OwnedTrackSnapshot(
        playback_session_id="session-private", content_generation=4,
        runtime_id="run-a", clock_domain_id="clock-a",
        observed_monotonic=100, expires_monotonic=104,
        catalog_complete=True, tracks=tuple(tracks),
    )


def caption(*, selected=False, callback=False):
    return AuthoredTrack("caption-en", AuthoredTrackKind.SDH, "en",
                         selected_by_player=selected, presentation_callback_reported=callback)


def test_selection_is_not_captions_rendered_or_read_by_a_person():
    catalog = snapshot(caption(selected=True))
    view = authored_track_view(catalog, kind=AuthoredTrackKind.SDH, language="en",
                               runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101)
    assert view.availability == "PLAYER_REPORTS_AVAILABLE"
    assert view.selection == "PLAYER_REPORTS_SELECTED"
    assert view.presentation == "NO_PRESENTATION_CALLBACK"
    assert view.physical_output_verified is False


def test_render_callback_still_does_not_claim_acoustic_or_visual_delivery():
    catalog = snapshot(caption(selected=True, callback=True))
    view = authored_track_view(catalog, kind=AuthoredTrackKind.SDH, language="en",
                               runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101)
    assert view.presentation == "PLAYER_CALLBACK_REPORTED"
    assert view.physical_output_verified is False


def test_missing_metadata_and_stale_catalog_are_unknown_not_absent():
    for data, runtime, clock, now in ((None, "run-a", "clock-a", 101),
                                      (snapshot(), "run-a", "clock-a", 105),
                                      (snapshot(), "run-b", "clock-b", 1)):
        view = authored_track_view(data, kind=AuthoredTrackKind.AUDIO_DESCRIPTION,
                                   language="en", runtime_id=runtime,
                                   clock_domain_id=clock, now_monotonic=now)
        assert view.availability == "UNKNOWN"
        assert view.physical_output_verified is False


def test_complete_catalog_can_report_absence_but_partial_catalog_cannot():
    complete = snapshot()
    partial = replace(complete, catalog_complete=False)
    for data, expected in ((complete, "PLAYER_REPORTS_ABSENT"), (partial, "UNKNOWN")):
        view = authored_track_view(data, kind=AuthoredTrackKind.SUBTITLES,
                                   language="en", runtime_id="run-a",
                                   clock_domain_id="clock-a", now_monotonic=101)
        assert view.availability == expected


def test_manual_choice_blocks_a_competing_suggestion_and_does_not_dispatch():
    manual = ManualTrackChoice(playback_session_id="session-private", content_generation=4,
                               track_id="caption-en")
    available = snapshot(caption(), AuthoredTrack("caption-es", AuthoredTrackKind.SDH, "es"))
    decision = proposed_track_choice(available, suggested_track_id="caption-es", manual_choice=manual,
                                     runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101)
    assert decision.status == "MANUAL_CHOICE_PRIORITY"
    assert decision.chosen_track_id == "caption-en"
    assert decision.can_actuate is False
    assert proposed_track_choice(available, suggested_track_id="caption-es", manual_choice=None,
                                 runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101).status == "PROPOSAL_ONLY"


def test_changed_content_does_not_apply_an_old_manual_choice_or_auto_select():
    manual = ManualTrackChoice(playback_session_id="session-private", content_generation=4,
                               track_id="caption-en")
    changed = replace(snapshot(caption()), content_generation=5)
    result = proposed_track_choice(changed, suggested_track_id="caption-en", manual_choice=manual,
                                   runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101)
    assert result.status == "MANUAL_CHOICE_REVALIDATION_REQUIRED"
    assert result.chosen_track_id is None


def test_unknown_suggested_track_and_broken_catalog_reject():
    assert proposed_track_choice(snapshot(caption()), suggested_track_id="missing", manual_choice=None,
                                 runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=101).status == "TRACK_UNAVAILABLE"
    assert proposed_track_choice(snapshot(caption()), suggested_track_id="caption-en", manual_choice=None,
                                 runtime_id="run-a", clock_domain_id="clock-a", now_monotonic=107).status == "CATALOG_UNKNOWN"
    with pytest.raises(ValueError, match="duplicate track"):
        snapshot(caption(), caption())
    with pytest.raises(ValueError):
        replace(snapshot(caption()), catalog_complete=True, tracks=(replace(caption(), selected_by_player=False,
                                                                          presentation_callback_reported=True),))
