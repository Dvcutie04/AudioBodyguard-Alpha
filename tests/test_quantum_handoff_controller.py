from src.quantum.handoff_controller import QuantumHandoffController


def test_quantum_handoff_controller_initializes_local_proposal_state():
    controller = QuantumHandoffController()
    assert controller.state == "LOCAL"
    assert controller.enter == 0.8
    assert controller.exit == 0.5


def test_quantum_handoff_controller_preserves_configured_thresholds():
    controller = QuantumHandoffController(enter_threshold=0.9, exit_threshold=0.4)
    assert controller.state == "LOCAL"
    assert controller.enter == 0.9
    assert controller.exit == 0.4
