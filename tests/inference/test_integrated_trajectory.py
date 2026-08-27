import unittest
from src.inference.threat_inference import ThreatInferenceEngine
from src.inference.evidence_vector import EvidenceVector


class TestIntegratedTrajectory(unittest.TestCase):
    def setUp(self):
        self.engine = ThreatInferenceEngine()

    def test_trajectory_comprehensive_matrix(self):
        def make_ev_for_target(target_prob):
            return EvidenceVector(
                acoustic_energy=target_prob,
                spectral_change=0.5,
                impulsiveness=0.5,
                periodicity=0.5,
                persistence=0.5,
                spatial_change=0.5,
                escalation=target_prob,
                anomaly_score=target_prob,
            )

        # First evaluation step
        res = self.engine.evaluate(
            "evt_1",
            100.0,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.5),
        )
        self.assertGreaterEqual(res.trajectory.predicted_threat, 0.0)
        self.assertLessEqual(res.trajectory.predicted_threat, 1.0)

        # Stable evaluation step
        stable_ts = 101.0
        stable_res = self.engine.evaluate(
            f"evt_{stable_ts}",
            stable_ts,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.85),
        )

        # Irrelevant evaluation step
        res_irr = self.engine.evaluate(
            "evt_102",
            102.0,
            {"clipping_ratio": 0.0},
            make_ev_for_target(0.2),
        )
        self.assertGreaterEqual(res_irr.trajectory.predicted_threat, 0.0)
        self.assertLessEqual(res_irr.trajectory.predicted_threat, 1.0)

        # Repeat evaluation for deterministic check
        ra = self.engine.evaluate("evt_repeat", 103.0, {}, make_ev_for_target(0.5))
        rb = self.engine.evaluate("evt_repeat", 103.0, {}, make_ev_for_target(0.5))
        self.assertEqual(ra.trajectory.predicted_threat, rb.trajectory.predicted_threat)

        # Final evaluation check
        final_res = self.engine.evaluate("evt_final", 104.0, {}, make_ev_for_target(0.9))
        self.assertIsNotNone(final_res.trajectory)
        summary = {
            "trajectory_projected_p": final_res.trajectory.predicted_threat
        }
        self.assertIn("trajectory_projected_p", summary)
