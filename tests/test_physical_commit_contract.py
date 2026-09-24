import importlib.util
from pathlib import Path


def load_contracts():
    path = Path("src/device_fabric/contracts.py")
    spec = importlib.util.spec_from_file_location("device_fabric_contracts_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_manager_is_quarantined():
    assert not Path("src/device_fabric/manager.py").exists()
    assert Path("src/device_fabric/quarantine/manager_legacy.py").exists()


def test_actuation_status_has_physical_lifecycle_states():
    c = load_contracts()
    names = {x.name for x in c.ActuationStatus}
    assert {"EXECUTED", "COMMITTED", "REJECTED", "FAILED"}.issubset(names)


def test_device_state_digest_is_deterministic():
    c = load_contracts()
    a = c.DeviceState(power=True, volume=25.0, muted=False, input_source="HDMI_2")
    b = c.DeviceState(power=True, volume=25.0, muted=False, input_source="HDMI_2")
    assert a.state_digest == b.state_digest


def test_authorized_intent_contains_commit_preconditions():
    c = load_contracts()
    fields = c.AuthorizedActionIntent.__dataclass_fields__
    assert "expected_pre_state" in fields
    assert "authorization_digest" in fields
    assert "deadline_at" in fields


def test_capability_lease_permits_declared_action_only():
    c = load_contracts()
    lease = c.CapabilityLease(capabilities=frozenset({"set_volume"}))
    assert lease.permits("set_volume")
    assert not lease.permits("set_power")


def test_receipt_can_distinguish_execution_from_commit():
    c = load_contracts()
    executed = c.ActuationReceipt(status=c.ActuationStatus.EXECUTED)
    committed = c.ActuationReceipt(status=c.ActuationStatus.COMMITTED)
    assert executed.status != committed.status

def test_physical_verification_record_binds_commit_evidence():
    c = load_contracts()
    assert hasattr(c, "PhysicalVerificationRecord")
    fields = c.PhysicalVerificationRecord.__dataclass_fields__
    required = {
        "intent_id",
        "device_id",
        "receipt_id",
        "expected_state_digest",
        "observed_state_digest",
        "verification_status",
    }
    assert required.issubset(fields)

def test_physical_verification_record_is_exported_by_device_fabric_package():
    import src.device_fabric as df
    assert hasattr(df, "PhysicalVerificationRecord")
    assert "PhysicalVerificationRecord" in df.__all__

def test_physical_verification_record_binds_authorization_lineage():
    c = load_contracts()
    fields = c.PhysicalVerificationRecord.__dataclass_fields__
    required = {
        "authorization_digest",
        "transaction_id",
        "capability_digest",
    }
    assert required.issubset(fields)


def test_legacy_authorize_and_execute_is_deprecated_or_production_isolated():
    bridge=Path("src/control/device_fabric_bridge.py").read_bytes()
    legacy_marked=(b"legacy" in bridge.lower() or b"deprecated" in bridge.lower())
    production_callers=[]
    needle=b"authorize_and_execute("
    for path in Path("src").rglob("*.py"):
        if path.as_posix()=="src/control/device_fabric_bridge.py":
            continue
        if needle in path.read_bytes():
            production_callers.append(path.as_posix())
    assert legacy_marked or production_callers==[], (
        "authorize_and_execute must be explicitly legacy/deprecated or have no production callers: "
        + repr(production_callers)
    )
