import time
from typing import Optional
from src.device_fabric.contracts import DeviceState, PreconditionStatus


class PreconditionEvaluator:
    def __init__(self, staleness_threshold_seconds: float = 2.0):
        self.staleness_threshold_seconds = staleness_threshold_seconds

    def evaluate(
        self,
        observed_state: DeviceState,
        expected_state: DeviceState,
        observation_timestamp: Optional[float] = None,
    ) -> PreconditionStatus:
        if observation_timestamp is not None:
            if time.time() - observation_timestamp > self.staleness_threshold_seconds:
                return PreconditionStatus.TIMEOUT

        if observed_state.power != expected_state.power:
            return PreconditionStatus.MISMATCH

        if observed_state.volume != expected_state.volume:
            return PreconditionStatus.MISMATCH

        if observed_state.input_source != expected_state.input_source:
            return PreconditionStatus.MISMATCH

        return PreconditionStatus.MATCH
