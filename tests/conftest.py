import pytest
from unittest.mock import MagicMock

@pytest.fixture
def hil_env():
    """Hardware-In-the-Loop test environment fixture for capstone tests."""
    manager = MagicMock(name="HILManager")
    adapter = MagicMock(name="HILAdapter")
    intent = MagicMock(name="AuthorizedActionIntent")
    lease = MagicMock(name="CapabilityLease")
    
    # Configure default mock attributes/behaviors as required by capstone tests
    intent.nonce = "test-nonce-123"
    lease.is_valid = MagicMock(return_value=True)
    
    return manager, adapter, intent, lease
