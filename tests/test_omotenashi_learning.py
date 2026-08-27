import pytest
from src.personalization.omotenashi import (
    OmotenashiLearningEngine,
    UserPreferenceState,
)


def test_omotenashi_learning_dynamics_and_bounds():
    # 1. Verify default initialization
    engine = OmotenashiLearningEngine()
    initial_state = engine.get_state()
    assert initial_state.preferred_db_drop == 6.0
    assert initial_state.sensitivity_threshold == 0.85

    # 2. Test positive feedback loop (incremental learning)
    engine_pos = OmotenashiLearningEngine()
    state_pos = engine_pos.apply_feedback(action_type="REDUCE_VOLUME", positive=True)
    assert state_pos.preferred_db_drop == 6.2

    # 3. Test negative feedback loop from initial baseline
    engine_neg = OmotenashiLearningEngine()
    state_neg = engine_neg.apply_feedback(action_type="REDUCE_VOLUME", positive=False)
    assert state_neg.preferred_db_drop == 5.8
    assert state_neg.preferred_db_drop < state_pos.preferred_db_drop

    # 4. Enforce upper bound (18.0 dB ceiling)
    engine_upper = OmotenashiLearningEngine()
    for _ in range(500):
        state_upper = engine_upper.apply_feedback(
            action_type="REDUCE_VOLUME", positive=True
        )
    assert state_upper.preferred_db_drop == 18.0

    # 5. Enforce lower bound (3.0 dB floor)
    engine_lower = OmotenashiLearningEngine()
    for _ in range(500):
        state_lower = engine_lower.apply_feedback(
            action_type="REDUCE_VOLUME", positive=False
        )
    assert state_lower.preferred_db_drop == 3.0

    # 6. Verify non-mutation of state fields for unknown action types
    engine_unknown = OmotenashiLearningEngine()
    unrelated_state = engine_unknown.apply_feedback(
        action_type="UNKNOWN_ACTION", positive=True
    )
    assert unrelated_state.preferred_db_drop == 6.0
