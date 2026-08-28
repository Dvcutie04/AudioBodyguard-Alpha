import time
import pytest

from src.device_fabric.contracts import (
    AuthorizedActionIntent, CapabilityLease, DeviceState
)
from src.device_fabric.precondition import PreconditionEvaluator
from src.device_fabric.digital_twin import DigitalTwin
from src.device_fabric.transaction import PhysicalTransactionManager
from src.device_fabric.mocks.mock_tv import MockTVAdapter

@pytest.fixture
def hil_env():
    # Setup the physical commit layer ecosystem
    adapter = MockTVAdapter("tv_hil_target")
    evaluator = PreconditionEvaluator(staleness_threshold_seconds=2.0)
    twin = DigitalTwin()
    twin.register_constraint("tv_hil_target", lambda curr, target: target.volume <= 80.0)
    
    manager = PhysicalTransactionManager(adapter, evaluator, twin)
    
    # Establish baseline and target states
    pre_state = DeviceState(power=True, volume=50.0, input_source="HDMI_1")
    target = DeviceState(power=True, volume=44.0, input_source="HDMI_1", payload={"delta_db": 6.0})
    
    intent = AuthorizedActionIntent(
        intent_id="capstone_act_001",
        device_id="tv_hil_target",
        operation="REDUCE_VOLUME",
        target_state=target,
        expected_pre_state=pre_state,
        authorization_digest="auth_hash_capstone",
        deadline_at=time.time() + 5.0
    )
    
    lease = CapabilityLease(
        device_id="tv_hil_target",
        capability_digest="mock_cap_sha256_001",
        firmware_identity="1.0.0-mock",
        protocol_version="1.0",
        issued_at=time.time(),
        expires_at=time.time() + 30.0,
        nonce="nonce_capstone",
        issuer="gov_1"
    )
    
    return manager, adapter, intent, lease
