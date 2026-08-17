import json
from dataclasses import dataclass, field, asdict
from time import monotonic
from typing import Optional, Dict, Any

@dataclass
class IntentContext:
    intent: str
    entities: Dict[str, Any]
    zone_id: str
    created_at: float
    expires_at: float
    confidence: float
    state_fingerprint: Dict[str, Any] = field(default_factory=dict)

class IntentContinuityEngine:
    def __init__(self, context_ttl: float = 300.0):
        self.context_ttl = context_ttl
        self._context: Optional[IntentContext] = None

    def capture(self, intent: str, entities: Dict[str, Any], zone_id: str, confidence: float, state_fingerprint: Dict[str, Any]):
        now = monotonic()
        self._context = IntentContext(
            intent=intent,
            entities=entities,
            zone_id=zone_id,
            created_at=now,
            expires_at=now + self.context_ttl,
            confidence=confidence,
            state_fingerprint=state_fingerprint,
        )

    def resolve(self, new_input: str, current_environment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._expired():
            self.clear()
            return None
        if self._state_invalidated(current_environment):
            self.clear()
            return None
        return self._continue(new_input, current_environment)

    def on_zone_exit(self, zone_id: str):
        if self._context and self._context.zone_id == zone_id:
            self.clear()

    def _expired(self) -> bool:
        return self._context is None or monotonic() >= self._context.expires_at

    def _state_invalidated(self, current_environment: Dict[str, Any]) -> bool:
        if not self._context:
            return True
        for key, val in self._context.state_fingerprint.items():
            if current_environment.get(key) != val:
                return True
        return False

    def _continue(self, new_input: str, current_environment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._context:
            return None
        proposal = {
            "action": "PROPOSED_EXECUTION",
            "original_intent": self._context.intent,
            "continuation_input": new_input,
            "confidence": self._context.confidence,
            "target_zone": self._context.zone_id
        }
        return proposal


    def clear(self):
        self._context = None

if __name__ == '__main__':
    engine = IntentContinuityEngine(context_ttl=300.0)
    engine.capture(
        intent="adjust_temperature", 
        entities={"direction": "up"}, 
        zone_id="Living Room", 
        confidence=0.85, 
        state_fingerprint={"HVAC": "ON", "occupant_count": 1}
    )
    current_env = {"HVAC": "ON", "occupant_count": 1, "TV": "ON"}
    proposal = engine.resolve("increase_more", current_env)
    print("Valid Continuation Proposal:\n", json.dumps(proposal, indent=2))
    
    invalid_env = {"HVAC": "ON", "occupant_count": 0}
    proposal_invalid = engine.resolve("increase_more", invalid_env)
    print("\n[Invalidated by State Change Proposal]:", proposal_invalid)
    
    engine.capture("adjust_lights", {}, "Livingg Room", 0.90, {"lights": "dim"})
    engine.on_zone_exit("Living Room")
    print("\n[Context after Zone Exit]:", "Cleared" if engine._context is None else "Active")
