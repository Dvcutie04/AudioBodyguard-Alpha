from dataclasses import dataclass
from enum import Enum


class Accelerator(Enum):
    CPU="cpu"
    GPU="gpu"
    NPU="npu"


class EnergyTier(Enum):
    LOW="low"
    MODERATE="moderate"
    HIGH="high"


class ExecutionTier(Enum):
    SLEEP="sleep"
    SENTINEL="sentinel"
    PERCEPTION="perception"
    REASONING="reasoning"
    DEEP_REASONING="deep_reasoning"


@dataclass(frozen=True)
class ModelResourceProfile:
    task: str
    execution_tier: ExecutionTier
    memory_mb: int
    expected_latency_ms: int
    energy_tier: EnergyTier
    supported_accelerators: frozenset[Accelerator]
    model_version: str
    cold_start_latency_ms: int = 0
