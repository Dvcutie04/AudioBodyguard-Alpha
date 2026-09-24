from dataclasses import dataclass

from src.edge.resource_contract import Accelerator, EnergyTier, ExecutionTier, ModelResourceProfile


@dataclass(frozen=True)
class RuntimeResources:
    available_memory_mb: int
    available_accelerators: frozenset[Accelerator]
    max_latency_ms: int | None = None
    low_power_mode: bool = False
    thermal_pressure: bool = False
    resident_models: frozenset[tuple[str, str]] = frozenset()
    max_execution_tier: ExecutionTier | None = None


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: str
    selected_accelerator: Accelerator | None = None


class ResourceGovernor:
    def admit(self,profile: ModelResourceProfile,resources: RuntimeResources) -> AdmissionDecision:
        tier_rank={ExecutionTier.SLEEP:0,ExecutionTier.SENTINEL:1,ExecutionTier.PERCEPTION:2,ExecutionTier.REASONING:3,ExecutionTier.DEEP_REASONING:4}
        if resources.max_execution_tier is not None and tier_rank[profile.execution_tier] > tier_rank[resources.max_execution_tier]:
            return AdmissionDecision(False,"EXECUTION_TIER_EXCEEDED")
        if profile.memory_mb > resources.available_memory_mb:
            return AdmissionDecision(False,"MEMORY_BUDGET_EXCEEDED")
        if not profile.supported_accelerators.intersection(resources.available_accelerators):
            return AdmissionDecision(False,"NO_COMPATIBLE_ACCELERATOR")
        effective_latency_ms=profile.expected_latency_ms
        if (profile.task,profile.model_version) not in resources.resident_models:
            effective_latency_ms+=profile.cold_start_latency_ms
        if resources.max_latency_ms is not None and effective_latency_ms > resources.max_latency_ms:
            return AdmissionDecision(False,"LATENCY_BUDGET_EXCEEDED")
        if resources.low_power_mode and profile.energy_tier is EnergyTier.HIGH:
            return AdmissionDecision(False,"LOW_POWER_ENERGY_REJECTED")
        if resources.thermal_pressure and profile.energy_tier is EnergyTier.HIGH:
            return AdmissionDecision(False,"THERMAL_PRESSURE_REJECTED")
        compatible=profile.supported_accelerators.intersection(resources.available_accelerators)
        for accelerator in (Accelerator.NPU,Accelerator.GPU,Accelerator.CPU):
            if accelerator in compatible:
                return AdmissionDecision(True,"ADMITTED",accelerator)
        raise AssertionError("compatible accelerator invariant violated")
