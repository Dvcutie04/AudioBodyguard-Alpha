def test_cache_protects_active_model_and_unloads_after_release():
    from src.edge.model_cache import ModelCache
    key=("acoustic_event_detection","1.0.0")
    model=object()
    unload_calls=[]
    cache=ModelCache()
    cache.register(key,model,unload=lambda value: unload_calls.append(value))
    with cache.acquire(key) as acquired:
        assert acquired is model
        assert cache.evict(key) is False
        assert unload_calls==[]
    assert cache.evict(key) is True
    assert len(unload_calls)==1
    assert unload_calls[0] is model
    assert cache.evict(key) is False
    assert len(unload_calls)==1


def test_cache_waits_for_all_acquisitions_before_unloading():
    from src.edge.model_cache import ModelCache
    key=("acoustic_event_detection","1.0.0")
    model=object()
    unload_calls=[]
    cache=ModelCache()
    cache.register(key,model,unload=lambda value: unload_calls.append(value))
    with cache.acquire(key) as first:
        with cache.acquire(key) as second:
            assert first is model
            assert second is model
            assert cache.evict(key) is False
            assert unload_calls==[]
        assert cache.evict(key) is False
        assert unload_calls==[]
    assert cache.evict(key) is True
    assert len(unload_calls)==1
    assert unload_calls[0] is model


def test_cache_releases_acquisition_when_model_use_raises():
    import pytest
    from src.edge.model_cache import ModelCache
    key=("acoustic_event_detection","1.0.0")
    model=object()
    unload_calls=[]
    cache=ModelCache()
    cache.register(key,model,unload=lambda value: unload_calls.append(value))
    failure=RuntimeError("inference failed")
    with pytest.raises(RuntimeError) as caught:
        with cache.acquire(key) as acquired:
            assert acquired is model
            raise failure
    assert caught.value is failure
    assert unload_calls==[]
    assert cache.evict(key) is True
    assert len(unload_calls)==1
    assert unload_calls[0] is model


def test_cache_failed_unload_blocks_reacquisition_and_repeat_unload():
    import pytest
    from src.edge.model_cache import ModelCache
    key=("acoustic_event_detection","1.0.0")
    model=object()
    unload_calls=[]
    failure=RuntimeError("unload failed")
    def unload(value):
        unload_calls.append(value)
        raise failure
    cache=ModelCache()
    cache.register(key,model,unload=unload)
    with pytest.raises(RuntimeError) as caught:
        cache.evict(key)
    assert caught.value is failure
    with pytest.raises(RuntimeError):
        with cache.acquire(key):
            pytest.fail("failed-unload model must not be acquired")
    assert cache.evict(key) is False
    assert len(unload_calls)==1
    assert unload_calls[0] is model


def test_cache_reports_only_available_models_as_resident():
    import pytest
    from src.edge.model_cache import ModelCache
    ready=("acoustic_event_detection","1.0.0")
    failed=("deep_reasoning","1.0.0")
    ready_model=object()
    failed_model=object()
    cache=ModelCache()
    cache.register(ready,ready_model,unload=lambda value: None)
    cache.register(failed,failed_model,unload=lambda value: (_ for _ in ()).throw(RuntimeError("unload failed")))
    assert cache.resident_models()==frozenset({ready,failed})
    with pytest.raises(RuntimeError):
        cache.evict(failed)
    assert cache.resident_models()==frozenset({ready})
    assert cache.evict(ready) is True
    assert cache.resident_models()==frozenset()


def test_cache_evicts_least_recently_used_idle_model_to_meet_memory_budget():
    from src.edge.model_cache import ModelCache
    first_key=("acoustic_event_detection","1.0.0")
    second_key=("deep_reasoning","1.0.0")
    first_model=object()
    second_model=object()
    unload_calls=[]
    cache=ModelCache(max_memory_mb=64)
    cache.register(first_key,first_model,memory_mb=40,unload=lambda value: unload_calls.append(value))
    cache.register(second_key,second_model,memory_mb=40,unload=lambda value: unload_calls.append(value))
    assert cache.resident_models()==frozenset({second_key})
    assert unload_calls==[first_model]
    with cache.acquire(second_key) as acquired:
        assert acquired is second_model


def test_cache_acquisition_refreshes_lru_recency():
    from src.edge.model_cache import ModelCache
    first_key=("acoustic_event_detection","1.0.0")
    second_key=("speech_recognition","1.0.0")
    third_key=("deep_reasoning","1.0.0")
    first_model=object()
    second_model=object()
    third_model=object()
    unload_calls=[]
    cache=ModelCache(max_memory_mb=40)
    cache.register(first_key,first_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    cache.register(second_key,second_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    with cache.acquire(first_key) as acquired:
        assert acquired is first_model
    cache.register(third_key,third_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    assert cache.resident_models()==frozenset({first_key,third_key})
    assert unload_calls==[second_model]


def test_cache_memory_pressure_never_evicts_active_model():
    from src.edge.model_cache import ModelCache
    active_key=("acoustic_event_detection","1.0.0")
    incoming_key=("deep_reasoning","1.0.0")
    active_model=object()
    incoming_model=object()
    unload_calls=[]
    cache=ModelCache(max_memory_mb=40)
    cache.register(active_key,active_model,memory_mb=40,unload=lambda value: unload_calls.append(value))
    with cache.acquire(active_key) as acquired:
        assert acquired is active_model
        cache.register(incoming_key,incoming_model,memory_mb=40,unload=lambda value: unload_calls.append(value))
        assert cache.resident_models()==frozenset({active_key})
        assert unload_calls==[incoming_model]
    with cache.acquire(active_key) as acquired:
        assert acquired is active_model


def test_cache_shrinks_runtime_memory_budget_by_evicting_lru_idle_model():
    from src.edge.model_cache import ModelCache
    first_key=("acoustic_event_detection","1.0.0")
    second_key=("speech_recognition","1.0.0")
    third_key=("deep_reasoning","1.0.0")
    first_model=object()
    second_model=object()
    third_model=object()
    unload_calls=[]
    cache=ModelCache(max_memory_mb=60)
    cache.register(first_key,first_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    cache.register(second_key,second_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    cache.register(third_key,third_model,memory_mb=20,unload=lambda value: unload_calls.append(value))
    with cache.acquire(first_key):
        pass
    cache.set_memory_budget(40)
    assert cache.resident_models()==frozenset({first_key,third_key})
    assert unload_calls==[second_model]


def test_cache_enforces_pending_memory_budget_after_active_model_release():
    from src.edge.model_cache import ModelCache
    key=("acoustic_event_detection","1.0.0")
    model=object()
    unload_calls=[]
    cache=ModelCache(max_memory_mb=40)
    cache.register(key,model,memory_mb=40,unload=lambda value: unload_calls.append(value))
    with cache.acquire(key) as acquired:
        assert acquired is model
        cache.set_memory_budget(20)
        assert cache.resident_models()==frozenset({key})
        assert unload_calls==[]
    assert cache.resident_models()==frozenset()
    assert unload_calls==[model]


def test_cache_reports_allocated_memory_including_failed_unload():
    import pytest
    from src.edge.model_cache import ModelCache
    ready=("acoustic_event_detection","1.0.0")
    failed=("deep_reasoning","1.0.0")
    cache=ModelCache(max_memory_mb=64)
    cache.register(ready,object(),memory_mb=24,unload=lambda value: None)
    cache.register(failed,object(),memory_mb=32,unload=lambda value: (_ for _ in ()).throw(RuntimeError("unload failed")))
    assert cache.allocated_memory_mb()==56
    with pytest.raises(RuntimeError):
        cache.evict(failed)
    assert cache.resident_models()==frozenset({ready})
    assert cache.allocated_memory_mb()==56
    assert cache.evict(ready) is True
    assert cache.allocated_memory_mb()==32
