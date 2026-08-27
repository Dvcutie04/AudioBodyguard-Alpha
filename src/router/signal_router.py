from dataclasses import dataclass

@dataclass
class SignalState:
    threat_probability: float
    confidence: float
    inference_level: str
    recommended_policy: str


# Inside the SignalRouter class, append this method:
def route(self, inference_result):
    threat_prob = inference_result.threat_probability
    
    if threat_prob >= 0.8:
        inference_level = "CRITICAL"
    elif threat_prob >= 0.6:
        inference_level = "HIGH"
    elif threat_prob >= 0.4:
        inference_level = "ELEVATED"
    else:
        inference_level = "UNKNOWN"
        
    policy_map = {
        "CRITICAL": "IMMEDIATE_MITIGATION",
        "HIGH": "ACTIVE_MONITORING",
        "ELEVATED": "ELEVATED_MONITORING",
        "UNKNOWN": "LOG_ONLY"
    }
    
    return SignalState(
        threat_probability=threat_prob,
        confidence=0.95,
        inference_level=inference_level,
        recommended_policy=policy_map[inference_level]
    )
