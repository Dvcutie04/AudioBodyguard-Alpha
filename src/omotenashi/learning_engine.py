from dataclasses import dataclass


@dataclass
class UserPreferenceState:
    preferred_db_drop: float = 6.0
    sensitivity_threshold: float = 0.85
    auto_skip_intros: bool = True
    auto_skip_ads: bool = True


class OmotenashiLearningEngine:
    def __init__(self, state: UserPreferenceState = None):
        self.state = state if state is not None else UserPreferenceState()

    def get_state(self) -> UserPreferenceState:
        return self.state

    def apply_feedback(self, action_type: str, positive: bool) -> UserPreferenceState:
        if action_type == "REDUCE_VOLUME":
            delta = 0.2 if positive else -0.2
            self.state.preferred_db_drop = max(
                3.0, min(18.0, self.state.preferred_db_drop + delta)
            )
        elif action_type == "SKIP_INTRO":
            if positive:
                self.state.auto_skip_intros = True
            else:
                self.state.sensitivity_threshold = min(
                    0.98, self.state.sensitivity_threshold + 0.03
                )
        return self.state
