import unittest
from src.reinforcement.feedback_event import FeedbackEvent
from src.reinforcement.reinforcement_engine import ConfidenceWeightedReinforcementEngine
from src.audit.policy_audit import PolicyAuditLedger, PolicyAuditRecord
from src.shadow.shadow_policy import ShadowPolicyEngine
from src.shadow.rollback_manager import RollbackManager
from src.shadow.calibration_analytics import CalibrationAnalyticsEngine

class TestFullSystemIntegration(unittest.TestCase):
    def test_complete_pipeline_flow(self):
        # 1. Initialize components
        engine = ConfidenceWeightedReinforcementEngine(alpha=2.0)
        audit_ledger = PolicyAuditLedger()
        shadow_engine = ShadowPolicyEngine()
        rollback_mgr = RollbackManager()
        analytics_engine = CalibrationAnalyticsEngine()

        # 2. Commit initial baseline policy version
        rollback_mgr.commit_version(1, {"sensitivity": 50.0, "alert_preference": 0.5}, "Initial Baseline")

        # 3. Simulate incoming feedback event
        event = FeedbackEvent(
            event_id="int_01",
            action_id="act_01",
            feedback_type="AGREE",
            action_confidence=0.92,
            context_id="home"
        )
        proposal = engine.compute_proposal(event)
        self.assertIsNotNone(proposal)

        # 4. Record decision to audit ledger
        audit_record = PolicyAuditRecord(
            decision_id="dec_01",
            event_id=event.event_id,
            previous_policy_version=1,
            proposed_policy_version=2,
            target_field=proposal.target,
            previous_value=50.0,
            proposed_value=50.0 + proposal.delta,
            accepted_value=50.0 + proposal.delta,
            feedback_type=event.feedback_type,
            confidence_weight=event.action_confidence,
            bounded_delta=proposal.delta
        )
        audit_ledger.record(audit_record)

        # 5. Run shadow policy evaluation
        current_pol = {"version": 1, "action": "monitor"}
        candidate_pol = {"version": 2, "action": "alert"}
        deltas = {"notification": 2.0, "sensitivity": proposal.delta}
        shadow_res = shadow_engine.evaluate_shadow(current_pol, candidate_pol, deltas)
        self.assertEqual(shadow_res.current_policy_version, 1)

        # 6. Evaluate calibration analytics from ledger
        records = audit_ledger.export_ledger()
        metrics = analytics_engine.evaluate_window(records)
        self.assertEqual(metrics.total_decisions, 1)
        self.assertEqual(metrics.status, "WELL_CALIBRATED")

if __name__ == "__main__":
    unittest.main()
