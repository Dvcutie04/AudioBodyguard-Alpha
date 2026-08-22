import pytest
from src.control.fusion_router import AQSNgressRouter
from src.control.action_dispatcher import ActionDispatcher

def test_action_dispatcher_local():
    dispatcher = ActionDispatcher()
    res = dispatcher.dispatch("VOICE_COMMAND_EXECUTED: NEXT", {"motion_magnitude": 9.8})
    assert res["status"] == "SUCCESS"
    assert res["command"] == "next"
    assert res["target"] == "local_system"

def test_action_dispatcher_ignored():
    dispatcher = ActionDispatcher()
    res = dispatcher.dispatch("LEVEL_0: FALSE_POSITIVE_SUPPRESSED")
    assert res["status"] == "IGNORED"

def test_full_pipeline_mock_commands():
    router = AQSNgressRouter(profile_path="mock_test_profile.json")
    router.voice.enroll([{"freq": 1800.0, "db": 75.0}])
    
    # Test skip_intro command
    event = {
        "db": 78.0, 
        "freq": 1810.0, 
        "impulse_like": False, 
        "decay_ms": 10.0,
        "accel_vector": {"x": 0.0, "y": 0.0, "z": 9.8},
        "command_intent": "skip_intro"
    }
    result = router.process_event(event)
    assert result["fusion_state"] == "AUDIO_VOICE_FUSED"
    assert result["decision"] == "VOICE_COMMAND_EXECUTED: SKIP_INTRO"
    assert result["action_result"]["status"] == "SUCCESS"
    assert result["action_result"]["command"] == "skip_intro"
