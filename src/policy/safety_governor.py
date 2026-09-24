class SafetyGovernor:
    def __init__(self, pm):
        self.pm = pm
    def evaluate_action(self, action_type, p_current, attenuation_level):
        state = self.pm.current_state
        is_alert = p_current >= (state.global_sensitivity / 100.0)
        return {"allowed": True, "is_alert": is_alert, "adjusted_attenuation": attenuation_level * (state.attenuation_preference / 50.0) if is_alert else attenuation_level, "policy_version": state.version}
