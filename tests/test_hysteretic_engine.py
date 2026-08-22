import pytest
from src.control.hysteretic_engine import AQSSSafetyEngine

def test_engine_initialization():
    engine = AQSSSafetyEngine()
    assert engine.p_threat == 0.0
    assert engine.attack_rate == 0.8
    assert engine.release_rate == 0.05

def test_threat_escalation():
    engine = AQSSSafetyEngine()
    res = engine.update({"db": 95.0, "freq": 3400.0, "sensor_quality": 1.0})
    assert res["weights"]["p_threat"] > 0.5
    assert "LEVEL_" in res["decision"]

def test_environmental_false_positive_suppression():
    engine = AQSSSafetyEngine()
    res_normal = engine.update({"db": 85.0, "freq": 1000.0, "impulse_like": False, "decay_ms": 100.0})
    p_normal = res_normal["weights"]["p_threat"]
    engine_suppressed = AQSSSafetyEngine()
    res_suppressed = engine_suppressed.update({"db": 85.0, "freq": 1000.0, "impulse_like": True, "decay_ms": 25.0})
    p_suppressed = res_suppressed["weights"]["p_threat"]
    assert p_suppressed < p_normal

def test_release_decay():
    engine = AQSSSafetyEngine()
    engine.update({"db": 95.0, "freq": 3000.0})
    initial_p = engine.p_threat
    res = engine.update({"db": 40.0, "freq": 3000.0})
    assert res["weights"]["p_threat"] < initial_p
