import time
from typing import Optional

from src.device_fabric.contracts import DeviceState, PreconditionStatus


class PreconditionEvaluator:
    """
    Evaluates the physical state of a device against expected preconditions prior to transaction execution.
    Protects the physical execution layer against World-State Drift and stale telemetry.
    """
    
    def __init__(self, staleness_threshold_seconds: float = 5.0):
        self.staleness_threshold = staleness_threshold_seconds

    def evaluate(
        self, 
        expected_state: DeviceState, 
        observed_state: Optional[DeviceState],
        current_time: Optional[float] = None
    ) -> PreconditionStatus:
        
        if current_time is None:
            current_time = time.time()

        # 1. UNAVAILABLE: No physical state can be observed
        if observed_state is None:
            return PreconditionStatus.UNAVAILABLE
        
        # 2. MALFORMED: The state object exists but lacks minimum valid identity
        # (Assuming 'unknown' is the default for unitialized Phase 2.5 states)
        if expected_state.device_id != "unknown" and observed_state.device_id != "unknown":
            if expected_state.device_id != observed_state.device_id:
                return PreconditionStatus.MALFORMED

        # 3. STALE: Telemetry is too old to safely act upon (mitigates network buffering issues)
        if (current_time - observed_state.observed_at) > self.staleness_threshold:
            return PreconditionStatus.STALE

        # 4. DRIFT: The world state has physically mutated since the action was authorized
        
        # A. Check Phase 2.5 canonical payload dictionary
        if expected_state.payload:
            for key, expected_val in expected_state.payload.items():
                if key not in observed_state.payload:
                    return PreconditionStatus.DRIFT
                if observed_state.payload[key] != expected_val:
                    return PreconditionStatus.DRIFT

        # B. Check legacy backward compatibility fields (for our current integration tests)
        legacy_drift = False
        if expected_state.power != observed_state.power:
            legacy_drift = True
        elif abs(expected_state.volume - observed_state.volume) >= 0.1:
            legacy_drift = True
        elif expected_state.muted != observed_state.muted:
            legacy_drift = True
        elif expected_state.input_source != observed_state.input_source:
            legacy_drift = True

        if legacy_drift:
            return PreconditionStatus.DRIFT

        # 5. MATCH: Physical reality perfectly aligns with authorized expectation
        return PreconditionStatus.MATCH
