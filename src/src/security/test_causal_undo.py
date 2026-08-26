from unittest import TestCase
from src.security.causal_undo import (
    EnvironmentalUndoManager,
    RollbackRequest,
    RequestOrigin,
    RollbackScope,
    SnapshotHasher
)

class TestCausalUndo(TestCase):
    def test_snapshot_creation_and_hashing(self):
        manager = EnvironmentalUndoManager()
        snap1 = manager.create_snapshot({"volume": 40}, {"mode": "auto"}, "ctx_hash_1")
        
        self.assertEqual(snap1.sequence, 1)
        self.assertIsNotNone(snap1.state_digest)
        
        expected_digest = SnapshotHasher.compute_digest(
            parent_digest="0" * 64,
            sequence=snap1.sequence,
            device_state=snap1.device_state,
            policy_state=snap1.policy_state,
            context_hash=snap1.context_hash
        )
        self.assertEqual(snap1.state_digest, expected_digest)

    def test_causal_lineage_validation(self):
        manager = EnvironmentalUndoManager()
        snap1 = manager.create_snapshot({"volume": 40}, {"mode": "auto"}, "ctx_hash_1")
        snap2 = manager.create_snapshot({"volume": 30}, {"mode": "auto"}, "ctx_hash_2")

        is_valid = manager.lineage_validator.validate_lineage(snap1, snap2)
        self.assertTrue(is_valid)

    def test_rollback_validation_rules(self):
        manager = EnvironmentalUndoManager()
        snap1 = manager.create_snapshot({"volume": 40}, {"mode": "auto"}, "ctx_hash_1")
        snap2 = manager.create_snapshot({"volume": 30}, {"mode": "auto"}, "ctx_hash_2")

        request = RollbackRequest(
            target_snapshot_id=snap1.snapshot_id,
            requested_by=RequestOrigin.USER,
            scope=RollbackScope.DEVICE,
            source_event_id="evt_test_01"
        )

        can_rollback = manager.rollback_validator.validate(request, snap1, snap2)
        self.assertTrue(can_rollback)

        invalid_request = RollbackRequest(
            target_snapshot_id=snap2.snapshot_id,
            requested_by=RequestOrigin.USER,
            scope=RollbackScope.DEVICE,
            source_event_id="evt_test_02"
        )
        self.assertFalse(manager.rollback_validator.validate(invalid_request, snap2, snap2))

if __name__ == "__main__":
    import unittest
    unittest.main()
