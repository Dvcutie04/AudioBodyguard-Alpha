import unittest, os, time
from src.sim.acoustic_environment import MultiMicSimulator
from src.voice.orchestrator import SpatialVoiceEngine
from src.crypto.attestation import ActionAttestor
from src.actuation.gateway import ActuatorGateway
from src.audit.flight_recorder import FlightRecorder

class TestEndToEndSafetyChain(unittest.TestCase):
    def setUp(self):
        self.key = b"SUPER_SECRET_AQSS_KEY_36_OMEGA"
        self.sim = MultiMicSimulator(mic_positions=[[0.0,0.0,0.0], [0.02,0.0,0.0]], seed=1337)
        self.engine = SpatialVoiceEngine()
        self.attestor = ActionAttestor(secret_key=self.key)
        self.gateway = ActuatorGateway(secret_key=self.key)
        self.recorder = FlightRecorder()

    def _run_pipeline_with_decision(self, frame, forced_decision=None, state_ver="v1"):
        res = self.engine.process_frame(frame)
        decision = forced_decision if forced_decision else res.get("decision", "NOMINAL")
        confidence = res.get("confidence", 0.99)
        att = self.attestor.generate_attestation(decision, confidence, state_ver)
        success, msg = self.gateway.process_action_proposal(att)
        
        self.recorder.record_event(
            proposal_id=att["payload"]["proposal_id"],
            sequence_num=att["payload"]["sequence_num"],
            system_state=state_ver,
            sensor_health=res.get("health", {"ok": True}),
            decision=decision,
            confidence=confidence,
            risk_state="ELEVATED" if decision == "RISING_THREAT" else "STABLE",
            policy_version=att["payload"]["policy_version"],
            auth_result=ActionAttestor.verify_attestation(att, self.key),
            interlock_state=self.gateway.hardware_interlock_tripped,
            exec_result=msg,
            rejection_reason="NONE" if success else msg
        )
        return success, msg, att

    def test_scenarios_1_to_3_state_transitions(self):
        # Nominal state execution
        frame = self.sim.generate_frame([2.0, 1.0, 0.0], 0.1)
        ok_nom, msg_nom, _ = self._run_pipeline_with_decision(frame, forced_decision="NOMINAL")
        self.assertTrue(ok_nom)
        self.assertEqual(msg_nom, "EXECUTED_NOMINAL")
        
        # Rising threat state execution
        ok_threat, msg_threat, _ = self._run_pipeline_with_decision(frame, forced_decision="RISING_THREAT")
        self.assertTrue(ok_threat)
        self.assertEqual(msg_threat, "EXECUTED_RISING_THREAT")

    def test_scenarios_5_to_8_auth_and_tamper_failures(self):
        frame = self.sim.generate_frame([2.0, 1.0, 0.0], 0.1)
        _, _, att = self._run_pipeline_with_decision(frame)
        
        # Scenario 5: Invalid HMAC signature check
        att_fresh = self.attestor.generate_attestation("NOMINAL", 0.9, "v1")
        att_fresh["signature"] = "0" * 64
        ok, msg = self.gateway.process_action_proposal(att_fresh)
        self.assertFalse(ok)
        self.assertEqual(msg, "REJECTED_INVALID_SIGNATURE")

        # Scenario 6: Replay attack check
        ok, msg = self.gateway.process_action_proposal(att)
        self.assertFalse(ok)
        self.assertEqual(msg, "REJECTED_REPLAY_ATTACK_DETECTED")

    def test_scenarios_9_and_10_interlock_fault_recovery_stale_prevention(self):
        frame = self.sim.generate_frame([2.0, 1.0, 0.0], 0.1)
        res = self.engine.process_frame(frame)
        stale_att = self.attestor.generate_attestation(res.get("decision", "NOMINAL"), 0.99, "v1")
        
        # Scenario 9: Hardware Fault during proposal processing
        self.gateway.set_hardware_interlock(True)
        ok, msg = self.gateway.process_action_proposal(stale_att)
        self.assertFalse(ok)
        self.assertEqual(msg, "REJECTED_HARDWARE_INTERLOCK_TRIPPED")
        
        # Scenario 10: Hardware fault clears -> stale proposal MUST NOT re-execute
        self.gateway.set_hardware_interlock(False)
        ok_stale, msg_stale = self.gateway.process_action_proposal(stale_att)
        self.assertFalse(ok_stale)
        self.assertEqual(msg_stale, "REJECTED_REPLAY_ATTACK_DETECTED")

    def test_flight_recorder_hash_chain_integrity(self):
        frame = self.sim.generate_frame([2.0, 1.0, 0.0], 0.1)
        self._run_pipeline_with_decision(frame)
        self.assertTrue(self.recorder.verify_chain_integrity())
