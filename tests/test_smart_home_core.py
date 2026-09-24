import json

from src.bridges.smart_home_core import DeviceProfileManager


def test_device_profiles_persist_and_reload(tmp_path):
    storage = tmp_path / "devices.json"
    manager = DeviceProfileManager(storage)
    assert manager.list_devices() == {}
    assert manager.register_device("Living Room TV", "SAMSUNG_TV", "192.168.1.101") == {"status": "registered", "name": "Living Room TV"}
    expected = {"device_type": "samsung_tv", "ip": "192.168.1.101"}
    assert manager.get_device("Living Room TV") == expected
    assert DeviceProfileManager(storage).list_devices() == {"Living Room TV": expected}
    assert json.loads(storage.read_text(encoding="utf-8")) == {"Living Room TV": expected}


def test_invalid_profile_storage_fails_safe_to_empty(tmp_path):
    storage = tmp_path / "devices.json"
    storage.write_text("not-json", encoding="utf-8")
    assert DeviceProfileManager(storage).list_devices() == {}
