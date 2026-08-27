import unittest
from src.inference.threat_inference import ThreatInferenceEngine
from src.inference.evidence_envelope import EvidenceEnvelope


class TestIntegratedTrajectory(unittest.TestCase):
    def setUp(self):
        self.engine = ThreatInferenceEngine()

    def test_trajectory_comprehensive_matrix(self):
        def make_ev_for_target(target_prob, event_id, sequence):
            return EvidenceEnvelope(
                event_id=event_id,
                sequence=sequence,
                source_id="test_sensor",
                sensor_quality=0.9,
                feature_vector={"f1": target_prob},
                change_point_evidence=None,
                posterior_before=0.5,
                posterior_after=target_prob,
                timestamp=100.0,
            )

        # First evaluation step
        res = self.engine.evaluate(
            "evt_1",
            100.0,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.5, "evt_1", 1),
        )
        self.assertGreaterEqual(res.trajectory.predicted_threat, 0.0)
        self.assertLessEqual(res.trajectory.predicted_threat, 1.0)

        # Stable evaluation step
        stable_ts = 101.0
        stable_res = self.engine.evaluate(
            f"evt_{stable_ts}",
            stable_ts,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.85, f"evt_{stable_ts}", 2),
        )

        # Irrelevant evaluation step
        res_irr = self.engine.evaluate(
            "evt_102",
            102.0,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.2, "evt_102", 3),
        )
        self.assertGreaterEqual(res_irr.trajectory.predicted_threat, 0.0)
        self.assertLessEqual(res_irr.trajectory.predicted_threat, 1.0)

        # Repeat evaluation for deterministic check
        ra = self.engine.evaluate("evt_repeat", 103.0, {}, make_ev_for_target(0.5, "evt_repeat", 4))
        rb = self.engine.evaluate("evt_repeat", 103.0, {}, make_ev_for_target(0.5, "evt_repeat", 4))
        self.assertEqual(ra.trajectory.predicted_threat, rb.trajectory.predicted_threat)

        # Final evaluation check
        final_res = self.engine.evaluate("evt_final", 104.0, {}, make_ev_for_target(0.9, "evt_final", 5))
        self.assertIsNotNone(final_res.trajectory)
        summary = {
            "trajectory_projected_p": final_res.trajectory.predicted_threat
        }
        self.assertIn("trajectory_projected_p", summary)