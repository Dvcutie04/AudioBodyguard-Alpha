import pytest
from src.control.fusion_router import AQSNgressRouter

def test_fusion_router_init():
    router = AQSNgressRouter()
    assert router.hysteretic is not None
    assert router.voice is not None

def test_authorized_voice_suppression():
    router = AQSNgressRouter(profile_path="test_router_profile.json")
    router.voice.enroll([{"freq": 1800.0, "db": 75.0}, {"freq": 1850.0, "db": 76.0}])
    
    event = {"db": 85.0, "freq": 1820.0, "impulse_like": True, "decay_ms": 20.0}
    res = router.process_event(event)
    assert "FALSE_POSITIVE" in res["decision"] or "SUPPRESSED" in res["decision"]
