import json


class DeviceProfileManager:
    def __init__(self, storage_path="devices.json"):
        self.storage_path = storage_path
        self.devices = self.load_devices()

    def load_devices(self):
        try:
            with open(self.storage_path, "r") as storage:
                return json.load(storage)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_devices(self):
        with open(self.storage_path, "w") as storage:
            json.dump(self.devices, storage, indent=4)

    def register_device(self, name, device_type, ip_address):
        self.devices[name] = {"device_type": device_type.lower(), "ip": ip_address}
        self.save_devices()
        return {"status": "registered", "name": name}

    def get_device(self, name):
        return self.devices.get(name)

    def list_devices(self):
        return self.devices
