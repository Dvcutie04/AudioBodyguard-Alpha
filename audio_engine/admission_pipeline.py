from audio_engine.symmetric_auth import SymmetricAuthenticator
from audio_engine.node_trust import TrustEvaluator, NodeTrust
from audio_engine.decision_envelope import DecisionEnvelope

class AdmissionPipeline:
    def __init__(self, authenticator: SymmetricAuthenticator, current_epoch: int):
        self.authenticator = authenticator
        self.current_epoch = current_epoch
        self.fusion_calls = 0
        self.dispatcher_calls = 0

    def process(self, envelope: DecisionEnvelope, tag: str, node_trust: NodeTrust):
        # 1. Symmetric Auth + Replay + Stale Epoch Gate
        auth_result = self.authenticator.admit(envelope, tag, self.current_epoch)
        if auth_result != "ACCEPT":
            return auth_result

        # 2. NodeTrust Evaluation Gate
        evaluator = TrustEvaluator(current_known_epoch=self.current_epoch)
        trust_state, trust_score, reasons = evaluator.evaluate(node_trust)
        
        if trust_state in ("REJECT", "QUARANTINE", "DEGRADED"):
            return trust_state

        # 3. Fusion / Policy Simulation (Tracked for non-reachability testing)
        self.fusion_calls += 1
        
        # 4. Dispatcher Simulation
        self.dispatcher_calls += 1
        return "DISPATCHED"
