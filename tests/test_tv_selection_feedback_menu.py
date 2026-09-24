import pytest
from src.edge.tv_selection_preferences import SelectionPreference, SwitchingMode, TVSelectionPreferences
from src.edge.tv_selection_feedback_menu import TVSelectionFeedbackMenu


def test_opening_and_dismissing_menus_changes_nothing(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    original=SelectionPreference(SwitchingMode.FOLLOW,"tv_a")
    store.save("profile_1",original)
    up=TVSelectionFeedbackMenu(store,"profile_1","tv_b",approved=True)
    down=TVSelectionFeedbackMenu(store,"profile_1","tv_b",approved=False)
    assert [item.identifier for item in up.items]==["rating","keep_this_tv"]
    assert [item.identifier for item in down.items]==["rating","never_switch_automatically"]
    assert all(item.label and item.accessibility_identifier for item in up.items+down.items)
    up.dismiss()
    down.dismiss()
    assert store.get("profile_1")==original
    assert store.feedback_history("profile_1")==[]


@pytest.mark.parametrize("approved,choice,mode,device", [(True,"rating",SwitchingMode.FOLLOW,"tv_a"),(False,"rating",SwitchingMode.FOLLOW,"tv_a"),(True,"keep_this_tv",SwitchingMode.KEEP,"tv_b"),(False,"never_switch_automatically",SwitchingMode.ASK,"tv_a")])
def test_menu_choice_is_saved_once(tmp_path,approved,choice,mode,device):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    store.save("profile_1",SelectionPreference(SwitchingMode.FOLLOW,"tv_a"))
    menu=TVSelectionFeedbackMenu(store,"profile_1","tv_b",approved=approved)
    menu.select(choice)
    with pytest.raises(ValueError):
        menu.select(choice)
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==SelectionPreference(mode,device)
    history=reopened.feedback_history("profile_1")
    assert len(history)==1
    assert history[0]["reason"]==choice
    assert history[0]["approved"] is approved


def test_invalid_or_dismissed_menu_cannot_save(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    menu=TVSelectionFeedbackMenu(store,"profile_1","tv_b",approved=False)
    with pytest.raises(ValueError):
        menu.select("keep_this_tv")
    menu.dismiss()
    with pytest.raises(ValueError):
        menu.select("rating")
    assert store.get("profile_1")==SelectionPreference(SwitchingMode.ASK,None)
    assert store.feedback_history("profile_1")==[]
