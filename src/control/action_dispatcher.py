from typing import Union, Dict, Any, Optional
from src.control.intent_firewall import IntentFirewall, AuthRejectionCode
from src.control.authorized_intent import SignedActionIntent
from src.control.capability_lease import SignedCapabilityLease
from state_logger import StateLogger


class ActionDispatcher:
    def __init__(self, firewall: Optional[IntentFirewall] = None, logger: Optional[StateLogger] = None):
        self.firewall = firewall
        self.logger = logger or StateLogger()

    def dispatch(
        self, 
        intent: SignedActionIntent, 
        lease: SignedCapabilityLease
    ) -> Dict[str, Any]:
        if self.firewall:
            validation_result = self.firewall.validate_intent(intent, lease)
            if isinstance(validation_result, AuthRejectionCode):
                log_payload = {
                    "event_type": "AUTH_FIREWALL_REJECTION",
                    "intent_id": intent.intent_id,
                    "device_id": intent.device_id,
                    "rejection_code": validation_result.value
                }
                try:
                    if hasattr(self.logger, "log_event"):
                        self.logger.log_event(log_payload)
                    elif hasattr(self.logger, "log"):
                        self.logger.log(log_payload)
                except Exception:
                    pass
                
                return {
                    "status": "REJECTED",
                    "code": validation_result.value,
                    "intent_id": intent.intent_id
                }
        
        return {
            "status": "EXECUTED",
            "intent_id": intent.intent_id,
            "operation": intent.operation,
            "parameters": intent.parameters
        }
