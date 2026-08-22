class ActionDispatcher:
    def __init__(self):
        self.action_log = []
        self.seen_sequences = set()

    def dispatch(self, envelope):
        if envelope.sequence_id in self.seen_sequences:
            return "NO_ACTION"
        self.seen_sequences.add(envelope.sequence_id)
        state = envelope.decision_state
        action = self._map_state_to_action(state, envelope)
        self.action_log.append((envelope.sequence_id, state, action))
        return action

    def _map_state_to_action(self, state, envelope):
        if state == "ESCALATE":
            return "TRIGGER_HIGH_PRIORITY_ALARM"
        elif state == "PERMIT_ESCALATION":
            return "LOG_AND_MONITOR"
        elif state == "AMBIGUOUS_EVIDENCE":
            return "REQUEST_SECONDARY_VALIDATION"
        elif state == "REDUCED_CONFIDENCE":
            return "SUPPRESS_OR_LOG_ONLY"
        elif state == "DEGRADED_STATE":
            return "FALLBACK_LOCAL_LOG"
        else:
            return "NO_ACTION"
