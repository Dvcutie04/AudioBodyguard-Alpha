import pytest
from src.edge.tv_selection_preferences import SelectionPreference, SwitchingMode, TVSelectionPreferences
from src.interface.tv_selection_web import TVSelectionWebUI


def test_mobile_page_exposes_accessible_tap_and_long_press_controls(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ui=TVSelectionWebUI(store)
    page=ui.render("profile_1","living-room-tv")
    assert "width=device-width" in page
    assert "id=\"thumbs-up\"" in page
    assert "id=\"thumbs-down\"" in page
    assert "aria-label=\"Good TV choice\"" in page
    assert "aria-label=\"Bad TV choice\"" in page
    assert "pointerdown" in page and "pointerup" in page and "pointercancel" in page
    assert "showModal" in page
    assert "Keep this TV" in page
    assert "Never switch automatically" in page
    assert "More feedback options" in page


@pytest.mark.parametrize("approved",[True,False])
def test_short_tap_records_rating_without_changing_mode(tmp_path,approved):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    original=SelectionPreference(SwitchingMode.FOLLOW,"tv_a")
    store.save("profile_1",original)
    result=TVSelectionWebUI(store).submit({"profile_id":"profile_1","device_id":"tv_b","approved":approved,"choice":"rating"})
    assert result=={"ok":True}
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==original
    assert reopened.feedback_history("profile_1")[0]["approved"] is approved


@pytest.mark.parametrize("approved,choice,expected",[(True,"keep_this_tv",SelectionPreference(SwitchingMode.KEEP,"tv_b")),(False,"never_switch_automatically",SelectionPreference(SwitchingMode.ASK,"tv_a"))])
def test_long_press_choice_updates_durable_preference(tmp_path,approved,choice,expected):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    store.save("profile_1",SelectionPreference(SwitchingMode.FOLLOW,"tv_a"))
    assert TVSelectionWebUI(store).submit({"profile_id":"profile_1","device_id":"tv_b","approved":approved,"choice":choice})=={"ok":True}
    assert TVSelectionPreferences(path).get("profile_1")==expected


def test_invalid_submission_is_atomic(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    original=SelectionPreference(SwitchingMode.KEEP,"tv_a")
    store.save("profile_1",original)
    ui=TVSelectionWebUI(store)
    with pytest.raises(ValueError):
        ui.submit({"profile_id":"profile_1","device_id":"tv_b","approved":True,"choice":"never_switch_automatically"})
    with pytest.raises(ValueError):
        ui.submit({"profile_id":"profile_1","device_id":"tv_b","approved":True,"choice":"rating","extra":"forbidden"})
    assert store.get("profile_1")==original
    assert store.feedback_history("profile_1")==[]


def test_mobile_page_queues_feedback_when_backend_is_unavailable(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    page=TVSelectionWebUI(store).render("profile_1","living-room-tv")
    assert "tv_selection_feedback_outbox_v1" in page
    assert "localStorage.setItem" in page
    assert "crypto.randomUUID" in page
    assert "location.protocol" in page
    assert "Saved on this device" in page
    assert "fetch(\"/feedback\"" in page


def test_mobile_sync_endpoint_ingests_offline_events(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ui=TVSelectionWebUI(store)
    event={"schema_version":1,"event_id":"mobile_001","profile_id":"profile_1","device_id":"tv_b","approved":True,"choice":"rating","recorded_at":"2026-09-13T20:00:00Z"}
    assert ui.sync({"events":[event,event]})=={"applied":["mobile_001"],"duplicates":["mobile_001"]}
    assert len(store.feedback_history("profile_1"))==1
    with pytest.raises(ValueError):
        ui.sync({"events":[event],"extra":"forbidden"})


def test_mobile_page_retries_outbox_and_removes_only_acknowledged_events(tmp_path):
    page=TVSelectionWebUI(TVSelectionPreferences(tmp_path / "preferences.sqlite3")).render("profile_1","living-room-tv")
    assert "fetch(\"/feedback/sync\"" in page
    assert "window.addEventListener(\"online\",flushOutbox)" in page
    assert "result.applied" in page
    assert "result.duplicates" in page
    assert "acknowledged.has(event.event_id)" in page
    assert "localStorage.removeItem(outboxKey)" in page


def test_sync_interface_enforces_authorized_profile(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ui=TVSelectionWebUI(store,authorized_profile_id="profile_1")
    event={"schema_version":1,"event_id":"mobile_cross_profile","profile_id":"profile_2","device_id":"tv_b","approved":True,"choice":"rating","recorded_at":"2026-09-13T20:00:00Z"}
    with pytest.raises(ValueError):
        ui.sync({"events":[event]})
    assert store.feedback_history("profile_1")==[]
    assert store.feedback_history("profile_2")==[]


def test_server_construction_requires_and_enforces_authorized_profile(tmp_path):
    import inspect
    from src.interface.tv_selection_web import build_ui,serve
    assert inspect.signature(serve).parameters["authorized_profile_id"].default is inspect.Parameter.empty
    ui=build_ui(tmp_path / "preferences.sqlite3","profile_1")
    event={"schema_version":1,"event_id":"server_cross_profile","profile_id":"profile_2","device_id":"tv_b","approved":True,"choice":"rating","recorded_at":"2026-09-13T20:00:00Z"}
    with pytest.raises(ValueError):
        ui.sync({"events":[event]})
    assert ui.store.feedback_history("profile_1")==[]
    assert ui.store.feedback_history("profile_2")==[]
