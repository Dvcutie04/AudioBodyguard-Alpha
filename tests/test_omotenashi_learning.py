import pytest
from src.personalization.omotenashi import OmotenashiLearningEngine, UserPreferenceState


def test_omotenashi_learning_dynamics_and_bounds():
    engine = OmotenashiLearningEngine()
    initial_state = engine.get_state()

    # 1. Verify default initialization
    assert initial_state.preferred_db_drop == 6.0
    assert initial_state.sensitivity_threshold == 0.85

    # 2. Test positive feedback loop (incremental learning)
    state_after_positive = engine.apply_feedback(action_type="REDUCE_VOLUME", positive=True)
    assert state_after_positive.preferred_db_drop > 6.0

    # 3. Test negative feedback loop
    state_after_negative = engine.apply_feedback(action_type="REDUCE_VOLUME", positive=False)
    assert state_after_negative.preferred_db_drop < state_after_positive.preferred_db_drop

    # 4. Enforce upper bound (18.0 dB ceiling)
    for _ in range(500):
        state_upper = engine.apply_feedback(action_type="REDUCE_VOLUME", positive=True)
    assert state_upper.preferred_db_drop <= 18.0

    # 5. Enforce lower bound (3.0 dB floor)
    for _ in range(500):
        state_lower = engine.apply_feedback(action_type="REDUCE_VOLUME", positive=False)
    assert state_lower.preferred_db_drop >= 3.0

    # 6. Verify non-mutation of unrelated state fields for unknown action types
    unrelated_state = engine.apply_feedback(action_type="UNKNOWN_ACTION", positive=True)
    assert unrelated_state.preferred_db_drop == state_lower.preferred_db_drop
