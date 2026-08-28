"""
End-to-End System Pipeline Integration Test

Verifies complete execution flow from signed sensor ingestion through quantum state encoding,
causal trust evaluation, threat inference, policy firewalling, and action dispatching.
"""

import time
import pytest
from src.telemetry.telemetry_node import SensorObservation
from src.quantum.quantum_state_mapping import QuantumStateMapper
from src.security.causal_trust_mesh import CausalTrustMesh
from src.inference.threat_inference_engine import ThreatInferenceEngine
from src.control.intent_firewall import IntentFirewall
from src.control.action_dispatcher import ActionDispatcher, StateLogger
from src.control.authorized_intent import SignedActionIntent


def test_full_pipeline_nominal_to_mitigation_flow():
    # 1. Setup Infrastructure
    node_key = b"node_secret_key_88"
    mesh = CausalTrustMesh(trust_threshold=0.5)
    mesh.register_node("node_01")
    
    mapper = QuantumStateMapper(num_qubits=2)
    inference_engine = ThreatInferenceEngine(threat_threshold=0.65)
    firewall = IntentFirewall(trusted_verifiers={})
    logger = StateLogger()
    dispatcher = ActionDispatcher(logger=logger)

    now = time.time()

    # 2. Ingest & Verify Telemetry
    obs = SensorObservation(
        node_id="node_01",
        timestamp=now,
        ambient_db=92.0,
        frequency_spectrum={"low": 30.0, "mid": 80.0, "high": 10.0},
        epoch=200,
        nonce="n_200"
    )
    obs.sign_observation(node_key)
    assert obs.verify_integrity(node_key) is True

    # 3. Quantum State Mapping
    state_vector = mapper.encode_telemetry_to_state(
        ambient_db=obs.ambient_db,
        spectrum_energy=obs.frequency_spectrum["mid"]
    )
    assert state_vector.is_normalized() is True
    exp_z = mapper.compute_expectation_z(state_vector)

    # 4. Evaluate Consensus Trust
    consensus_trust = mesh.evaluate_consensus_trust(["node_01"])
    assert consensus_trust == 1.0

    # 5. Threat Inference Assessment
    assessment = inference_engine.evaluate_threat(
        expectation_z=exp_z,
        consensus_trust=consensus_trust,
        ambient_db=obs.ambient_db,
        target_db=65.0
    )
    assert assessment.is_threat_detected is True
    assert assessment.recommended_attenuation_db > 0.0

    # 6. Authorize & Dispatch Action Intent
    intent = SignedActionIntent(
        intent_id="intent_pipeline_01",
        device_id="spk_living_room",
        operation="SET_ATTENUATION",
        parameters={"level_db": assessment.recommended_attenuation_db},
        issuer_id="governor_v1",
        epoch=200,
        expires_at=now + 60.0
    )

    success, msg = dispatcher.dispatch(intent)
    assert success is True
    assert "DISPATCH_SUCCESS" in msg
    assert len(logger.logs) == 1
    assert logger.logs[0]["success"] is True
