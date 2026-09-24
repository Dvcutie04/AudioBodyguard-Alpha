from src.device_fabric.contracts import CapabilityLease


def test_lease_digest_binds_max_world_state_age_ms():
    strict=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000)
    permissive=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=5000)
    assert strict.lease_digest != permissive.lease_digest


def test_lease_digest_binds_max_clock_skew_ms():
    strict=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500)
    permissive=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=2000)
    assert strict.lease_digest != permissive.lease_digest


def test_lease_digest_binds_capabilities():
    volume=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}))
    power=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_power"}))
    assert volume.lease_digest != power.lease_digest


def test_lease_digest_canonicalizes_equivalent_capability_sets():
    a=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=["set_volume","set_power"])
    b=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_power","set_volume"}))
    assert a.lease_digest == b.lease_digest


def test_lease_digest_binds_granted_actions():
    volume=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset(),granted_actions=["set_volume"])
    power=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset(),granted_actions=["set_power"])
    assert volume.lease_digest != power.lease_digest


def test_lease_digest_binds_valid_from():
    from datetime import datetime,timezone
    early=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime.fromtimestamp(100.0,timezone.utc))
    late=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime.fromtimestamp(200.0,timezone.utc))
    assert early.lease_digest != late.lease_digest


def test_lease_digest_binds_expires_at():
    from datetime import datetime,timezone
    short=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),expires_at=datetime.fromtimestamp(200.0,timezone.utc))
    long=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),expires_at=datetime.fromtimestamp(300.0,timezone.utc))
    assert short.lease_digest != long.lease_digest


def test_lease_digest_canonicalizes_equivalent_valid_from_instants():
    from datetime import datetime,timezone,timedelta
    a=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime(1970,1,1,0,1,40,tzinfo=timezone.utc))
    b=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime(1970,1,1,1,1,40,tzinfo=timezone(timedelta(hours=1))))
    assert a.lease_digest == b.lease_digest


def test_lease_digest_canonicalizes_equivalent_expires_at_instants():
    from datetime import datetime,timezone,timedelta
    a=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),expires_at=datetime(1970,1,1,0,5,0,tzinfo=timezone.utc))
    b=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),expires_at=datetime(1970,1,1,1,5,0,tzinfo=timezone(timedelta(hours=1))))
    assert a.lease_digest == b.lease_digest


def test_lease_digest_rejects_naive_valid_from():
    import pytest
    from datetime import datetime
    lease=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime(1970,1,1,0,1,40))
    with pytest.raises(ValueError,match="timezone-aware"):
        _=lease.lease_digest


def test_lease_digest_rejects_naive_expires_at():
    import pytest
    from datetime import datetime
    lease=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),expires_at=datetime(1970,1,1,0,5,0))
    with pytest.raises(ValueError,match="timezone-aware"):
        _=lease.lease_digest


def test_lease_digest_rejects_reversed_validity_interval():
    import pytest
    from datetime import datetime,timezone
    lease=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=datetime.fromtimestamp(300.0,timezone.utc),expires_at=datetime.fromtimestamp(200.0,timezone.utc))
    with pytest.raises(ValueError,match="validity window"):
        _=lease.lease_digest


def test_lease_digest_rejects_zero_duration_validity_interval():
    import pytest
    from datetime import datetime,timezone
    t=datetime.fromtimestamp(200.0,timezone.utc)
    lease=CapabilityLease(lease_id="lease_1",subject_id="subject_1",object_id="object_1",device_id="device_1",authorized_epoch=7,nonce="nonce_1",max_world_state_age_ms=1000,max_clock_skew_ms=500,capabilities=frozenset({"set_volume"}),valid_from=t,expires_at=t)
    with pytest.raises(ValueError,match="validity window"):
        _=lease.lease_digest
