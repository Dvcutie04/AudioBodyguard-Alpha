from src.edge.resource_contract import Accelerator, EnergyTier, ExecutionTier, ModelResourceProfile


def test_model_resource_profile_preserves_runtime_cost_contract():
    profile=ModelResourceProfile(task="acoustic_event_detection",execution_tier=ExecutionTier.SENTINEL,memory_mb=24,expected_latency_ms=8,energy_tier=EnergyTier.LOW,supported_accelerators=frozenset({Accelerator.NPU,Accelerator.CPU}),model_version="1.0.0")
    assert profile.task=="acoustic_event_detection"
    assert profile.execution_tier is ExecutionTier.SENTINEL
    assert profile.memory_mb==24
    assert profile.expected_latency_ms==8
    assert profile.energy_tier is EnergyTier.LOW
    assert profile.supported_accelerators==frozenset({Accelerator.NPU,Accelerator.CPU})
    assert profile.model_version=="1.0.0"
