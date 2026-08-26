import unittest
from src.tv.tv_state_machine import TVState, TVVolumeStateMachine


class TestTVVolumeStateMachine(unittest.TestCase):

    def setUp(self):
        self.sm = TVVolumeStateMachine(
            enter_threshold=0.90,
            exit_threshold=0.65,
            candidate_dwell_ns=1_000_000_000,  # 1s
            recovery_dwell_ns=2_000_000_000,   # 2s
        )
        self.base_time = 1_000_000_000

    def test_normal_transition_flow(self):
        # 1. Program -> Candidate
        record = self.sm.process_input(0.92, 1, "digest_1", now_ns=self.base_time)
        self.assertEqual(self.sm.current_state, TVState.COMMERCIAL_CANDIDATE)
        self.assertIsNotNone(record)

        # 2. Candidate Dwell Check (Premature - under 1s)
        record = self.sm.process_input(0.92, 2, "digest_2", now_ns=self.base_time + 500_000_000)
        self.assertEqual(self.sm.current_state, TVState.COMMERCIAL_CANDIDATE)
        self.assertIsNone(record)

        # 3. Candidate -> Active (Dwell threshold met)
        record = self.sm.process_input(0.92, 3, "digest_3", now_ns=self.base_time + 1_100_000_000)
        self.assertEqual(self.sm.current_state, TVState.COMMERCIAL_ACTIVE)
        self.assertIsNotNone(record)

        # 4. Active -> Recovery
        record = self.sm.process_input(0.60, 4, "digest_4", now_ns=self.base_time + 2_000_000_000)
        self.assertEqual(self.sm.current_state, TVState.PROGRAM_RECOVERY)

        # 5. Recovery -> Program (Dwell threshold met)
        record = self.sm.process_input(0.60, 5, "digest_5", now_ns=self.base_time + 4_100_000_000)
        self.assertEqual(self.sm.current_state, TVState.PROGRAM)

    def test_hysteresis_prevents_volume_hunting(self):
        # Move to Candidate
        self.sm.process_input(0.91, 1, "digest_1", now_ns=self.base_time)
        
        # Immediate drop back below threshold resets to Program (no action taken)
        record = self.sm.process_input(0.89, 2, "digest_2", now_ns=self.base_time + 100_000_000)
        self.assertEqual(self.sm.current_state, TVState.PROGRAM)
        self.assertEqual(record.new_state, TVState.PROGRAM)


if __name__ == "__main__":
    unittest.main()
