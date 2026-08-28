"""
Unit tests for SensorObservation cryptographic verification and timestamp drift controls.
"""

import time
import pytest
from src.telemetry.telemetry_node import SensorObservation


def test_valid_telemetry_observation_passes():
    node_key = b"node_secret_key_99"
    now = time.time()
    
    obs = SensorObservation(
        node_id="acoustic_node_01",
        timestamp=now,
        ambient_db=64.5,
        frequency_spectrum={"low": 12.0, "mid": 45.0, "high": 7.5},
        epoch=101,
        nonce="n_9901"
    )
    obs.sign_observation(node_key)
    
    assert obs.verify_integrity(node_key) is True


def test_tampered_telemetry_db_fails():
    node_key = b"node_secret_key_99"
    now = time.time()
    
    obs = SensorObservation(
        node_id="acoustic_node_01",
        timestamp=now,
        ambient_db=64.5,
        epoch=101,
        nonce="n_9901"
    )
    obs.sign_observation(node_key)
    
    # Adversarial tampering of observed noise level
    obs.ambient_db = 30.0
    assert obs.verify_integrity(node_key) is False


def test_stale_telemetry_timestamp_fails():
    node_key = b"node_secret_key_99"
    stale_time = time.time() - 10.0  # 10 seconds in the past
    
    obs = SensorObservation(
        node_id="acoustic_node_01",
        timestamp=stale_time,
        ambient_db=64.5,
        epoch=101,
        nonce="n_9901"
    )
    obs.sign_observation(node_key)
    
    # Timestamp skew exceeds max threshold (5.0s default)
    assert obs.verify_integrity(node_key) is False
