import pytest
from policy.hysteresis import HysteresisGate


def test_hysteresis_gate_transitions():
    gate = HysteresisGate(high_threshold=0.8, low_threshold=0.3, initial_state=False)

    # Below high threshold - should remain False
    assert gate.update(0.7) is False

    # Exceed high threshold - transition to True
    assert gate.update(0.85) is True

    # Drop between thresholds - stay True (hysteresis holding)
    assert gate.update(0.4) is True

    # Drop below low threshold - transition to False
    assert gate.update(0.2) is False


def test_invalid_thresholds():
    with pytest.raises(ValueError):
        HysteresisGate(high_threshold=0.3, low_threshold=0.8)
