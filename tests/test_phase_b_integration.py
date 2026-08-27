import hashlib
import time
import unittest

from src.inference.gate import HypothesisGate
from src.inference.hypothesis import HypothesisFrame
from src.policy.governor import SafetyGovernor
from src.tv.tv_state_machine import TVState, TVVolumeStateMachine


class TestPhaseBIntegration(unittest.TestCase):

    def setUp(self):
        self.gate = HypothesisGate(min_probability=0.85, min_quality=0.80)
        self.governor = SafetyGovernor(max_allowed_db_drop=12.0)
        self.state_machine = TVVolumeStateMachine(
            enter_threshold=0.90,
            exit_threshold=0.65,
            candidate_dwell_ns=1_000_000_000,
            recovery_dwell_ns=2_000_000_000,
        )
        self.base_time = 1_000_000_000

    def test_end_to_end_hypothesis_to_state_transition(self):
        # 1. High probability commercial hypothesis constructed
        hypothesis = HypothesisFrame(
            hypothesis_id="hyp_201",
            hypothesis_type="COMMERCIAL_ACTIVE",
            hypothesis_probability=0.93,
            evidence_quality=0.88,
            model_confidence=0.95,
            evidence_window_ns=1_000_000_000,
            sequence_start=200,
            sequence_end=205,
            source_lineage_digest="digest_chain_root_abc123",
            model_version="v1.0.0",
            created_at_ns=self.base_time,
        )

        # 2. HypothesisGate processes hypothesis into ActionIntent
        intent = self.gate.evaluate(hypothesis)
        self.assertIsNotNone(intent)
        self.assertEqual(intent.intent_type, "REDUCE_TV_VOLUME")

        # 3. SafetyGovernor evaluates ActionIntent
        is_safe, reason = self.governor.evaluate_intent(intent)
        self.assertTrue(is_safe)
        self.assertEqual(reason, "SAFETY_PASSED")

        # 4. State Machine processes authorized signal -> Transitions to COMMERCIAL_CANDIDATE
        record_1 = self.state_machine.process_input(
            probability=hypothesis.hypothesis_probability,
            sequence_id=hypothesis.sequence_end,
            lineage_digest=intent.triggering_lineage_digest,
            now_ns=self.base_time,
        )
        self.assertEqual(self.state_machine.current_state, TVState.COMMERCIAL_CANDIDATE)
        self.assertIsNotNone(record_1)

        # 5. Dwell time elapses (1.1s later) -> Transitions to COMMERCIAL_ACTIVE
        record_2 = self.state_machine.process_input(
            probability=hypothesis.hypothesis_probability,
            sequence_id=hypothesis.sequence_end + 1,
            lineage_digest=intent.triggering_lineage_digest,
            now_ns=self.base_time + 1_100_000_000,
        )
        self.assertEqual(self.state_machine.current_state, TVState.COMMERCIAL_ACTIVE)
        self.assertIsNotNone(record_2)

        # Lineage Digest Consistency Verification
        self.assertEqual(record_2.trigger_lineage_digest, intent.triggering_lineage_digest)


if __name__ == "__main__":
    unittest.main()
