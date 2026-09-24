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


@dataclass(frozen=True, slots=True)
class SyntheticSubmissionCandidate:
    """In-memory test token, not signed authority or a retirement certificate."""

    work_id: str
    generation: int
    runtime_id: str
    route_id: str
    route_epoch: int
    request_id: str
    controller_id: str
    fencing_token: int
    activated_at: int
    expires_at: int
    context_revision: int


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
        # Synthetic context only. No OS callback, clock, or durable store exists.
        self._runtime_id = "runtime-one"
        self._actual_route_id = self._cached_route_id = "built-in"
        self._actual_route_epoch = self._cached_route_epoch = 1
        self._request_id = "handoff-a-to-b"
        self._controller_id = "phone-b"
        self._fencing_token = 9
        self._protection_active = True
        self._context_revision = 0
        self._candidates = {}
        self._published_runtime = {}

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
        return not any(
            work.phase == "published" and work.disposition == "unknown"
            and self._published_runtime.get(work.work_id) == self._runtime_id
            for work in self._work.values()
        )

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
        if not self._advance(work_id, "accepted", "published", "published", publication=True):
            return False
        self._published_runtime[work_id] = self._runtime_id
        return True

    def context_snapshot(self):
        """Copy the simulated actual and cached state; neither is physical evidence."""
        return {
            "runtime_id": self._runtime_id,
            "actual_route_id": self._actual_route_id,
            "actual_route_epoch": self._actual_route_epoch,
            "cached_route_id": self._cached_route_id,
            "cached_route_epoch": self._cached_route_epoch,
            "request_id": self._request_id,
            "controller_id": self._controller_id,
            "fencing_token": self._fencing_token,
            "protection_active": self._protection_active,
            "revision": self._context_revision,
        }

    def restart_runtime(self, runtime_id):
        """Synthetic incarnation change; retained work is in memory, not persisted."""
        runtime_id = _identifier(runtime_id)
        if runtime_id == self._runtime_id:
            return False
        self._runtime_id = runtime_id
        self._context_revision += 1
        return True

    def switch_actual_route(self, route_id, *, route_epoch):
        """Change actual output before the delayed application notification."""
        route_id = _identifier(route_id)
        route_epoch = _positive_integer(route_epoch)
        if route_epoch <= self._actual_route_epoch:
            raise ValueError("actual route epoch must advance")
        self._actual_route_id = route_id
        self._actual_route_epoch = route_epoch
        self._context_revision += 1
        return True

    def notify_route(self):
        if (self._cached_route_id, self._cached_route_epoch) == (
            self._actual_route_id, self._actual_route_epoch
        ):
            return False
        self._cached_route_id = self._actual_route_id
        self._cached_route_epoch = self._actual_route_epoch
        return True

    def replace_successor(self, *, request_id, controller_id, fencing_token):
        request_id = _identifier(request_id)
        controller_id = _identifier(controller_id)
        fencing_token = _positive_integer(fencing_token)
        if (request_id, controller_id, fencing_token) == (
            self._request_id, self._controller_id, self._fencing_token
        ):
            return False
        if fencing_token <= self._fencing_token:
            raise ValueError("successor token must advance")
        self._request_id = request_id
        self._controller_id = controller_id
        self._fencing_token = fencing_token
        self._context_revision += 1
        return True

    def set_protection_active(self, active):
        if type(active) is not bool:
            raise ValueError("protection state must be boolean")
        if active == self._protection_active:
            return False
        self._protection_active = active
        self._context_revision += 1
        return True

    def activate_candidate(
        self, work_id, *, request_id, controller_id, fencing_token,
        activated_at, expires_at,
    ):
        """Capture a synthetic scope; it cannot authorize real execution."""
        work_id = _identifier(work_id)
        request_id = _identifier(request_id)
        controller_id = _identifier(controller_id)
        fencing_token = _positive_integer(fencing_token)
        if (type(activated_at) is not int or type(expires_at) is not int
                or activated_at < 0 or activated_at >= expires_at):
            raise ValueError("invalid synthetic activation window")
        work = self._work[work_id]
        if (work.phase != "published" or work.disposition != "unknown"
                or self._retired_through is not None or not self._protection_active
                or work_id in self._candidates
                or self._published_runtime.get(work_id) != self._runtime_id
                or (request_id, controller_id, fencing_token) != (
                    self._request_id, self._controller_id, self._fencing_token
                )):
            return None
        candidate = SyntheticSubmissionCandidate(
            work_id, work.generation, self._runtime_id,
            self._actual_route_id, self._actual_route_epoch,
            request_id, controller_id, fencing_token, activated_at,
            expires_at, self._context_revision,
        )
        self._candidates[work_id] = candidate
        return candidate

    def submit(self, work_id, *, candidate=None, at=None):
        """Recheck the live synthetic scope at the final state transition."""
        work_id = _identifier(work_id)
        bound = self._candidates.get(work_id)
        if bound is not None:
            if (candidate is not bound or type(at) is not int
                    or at < bound.activated_at or at >= bound.expires_at
                    or not self._protection_active
                    or bound.context_revision != self._context_revision
                    or bound.runtime_id != self._runtime_id
                    or (bound.route_id, bound.route_epoch) != (
                        self._actual_route_id, self._actual_route_epoch
                    )
                    or (bound.request_id, bound.controller_id, bound.fencing_token) != (
                        self._request_id, self._controller_id, self._fencing_token
                    )):
                return False
        elif (candidate is not None or at is not None
              or self._context_revision or not self._protection_active):
            # The legacy unbound work simulation only runs in its original scope.
            return False
        # An old application's published work cannot escape a new incarnation.
        if self._published_runtime.get(work_id) != self._runtime_id:
            return False
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
            "actual_route_id": self._actual_route_id,
            "actual_route_epoch": self._actual_route_epoch,
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
