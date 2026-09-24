from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Callable


@dataclass
class _Entry:
    model: object
    unload: Callable[[object], None]
    users: int = 0
    unloading: bool = False
    memory_mb: int = 0
    last_used: int = 0


class ModelCache:
    def __init__(self, max_memory_mb: int | None = None):
        if max_memory_mb is not None and max_memory_mb < 0:
            raise ValueError("max_memory_mb must be nonnegative")
        self._entries = {}
        self._lock = Lock()
        self._max_memory_mb = max_memory_mb
        self._resident_memory_mb = 0
        self._clock = 0

    def register(self, key: tuple[str, str], model: object, *, memory_mb: int = 0, unload: Callable[[object], None]):
        if not callable(unload):
            raise TypeError("unload must be callable")
        if memory_mb < 0:
            raise ValueError("memory_mb must be nonnegative")
        with self._lock:
            if key in self._entries:
                raise ValueError("model key already registered")
            self._clock += 1
            self._entries[key] = _Entry(model, unload, memory_mb=memory_mb, last_used=self._clock)
            self._resident_memory_mb += memory_mb
        self._enforce_budget()

    def set_memory_budget(self, max_memory_mb: int | None):
        if max_memory_mb is not None and max_memory_mb < 0:
            raise ValueError("max_memory_mb must be nonnegative")
        with self._lock:
            self._max_memory_mb = max_memory_mb
        self._enforce_budget()

    def _enforce_budget(self):
        while True:
            with self._lock:
                if self._max_memory_mb is None or self._resident_memory_mb <= self._max_memory_mb:
                    return
                candidates=[(entry.last_used,key) for key,entry in self._entries.items() if not entry.users and not entry.unloading]
                if not candidates:
                    return
                key=min(candidates)[1]
            if not self.evict(key):
                return

    @contextmanager
    def acquire(self, key: tuple[str, str]):
        with self._lock:
            entry = self._entries[key]
            if entry.unloading:
                raise RuntimeError("model unavailable during or after failed unload")
            entry.users += 1
            self._clock += 1
            entry.last_used = self._clock
        try:
            yield entry.model
        finally:
            with self._lock:
                entry.users -= 1
            self._enforce_budget()

    def allocated_memory_mb(self) -> int:
        with self._lock:
            return self._resident_memory_mb

    def resident_models(self) -> frozenset[tuple[str, str]]:
        with self._lock:
            return frozenset(key for key, entry in self._entries.items() if not entry.unloading)

    def evict(self, key: tuple[str, str]) -> bool:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.users or entry.unloading:
                return False
            entry.unloading = True
        entry.unload(entry.model)
        with self._lock:
            del self._entries[key]
            self._resident_memory_mb -= entry.memory_mb
        return True
