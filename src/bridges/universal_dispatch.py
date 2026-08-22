import unittest

class UniversalDeviceDispatch:
    def __init__(self):
        self.record = {}
    def dispatch_command(self, device_type, ip, payload):
        device_type = device_type.lower()
        if device_type == "vizio_tv":
            formatted_payload = {"KEYLIST": [{"CODESET": payload.get("codeset", 11), "CODE": payload.get("code", 1), "ACTION": "KEYPRESS"}]}
            endpoint = f"https://{ip}:7345/key_command/"
            protocol = "vizio-smartcast-rest"
        elif device_type == "samsung_tv":
            formatted_payload = {"method": "ms.remote.control", "params": {"Cmd": payload.get("cmd", "Click"), "DataOfCmd": payload.get("data", "KEY_VOLUP"), "Option": "false", "TypeOfRemote": "RemoteControlInput"}}
            endpoint = f"wss://{ip}:8002/api/v2/channels/samsung.remote.control"
            protocol = "samsung-tizen-wss"
        elif device_type == "lg_tv":
            formatted_payload = {"type": "request", "id": payload.get("id", 1), "uri": payload.get("uri", "ssap://audio/setVolume"), "payload": payload.get("params", {"volume": 15})}
            endpoint = f"wss://{ip}:3001"
            protocol = "lg-webos-wss"
        elif device_type == "sony_tv":
            formatted_payload = {"method": "setPowerStatus", "params": [{"status": payload.get("power", True)}], "id": 1, "version": "1.0"}
            endpoint = f"http://{ip}/sony/system"
            protocol = "sony-bravia-rest"
        else:
            formatted_payload = payload
            endpoint = ip
            protocol = "device-agnostic"
        self.record[ip] = {"status": "dispatched", "payload": formatted_payload}
        return {"status": "success", "target": endpoint, "protocol": protocol, "payload": formatted_payload}

class IFTTTWebhookIngestor:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
    def handle_webhook(self, event_data):
        device_type = event_data.get("value1", "generic")
        ip = event_data.get("value2", "127.0.0.1")
        payload = {"cmd": event_data.get("value3", "toggle")}
        return self.dispatcher.dispatch_command(device_type, ip, payload)

class TestIFTTTWebhookBridge(unittest.TestCase):
    def test_webhook_ingestion(self):
        dispatcher = UniversalDeviceDispatch()
        ingestor = IFTTTWebhookIngestor(dispatcher)
        mock_ifttt_packet = {"value1": "samsung_tv", "value2": "192.168.1.55", "value3": "KEY_MUTE"}
        result = ingestor.handle_webhook(mock_ifttt_packet)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["protocol"], "samsung-tizen-wss")

if __name__ == "__main__":
    unittest.main()
