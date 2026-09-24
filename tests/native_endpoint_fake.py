"""Bounded N1 test fixture for work ordering, with no device I/O or authority.

One instance models one resource and one handoff. Settlement and observations
are explicitly injected by tests, never discovered from a real output. This
fake cannot certify native exclusion, release a production hold, or authorize
successor execution. The native implementation and physical experiment are
later roadmap gates.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class NativeTraceEvent:
    sequence: int
    kind: str
    work_id: str | None
    generation: int


@dataclass(frozen=True, slots=True)
class _Work:
    work_id: str
    generation: int
    parent_id: str | None = None
    phase: str = "accepted"
    disposition: str = "unknown"
    observed: bool = False


def _positive_integer(value):
    if type(value) is not int or value <= 0:
        raise ValueError("expected a positive integer")
    return value


def _identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError("expected a nonblank work identifier")
    return value


class UnqualifiedNativeEndpointFake:
    """Explicit event ordering only; every production readiness result is False."""

    def __init__(self, *, max_work_items=32):
        self._limit = _positive_integer(max_work_items)
        self._work = {}
        self._events = []
        self._retired_through = None

    def _record(self, kind, work_id, generation):
        # Each work has at most six events; one generation-close event is allowed.
        # Rejected/replayed operations append nothing. No records are evicted.
        self._events.append(NativeTraceEvent(len(self._events) + 1, kind, work_id, generation))

    @property
    def trace(self):
        return tuple(self._events)

    @property
    def applied_work(self):
        return tuple(event.work_id for event in self._events if event.kind == "simulated_applied")

    @property
    def observed_work(self):
        return tuple(event.work_id for event in self._events if event.kind == "simulated_observed")

    @property
    def app_queue_empty(self):
        return not any(work.phase == "published" and work.disposition == "unknown" for work in self._work.values())

    @property
    def old_work_settled(self):
        # Model bookkeeping only; this property is not native qualification.
        return self._retired_through is not None and all(
            work.disposition in ("completed", "discarded")
            for work in self._work.values()
            if work.generation <= self._retired_through
        )

    @property
    def production_ready(self):
        return False

    def _accept(self, work_id, generation, parent_id):
        work_id = _identifier(work_id)
        generation = _positive_integer(generation)
        existing = self._work.get(work_id)
        if existing is not None:
            if (existing.generation, existing.parent_id) != (generation, parent_id):
                raise ValueError("work binding mismatch")
            return False
        if self._retired_through is not None:
            return False
        if len(self._work) >= self._limit:
            raise BufferError("native work registry full")
        self._work[work_id] = _Work(work_id, generation, parent_id)
        self._record("accepted", work_id, generation)
        return True

    def accept(self, work_id, *, generation):
        return self._accept(work_id, generation, None)

    def register_descendant(self, work_id, *, parent_id):
        parent = self._work[_identifier(parent_id)]
        if parent.disposition != "unknown" or self._retired_through is not None:
            return False
        # Registration precedes parent settlement. Its child is never dropped
        # when the parent settles, and it keeps the parent's original generation.
        return self._accept(work_id, parent.generation, parent.work_id)

    def _advance(self, work_id, expected, phase, event, *, publication=False):
        work = self._work[_identifier(work_id)]
        if work.phase != expected or work.disposition != "unknown":
            return False
        if publication and self._retired_through is not None:
            return False
        self._work[work_id] = replace(work, phase=phase)
        self._record(event, work_id, work.generation)
        return True

    def publish(self, work_id):
        return self._advance(work_id, "accepted", "published", "published", publication=True)

    def submit(self, work_id):
        return self._advance(work_id, "published", "submitted", "submitted", publication=True)

    def apply(self, work_id):
        # A submitted native frame can still produce an effect after a hold.
        # The hold alone must not be modeled as cancellation of that frame.
        return self._advance(work_id, "submitted", "applied", "simulated_applied")

    def observe(self, work_id):
        work = self._work[_identifier(work_id)]
        if work.phase != "applied" or work.observed:
            return False
        self._work[work_id] = replace(work, observed=True)
        self._record("simulated_observed", work_id, work.generation)
        return True

    def settle(self, work_id, *, disposition):
        work = self._work[_identifier(work_id)]
        if type(disposition) is not str or disposition not in ("unknown", "partial", "completed", "discarded"):
            raise ValueError("invalid output disposition")
        if work.disposition != "unknown":
            if work.disposition != disposition:
                raise ValueError("native settlement conflict")
            return False
        if disposition in ("unknown", "partial"):
            return False
        if disposition == "completed" and work.phase != "applied":
            return False
        if disposition == "discarded" and work.phase == "applied":
            return False
        self._work[work_id] = replace(work, disposition=disposition)
        self._record("native_settled", work_id, work.generation)
        return True

    def close_generation(self, generation):
        generation = _positive_integer(generation)
        if self._retired_through is not None:
            if generation != self._retired_through:
                raise ValueError("this fake models one handoff only")
            return False
        self._retired_through = generation
        # Inhibition is not queued behind work and cannot fail on registry capacity.
        self._record("generation_closed", None, generation)
        return True

    def native_snapshot(self):
        retained = sorted({work.generation for work in self._work.values()})
        retired = self._retired_through or 0
        return {
            "backend_qualified": False,
            "evidence_authorized": False,
            "history_authenticated": False,
            "route_enforced": False,
            "cut_closed": False,
            "admission_closed": self._retired_through is not None,
            "publication_closed": self._retired_through is not None,
            "app_queue_empty": self.app_queue_empty,
            "retained_generations": retained,
            "closed_generations": [generation for generation in retained if generation <= retired],
            "retired_through_generation": retired,
            "work": [
                {"id": work.work_id, "generation": work.generation,
                 "settled": work.disposition in ("completed", "discarded")}
                for work in self._work.values()
            ],
        }
