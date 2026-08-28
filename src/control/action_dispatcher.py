"""
Action Dispatcher with Integrated State Logger

Handles secure dispatching of authorized action intents to underlying device fabric components.
"""

from typing import Tuple, Dict, Any, Optional
from src.control.authorized_intent import AuthorizedIntent


class StateLogger:
    def __init__(self):
        self.logs = []

    def log_dispatch(self, intent: AuthorizedIntent, result: bool):
        self.logs.append({
            "intent_id": getattr(intent, "intent_id", "unknown"),
            "target": getattr(intent, "target", "unknown"),
            "action": getattr(intent, "action", "unknown"),
            "success": result
        })


class ActionDispatcher:
    def __init__(self, fabric_router=None, logger: Optional[StateLogger] = None):
        self.fabric_router = fabric_router
        self.logger = logger or StateLogger()

    def dispatch(self, intent: AuthorizedIntent) -> Tuple[bool, str]:
        """
        Dispatches an authorized intent to the device fabric.
        Returns a tuple of (success_status, status_message).
        """
        if intent is None:
            return False, "INVALID_INTENT: Intent cannot be None"

        if hasattr(intent, "is_expired") and intent.is_expired():
            self.logger.log_dispatch(intent, False)
            return False, "EXPIRED_INTENT: Action authorization has expired"

        # Route execution to fabric if router exists
        if self.fabric_router:
            success, msg = self.fabric_router.execute(intent)
            self.logger.log_dispatch(intent, success)
            return success, msg

        # Default successful dispatch stub for dry-run / integration testing
        self.logger.log_dispatch(intent, True)
        return True, "DISPATCH_SUCCESS: Intent dispatched to execution target"
