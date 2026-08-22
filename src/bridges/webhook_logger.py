import json
import urllib.request
import urllib.error

class IFTTTWebhookLogger:
    def __init__(self, event_name, webhook_key):
        self.event_name = event_name
        self.webhook_key = webhook_key
        self.url = f"https://maker.ifttt.com/trigger/{event_name}/with/key/{webhook_key}"

    def log_event(self, value1="", value2="", value3=""):
        payload = {"value1": value1, "value2": value2, "value3": value3}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return {"status": "success", "code": resp.code}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class WebhookManager:
    @staticmethod
    def get_logger(event_name, webhook_key):
        return IFTTTWebhookLogger(event_name, webhook_key)
