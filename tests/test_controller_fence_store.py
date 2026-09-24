from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from src.device_fabric.controller_fence_store import ControllerFenceStore


def test_concurrent_store_instances_never_roll_fence_backward(tmp_path):
    store_path=tmp_path/"controller-fences.json"
    barrier=Barrier(2)
    def submit(controller_id,token):
        store=ControllerFenceStore(store_path)
        barrier.wait()
        return store.accept("tv:living-room",controller_id,token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        token9=pool.submit(submit,"phone-a",9)
        token10=pool.submit(submit,"phone-b",10)
        results=(token9.result(),token10.result())
    final_store=ControllerFenceStore(store_path)
    assert results[1] is True
    assert final_store.snapshot()=={"tv:living-room":(10,"phone-b")}
    assert final_store.accept("tv:living-room","phone-a",9) is False
    assert final_store.snapshot()=={"tv:living-room":(10,"phone-b")}


def test_store_rejects_corruption_and_equal_token_forgery(tmp_path):
    store_path=tmp_path/"controller-fences.json"
    store=ControllerFenceStore(store_path)
    assert store.accept("tv:living-room","phone-a",10) is True
    assert store.accept("tv:living-room","phone-b",10) is False
    assert store.snapshot()=={"tv:living-room":(10,"phone-a")}
    store_path.write_text("{corrupt",encoding="utf-8")
    with pytest.raises(ValueError):
        store.snapshot()
    with pytest.raises(ValueError):
        store.accept("tv:living-room","phone-c",11)


def test_store_isolates_resources_and_allows_active_controller_reuse(tmp_path):
    store=ControllerFenceStore(tmp_path/"controller-fences.json")
    assert store.accept("tv:living-room","phone-a",10) is True
    assert store.accept("tv:living-room","phone-a",10) is True
    assert store.accept("tv:bedroom","phone-b",3) is True
    assert store.accept("tv:living-room","phone-b",10) is False
    assert store.accept("tv:bedroom","phone-c",2) is False
    assert store.snapshot()=={
        "tv:living-room":(10,"phone-a"),
        "tv:bedroom":(3,"phone-b"),
    }


def test_store_rejects_rolled_back_primary_fence_state(tmp_path):
    import pytest
    store_path=tmp_path/"controller-fences.json"
    store=ControllerFenceStore(store_path)
    assert store.accept("tv:living-room","phone-a",8) is True
    rolled_back_bytes=store_path.read_bytes()
    assert store.accept("tv:living-room","phone-b",9) is True
    assert store.snapshot()=={"tv:living-room":(9,"phone-b")}
    store_path.write_bytes(rolled_back_bytes)
    with pytest.raises(ValueError,match="rollback"):
        ControllerFenceStore(store_path).snapshot()


def test_store_rejects_rolled_back_fence_anchor(tmp_path):
    import pytest
    from pathlib import Path
    store_path=tmp_path/"controller-fences.json"
    anchor_path=Path(str(store_path)+".anchor")
    store=ControllerFenceStore(store_path)
    assert store.accept("tv:living-room","phone-a",8) is True
    rolled_back_anchor_bytes=anchor_path.read_bytes()
    assert store.accept("tv:living-room","phone-b",9) is True
    assert store.snapshot()=={"tv:living-room":(9,"phone-b")}
    anchor_path.write_bytes(rolled_back_anchor_bytes)
    with pytest.raises(ValueError,match="rollback"):
        ControllerFenceStore(store_path).snapshot()


def test_store_rejects_missing_required_fence_anchor(tmp_path):
    import pytest
    from pathlib import Path
    store_path=tmp_path/"controller-fences.json"
    anchor_path=Path(str(store_path)+".anchor")
    store=ControllerFenceStore(store_path)
    assert store.accept("tv:living-room","phone-a",8) is True
    assert anchor_path.exists()
    anchor_path.unlink()
    with pytest.raises(ValueError,match="anchor"):
        ControllerFenceStore(store_path).snapshot()


def test_legacy_fence_store_migrates_without_advancing_token(tmp_path):
    import json
    import pytest
    from pathlib import Path
    store_path=tmp_path/"controller-fences.json"
    anchor_path=Path(str(store_path)+".anchor")
    legacy={"tv:living-room":{"token":8,"controller_id":"phone-a"}}
    store_path.write_text(json.dumps(legacy),encoding="utf-8")
    store=ControllerFenceStore(store_path)
    assert store.snapshot()=={"tv:living-room":(8,"phone-a")}
    assert not anchor_path.exists()
    assert store.accept("tv:living-room","phone-a",8) is True
    migrated=json.loads(store_path.read_text(encoding="utf-8"))
    assert migrated=={"version":2,"anchor_required":True,"resources":legacy}
    assert json.loads(anchor_path.read_text(encoding="utf-8"))==legacy
    assert store.snapshot()=={"tv:living-room":(8,"phone-a")}
    anchor_path.unlink()
    with pytest.raises(ValueError,match="anchor"):
        ControllerFenceStore(store_path).snapshot()


def test_anchor_first_primary_write_failure_is_fail_closed(tmp_path):
    import pytest
    store_path=tmp_path/"controller-fences.json"
    store=ControllerFenceStore(store_path)
    assert store.accept("tv:living-room","phone-a",8) is True
    def fail_primary_write(records):
        raise OSError("simulated primary persistence failure")
    store._save=fail_primary_write
    with pytest.raises(OSError,match="primary persistence failure"):
        store.accept("tv:living-room","phone-b",9)
    with pytest.raises(ValueError,match="rollback"):
        ControllerFenceStore(store_path).snapshot()


def test_trusted_monotonic_anchor_detects_coordinated_file_rollback(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    primary_at_8=store_path.read_bytes()
    sidecar_at_8=store.anchorpath.read_bytes()
    assert store.accept("tv:living-room","phone-b",9) is True
    store_path.write_bytes(primary_at_8)
    store.anchorpath.write_bytes(sidecar_at_8)
    with pytest.raises(ValueError,match="trusted anchor"):
        ControllerFenceStore(store_path,monotonic_anchor=trusted).snapshot()


def test_trusted_monotonic_anchor_detects_deleted_filesystem_resource(tmp_path):
    import json
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    store_path.write_text(json.dumps({"version":2,"anchor_required":True,"resources":{}}),encoding="utf-8")
    store.anchorpath.write_text("{}",encoding="utf-8")
    with pytest.raises(ValueError,match="trusted anchor"):
        ControllerFenceStore(store_path,monotonic_anchor=trusted).snapshot()


def test_existing_fence_rejects_empty_replacement_trusted_anchor(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    established=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=established)
    assert store.accept("tv:living-room","phone-a",8) is True
    empty_replacement=InMemoryMonotonicFenceAnchor()
    with pytest.raises(ValueError,match="trusted anchor"):
        ControllerFenceStore(store_path,monotonic_anchor=empty_replacement).snapshot()


def test_persisted_trusted_anchor_requirement_rejects_provider_omission(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    with pytest.raises(ValueError,match="trusted anchor"):
        ControllerFenceStore(store_path).snapshot()


def test_trusted_anchor_snapshot_outage_fails_closed(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    def unavailable_snapshot():
        raise OSError("simulated trusted provider outage")
    trusted.snapshot=unavailable_snapshot
    with pytest.raises(ValueError,match="trusted anchor unavailable"):
        ControllerFenceStore(store_path,monotonic_anchor=trusted).snapshot()


def test_trusted_anchor_advance_outage_preserves_filesystem_state(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    primary_before=store_path.read_bytes()
    sidecar_before=store.anchorpath.read_bytes()
    def unavailable_advance(*args):
        raise OSError("simulated trusted provider outage")
    trusted.advance=unavailable_advance
    with pytest.raises(ValueError,match="trusted anchor advance failed"):
        store.accept("tv:living-room","phone-b",9)
    assert store_path.read_bytes()==primary_before
    assert store.anchorpath.read_bytes()==sidecar_before
    assert ControllerFenceStore(store_path,monotonic_anchor=trusted).snapshot()=={"tv:living-room":(8,"phone-a")}


def test_trusted_advance_then_sidecar_failure_is_fail_closed(tmp_path):
    import pytest
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor,MonotonicFenceValue
    store_path=tmp_path/"controller-fences.json"
    trusted=InMemoryMonotonicFenceAnchor()
    store=ControllerFenceStore(store_path,monotonic_anchor=trusted)
    assert store.accept("tv:living-room","phone-a",8) is True
    primary_before=store_path.read_bytes()
    sidecar_before=store.anchorpath.read_bytes()
    def fail_sidecar_write(records):
        raise OSError("simulated sidecar persistence failure")
    store._save_anchor=fail_sidecar_write
    with pytest.raises(OSError,match="sidecar persistence failure"):
        store.accept("tv:living-room","phone-b",9)
    assert store_path.read_bytes()==primary_before
    assert store.anchorpath.read_bytes()==sidecar_before
    assert trusted.read("tv:living-room")==MonotonicFenceValue(resource_id="tv:living-room",controller_id="phone-b",fencing_token=9)
    with pytest.raises(ValueError,match="trusted anchor"):
        ControllerFenceStore(store_path,monotonic_anchor=trusted).snapshot()


def test_production_fence_store_rejects_test_only_anchor(tmp_path):
    import pytest
    from src.device_fabric.controller_fence_store import build_production_controller_fence_store
    from src.device_fabric.monotonic_fence_anchor import InMemoryMonotonicFenceAnchor
    with pytest.raises(ValueError,match="production monotonic anchor"):
        build_production_controller_fence_store(tmp_path/"controller-fences.json",monotonic_anchor=InMemoryMonotonicFenceAnchor())


def test_production_fence_store_uses_external_atomic_anchor(tmp_path):
    from src.device_fabric.controller_fence_store import build_production_controller_fence_store
    from src.device_fabric.monotonic_fence_anchor import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorDecision,MonotonicAnchorSecurityLevel,MonotonicFenceValue
    class RemoteBackend:
        provider_id="remote-controller-authority"
        def __init__(self):
            self.values={}
        def snapshot(self):
            return dict(self.values)
        def advance(self,resource_id,controller_id,fencing_token):
            current=self.values.get(resource_id)
            proposed=MonotonicFenceValue(resource_id=resource_id,controller_id=controller_id,fencing_token=fencing_token)
            if current is None or fencing_token>current.fencing_token:
                self.values[resource_id]=proposed
                return MonotonicAnchorDecision.ADVANCED
            if fencing_token<current.fencing_token:
                return MonotonicAnchorDecision.STALE
            if controller_id!=current.controller_id:
                return MonotonicAnchorDecision.CONTROLLER_MISMATCH
            return MonotonicAnchorDecision.ALREADY_CURRENT
    backend=RemoteBackend()
    anchor=ExternalAtomicMonotonicFenceAnchor(backend,security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    store=build_production_controller_fence_store(tmp_path/"controller-fences.json",monotonic_anchor=anchor)
    assert store.accept("tv:living-room","phone-a",8) is True
    assert store.snapshot()=={"tv:living-room":(8,"phone-a")}
    assert backend.snapshot()=={"tv:living-room":MonotonicFenceValue(resource_id="tv:living-room",controller_id="phone-a",fencing_token=8)}


def test_production_backend_invalid_decision_creates_no_local_authority(tmp_path):
    import pytest
    from src.device_fabric.controller_fence_store import build_production_controller_fence_store
    from src.device_fabric.monotonic_fence_anchor import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorSecurityLevel
    class InvalidDecisionBackend:
        provider_id="remote-controller-authority"
        def snapshot(self):
            return {}
        def advance(self,resource_id,controller_id,fencing_token):
            return "ADVANCED"
    store_path=tmp_path/"controller-fences.json"
    anchor=ExternalAtomicMonotonicFenceAnchor(InvalidDecisionBackend(),security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    store=build_production_controller_fence_store(store_path,monotonic_anchor=anchor)
    with pytest.raises(ValueError,match="trusted anchor advance failed"):
        store.accept("tv:living-room","phone-a",8)
    assert not store_path.exists()
    assert not store.anchorpath.exists()


def test_production_backend_malformed_manifest_fails_closed(tmp_path):
    import pytest
    from src.device_fabric.controller_fence_store import build_production_controller_fence_store
    from src.device_fabric.monotonic_fence_anchor import ExternalAtomicMonotonicFenceAnchor,MonotonicAnchorDecision,MonotonicAnchorSecurityLevel
    class MalformedManifestBackend:
        provider_id="remote-controller-authority"
        def snapshot(self):
            return {"tv:living-room":"forged-value"}
        def advance(self,resource_id,controller_id,fencing_token):
            return MonotonicAnchorDecision.ADVANCED
    store_path=tmp_path/"controller-fences.json"
    anchor=ExternalAtomicMonotonicFenceAnchor(MalformedManifestBackend(),security_level=MonotonicAnchorSecurityLevel.REMOTE_ATOMIC)
    store=build_production_controller_fence_store(store_path,monotonic_anchor=anchor)
    with pytest.raises(ValueError,match="trusted anchor unavailable"):
        store.snapshot()
    assert not store_path.exists()
    assert not store.anchorpath.exists()
