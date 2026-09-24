from dataclasses import dataclass, replace
from enum import Enum, auto
from threading import Lock
from time import time


class DirectiveStatus(Enum):
    CANDIDATE = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    BLOCKED = auto()


class DirectiveLifecycleStage(Enum):
    OBSERVE = auto()
    SUGGEST = auto()
    SHADOW = auto()
    AUTOMATE = auto()
    SUSPEND = auto()


class DirectiveSuspensionReason(Enum):
    EXPLICIT_NEGATIVE_FEEDBACK = auto()
    NEVER_AUTOMATE = auto()
    POLICY_BLOCK = auto()


class FeedbackSource(Enum):
    TOUCH = auto()
    VOICE = auto()


class ProfileConfidenceBand(Enum):
    UNVERIFIED = auto()
    VERY_LOW = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    VERY_HIGH = auto()


class FeedbackMenuDirection(Enum):
    DOWN = auto()
    UP = auto()


class FeedbackReason(Enum):
    CORRECT_ACTION = auto()
    CORRECT_TIMING = auto()
    RIGHT_AMOUNT = auto()
    RIGHT_CONTEXT = auto()
    HELPFUL_AUTOMATION = auto()
    REMEMBER_THIS = auto()
    WRONG_ACTION = auto()
    TOO_EARLY = auto()
    TOO_LATE = auto()
    TOO_MUCH = auto()
    TOO_LITTLE = auto()
    WRONG_CONTEXT = auto()
    ASKED_TOO_OFTEN = auto()
    NEVER_AUTOMATE = auto()


_POSITIVE_FEEDBACK_REASONS = (FeedbackReason.CORRECT_ACTION, FeedbackReason.CORRECT_TIMING, FeedbackReason.RIGHT_AMOUNT, FeedbackReason.RIGHT_CONTEXT, FeedbackReason.HELPFUL_AUTOMATION, FeedbackReason.REMEMBER_THIS)
_NEGATIVE_FEEDBACK_REASONS = (FeedbackReason.WRONG_ACTION, FeedbackReason.TOO_EARLY, FeedbackReason.TOO_LATE, FeedbackReason.TOO_MUCH, FeedbackReason.TOO_LITTLE, FeedbackReason.WRONG_CONTEXT, FeedbackReason.ASKED_TOO_OFTEN, FeedbackReason.NEVER_AUTOMATE)


def feedback_reasons(*, approved: bool) -> tuple[FeedbackReason, ...]:
    return _POSITIVE_FEEDBACK_REASONS if approved else _NEGATIVE_FEEDBACK_REASONS


@dataclass(frozen=True)
class FeedbackEvent:
    key: tuple[str, str, str, str]
    approved: bool
    source: FeedbackSource
    reason: FeedbackReason
    strength_before: int
    strength_after: int


@dataclass(frozen=True)
class FeedbackLedgerRecord:
    context_ids: tuple[str, str, str, str]
    action_code: str
    approved: bool
    source: FeedbackSource
    reason: FeedbackReason
    strength_delta: int
    profile_confidence_band: ProfileConfidenceBand
    timestamp_bucket: int

    @property
    def grants_physical_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class FeedbackMenuItem:
    reason: FeedbackReason
    label: str
    accessibility_identifier: str


@dataclass(frozen=True)
class FeedbackMenu:
    approved: bool
    direction: FeedbackMenuDirection
    reasons: tuple[FeedbackReason, ...]
    strength: int

    @property
    def items(self) -> tuple[FeedbackMenuItem, ...]:
        return tuple(FeedbackMenuItem(reason, reason.name.replace("_", " ").capitalize(), "feedback_reason_" + reason.name.lower()) for reason in self.reasons)


@dataclass(frozen=True)
class VoiceFeedbackCandidate:
    approved: bool
    reason: FeedbackReason
    confidence: float

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True)
class DirectiveProposal:
    key: tuple[str, str, str, str]
    action: str
    confidence: float
    threshold: float
    strength: int
    version: int
    context_match: float

    @property
    def grants_physical_authority(self) -> bool:
        return False


class DirectivePersistenceScope(Enum):
    SESSION_ONLY = auto()
    DURABLE = auto()


@dataclass(frozen=True)
class AdaptiveDirective:
    key: tuple[str, str, str, str]
    action: str
    status: DirectiveStatus
    strength: int = 13
    pinned: bool = False
    lifecycle_stage: DirectiveLifecycleStage = DirectiveLifecycleStage.OBSERVE
    suspension_reason: DirectiveSuspensionReason | None = None
    persistence_scope: DirectivePersistenceScope = DirectivePersistenceScope.DURABLE


class AdaptiveDirectiveMemory:
    def __init__(self, max_entries: int):
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._entries = {}
        self._reason_counts = {}
        self._versions = {}
        self._next_version = 0
        self._feedback_ledger = []
        self._lock = Lock()

    @staticmethod
    def _validate_context_key(key: tuple[str, str, str, str]) -> None:
        if not isinstance(key, tuple) or len(key) != 4 or any(not isinstance(part, str) or not part.strip() for part in key):
            raise ValueError("invalid context key")

    def remember(self, key: tuple[str, str, str, str], *, action: str, pinned: bool = False, persistence_scope: DirectivePersistenceScope = DirectivePersistenceScope.DURABLE):
        self._validate_context_key(key)
        if not isinstance(persistence_scope, DirectivePersistenceScope):
            raise ValueError("invalid directive persistence scope")
        with self._lock:
            if key in self._entries:
                existing = self._entries[key]
                if existing.status is DirectiveStatus.BLOCKED:
                    raise ValueError("blocked directive requires explicit replacement")
                if existing.action == action and existing.pinned == pinned and existing.persistence_scope is persistence_scope:
                    del self._entries[key]
                    self._entries[key] = existing
                    return
                del self._entries[key]
                self._reason_counts = {record: count for record, count in self._reason_counts.items() if record[0] != key}
            elif len(self._entries) >= self._max_entries:
                candidates = [existing_key for existing_key, directive in self._entries.items() if not directive.pinned and directive.status is DirectiveStatus.CANDIDATE]
                evictable = candidates or [existing_key for existing_key, directive in self._entries.items() if not directive.pinned]
                if not evictable:
                    raise MemoryError("directive memory contains only pinned entries")
                evicted_key = evictable[0]
                del self._entries[evicted_key]
                del self._versions[evicted_key]
                self._reason_counts = {record: count for record, count in self._reason_counts.items() if record[0] != evicted_key}
            status = DirectiveStatus.ACTIVE if pinned else DirectiveStatus.CANDIDATE
            self._entries[key] = AdaptiveDirective(key, action, status, pinned=pinned, persistence_scope=persistence_scope)
            self._next_version += 1
            self._versions[key] = self._next_version

    def long_press_menu(self, key: tuple[str, str, str, str], *, approved: bool) -> FeedbackMenu:
        self._validate_context_key(key)
        with self._lock:
            reasons = feedback_reasons(approved=approved)
            ranked = tuple(sorted(reasons, key=lambda reason: -self._reason_counts.get((key, approved, reason), 0)))
            strength = self._entries[key].strength
        direction = FeedbackMenuDirection.DOWN if approved else FeedbackMenuDirection.UP
        return FeedbackMenu(approved, direction, ranked, strength)

    def accept_voice_candidate(self, key: tuple[str, str, str, str], candidate: VoiceFeedbackCandidate, *, min_confidence: float) -> FeedbackEvent:
        self._validate_context_key(key)
        if candidate.reason is FeedbackReason.NEVER_AUTOMATE:
            raise ValueError("never automate requires explicit user confirmation")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("minimum confidence must be between zero and one")
        if candidate.confidence < min_confidence:
            raise ValueError("confidence below policy threshold")
        return self.feedback(key, approved=candidate.approved, source=FeedbackSource.VOICE, reason=candidate.reason)

    def feedback_from_voice(self, key: tuple[str, str, str, str], utterance: str) -> FeedbackEvent:
        self._validate_context_key(key)
        normalized = " ".join(utterance.casefold().strip(" .!?").split())
        interpretations = {"that happened too late": (False, FeedbackReason.TOO_LATE), "perfect timing": (True, FeedbackReason.CORRECT_TIMING)}
        interpretation = interpretations.get(normalized)
        if interpretation is None:
            raise ValueError("unrecognized voice feedback")
        approved, reason = interpretation
        return self.feedback(key, approved=approved, source=FeedbackSource.VOICE, reason=reason)

    def ranked_feedback_reasons(self, key: tuple[str, str, str, str], *, approved: bool) -> tuple[FeedbackReason, ...]:
        self._validate_context_key(key)
        reasons = feedback_reasons(approved=approved)
        with self._lock:
            return tuple(sorted(reasons, key=lambda reason: -self._reason_counts.get((key, approved, reason), 0)))

    def replace_blocked(self, key: tuple[str, str, str, str], *, action: str) -> AdaptiveDirective:
        self._validate_context_key(key)
        with self._lock:
            directive = self._entries[key]
            if directive.status is not DirectiveStatus.BLOCKED:
                raise ValueError("only a blocked directive can be explicitly replaced")
            replacement = AdaptiveDirective(key, action, DirectiveStatus.ACTIVE, strength=13, pinned=True)
            del self._entries[key]
            self._reason_counts = {record: count for record, count in self._reason_counts.items() if record[0] != key}
            self._entries[key] = replacement
            self._next_version += 1
            self._versions[key] = self._next_version
            return replacement

    def feedback(self, key: tuple[str, str, str, str], *, approved: bool, source: FeedbackSource = FeedbackSource.TOUCH, reason: FeedbackReason | None = None, profile_confidence_band: ProfileConfidenceBand = ProfileConfidenceBand.UNVERIFIED, timestamp_bucket: int | None = None) -> FeedbackEvent:
        self._validate_context_key(key)
        if not isinstance(profile_confidence_band, ProfileConfidenceBand):
            raise ValueError("invalid profile confidence band")
        if timestamp_bucket is None:
            timestamp_bucket = int(time() // 900)
        if isinstance(timestamp_bucket, bool) or not isinstance(timestamp_bucket, int) or timestamp_bucket < 0:
            raise ValueError("invalid timestamp bucket")
        with self._lock:
            directive = self._entries[key]
            if directive.status is DirectiveStatus.BLOCKED:
                raise ValueError("blocked directive requires explicit replacement")
            if reason is None:
                reason = FeedbackReason.CORRECT_ACTION if approved else FeedbackReason.WRONG_ACTION
            valid_reasons = _POSITIVE_FEEDBACK_REASONS if approved else _NEGATIVE_FEEDBACK_REASONS
            if reason not in valid_reasons:
                raise ValueError("feedback reason does not match approval")
            self._reason_counts[(key, approved, reason)] = self._reason_counts.get((key, approved, reason), 0) + 1
            strength_before = directive.strength
            pinned = directive.pinned
            if reason is FeedbackReason.NEVER_AUTOMATE:
                status = DirectiveStatus.BLOCKED
                strength_after = 1
                pinned = True
                lifecycle_stage = DirectiveLifecycleStage.SUSPEND
                suspension_reason = DirectiveSuspensionReason.NEVER_AUTOMATE
            else:
                status = DirectiveStatus.ACTIVE if approved else DirectiveStatus.SUSPENDED
                strength_after = min(25, strength_before + 1) if approved else max(1, strength_before - 2)
                lifecycle_stage = DirectiveLifecycleStage.SUGGEST if approved else DirectiveLifecycleStage.SUSPEND
                suspension_reason = None if approved else DirectiveSuspensionReason.EXPLICIT_NEGATIVE_FEEDBACK
            self._entries[key] = replace(directive, status=status, strength=strength_after, pinned=pinned, lifecycle_stage=lifecycle_stage, suspension_reason=suspension_reason)
            self._next_version += 1
            self._versions[key] = self._next_version
            self._feedback_ledger.append(FeedbackLedgerRecord(key, directive.action, approved, source, reason, strength_after - strength_before, profile_confidence_band, timestamp_bucket))
            if len(self._feedback_ledger) > self._max_entries:
                del self._feedback_ledger[0]
            return FeedbackEvent(key, approved, source, reason, strength_before, strength_after)

    def feedback_ledger(self) -> tuple[FeedbackLedgerRecord, ...]:
        with self._lock:
            return tuple(self._feedback_ledger)

    def recall(self, key: tuple[str, str, str, str]) -> AdaptiveDirective | None:
        self._validate_context_key(key)
        with self._lock:
            directive = self._entries.get(key)
            if directive is None or directive.status is not DirectiveStatus.ACTIVE:
                return None
            del self._entries[key]
            self._entries[key] = directive
            return directive

    def persistence_scope(self, key: tuple[str, str, str, str]) -> DirectivePersistenceScope:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].persistence_scope

    def durable_directives(self) -> tuple[AdaptiveDirective, ...]:
        with self._lock:
            return tuple(directive for directive in self._entries.values() if directive.persistence_scope is DirectivePersistenceScope.DURABLE)

    def is_pinned(self, key: tuple[str, str, str, str]) -> bool:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].pinned

    def propose(self, key: tuple[str, str, str, str], *, confidence: float, context_match: float) -> DirectiveProposal | None:
        self._validate_context_key(key)
        if isinstance(confidence, bool) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")
        if isinstance(context_match, bool) or not 0.0 <= context_match <= 1.0:
            raise ValueError("context match must be between zero and one")
        with self._lock:
            directive = self._entries[key]
            threshold = (26 - directive.strength) / 25
            if directive.status is not DirectiveStatus.ACTIVE or confidence < threshold or context_match < threshold:
                return None
            return DirectiveProposal(directive.key, directive.action, confidence, threshold, directive.strength, self._versions[key], context_match)

    def version(self, key: tuple[str, str, str, str]) -> int:
        self._validate_context_key(key)
        with self._lock:
            if key not in self._entries:
                raise KeyError(key)
            return self._versions[key]

    def proposal_is_current(self, proposal: DirectiveProposal) -> bool:
        try:
            hash(proposal.key)
        except TypeError:
            return False
        with self._lock:
            directive = self._entries.get(proposal.key)
            return directive is not None and directive.status is DirectiveStatus.ACTIVE and self._versions.get(proposal.key) == proposal.version and directive.action == proposal.action and directive.strength == proposal.strength and (26 - directive.strength) / 25 == proposal.threshold and isinstance(proposal.confidence, (int, float)) and not isinstance(proposal.confidence, bool) and 0.0 <= proposal.confidence <= 1.0 and proposal.confidence >= proposal.threshold and isinstance(proposal.context_match, (int, float)) and not isinstance(proposal.context_match, bool) and 0.0 <= proposal.context_match <= 1.0 and proposal.context_match >= proposal.threshold and proposal.grants_physical_authority is False

    def proposal_threshold(self, key: tuple[str, str, str, str]) -> float:
        self._validate_context_key(key)
        with self._lock:
            return (26 - self._entries[key].strength) / 25

    def should_propose(self, key: tuple[str, str, str, str], *, confidence: float, context_match: float) -> bool:
        self._validate_context_key(key)
        if isinstance(confidence, bool) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")
        if isinstance(context_match, bool) or not 0.0 <= context_match <= 1.0:
            raise ValueError("context match must be between zero and one")
        with self._lock:
            directive = self._entries[key]
            threshold = (26 - directive.strength) / 25
            return directive.status is DirectiveStatus.ACTIVE and confidence >= threshold and context_match >= threshold

    def strength(self, key: tuple[str, str, str, str]) -> int:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].strength

    def suspend_for_policy(self, key: tuple[str, str, str, str]) -> AdaptiveDirective:
        self._validate_context_key(key)
        with self._lock:
            directive = self._entries[key]
            if directive.status in (DirectiveStatus.SUSPENDED, DirectiveStatus.BLOCKED) or directive.lifecycle_stage is DirectiveLifecycleStage.SUSPEND:
                raise ValueError("existing suspension reason cannot be overwritten")
            suspended = replace(directive, status=DirectiveStatus.SUSPENDED, lifecycle_stage=DirectiveLifecycleStage.SUSPEND, suspension_reason=DirectiveSuspensionReason.POLICY_BLOCK)
            self._entries[key] = suspended
            self._next_version += 1
            self._versions[key] = self._next_version
            return suspended

    def advance_lifecycle(self, key: tuple[str, str, str, str], *, target: DirectiveLifecycleStage) -> AdaptiveDirective:
        self._validate_context_key(key)
        if not isinstance(target, DirectiveLifecycleStage):
            raise ValueError("invalid lifecycle target")
        with self._lock:
            directive = self._entries[key]
            transitions = {DirectiveLifecycleStage.OBSERVE: DirectiveLifecycleStage.SUGGEST, DirectiveLifecycleStage.SUGGEST: DirectiveLifecycleStage.SHADOW, DirectiveLifecycleStage.SHADOW: DirectiveLifecycleStage.AUTOMATE}
            if directive.status in (DirectiveStatus.SUSPENDED, DirectiveStatus.BLOCKED) or directive.lifecycle_stage is DirectiveLifecycleStage.SUSPEND:
                raise ValueError("suspended directive cannot advance")
            if transitions.get(directive.lifecycle_stage) is not target:
                raise ValueError("lifecycle stages cannot be skipped")
            advanced = replace(directive, lifecycle_stage=target, suspension_reason=None)
            self._entries[key] = advanced
            self._next_version += 1
            self._versions[key] = self._next_version
            return advanced

    def lifecycle_stage(self, key: tuple[str, str, str, str]) -> DirectiveLifecycleStage:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].lifecycle_stage

    def suspension_reason(self, key: tuple[str, str, str, str]) -> DirectiveSuspensionReason | None:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].suspension_reason

    def status(self, key: tuple[str, str, str, str]) -> DirectiveStatus:
        self._validate_context_key(key)
        with self._lock:
            return self._entries[key].status
