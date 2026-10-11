import pytest
from src.actuation.gateway import ActuatorGateway
from src.crypto.attestation import ActionAttestor

def test_authenticated_proposal_does_not_claim_physical_execution():
    key = b"k" * 32
    evidence = ActionAttestor(key).generate_attestation("ALLOW", 0.8, "state-1")
    assert ActuatorGateway(key).process_action_proposal(evidence) == (True, "AUTHENTICATED_PROPOSAL_ALLOW")

@pytest.mark.parametrize("evidence", [None, {}, {"payload": {"sequence_num": []}}, {"payload": {}, "signature": "é"}])
def test_malformed_proposal_rejected_without_crash(evidence):
    assert ActuatorGateway(b"k" * 32).process_action_proposal(evidence)[0] is False

def test_interlock_does_not_consume_unauthenticated_sequence():
    key = b"k" * 32
    gateway = ActuatorGateway(key)
    gateway.set_hardware_interlock(True)
    gateway.process_action_proposal({"payload": {"sequence_num": 1}, "signature": "forged"})
    gateway.set_hardware_interlock(False)
    signed = ActionAttestor(key).generate_attestation("ALLOW", 0.8, "state-1")
    assert gateway.process_action_proposal(signed)[0] is True

def test_nonfinite_attestation_is_not_authenticated():
    key = b"k" * 32
    signed = ActionAttestor(key).generate_attestation("ALLOW", float("nan"), "state-1")
    assert ActionAttestor.verify_attestation(signed, key) is False


@pytest.mark.parametrize("device_type,protocol", [
    ("vizio_tv", "vizio-smartcast-rest"),
    ("samsung_tv", "samsung-tizen-wss"),
    ("lg_tv", "lg-webos-wss"),
    ("sony_tv", "sony-bravia-rest"),
    ("generic", "device-agnostic"),
])
def test_legacy_payload_formatter_never_reports_dispatch(device_type, protocol):
    from src.bridges.universal_dispatch import UniversalDeviceDispatch

    dispatcher = UniversalDeviceDispatch()
    result = dispatcher.dispatch_command(device_type, "192.168.1.55", {})
    assert result["status"] == "NOT_EXECUTED"
    assert result["protocol"] == protocol
    assert dispatcher.record["192.168.1.55"]["status"] == "NOT_EXECUTED"


def test_legacy_driver_cannot_report_success_without_output(capsys):
    from src.engine.tv_drivers import TVDriver

    assert TVDriver.dispatch("ecp", "192.168.1.55", "lower_volume") is False
    assert "NOT_EXECUTED" in capsys.readouterr().out


def test_legacy_queue_does_not_log_unexecuted_proposal_as_action(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    # Isolate this historical module's import-time threads and database.
    script = """
import sqlite3
from src.engine.dispatch import cmd_queue, evt_queue, enqueue
enqueue('lower_volume', 'ecp', '192.168.1.55', 'synthetic_trigger')
cmd_queue.join()
evt_queue.join()
with sqlite3.connect('events.db') as db:
    assert db.execute('SELECT COUNT(*) FROM event_log').fetchone()[0] == 0
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "DISPATCH OK" not in result.stdout
    assert "NOT_EXECUTED" in result.stdout
