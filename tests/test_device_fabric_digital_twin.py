import pytest
from src.device_fabric.contracts import DeviceState
from src.device_fabric.digital_twin import DigitalTwin


@pytest.fixture
def twin():
    t = DigitalTwin()
    
    # 1. Absolute Acoustic Threshold (e.g., never exceed 80 dB/volume)
    def max_volume_constraint(current: DeviceState, target: DeviceState) -> bool:
        return target.volume <= 80.0
        
    # 2. Rate-of-Change Constraint (e.g., don't jump more than 20 points at once)
    def safe_delta_constraint(current: DeviceState, target: DeviceState) -> bool:
        return abs(target.volume - current.volume) <= 20.0
        
    # 3. Logical Dependency (e.g., cannot change volume if power is Off)
    def power_dependency_constraint(current: DeviceState, target: DeviceState) -> bool:
        if not target.power and target.volume != current.volume:
            return False
        return True

    t.register_constraint("tv_living_room", max_volume_constraint)
    t.register_constraint("tv_living_room", safe_delta_constraint)
    t.register_constraint("tv_living_room", power_dependency_constraint)
    
    return t


def test_digital_twin_allows_valid_transition(twin):
    current = DeviceState(power=True, volume=50.0)
    target = DeviceState(power=True, volume=65.0)  # +15 delta (under 20), below 80 max
    
    assert twin.validate_transition("tv_living_room", current, target) is True


def test_digital_twin_blocks_absolute_threshold_violation(twin):
    current = DeviceState(power=True, volume=70.0)
    target = DeviceState(power=True, volume=85.0)  # Exceeds 80.0 max limit
    
    assert twin.validate_transition("tv_living_room", current, target) is False


def test_digital_twin_blocks_rate_of_change_violation(twin):
    current = DeviceState(power=True, volume=30.0)
    target = DeviceState(power=True, volume=60.0)  # +30 delta (exceeds 20 max jump)
    
    assert twin.validate_transition("tv_living_room", current, target) is False


def test_digital_twin_blocks_logical_impossibility(twin):
    current = DeviceState(power=False, volume=30.0)
    target = DeviceState(power=False, volume=40.0)  # Trying to adjust volume while powered off
    
    assert twin.validate_transition("tv_living_room", current, target) is False


def test_digital_twin_allows_unregistered_devices(twin):
    current = DeviceState(power=True, volume=99.0)
    target = DeviceState(power=True, volume=100.0)
    
    # If no constraints are registered for a device, it implicitly passes bounds checks
    assert twin.validate_transition("unknown_device_001", current, target) is True
