class ChangePointEvidence:
    def __init__(self, detected=False, magnitude=0.0, direction=0.0, persistence=0.0, confidence=1.0):
        for val, name in [(magnitude, 'magnitude'), (direction, 'direction'), (persistence, 'persistence'), (confidence, 'confidence')]:
            if val is not None and isinstance(val, float) and val != val:
                raise ValueError('NaN values are not allowed')
        if not (0.0 <= magnitude <= 1.0) or not (0.0 <= persistence <= 1.0) or not (0.0 <= confidence <= 1.0):
            raise ValueError('Out of bounds values')
        self.detected = detected
        self.magnitude = magnitude
        self.direction = direction
        self.persistence = persistence
        self.confidence = confidence

class BayesianAdapter:
    def __init__(self, base_prior=0.1):
        self.base_prior = base_prior

    def fuse(self, prior, evidence, sensor_quality=1.0):
        for val, name in [(prior, 'prior'), (evidence.magnitude, 'magnitude'), (evidence.persistence, 'persistence'), (evidence.confidence, 'confidence'), (sensor_quality, 'sensor_quality')]:
            if val is not None and isinstance(val, float) and val != val:
                raise ValueError('NaN values not allowed')
        if not (0.0 <= evidence.magnitude <= 1.0) or not (0.0 <= evidence.persistence <= 1.0) or not (0.0 <= evidence.confidence <= 1.0):
            raise ValueError('Out of bounds')
        if not evidence.detected:
            return prior
        adjustment = evidence.magnitude * evidence.persistence * evidence.confidence * sensor_quality
        if evidence.direction > 0:
            posterior = prior * (1.0 - 0.5 * adjustment)
        else:
            posterior = prior + (1.0 - prior) * 0.5 * adjustment
        return max(0.0, min(1.0, posterior))
