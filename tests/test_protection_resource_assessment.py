from src.control.protection_resource_assessment import ProtectionResourceReason,ProtectionRemediationAction,ProtectionResourceAssessment
from src.edge.resource_contract import Accelerator,EnergyTier,ExecutionTier,ModelResourceProfile
from src.edge.resource_governor import ResourceGovernor,RuntimeResources


def test_memory_rejection_becomes_ineligible_with_bounded_recovery_actions():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=16,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=200)
    decision=ResourceGovernor().admit(profile,resources)
    assessment=ProtectionResourceAssessment.from_admission(decision)
    assert assessment.eligible is False
    assert assessment.reason is ProtectionResourceReason.MEMORY_BUDGET_EXCEEDED
    assert assessment.remediation_actions==(ProtectionRemediationAction.UNLOAD_OPTIONAL_MODELS,ProtectionRemediationAction.REDUCE_EXECUTION_TIER)


def test_latency_rejection_becomes_ineligible_with_bounded_recovery_actions():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=220,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=200)
    decision=ResourceGovernor().admit(profile,resources)
    assessment=ProtectionResourceAssessment.from_admission(decision)
    assert assessment.eligible is False
    assert assessment.reason is ProtectionResourceReason.LATENCY_BUDGET_EXCEEDED
    assert assessment.remediation_actions==(ProtectionRemediationAction.SELECT_LOWER_LATENCY_MODEL,ProtectionRemediationAction.REDUCE_EXECUTION_TIER)


def test_low_power_rejection_preserves_battery_policy_with_bounded_actions():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.HIGH,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=200,low_power_mode=True)
    decision=ResourceGovernor().admit(profile,resources)
    assessment=ProtectionResourceAssessment.from_admission(decision)
    assert assessment.eligible is False
    assert assessment.reason is ProtectionResourceReason.LOW_POWER_ENERGY_REJECTED
    assert assessment.remediation_actions==(ProtectionRemediationAction.SELECT_LOWER_ENERGY_MODEL,ProtectionRemediationAction.REDUCE_EXECUTION_TIER)


def test_thermal_rejection_avoids_hot_retry_loop():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.HIGH,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=200,thermal_pressure=True)
    decision=ResourceGovernor().admit(profile,resources)
    assessment=ProtectionResourceAssessment.from_admission(decision)
    assert assessment.eligible is False
    assert assessment.reason is ProtectionResourceReason.THERMAL_PRESSURE_REJECTED
    assert assessment.remediation_actions==(ProtectionRemediationAction.WAIT_FOR_THERMAL_RECOVERY,ProtectionRemediationAction.SELECT_LOWER_ENERGY_MODEL)
