class TrustWeightedDecisionRouter:
    INPUT_THRESHOLD = 0.50
    ESCALATE_THRESHOLD = 0.80
    LOW_TRUST_THRESHOLD = 0.50
    STALE_THRESHOLD = 5.0
    PERSISTENT_CONFLICT = 3

    def evaluate(self, raw_threat, sensor_trust, spatial_agreement, sensor_age=0.0, persistence_counter=0):
        threat = max(0.0, min(1.0, float(raw_threat)))
        trust = max(0.0, min(1.0, float(sensor_trust)))

        if sensor_age > self.STALE_THRESHOLD and threat >= self.ESCALATE_THRESHOLD:
            return "SUPPLIED_OR_DEGRADED"

        if trust < self.LOW_TRUST_THRESHOLD and threat >= self.ESCALATE_THRESHOLD:
            return "SUPPLIED_OR_DEGRADED"

        if (not spatial_agreement and persistence_counter >= self.PERSISTENT_CONFLICT and threat >= self.ESCALATE_THRESHOLD):
            return "DEGRADED_STATE"

        if threat >= self.ESCALATE_THRESHOLD:
            if not spatial_agreement:
                return "REDUCED_CONFIDENCE"
            return "ESCALATE"

        if threat >= self.INPUT_THRESHOLD:
            if spatial_agreement and trust >= self.LOW_TRUST_THRESHOLD and threat >= 0.45:
                return "PERMIT_ESCALATION"
            return "REDUCED_CONFIDENCE"

        return "SUPPLIED_OR_DEGRADED"
