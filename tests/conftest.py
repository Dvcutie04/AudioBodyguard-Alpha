import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def hil_env():
    """Hardware-In-the-Loop test environment fixture for capstone tests."""
    manager = MagicMock(name="HILManager")
    adapter = MagicMock(name="HILAdapter")
    intent = MagicMock(name="AuthorizedActionIntent")
    lease = MagicMock(name="CapabilityLease")
    
    # Configure execute_transaction as an AsyncMock to allow 'await'
    manager.execute_transaction = AsyncMock(return_value=("FAILED_VERIFICATION", "Adversarial drift detected"))
    
    # Configure default attributes on intent and lease
    intent.nonce = "test-nonce-123"
    intent.expected_pre_state = MagicMock(name="DeviceState")
    lease.is_valid = MagicMock(return_value=True)
    
    return manager, adapter, intent, lease
