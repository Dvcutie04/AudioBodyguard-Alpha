python3 -c 'import os; os.makedirs("src/omotenashi", exist_ok=True); open("src/omotenashi/learning_engine.py", "w").write("""from dataclasses import dataclass

@dataclass
class UserPreferenceState:
    preferred_db_drop: float = 8.0
    detection_sensitivity: float = 0.85
    auto_skip_intros: bool = True
    auto_skip_ads: bool = True

class OmotenashiLearningEngine:
    def __init__(self, state: UserPreferenceState = None):
        self.state = state if state is not None else UserPreferenceState()

    def register_feedback(self, action_type: str, positive: bool):
        if action_type == "REDUCE_VOLUME":
            delta = 0.05 if positive else -0.05
            self.state.preferred_db_drop = round(max(3.0, min(18.0, self.state.preferred_db_drop + delta)), 2)
        elif action_type == "SKIP_INTRO":
            if not positive:
                self.state.detection_sensitivity = round(min(0.98, self.state.detection_sensitivity + 0.03), 2)
""")'
