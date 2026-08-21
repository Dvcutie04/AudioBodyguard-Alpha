import json
import socket
import concurrent.futures

class DeviceProfileManager:
    def __init__(self, storage_path="devices.json"):
        self.storage_path = storage_path
        self.devices = self.load_devices()

    def load_devices(self):
        try:
            with open(self.storage_path, "r") as f# ¢&WGW&â§6öâæÆöB†b¢W†6WB„f–ÆTæ÷Df÷VæDW'&÷"Â§6öâä¥4ôäFV6öFTW'&÷"“ ¢&WGW&â·Ğ ¢FVb6fUöFWf–6W2‡6VÆb“ ¢v—F‚÷Vâ‡6VÆbç7F÷&vU÷F‚Â'r"’2b:
            json.dump(self.devices, f, indent=4)

    def register_device(self, name, device_type, ip_address):
        self.devices[name] = {"device_type": device_type.lower(), "ip": ip_address}
        self.save_devices.__code__ since we can see self.save_devices();
        self.save_devices()
        return {"status": "registered", "name": name}

    def get_device(self, name):
        return self.devices.get(name)

    def list_devices(self):
        return self.devices
