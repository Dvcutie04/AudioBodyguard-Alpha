import pytest
from src.edge.tv_selection_preferences import SelectionPreference, SwitchingMode, TVSelectionPreferences


def test_default_asks_before_switching(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    assert store.get("profile_1")==SelectionPreference(SwitchingMode.ASK,None)


@pytest.mark.parametrize("mode", list(SwitchingMode))
def test_preference_survives_reopening(tmp_path,mode):
    path=tmp_path / "preferences.sqlite3"
    preference=SelectionPreference(mode,"living_room_tv")
    TVSelectionPreferences(path).save("profile_1",preference)
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==preference


def test_correction_persists_without_changing_other_profile(tmp_path):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    first=SelectionPreference(SwitchingMode.KEEP,"living_room_tv")
    other=SelectionPreference(SwitchingMode.KEEP,"bedroom_tv")
    store.save("profile_1",first)
    store.save("profile_2",other)
    corrected=SelectionPreference(SwitchingMode.ASK,"study_tv")
    store.save("profile_1",corrected)
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==corrected
    assert reopened.get("profile_2")==other


def test_invalid_update_preserves_saved_choice(tmp_path):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    original=SelectionPreference(SwitchingMode.KEEP,"living_room_tv")
    store.save("profile_1",original)
    with pytest.raises(ValueError):
        store.save("profile_1",SelectionPreference(SwitchingMode.KEEP,None))
    assert TVSelectionPreferences(path).get("profile_1")==original


@pytest.mark.parametrize("mode,saved,nearest,eligible,target,suggestion,confirm", [
    (SwitchingMode.KEEP,"tv_a","tv_b",{"tv_a","tv_b"},"tv_a",None,False),
    (SwitchingMode.KEEP,"tv_a","tv_b",{"tv_b"},None,None,False),
    (SwitchingMode.ASK,"tv_a","tv_b",{"tv_a","tv_b"},"tv_a","tv_b",True),
    (SwitchingMode.ASK,None,"tv_b",{"tv_b"},None,"tv_b",True),
    (SwitchingMode.ASK,"tv_a","tv_a",{"tv_a"},"tv_a",None,False),
    (SwitchingMode.ASK,"tv_a","tv_b",{"tv_b"},None,"tv_b",True),
    (SwitchingMode.FOLLOW,"tv_a","tv_b",{"tv_a","tv_b"},"tv_b",None,False),
    (SwitchingMode.FOLLOW,"tv_a",None,{"tv_a"},None,None,False),
    (SwitchingMode.FOLLOW,"tv_a","tv_b",{"tv_a"},None,None,False),
])
def test_saved_preference_controls_selection(tmp_path,mode,saved,nearest,eligible,target,suggestion,confirm):
    path=tmp_path / "preferences.sqlite3"
    preference=SelectionPreference(mode,saved)
    TVSelectionPreferences(path).save("profile_1",preference)
    reopened=TVSelectionPreferences(path)
    decision=reopened.decide("profile_1",nearest_device_id=nearest,eligible_device_ids=eligible)
    assert decision.target_device_id==target
    assert decision.suggested_device_id==suggestion
    assert decision.requires_confirmation is confirm
    assert reopened.get("profile_1")==preference


@pytest.mark.parametrize("approved,reason,mode,device", [
    (True,"rating",SwitchingMode.FOLLOW,"tv_a"),
    (False,"rating",SwitchingMode.FOLLOW,"tv_a"),
    (True,"keep_this_tv",SwitchingMode.KEEP,"tv_b"),
    (False,"never_switch_automatically",SwitchingMode.ASK,"tv_a"),
])
def test_selection_feedback_persists(tmp_path,approved,reason,mode,device):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    store.save("profile_1",SelectionPreference(SwitchingMode.FOLLOW,"tv_a"))
    other=SelectionPreference(SwitchingMode.KEEP,"tv_c")
    store.save("profile_2",other)
    store.record_feedback("profile_1",device_id="tv_b",approved=approved,reason=reason)
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==SelectionPreference(mode,device)
    assert reopened.get("profile_2")==other
    history=reopened.feedback_history("profile_1")
    assert len(history)==1
    assert history[0]["device_id"]=="tv_b"
    assert history[0]["approved"] is approved
    assert history[0]["reason"]==reason
    assert history[0]["recorded_at"]>0
    assert reopened.feedback_history("profile_2")==[]


def test_invalid_feedback_changes_neither_preference_nor_history(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    original=SelectionPreference(SwitchingMode.KEEP,"tv_a")
    store.save("profile_1",original)
    with pytest.raises(ValueError):
        store.record_feedback("profile_1",device_id="tv_b",approved=False,reason="keep_this_tv")
    assert store.get("profile_1")==original
    assert store.feedback_history("profile_1")==[]
