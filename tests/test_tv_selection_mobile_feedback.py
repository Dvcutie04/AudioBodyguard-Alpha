import pytest

from src.edge.tv_selection_preferences import SelectionPreference, SwitchingMode, TVSelectionPreferences
from src.interface.tv_selection_mobile_feedback import TVSelectionMobileFeedbackIngestor


def payload(**changes):
    value={"schema_version":1,"event_id":"event_001","profile_id":"profile_1","device_id":"tv_b","approved":True,"choice":"rating","recorded_at":"2026-09-13T20:00:00Z"}
    value.update(changes)
    return value


def test_offline_feedback_is_ingested_exactly_once(tmp_path):
    path=tmp_path / "preferences.sqlite3"
    store=TVSelectionPreferences(path)
    store.save("profile_1",SelectionPreference(SwitchingMode.FOLLOW,"tv_a"))
    ingestor=TVSelectionMobileFeedbackIngestor(store)
    assert ingestor.ingest(payload()) is True
    assert ingestor.ingest(payload()) is False
    reopened=TVSelectionPreferences(path)
    assert reopened.get("profile_1")==SelectionPreference(SwitchingMode.FOLLOW,"tv_a")
    assert len(reopened.feedback_history("profile_1"))==1


@pytest.mark.parametrize("change",[{"schema_version":2},{"event_id":""},{"approved":1},{"choice":"keep_this_tv","approved":False},{"recorded_at":"not-a-time"},{"extra":"forbidden"}])
def test_invalid_mobile_feedback_is_atomic(tmp_path,change):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    original=SelectionPreference(SwitchingMode.KEEP,"tv_a")
    store.save("profile_1",original)
    with pytest.raises(ValueError):
        TVSelectionMobileFeedbackIngestor(store).ingest(payload(**change))
    assert store.get("profile_1")==original
    assert store.feedback_history("profile_1")==[]


def test_reused_event_id_with_changed_payload_is_rejected(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ingestor=TVSelectionMobileFeedbackIngestor(store)
    assert ingestor.ingest(payload()) is True
    with pytest.raises(ValueError):
        ingestor.ingest(payload(approved=False))
    history=store.feedback_history("profile_1")
    assert len(history)==1
    assert history[0]["approved"] is True


def test_mobile_feedback_batch_returns_per_event_acknowledgements(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ingestor=TVSelectionMobileFeedbackIngestor(store)
    first=payload()
    second=payload(event_id="event_002",approved=False)
    result=ingestor.ingest_batch([first,first,second])
    assert result=={"applied":["event_001","event_002"],"duplicates":["event_001"]}
    history=store.feedback_history("profile_1")
    assert len(history)==2
    assert [item["approved"] for item in history]==[True,False]


def test_mobile_feedback_cannot_cross_authorized_profile(tmp_path):
    store=TVSelectionPreferences(tmp_path / "preferences.sqlite3")
    ingestor=TVSelectionMobileFeedbackIngestor(store,authorized_profile_id="profile_1")
    with pytest.raises(ValueError):
        ingestor.ingest(payload(profile_id="profile_2"))
    assert store.feedback_history("profile_1")==[]
    assert store.feedback_history("profile_2")==[]
