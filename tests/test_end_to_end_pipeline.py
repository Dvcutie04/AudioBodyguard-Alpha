import hashlib
import unittest

from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.bridges.validator import EnvelopeValidator
from src.edge.protocol import AcousticObservation, PrivacyStatus
from src.inference.evidence import TemporalEvidenceAccumulator
from src.inference.gate import HypothesisGate
from src.policy.governor import SafetyGovernor
from src.tv.tv_state_machine import TVState, TVVolumeStateMachine


class TestEndToEndPipeline(unittest.TestCase):

    def test_complete_observation_to_actuation_pipeline(self):
        validator = EnvelopeValidator()
        accumulator = TemporalEvidenceAccumulator(window_size=3, spl_threshold=70.0)
        gate = HypothesisGate(min_probability=0.85, min_quality=0.80)
        governor = SafetyGovernor(max_allowed_db_drop=12.0)
        state_machine = TVVolumeStateMachine(
            enter_threshold=0.90,
            exit_threshold=0.65,
            candidate_dwell_ns=500_000_000,
        )

        base_time = 1_000_000_000
        dummy_digest = "0000000000000000000000000000000000000000000000000000000000000000"

        # Stream 3 high-SPL observations to trigger commercial hypothesis
        for seq in range(1, 4):
            obs = AcousticObservation(
                node_id="living_room_edge_01",
                sequence_id=seq,
                monotonic_timestamp_ns=base_time + (seq * 100_000_000),
                spl_estimate=75.0,
                event_class="commercial_candidate",
                confidence=0.95,
                temporal_metric=0.8,
                privacy_status=PrivacyStatus.RAW_AUDIO_DEAD,
                feature_digest="f" * 64,
                payload_digest=dummy_digest,
            )
            encoded = CanonicalCodec.encode_observation(obs)
            valid_digest = hashlib.sha256(encoded).hexdigest()

            envelope = ObservationEnvelope(
                protocol_version=ProtocolVersion.AQSS_EDGE_OBSERVATION_V1,
                message_type=MessageType.ACOUSTIC_OBSERVATION,
                node_id=obs.node_id,
                sequence_id=obs.sequence_id,
                monotonic_timestamp_ns=obs.monotonic_timestamp_ns,
                payload_digest=valid_digest,
                authentication_tag="mac_tag",
                payload=obs,
            )

            # 1. Validate
            self.assertTrue(validator.validate(envelope))

            # 2. Accumulate Evidence
            hypothesis = accumulator.process_envelope(envelope)

            if hypothesis:
                # 3. Gate Hypothesis -> ActionIntent
                intent = gate.evaluate(hypothesis)
                self.assertIsNotNone(intent)

                # 4. Govern Intent -> Safety Check
                is_safe, _ = governor.evaluate_intent(intent)
                self.assertTrue(is_safe)

                # 5. Drive State Machine
                state_machine.process_input(
                    probability=hypothesis.hypothesis_probability,
                    sequence_id=hypothesis.sequence_end,
                    lineage_digest=intent.triggering_lineage_digest,
                    now_ns=envelope.monotonic_timestamp_ns,
                )

        self.assertEqual(state_machine.current_state, TVState.COMMERCIAL_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
