"""
Unit tests for CausalTrustMesh node trust scoring, violation penalties, and quarantine triggers.
"""

import pytest
from src.security.causal_trust_mesh import CausalTrustMesh, NodeTrustProfile


def test_node_registration_and_initial_trust():
    mesh = CausalTrustMesh(trust_threshold=0.5)
    profile = mesh.register_node("node_alpha")
    
    assert profile.trust_score == 1.0
    assert profile.is_quarantined is False


def test_attestation_failure_quarantine_trigger():
    mesh = CausalTrustMesh(trust_threshold=0.5)
    mesh.register_node("node_beta")
    
    # Penalize trust down past 0.5 threshold
    mesh.record_attestation_failure("node_beta", severity=0.3)
    assert mesh.nodes["node_beta"].is_quarantined is False
    
    mesh.record_attestation_failure("node_beta", severity=0.3)
    assert mesh.nodes["node_beta"].trust_score == pytest.approx(0.4)
    assert mesh.nodes["node_beta"].is_quarantined is True


def test_consensus_trust_excludes_quarantined_nodes():
    mesh = CausalTrustMesh(trust_threshold=0.5)
    mesh.register_node("node_1")
    mesh.register_node("node_2")
    
    # Quarantine node_2
    mesh.record_attestation_failure("node_2", severity=0.6)
    
    consensus = mesh.evaluate_consensus_trust(["node_1", "node_2"])
    # Consensus should reflect only healthy node_1 (1.0)
    assert consensus == 1.0
