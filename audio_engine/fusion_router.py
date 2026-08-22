class TrustWeightedDecisionRouter:
    INPUT_THRESHOLD = 0.50
    ESCALATE_THRESHOLD = 0.80
    LOW_TRUST_THRESHOLD = 0.50
    STALE_THRESHOLD = 5.0
    PERSISTENT_CONFLICT = 3

    def evaluate(self, raw_threat, sensor_trust, spatial_agreement=1.0, sensor_age=0.0, persistence_counter=0):
        threat = max(0.0, min(1.0, float(raw_threat)))
        trust = max(0.0, min(1.0, float(sensor_trust)))
        spatial = max(0.0, min(1.0, float(spatial_agreement)))

        if sensor_age > self.STALE_THRESHOLD and threat >= self.ESCALATE_THRESHOLD:
            return "SUPPLIED_OR_DEGRADED"

        if trust < self.LOW_TRUST_THRESHOLD and threat >= self.ESCALATE_THRESHOLD:
            return "SUPPLIED_OR_DEGRADED"

        if spatial < 0.3 and persistence_counter >= self.PERSISTENT_CONFLICT and threat >= self.ESCALATE_THRESHOLD:
            return "DEGRADED_STATE"

        if threat >= self.ESCALATE_THRESHOLD:
            if spatial < 0.5:
                return "AMBIGUOUS_EVIDENCE" if spatial >= 0.3 else "REDUCED_CONFIDENCE"
            return "ESCALATE"

        if threat >= self.INPUT_THRESHOLD:
            if spatial >= 0.5 and trust >= self.LOW_TRUST_THRESHOLD:
                return "PERMIT_ESCALATION"
            return "AMBIGUOUS_EVIDENCE"

        return "SUPPLIED_OR_DEGRADED"
