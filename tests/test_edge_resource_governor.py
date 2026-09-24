from src.edge.resource_contract import Accelerator, EnergyTier, ExecutionTier, ModelResourceProfile
from src.edge.resource_governor import ResourceGovernor, RuntimeResources


def test_governor_rejects_model_that_exceeds_available_memory_budget():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=96,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU,Accelerator.CPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU,Accelerator.CPU}))
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="MEMORY_BUDGET_EXCEEDED"


def test_governor_rejects_model_without_compatible_accelerator():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.CPU,Accelerator.GPU}))
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="NO_COMPATIBLE_ACCELERATOR"


def test_governor_rejects_model_that_exceeds_latency_budget():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=18,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="LATENCY_BUDGET_EXCEEDED"


def test_governor_rejects_high_energy_model_in_low_power_mode():
    profile=ModelResourceProfile(task="deep_reasoning",execution_tier=ExecutionTier.DEEP_REASONING,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.HIGH,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=True)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="LOW_POWER_ENERGY_REJECTED"


def test_governor_rejects_high_energy_model_under_thermal_pressure():
    profile=ModelResourceProfile(task="deep_reasoning",execution_tier=ExecutionTier.DEEP_REASONING,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.HIGH,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=True)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="THERMAL_PRESSURE_REJECTED"


def test_governor_admits_model_when_all_resource_constraints_are_satisfied():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.reason=="ADMITTED"


def test_governor_admits_model_at_exact_memory_and_latency_boundaries():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=64,expected_latency_ms=10,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.reason=="ADMITTED"


def test_governor_selects_npu_over_cpu_when_both_are_compatible():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU,Accelerator.CPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU,Accelerator.CPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.selected_accelerator is Accelerator.NPU


def test_governor_selects_gpu_over_cpu_when_npu_is_unavailable():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.GPU,Accelerator.CPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.GPU,Accelerator.CPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.selected_accelerator is Accelerator.GPU


def test_governor_selects_cpu_when_it_is_the_only_compatible_accelerator():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.CPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.CPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.selected_accelerator is Accelerator.CPU


def test_governor_rejected_decision_never_selects_accelerator():
    profile=ModelResourceProfile(task="deep_reasoning",execution_tier=ExecutionTier.DEEP_REASONING,memory_mb=256,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=64,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="MEMORY_BUDGET_EXCEEDED"
    assert decision.selected_accelerator is None


def test_governor_counts_cold_start_latency_for_nonresident_model():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0",cold_start_latency_ms=20)
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,resident_models=frozenset())
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="LATENCY_BUDGET_EXCEEDED"


def test_governor_skips_cold_start_latency_for_resident_model():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0",cold_start_latency_ms=20)
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,resident_models=frozenset({("acoustic_event_detection","1.0.0")}))
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.reason=="ADMITTED"
    assert decision.selected_accelerator is Accelerator.NPU


def test_governor_rejects_model_above_runtime_execution_tier_ceiling():
    profile=ModelResourceProfile(task="deep_reasoning",execution_tier=ExecutionTier.DEEP_REASONING,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,max_execution_tier=ExecutionTier.REASONING)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="EXECUTION_TIER_EXCEEDED"
    assert decision.selected_accelerator is None


def test_governor_admits_model_at_exact_runtime_execution_tier_ceiling():
    profile=ModelResourceProfile(task="reasoning",execution_tier=ExecutionTier.REASONING,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0")
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,max_execution_tier=ExecutionTier.REASONING)
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.reason=="ADMITTED"
    assert decision.selected_accelerator is Accelerator.NPU


def test_governor_does_not_treat_same_version_different_task_as_resident():
    profile=ModelResourceProfile(task="deep_reasoning",execution_tier=ExecutionTier.REASONING,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0",cold_start_latency_ms=20)
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,resident_models=frozenset({("acoustic_event_detection","1.0.0")}))
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is False
    assert decision.reason=="LATENCY_BUDGET_EXCEEDED"


def test_governor_treats_matching_task_and_version_tuple_as_resident():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU}),model_version="1.0.0",cold_start_latency_ms=20)
    resources=RuntimeResources(available_memory_mb=128,available_accelerators=frozenset({Accelerator.NPU}),max_latency_ms=10,low_power_mode=False,thermal_pressure=False,resident_models=frozenset({("acoustic_event_detection","1.0.0")}))
    decision=ResourceGovernor().admit(profile,resources)
    assert decision.admitted is True
    assert decision.reason=="ADMITTED"
    assert decision.selected_accelerator is Accelerator.NPU
