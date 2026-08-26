import hashlib
import time
import unittest

from src.acoustic.event_graph import AcousticEvent, BoundedAcousticEventGraph, EdgeType
from src.audit.receipt import ActuationReceipt
from src.bridges.codec import CanonicalCodec
from src.bridges.envelope import ObservationEnvelope
from src.bridges.protocol import MessageType, ProtocolVersion
from src.bridges.validator import EnvelopeValidator
from src.edge.protocol import AcousticObservation, PrivacyStatus
from src.inference.hypothesis import HypothesisFrame
from src.intent.action_intent import ActionIntent


class TestVerticalSliceCausalLineage(unittest.TestCase):

    def test_full_perception_to_actuation_lineage(self):
        # 1. Edge Observation Creation
        dummy_digest = "0000000000000000000000000000000000000000000000000000000000000000"
        temp_obs = AcousticObservation(
            node_id="living_room_edge_01",
            sequence_id=101,
            monotonic_timestamp_ns=1_000_000_000,
            spl_estimate=74.5,
            event_class="commercial_candidate",
            confidence=0.92,
            temporal_metric=0.8,
            privacy_status=PrivacyStatus.RAW_AUDIO_DEAD,
            feature_digest="a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
            payload_digest=dummy_digest,
        )

        encoded_bytes = CanonicalCodec.encode_observation(temp_obs)
        valid_digest = hashlib.sha256(encoded_bytes).hexdigest()

        envelope = ObservationEnvelope(
            protocol_version=ProtocolVersion.AQSS_EDGE_OBSERVATION_V1,
            message_type=MessageType.ACOUSTIC_OBSERVATION,
            node_id="living_room_edge_01",
            sequence_id=101,
            monotonic_timestamp_ns=1_000_000_000,
            payload_digest=valid_digest,
            authentication_tag="mac_signature_stub",
            payload=temp_obs,
        )

        # 2. Envelope Validation
        validator = EnvelopeValidator()
        self.assertTrue(validator.validate(envelope))

        # 3. Bounded Event Graph Node Creation
        graph = BoundedAcousticEventGraph(max_events=50)
        event_digest = hashlib.sha256(f"{valid_digest}:event_01".encode("utf-8")).hexdigest()
        
        event = AcousticEvent(
            event_id="evt_101",
            node_id=envelope.node_id,
            sequence_start=101,
            sequence_end=101,
            t_start_ns=envelope.monotonic_timestamp_ns,
            t_end_ns=envelope.monotonic_timestamp_ns + 100_000_000,
            room_id="living_room",
            event_type="commercial_transition",
            spl_estimate=74.5,
            spl_variance=0.2,
            features={"spl": 74.5},
            observation_count=1,
            confidence=0.92,
            lineage_root=valid_digest,
            lineage_digest=event_digest,
        )
        graph.add_event(event)

        # 4. Hypothesis Frame Construction
        hypothesis_lineage = hashlib.sha256(f"{event.lineage_digest}:hyp_01".encode("utf-8")).hexdigest()
        hypothesis = HypothesisFrame(
            hypothesis_id="hyp_commercial_101",
            hypothesis_type="COMMERCIAL_ACTIVE",
            hypothesis_probability=0.94,
            evidence_quality=0.90,
            model_confidence=0.95,
            evidence_window_ns=100_000_000,
            sequence_start=101,
            sequence_end=101,
            source_lineage_digest=hypothesis_lineage,
            model_version="v1.0.0",
            created_at_ns=time.time_ns(),
        )

        # 5. Action Intent Generation
        intent_lineage = hashlib.sha256(f"{hypothesis.source_lineage_digest}:intent_01".encode("utf-8")).hexdigest()
        intent = ActionIntent(
            intent_id="intent_vol_down_01",
            intent_type="REDUCE_TV_VOLUME",
            target_device_id="tv_living_room",
            target_delta={"volume_db": -6.0},
            triggering_hypothesis_id=hypothesis.hypothesis_id,
            triggering_lineage_digest=intent_lineage,
            policy_context={"allowed_max_drop_db": 10.0},
        )

        # 6. Actuation Receipt Generation
        receipt = ActuationReceipt(
            action_id="act_001",
            device_id=intent.target_device_id,
            previous_state={"volume_db": 40.0},
            new_state={"volume_db": 34.0},
            triggering_hypothesis_id=hypothesis.hypothesis_id,
            policy_decision="POLICY_APPROVED",
            safety_decision="SAFETY_PASSED",
            source_lineage_digest=intent.triggering_lineage_digest,
            timestamp_ns=time.time_ns(),
        )

        # Assert Lineage Traceability End-to-End
        self.assertEqual(receipt.source_lineage_digest, intent.triggering_lineage_digest)
        self.assertEqual(intent.triggering_hypothesis_id, hypothesis.hypothesis_id)
        self.assertEqual(event.lineage_root, valid_digest)


if __name__ == "__main__":
    unittest.main()
