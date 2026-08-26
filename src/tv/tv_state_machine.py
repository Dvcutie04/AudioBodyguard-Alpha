from dataclasses import dataclass
from enum import Enum, auto
import time
from typing import Optional, List


class TVState(Enum):
    PROGRAM = auto()
    COMMERCIAL_CANDIDATE = auto()
    COMMERCIAL_ACTIVE = auto()
    PROGRAM_RECOVERY = auto()


@dataclass(frozen=True)
class StateTransitionRecord:
    previous_state: TVState
    new_state: TVState
    trigger_probability: float
    trigger_sequence: int
    trigger_lineage_digest: str
    timestamp_ns: int


class TVVolumeStateMachine:

    def __init__(
        self,
        enter_threshold: float = 0.90,
        exit_threshold: float = 0.65,
        candidate_dwell_ns: int = 1_000_000_000,  # 1 second minimum dwell
        recovery_dwell_ns: int = 2_000_000_000,   # 2 seconds minimum dwell
    ):
        self.enter_threshold = enter_threshold
        self.exit_threshold = exit_threshold
        self.candidate_dwell_ns = candidate_dwell_ns
        self.recovery_dwell_ns = recovery_dwell_ns

        self.current_state = TVState.PROGRAM
        self.state_entry_timestamp_ns = time.time_ns()
        self.history: List[StateTransitionRecord] = []

    def process_input(
        self,
        probability: float,
        sequence_id: int,
        lineage_digest: str,
        now_ns: Optional[int] = None,
    ) -> Optional[StateTransitionRecord]:
        
        current_time = now_ns if now_ns is not None else time.time_ns()
        dwell_duration = current_time - self.state_entry_timestamp_ns
        next_state = self.current_state

        # Pure Control State Transition Rules
        if self.current_state == TVState.PROGRAM:
            if probability >= self.enter_threshold:
                next_state = TVState.COMMERCIAL_CANDIDATE

        elif self.current_state == TVState.COMMERCIAL_CANDIDATE:
            if probability < self.enter_threshold:
                next_state = TVState.PROGRAM
            elif dwell_duration >= self.candidate_dwell_ns:
                next_state = TVState.COMMERCIAL_ACTIVE

        elif self.current_state == TVState.COMMERCIAL_ACTIVE:
            if probability <= self.exit_threshold:
                next_state = TVState.PROGRAM_RECOVERY

        elif self.current_state == TVState.PROGRAM_RECOVERY:
            if probability > self.exit_threshold:
                next_state = TVState.COMMERCIAL_ACTIVE
            elif dwell_duration >= self.recovery_dwell_ns:
                next_state = TVState.PROGRAM

        if next_state != self.current_state:
            record = StateTransitionRecord(
                previous_state=self.current_state,
                new_state=next_state,
                trigger_probability=probability,
                trigger_sequence=sequence_id,
                trigger_lineage_digest=lineage_digest,
                timestamp_ns=current_time,
            )
            self.current_state = next_state
            self.state_entry_timestamp_ns = current_time
            self.history.append(record)
            return record

        return None
