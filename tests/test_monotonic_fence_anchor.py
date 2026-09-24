from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor,MonotonicAnchorDecision,MonotonicFenceValue


def test_monotonic_anchor_never_moves_backward_or_changes_controller_at_equal_token():
    anchor=InMemoryMonotonicFenceAnchor()
    assert anchor.read("tv:living-room") is None
    assert anchor.advance("tv:living-room","phone-a",8) is MonotonicAnchorDecision.ADVANCED
    expected=MonotonicFenceValue(resource_id="tv:living-room",controller_id="phone-a",fencing_token=8)
    assert anchor.read("tv:living-room")==expected
    assert anchor.advance("tv:living-room","phone-a",8) is MonotonicAnchorDecision.ALREADY_CURRENT
    assert anchor.advance("tv:living-room","phone-a",7) is MonotonicAnchorDecision.STALE
    assert anchor.advance("tv:living-room","phone-b",8) is MonotonicAnchorDecision.CONTROLLER_MISMATCH
    assert anchor.read("tv:living-room")==expected


def test_in_memory_anchor_is_rejected_as_production_trust():
    import pytest
    from src.device_fabric.monotonic_fence_anchor import require_production_monotonic_anchor
    anchor=InMemoryMonotonicFenceAnchor()
    with pytest.raises(ValueError,match="production monotonic anchor"):
        require_production_monotonic_anchor(anchor)


def test_external_atomic_anchor_qualifies_for_production():
    from src.device_fabric.monotonic_fence_anchor import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorSecurityLevel,require_production_monotonic_anchor
    class RemoteBackend:
        provider_id="remote-controller-authority"
        def snapshot(self):
            return {}
        def advance(self,resource_id,controller_id,fencing_token):
            return MonotonicAnchorDecision.ADVANCED
    anchor=ExternalAtomicMonotonicFenceAnchor(RemoteBackend(),security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    assert require_production_monotonic_anchor(anchor) is anchor
    assert anchor.provider_id=="remote-controller-authority"
    assert anchor.snapshot()=={}
    assert anchor.read("tv:living-room") is None


def test_self_declared_anchor_cannot_spoof_production_qualification():
    import pytest
    from src.device_fabric.monotonic_fence_anchor import MonotonicAnchorSecurityLevel,require_production_monotonic_anchor
    class SelfDeclaredAnchor:
        provider_id="forged-provider"
        security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC
        def read(self,resource_id):
            return None
        def snapshot(self):
            return {}
        def advance(self,resource_id,controller_id,fencing_token):
            return MonotonicAnchorDecision.ADVANCED
    with pytest.raises(ValueError,match="production monotonic anchor"):
        require_production_monotonic_anchor(SelfDeclaredAnchor())


def test_production_anchor_contracts_are_public_device_fabric_api():
    import src.device_fabric as device_fabric
    from src.device_fabric.controller_fence_store import build_production_controller_fence_store
    from src.device_fabric.monotonic_fence_anchor import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorSecurityLevel
    assert device_fabric.ExternalAtomicMonotonicFenceAnchor is ExternalAtomicMonotonicFenceAnchor
    assert device_fabric.MonotonicAnchorSecurityLevel is MonotonicAnchorSecurityLevel
    assert device_fabric.build_production_controller_fence_store is build_production_controller_fence_store
    assert "ExternalAtomicMonotonicFenceAnchor" in device_fabric.__all__
    assert "MonotonicAnchorSecurityLevel" in device_fabric.__all__
    assert "build_production_controller_fence_store" in device_fabric.__all__
