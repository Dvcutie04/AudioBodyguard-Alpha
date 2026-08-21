import json
import urllib.request
import urllib.error
import ssl

class BaseTVController:
    def __init__(self, ip):
        self.ip = ip
    def power_on(self): raise NotImplementedError
    def power_off(self): raise NotImplementedError

class VizioTVController(BaseTVController):
    def __init__(self, ip, token=""):
        super().__init__(ip)
        self.token = token
        self.url = f"https://{ip}:7345"
    def _req(self, ep, payload):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(f"{self.url}{ep}", data=json.dumps(payload).encode(), method="PUT")
        req.add_header("Content-Type", "application/json")
        if self.token: req.add_header("AUTH", self.token)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=2.0) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"status": "error", "message": str(e)}
    def power_on(self): return self._req("/state/device/power_mode", {"PARAMETERS": {"POWER_STATE": 1}})
    def power_off(self): return self._req("/state/device/power_mode", {"PARAMETERS": {"POWER_STATE": 0}})

class SamsungTVController(BaseTVController):
    def power_on(self): return {"status": "dispatched", "brand": "samsung", "action": "POWER_ON"}
    def power_off(self): return {"status": "dispatched", "brand": "samsung", "action": "POWER_OFF"}

class LGWebOSTVController(BaseTVController):
    def power_on(self): return {"status": "dispatched", "brand": "lg", "action": "power_on"}
    def power_off(self): return {"status": "dispatched", "brand": "lg", "action": "power_off"}

class SonyBraviaTVController(BaseTVController):
    def power_on(self): return {"status": "dispatched", "brand": "sony", "action": "WakeUp"}
    def power_off(self): return {"status": "dispatched", "brand": "sony", "action": "PowerOff"}

class TCLRokuTVController(BaseTVController):\n    def __init__(self, ip):\n        super().__init__(ip)\n        self.url = f\"http://{ip}:8060\"\n    def _req(self, ep):\n        import urllib.request\n        try:\n            req = urllib.request.Request(f\"{self.url}{ep}\", data=b'', method=\"POST\")\n            with urllib.request.urlopen(req, timeout=2.0) as resp:\n                return {\"status\": \"dispatched\", \"brand\": \"tcl-roku\", \"code\": resp.code}\n        except Exception as e:\n            return {\"status\": \"error\", \"message\": str(e)}\n    def power_on(self): return self._req(\"/keypress/PowerOn\")\n    def power_off(self): return self._req(\"/keypress/PowerOff\")\n\nclass AmazonFireTVController(BaseTVController):\n    def __init__(self, ip):\n        super().__init__(ip)\n        self.ip = ip\n    def _adb(self, cmd):\n        import subprocess\n        try:\n            res = subprocess.run([\"adb\", \"connect\", self.ip], capture_files=False, capture_output=True, text=True, timeout=2.0)\n            if \"connected\" in res.stdout:\n                out = subprocess.run([\"adb\", \"-s\", self.ip, \"shell\", cmd], capture_output=True, text=True, timeout=2.0)\n                return {\"status\": \"dispatched\", \"brand\": \"firetv\", \"output\": out.stdout.strip()}\n            return {\"status\": \"error\", \"message\": \"ADB connection failed\"}\n        except Exception as e:\n            return {\"status\": \"error\", \"message\": str(e)}\n    def power_on(self): return self._adb(\"input keyevent KEYCODE_WAKEUP\")\n    def power_off(self): return self._adb(\"input keyevent KEYCODE_SLEEP\")\n\nclass RokuTVController(TCLRokuTVController):\n    pass\n\nclass TVControllerFactory:
    @staticmethod
    def get_controller(device_type, ip, **kw):
        dt = device_type.lower()
        if "vizio" in dt: return VizioTVController(ip, kw.get("token", ""))
        if "samsung" in dt: return SamsungTVController(ip)
        if "lg" in dt: return LGWebOSTVController(ip)
        if "sony" in dt: return SonyBraviaTVController(ip)
        raise ValueError(f"Unsupported brand: {device_type}")
