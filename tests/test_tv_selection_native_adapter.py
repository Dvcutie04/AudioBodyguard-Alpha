import pytest

from src.edge.tv_selection_preferences import TVSelectionPreferences
from src.interface.tv_selection_native_adapter import TVSelectionNativeFeedbackAdapter


def event(event_id):
    return {"schema_version":1,"event_id":event_id,"profile_id":"profile_1","device_id":"living-room-tv","approved":True,"choice":"rating","recorded_at":"2026-09-13T20:00:00Z"}


@pytest.mark.parametrize("platform",["ios","android"])
def test_native_adapter_is_profile_bound_feedback_only(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    item=event(f"{platform}_001")
    assert adapter.sync({"events":[item,item]})=={"applied":[f"{platform}_001"],"duplicates":[f"{platform}_001"]}
    assert len(store.feedback_history("profile_1"))==1
    assert not hasattr(adapter,"store")
    assert not hasattr(adapter,"execute")
    assert not hasattr(adapter,"set_volume")


def test_native_adapter_rejects_unsupported_platform_without_writes(tmp_path):
    store=TVSelectionPreferences(tmp_path / "unsupported.sqlite3")
    with pytest.raises(ValueError):
        TVSelectionNativeFeedbackAdapter(store,platform="web",authorized_profile_id="profile_1")
    assert store.feedback_history("profile_1")==[]


@pytest.mark.parametrize("platform",["ios","android"])
def test_native_adapter_rejects_cross_profile_feedback_without_writes(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}_cross_profile.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    item=event(f"{platform}_cross_profile")
    item["profile_id"]="profile_2"
    with pytest.raises(ValueError):
        adapter.sync({"events":[item]})
    assert store.feedback_history("profile_1")==[]
    assert store.feedback_history("profile_2")==[]


@pytest.mark.parametrize("platform",["ios","android"])
def test_native_adapter_returns_versioned_acknowledgement(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}_ack.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    item=event(f"{platform}_ack_001")
    assert adapter.handle({"events":[item,item]})=={"schema_version":1,"ok":True,"applied":[f"{platform}_ack_001"],"duplicates":[f"{platform}_ack_001"]}


@pytest.mark.parametrize("platform",["ios","android"])
def test_native_adapter_returns_profile_error_without_writes(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}_error.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    item=event(f"{platform}_error_001")
    item["profile_id"]="profile_2"
    assert adapter.handle({"events":[item]})=={"schema_version":1,"ok":False,"error":{"code":"PROFILE_NOT_AUTHORIZED"}}
    assert store.feedback_history("profile_1")==[]
    assert store.feedback_history("profile_2")==[]


@pytest.mark.parametrize("platform",["ios","android"])
def test_invalid_native_batch_returns_stable_error_without_partial_writes(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}_atomic.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    valid=event(f"{platform}_valid_001")
    invalid=event(f"{platform}_invalid_001")
    invalid["approved"]=1
    assert adapter.handle({"events":[valid,invalid]})=={"schema_version":1,"ok":False,"error":{"code":"INVALID_FEEDBACK"}}
    assert store.feedback_history("profile_1")==[]


@pytest.mark.parametrize("platform",["ios","android"])
def test_event_collision_rolls_back_entire_native_batch(tmp_path,platform):
    store=TVSelectionPreferences(tmp_path / f"{platform}_collision_atomic.sqlite3")
    adapter=TVSelectionNativeFeedbackAdapter(store,platform=platform,authorized_profile_id="profile_1")
    original=event(f"{platform}_existing_001")
    assert adapter.handle({"events":[original]})["ok"] is True
    new_item=event(f"{platform}_new_001")
    collision=dict(original)
    collision["approved"]=False
    assert adapter.handle({"events":[new_item,collision]})=={"schema_version":1,"ok":False,"error":{"code":"INVALID_FEEDBACK"}}
    history=store.feedback_history("profile_1")
    assert len(history)==1
    assert history[0]["approved"] is True
