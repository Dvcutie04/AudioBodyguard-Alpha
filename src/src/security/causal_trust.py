class CausalTrustEvaluator:
    def __init__(self, weight_freshness=0.3, weight_sensor=0.3, weight_history=0.4):
        self.w_f = weight_freshness
        self.w_s = weight_sensor
        self.w_h = weight_history

    def evaluate(self, freshness_score: float, sensor_quality: float, historical_consistency: float) -> float:
        score = (self.w_f * max(0.0, min(1.0, freshness_score))) + \
                (self.w_s * max(0.0, min(1.0, sensor_quality))) + \
                (self.w_h * max(0.0, min(1.0, historical_consistency)))
        return round(max(0.0, min(1.0, score)), 4)
