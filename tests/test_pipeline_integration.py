import pytest
from audio_engine.trust_model import TrustEngine
from audio_engine.fusion_router import TrustWeightedDecisionRouter
from audio_engine.decision_envelope import DecisionEnvelope
from audio_engine.action_dispatcher import ActionDispatcher

class SimulationHarness:
    def __init__(self):
        self.trust_engine = TrustEngine(alpha=0.2, initial_trust=1.0)
        self.router = TrustWeightedDecisionRouter()
        self.dispatcher = ActionDispatcher()
        self.sequence_counter = 0

    def step(self, raw_threat, sensor_trust, spatial_agreement, sensor_age, persistence_counter):
        self.sequence_counter += 1
        decision_state = self.router.evaluate(
            raw_threat=raw_threat,
            sensor_trust=sensor_trust,
            spatial_agreement=spatial_agreement,
            sensor_age=sensor_age,
            persistence_counter=persistence_counter
        )
        envelope = DecisionEnvelope(
            sequence_id=self.sequence_counter,
            raw_threat=raw_threat,
            effective_trust=sensor_trust,
            spatial_confidence=spatial_agreement,
            sensor_age=sensor_age,
            persistence_counter=persistence_counter,
            decision_state=decision_state
        )
        action = self.dispatcher.dispatch(envelope)
        return decision_state, action

@pytest.fixture
def harness():
    return SimulationHarness()

def test_integration_three_sensors_agree(harness):
    state, action = harness.step(0.85, 0.9, 1.0, 0.0, 0)
    assert state == "ESCALATE"
    assert action == "TRIGGER_HIGH_PRIORITY_ALARM"

def test_integration_noisy_sensor_degradation(harness):
    state, action = harness.step(0.85, 0.3, 1.0, 0.0, 0)
    assert state == "SUPPLIED_OR_DEGRADED"
    assert action == "NO_ACTION"

def test_integration_spatial_contradiction(harness):
    state, action = harness.step(0.85, 0.9, 0.2, 0.0, 0)
    assert state == "REDUCED_CONFIDENCE"
    assert action == "SUPPRESS_OR_LOG_ONLY"

def test_integration_persistent_contradiction(harness):
    state, action = harness.step(0.85, 0.8, 0.2, 0.0, 3)
    assert state == "DEGRADED_STATE"
    assert action == "FALLBACK_LOCAL_LOG"

def test_integration_stale_sensor(harness):
    state, action = harness.step(0.85, 0.9, 1.0, 6.0, 0)
    assert state == "SUPPLIED_OR_DEGRADED"
    assert action == "NO_ACTION"

def test_integration_replayed_evidence_identical(harness):
    state1, action1 = harness.step(0.85, 0.9, 1.0, 0.0, 0)
    harness2 = type(harness)()
    state2, action2 = harness2.step(0.85, 0.9, 1.0, 0.0, 0)
    assert state1 == state2
    assert action1 == action2

def test_integration_malformed_telemetry_rejection(harness):
    envelope = DecisionEnvelope(sequence_id=999, raw_threat=99.9, decision_state="MALFORMED")
    action = harness.dispatcher.dispatch(envelope)
    assert action == "NO_ACTION"

def test_integration_sequence_number_replay_rejection(harness):
    envelope1 = DecisionEnvelope(sequence_id=1, raw_threat=0.85, decision_state="ESCALATE")
    envelope2 = DecisionEnvelope(sequence_id=1, raw_threat=0.85, decision_state="ESCALATE")
    harness.dispatcher.dispatch(envelope1)
    assert harness.dispatcher.dispatch(envelope2) == "NO_ACTION"

def test_fail_safe_dispatch_invariant(harness):
    known_states = [
        ("ESCALATE", "TRIGGER_HIGH_PRIORITY_ALARM"),
        ("PERMIT_ESCALATION", "LOG_AND_MONITOR"),
        ("AMBIGUOUS_EVIDENCE", "REQUEST_SECONDARY_VALIDATION"),
        ("REDUCED_CONFIDENCE", "SUPPRESS_OR_LOG_ONLY"),
        ("DEGRADED_STATE", "FALLBACK_LOCAL_LOG"),
    ]
    for state_name, expected_action in known_states:
        env = DecisionEnvelope(sequence_id=500, decision_state=state_name)
        assert harness.dispatcher._map_state_to_action(state_name, env) == expected_action
    unrecognized_states = ["MALFORMED", "UNKNOWN", "", None, "OVERRIDE_ACTIVATION"]
    for bad_state in unrecognized_states:
        env = DecisionEnvelope(sequence_id=501, decision_state=bad_state)
        assert harness.dispatcher._map_state_to_action(bad_state, env) == "NO_ACTION"
