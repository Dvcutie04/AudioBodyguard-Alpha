import json
import sys
import os
import urllib.request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def load_config():
    try:
        with open('config/devices.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not read config/devices.json: {e}")
        return {"devices": []}

def pair_vizio(ip):
    print(f"[PAIR] Target Vizio TV at {ip}...")
    url = f"https://{ip}:7345/pairing/start"
    payload = json.dumps({"DEVICE_ID": "audio_bodyguard", "DEVICE_NAME": "Audio Bodyguard"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="PUT")
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx) as response:
            print(f"[SUCCESS] Vizio Pairing initiated on {ip}: {response.read().decode('utf-8')}")
    except Exception as e:
        print(f"[INFO] Vizio pairing status ({ip}): {e}")

def pair_all():
    cfg = load_config()
    devices = cfg.get("devices", [])
    print(f"[START] Verifying pairing status for {len(devices)} device(s)...")
    for dev in devices:
        proto = dev.get("protocol")
        ip = dev.get("ip")
        if proto == "smartcast":
            pair_vizio(ip)
        else:
            print(f"[READY] Protocol '{proto}' for {dev.get('name')} ready (IP: {ip}).")

if __name__ == "__main__":
    pair_all()
