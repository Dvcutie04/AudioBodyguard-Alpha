from datetime import datetime, timedelta, timezone
from src.device_fabric.contracts import CapabilityLease

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# Inside your fixture or setup function:
lease = CapabilityLease(
    lease_id="L_TEST_001",
    subject_id="gov_v1",
    device_id="dev_test_01",
    capabilities=frozenset(["SET_VOLUME", "SET_POWER"]),
    valid_from=utc_now(),
    expires_at=utc_now() + timedelta(minutes=5),
    authorized_epoch=100,
    max_world_state_age_ms=5000,
    max_clock_skew_ms=1000,
    nonce="nonce_999",
    lease_digest="mock_digest"
)
