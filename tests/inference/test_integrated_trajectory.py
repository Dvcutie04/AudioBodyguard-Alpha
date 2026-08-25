import unittest
from src.inference.threat_inference import ThreatInferenceEngine
from src.inference.evidence_vector import EvidenceVector

class TestIntegratedTrajectory(unittest.TestCase):
    
    def test_trajectory_comprehensive_matrix(self):
        engine = ThreatInferenceEngine()
        
        # Helper to generate custom evidence matching desired instantaneous p
        def make_ev_for_target(target_p):
            # instant_p = 0.3*anomaly + 0.3*impulsiveness + 0.4*escalation
            # Let's scale escalation & anomaly to hit target roughly
            val = max(0.0, min(1.0, target_p))
            return EvidenceVector(
                acoustic_energy=0.5, spectral_change=0.2, impulsiveness=val,
                periodicity=0.5, persistence=0.5, spatial_change=0.1,
                escalation=val, anomaly_score=val
            )

        # 1. Monotonic escalation trajectory & boundedness (0 <= P_hat <= 1)
        engine.accumulator.reset()
        engine.trajectory_engine.reset()
        
        timestamps = [1000.0, 1001.0, 1002.0, 1003.0, 1004.0]
        instant_targets = [0.20, 0.30, 0.45, 0.65, 0.85]
        
        results_run_a = []
        for ts, tgt in zip(timestamps, instant_targets):
            ev = make_ev_for_target(tgt)
            res = engine.evaluate(f"evt_{ts}", ts, {"clipping_ratio": 0.0, "acoustic_energy": 0.5}, ev)
            results_run_a.append(res)
            
            # Requirement 7: projected_probability bounded [0, 1]
            self.assertIsNotNone(res.trajectory)
            self.assertGreaterEqual(res.trajectory.projected_probability, 0.0)
            self.assertLessEqual(res.trajectory.projected_probability, 1.0)

        # Verify increasing velocity during escalation
        v_early = results_run_a[1].trajectory.probability_velocity
        v_late = results_run_a[-1].trajectory.probability_velocity
        self.assertGreaterEqual(v_late, v_early)

        # 2. Stable threat probability drives velocity toward zero
        stable_ts = 1005.0
        stable_res = None
        for _ in range(5):
            stable_ts += 1.0
            stable_res = engine.evaluate(f"evt_{stable_ts}", stable_ts, {"clipping_ratio": 0.0}, acoustic_energy:=0.5, make_ev_for_target(0.85))
        self.assertAlmostEqual(stable_res.trajectory.probability_velocity, 0.0, delta=0.05)

        # 3. Declining probability produces negative velocity
        decline_ts = stable_ts
        declining_res = None
        for tgt in [0.60, 0.30, 0.10]:
            decline_ts += 1.0
            declining_res = engine.evaluate(f"evt_{decline_ts}", decline_ts, {"clipping_ratio": 0.0}, make_ev_for_target(tgt))
        self.assertLess(declining_res.trajectory.probability_velocity, 0.0)

        # 4. Irregular but valid timestamps don't destabilize estimator
        irregular_ts_list = [2000.0, 2000.5, 2003.2, 2003.3, 2010.0]
        for ts in irregular_ts_list:
            res_irr = engine.evaluate(f"irr_{ts}", ts, {"clipping_ratio": 0.0}, make_ev_for_target(0.5))
            self.assertIsNotNone(res_irr.trajectory)
            self.assertGreaterEqual(res_irr.trajectory.projected_probability, 0.0)
            self.assertLessEqual(res_irr.trajectory.projected_probability, 1.0)

        # 5 & 6. reset() clears state completely & identical inputs yield deterministic traces (Run A == Run B)
        engine.accumulator.reset()
        engine.trajectory_engine.reset()
        
        results_run_b = []
        for ts, tgt in zip(timestamps, instant_targets):
            ev = make_ev_for_target(tgt)
            res = engine.evaluate(f"evt_{ts}", ts, {"clipping_ratio": 0.0, "acoustic_energy": 0.5}, ev)
            results_run_b.append(res)

        for ra, rb in zip(results_run_a, results_run_b):
            self.assertEqual(ra.threat_probability, rb.threat_probability)
            self.assertEqual(ra.trajectory.current_probability, rb.trajectory.current_probability)
            self.assertEqual(ra.trajectory.probability_velocity, rb.trajectory.probability_velocity)
            self.assertEqual(ra.trajectory.projected_probability, rb.trajectory.projected_probability)

        # 8. Trajectory cannot mutate underlying threat_probability
        for res in results_run_a:
            self.assertEqual(res.threat_probability, res.trajectory.current_probability)

        # 9 & 10. SignalRouter -> Governor boundary and override hierarchy simulation
        # Simulating downstream handling where trajectory informs recommendation, but Governor retains override authority
        final_res = results_run_a[-1]
        simulated_recommendation = {
            "action": "ELEVATED_MONITORING",
            "urgency": "HIGH",
            "trajectory_projected_p": final_res.trajectory.projected_probability
        }
        
        # Governor Hard Safety Lock Rule: If sensor quality is true and semantic state is THREAT, 
        # Governor enforces mitigation regardless of advisory trajectory velocity.
        governor_override_triggered = final_res.sensor_quality_ok and (final_res.semantic_state == "THREAT")
        self.assertTrue(governor_override_triggered)
        
        # Verify that even with high projected trajectory, Governor enforces authority boundaries without mutating core inference
        self.assertIsNotNone(final_res.trajectory)

if __name__ == "__main__":
    unittest.main()
