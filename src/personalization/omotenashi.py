from dataclasses import dataclass


@dataclass
class UserPreferenceState:
    """Represents the user's preference state for audio adjustments."""
    preferred_db_drop: float = 6.0
    sensitivity_threshold: float = 0.85
    auto_skip_intros: bool = True
    auto_skip_ads: bool = True


class OmotenashiLearningEngine:
    """Learning engine for adapting to user preferences over time."""

    def __init__(self, state: UserPreferenceState = None):
        self.state = state if state is not None else UserPreferenceState()

    def get_state(self) -> UserPreferenceState:
        """Get the current preference state."""
        return self.state

    def apply_feedback(self, action_type: str, positive: bool) -> UserPreferenceState:
        """
        Apply user feedback to update preference state with boundary enforcement.
        """
        if action_type == "REDUCE_VOLUME":
            adjustment = 0.2 if positive else -0.2
            new_db_drop = self.state.preferred_db_drop + adjustment
            # Enforce bounds: 3.0 to 18.0 dB
            self.state.preferred_db_drop = max(3.0, min(18.0, new_db_drop))
        elif action_type == "SKIP_INTRO":
            if positive:
                self.state.auto_skip_intros = True
            else:
                self.state.sensitivity_threshold = min(
                    0.98, self.state.sensitivity_threshold + 0.03
                )
        return self.state
