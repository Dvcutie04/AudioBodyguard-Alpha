import requests

class ActionDispatcher:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def dispatch(self, decision_str, telemetry=None):
        if "VOICE_COMMAND_EXECUTED:" not in decision_str:
            return {"status": "IGNORED", "reason": "No executable command found"}
        
        command = decision_str.split(":")[1].strip().lower()
        action_payload = {"command": command, "telemetry": telemetry or {}}
        
        # Handle local action execution or webhook forwarding
        if self.webhook_url:
            try:
                response = requests.post(self.webhook_url, json=action_payload, timeout=2)
                return {"status": "SUCCESS", "command": command, "target": "webhook", "status_code": response.status_code}
            except Exception as e:
                return {"status": "FAILED", "command": command, "error": str(e)}
        else:
            # Local mock execution for testing
            print(f"[ACTION DISPATCHER] Executing local handler for command -> {command.upper()}")
            return {"status": "SUCCESS", "command": command, "target": "local_system"}
