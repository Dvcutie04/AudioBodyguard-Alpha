import pytest
from src.device_fabric.lineage import CryptographicLineageManager


def test_lineage_records_events_with_correct_hashes():
    manager = CryptographicLineageManager()
    
    evt1 = manager.record_event("tx_1", "TX_COMMITTED", {"volume": 44.0})
    assert evt1.previous_hash == manager._genesis_hash
    assert evt1.event_hash is not None
    
    evt2 = manager.record_event("tx_2", "TX_ROLLED_BACK", {"reason": "verify_failed"})
    assert evt2.previous_hash == evt1.event_hash
    assert evt2.event_hash is not None


def test_lineage_verify_chain_integrity_success():
    manager = CryptographicLineageManager()
    manager.record_event("tx_1", "TX_COMMITTED", {"volume": 44.0})
    manager.record_event("tx_2", "TX_COMMITTED", {"volume": 30.0})
    manager.record_event("tx_3", "DRIFT_DETECTED", {"expected": 30.0, "observed": 55.0})
    
    assert manager.verify_chain_integrity() is True


def test_lineage_detects_payload_tampering():
    manager = CryptographicLineageManager()
    manager.record_event("tx_1", "TX_COMMITTED", {"volume": 44.0})
    manager.record_event("tx_2", "TX_COMMITTED", {"volume": 30.0})
    
    # Simulating an unauthorized modification of historical data
    # (e.g., trying to hide that the volume was set to 44.0)
    manager._chain[0].payload["volume"] = 99.0
    
    # The integrity check MUST catch the mismatch between the payload and the frozen hash
    assert manager.verify_chain_integrity() is False


def test_lineage_detects_linkage_tampering():
    manager = CryptographicLineageManager()
    manager.record_event("tx_1", "TX_COMMITTED", {"volume": 44.0})
    manager.record_event("tx_2", "TX_COMMITTED", {"volume": 30.0})
    manager.record_event("tx_3", "TX_COMMITTED", {"volume": 20.0})
    
    # Simulating a severed chain or replaced event
    manager._chain[2].previous_hash = "tampered_hash_123"
    
    # The integrity check MUST catch the broken pointer
    assert manager.verify_chain_integrity() is False
