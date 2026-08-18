from src.voice.sensor_health import SensorHealthMonitor
from src.voice.feature_fabric import FeatureFabric
from src.voice.trust_router import TrustGradientRouter
from src.voice.predictive_horizon import PredictiveHorizon

class SpatialVoiceEngine:
    def __init__(self):
        self.health_monitor = SensorHealthMonitor()
        self.fabric = FeatureFabric()
        self.router = TrustGradientRouter()
        self.horizon = PredictiveHorizon()

    def process_frame(self, frame):
        health = self.health_monitor.inspect_frame(frame)
        if not health["healthy"]:
            return {
                "status": "FAULT_DETECTED",
                "fault_reason": health["status"],
                "route": "FAIL_SAFE_GATED",
                "confidence": 1.0
            }
        
        features = self.fabric.extract_features(frame)
        prediction = self.horizon.update_and_predict(features)
        decision = self.router.evaluate(features)
        
        return {
            "energy": features["energy"],
            "zero_crossings": features["zero_crossings"],
            "route": decision["route"],
            "confidence": decision["confidence"],
            "trajectory": prediction["trajectory"],
            "risk_score": prediction["risk_score"],
            "status": "processed"
        }
