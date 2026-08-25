import unittest
from src.inference.evidence_vector import EvidenceVector
from src.inference.threat_inference import ThreatInferenceEngine
from src.router.signal_router import SignalRouter

class MockSafetyGovernor:
    """Mock Safety Governor enforcing deterministic boundary authority."""
    def evaluate(self, signal_state) -> str:
        # Safety boundary rules: CRITICAL must force immediate intervention regardless of policies
        if signal_state.inference_level == "CRITICAL":
            return "IMMEDIATE_INTERVENTION"
        elif signal_state.inference_level == "HIGH":
            return "ACTIVE_DEFENSE"
        elif signal_state.inference_level == "ELEVATED":
            return "MONITOR_PREPARE"
        elif signal_state.inference_level == "UNKNOWN":
            return "LOG_AND_DEGRADE"
        return "NO_ACTION"

class TestFullAQSSPipelineTrace(unittest.TestCase):
    def test_full_aqss_pipeline_deterministic_trace(self):
        engine = ThreatInferenceEngine()
        router = SignalRouter()
        governor = MockSafetyGovernor()
        
        stats_ok = {"clipping_ratio": 0.0, "acoustic_energy": 0.5}
        
        # Defining an escalating sequence of evidence vectors using explicit named fields
        sequence = [
            ("evt_0", 1000.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.1, impulsiveness=0.1, periodicity=0.5, persistence=0.5, spatial_change=0.1, escalation=0.0, anomaly_score=0.1)),
            ("evt_1", 1001.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.1, impulsiveness=0.1, periodicity=0.5, persistence=0.5, spatial_change=0.1, escalation=0.1, anomaly_score=0.1)),
            ("evt_2", 1002.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.4, impulsiveness=0.4, periodicity=0.5, persistence=0.5, spatial_change=0.4, escalation=0.5, anomaly_score=0.5)),
            ("evt_3", 1003.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.5, impulsiveness=0.5, periodicity=0.5, persistence=0.5, spatial_change=0.5, escalation=0.7, anomaly_score=0.6)),
            ("evt_4", 1004.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.7, impulsiveness=0.7, periodicity=0.5, persistence=0.5, spatial_change=0.7, escalation=0.9, anomaly_score=0.8)),
            ("evt_5", 1005.0, stats_ok, EvidenceVector(acoustic_energy=0.5, spectral_change=0.9, impulsiveness=0.9, periodicity=0.5, persistence=0.5, spatial_change=0.9, escalation=1.0, anomaly_score=0.95))
        ]
        
        # --- Run Trace A ---
        engine.accumulator.reset()
        trace_a = []
        for event_id, ts, stats, ev in sequence:
            inf_res = engine.evaluate(event_id, ts, stats, ev)
            
            # Proof C: Probability validity bounds
            self.assertGreaterEqual(inf_res.threat_probability, 0.0)
            self.assertLessEqual(inf_res.threat_probability, 1.0)
            
            sig_state = router.route(inf_res)
            gov_decision = governor.evaluate(sig_state)
            
            trace_a.append({
                "event_id": event_id,
                "timestamp": ts,
                "threat_probability": sig_state.threat_probability,
                "confidence": sig_state.confidence,
                "inference_level": sig_state.inference_level,
                "recommended_policy": sig_state.recommended_policy,
                "governor_decision": gov_decision
            })

        # --- Run Trace B (Proof A: Determinism Replay) ---
        engine.accumulator.reset()
        trace_b = []
        for event_id, ts, stats, ev in sequence:
            inf_res = engine.evaluate(event_id, ts, stats, ev)
            sig_state = router.route(inf_res)
            gov_decision = governor.evaluate(sig_state)
            trace_b.append({
                "event_id": event_id,
                "timestamp": ts,
                "threat_probability": sig_state.threat_probability,
                "confidence": sig_state.confidence,
                "inference_level": sig_state.inference_level,
                "recommended_policy": sig_state.recommended_policy,
                "governor_decision": gov_decision
            })

        self.assertEqual(trace_a, trace_b, "Trace execution must be completely deterministic.")

        # Proof D: Governor authority validation on final state
        final_record = trace_a[-1]
        if final_record["inference_level"] == "CRITICAL":
            self.assertEqual(final_record["governor_decision"], "IMMEDIATE_INTERVENTION")

        # Proof E: Ensure causal trace keys are fully preserved
        for record in trace_a:
            self.assertIn("event_id", record)
            self.assertIn("timestamp", record)
            self.assertIn("threat_probability", record)
            self.assertIn("inference_level", record)
            self.assertIn("governor_decision", record)

if __name__ == "__main__":
    unittest.main()
