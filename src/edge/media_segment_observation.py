import math
from dataclasses import dataclass,field
from enum import Enum,auto

from src.core.monotonic_clock_domain import current_monotonic_clock_domain_id,validate_monotonic_clock_domain_id
from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage,DirectiveProposal
from src.extensions.proposal import ExtensionProposal
from src.extensions.normalization import normalize_proposal


class MediaSegmentKind(Enum):
    INTRO=auto()


class MediaEvidenceSource(Enum):
    METADATA=auto()


@dataclass(frozen=True)
class MediaSegmentObservation:
    observation_id: str
    profile_id: str
    device_id: str
    provider_id: str
    content_id: str
    segment_kind: MediaSegmentKind
    source: MediaEvidenceSource
    observed_monotonic: float
    confidence: float
    segment_start_seconds: float
    segment_end_seconds: float
    evidence_digest: str
    clock_domain_id: str = field(default_factory=current_monotonic_clock_domain_id)

    def __post_init__(self):
        identifiers=(self.observation_id,self.profile_id,self.device_id,self.provider_id,self.content_id)
        if any(type(value) is not str or not value.strip() for value in identifiers):
            raise ValueError("media observation identifier is invalid")
        validate_monotonic_clock_domain_id(self.clock_domain_id)
        if not isinstance(self.segment_kind,MediaSegmentKind):
            raise ValueError("media segment kind is invalid")
        if not isinstance(self.source,MediaEvidenceSource):
            raise ValueError("media evidence source is invalid")
        if type(self.observed_monotonic) not in (int,float) or not math.isfinite(self.observed_monotonic) or self.observed_monotonic<0:
            raise ValueError("media observation monotonic time is invalid")
        if type(self.confidence) not in (int,float) or not math.isfinite(self.confidence) or not 0.0<=self.confidence<=1.0:
            raise ValueError("media observation confidence is invalid")
        if type(self.segment_start_seconds) not in (int,float) or not math.isfinite(self.segment_start_seconds) or self.segment_start_seconds<0:
            raise ValueError("media segment start is invalid")
        if type(self.segment_end_seconds) not in (int,float) or not math.isfinite(self.segment_end_seconds) or self.segment_end_seconds<=self.segment_start_seconds:
            raise ValueError("media segment end is invalid")
        if type(self.evidence_digest) is not str or len(self.evidence_digest)!=64 or any(character not in "0123456789abcdef" for character in self.evidence_digest):
            raise ValueError("media evidence digest is invalid")

    @property
    def grants_physical_authority(self) -> bool:
        return False

@dataclass(frozen=True)
class MediaSegmentProposal:
    directive: DirectiveProposal
    observation: MediaSegmentObservation

    def __post_init__(self):
        if not isinstance(self.directive,DirectiveProposal):
            raise ValueError("adaptive directive proposal is invalid")
        if not isinstance(self.observation,MediaSegmentObservation):
            raise ValueError("media segment observation is invalid")

    @property
    def key(self):
        return self.directive.key

    @property
    def action(self):
        return self.directive.action

    @property
    def confidence(self):
        return self.directive.confidence

    @property
    def threshold(self):
        return self.directive.threshold

    @property
    def strength(self):
        return self.directive.strength

    @property
    def version(self):
        return self.directive.version

    @property
    def context_match(self):
        return self.directive.context_match

    @property
    def grants_physical_authority(self) -> bool:
        return False


class MediaSegmentProposalAdapter:
    def __init__(self,memory: AdaptiveDirectiveMemory):
        if not isinstance(memory,AdaptiveDirectiveMemory):
            raise ValueError("adaptive directive memory is invalid")
        self._memory=memory

    def context_key(self,observation: MediaSegmentObservation) -> tuple[str,str,str,str]:
        if not isinstance(observation,MediaSegmentObservation):
            raise ValueError("media segment observation is invalid")
        if observation.segment_kind is not MediaSegmentKind.INTRO:
            raise ValueError("media segment kind is unsupported")
        return (observation.profile_id,observation.device_id,"show_intro:"+observation.provider_id,observation.content_id)

    def propose(self,observation: MediaSegmentObservation,*,context_match: float,now_monotonic: float,max_age_seconds: float):
        key=self.context_key(observation)
        if type(now_monotonic) not in (int,float) or not math.isfinite(now_monotonic) or now_monotonic<0:
            raise ValueError("proposal monotonic time is invalid")
        if type(max_age_seconds) not in (int,float) or not math.isfinite(max_age_seconds) or max_age_seconds<=0:
            raise ValueError("proposal maximum age is invalid")
        age=now_monotonic-observation.observed_monotonic
        if age<0 or age>max_age_seconds:
            return None
        directive=self._memory.propose(key,confidence=observation.confidence,context_match=context_match)
        if directive is None:
            return None
        return MediaSegmentProposal(directive=directive,observation=observation)

class MediaAutomationDecision(Enum):
    ALLOW=auto()
    PROPOSAL_INVALID=auto()
    OBSERVATION_MISMATCH=auto()
    EVIDENCE_MISMATCH=auto()
    ACTION_UNSUPPORTED=auto()
    NOT_PINNED=auto()
    NOT_AUTOMATE=auto()
    STALE_EVIDENCE=auto()


class MediaAutomationEligibilityGate:
    def __init__(self,memory: AdaptiveDirectiveMemory,proposal_adapter: MediaSegmentProposalAdapter):
        if not isinstance(memory,AdaptiveDirectiveMemory):
            raise ValueError("adaptive directive memory is invalid")
        if not isinstance(proposal_adapter,MediaSegmentProposalAdapter) or proposal_adapter._memory is not memory:
            raise ValueError("media segment proposal adapter is invalid")
        self._memory=memory
        self._proposal_adapter=proposal_adapter

    def evaluate(self,observation,proposal,*,now_monotonic: float,max_age_seconds: float) -> MediaAutomationDecision:
        if type(now_monotonic) not in (int,float) or not math.isfinite(now_monotonic) or now_monotonic<0:
            raise ValueError("eligibility monotonic time is invalid")
        if type(max_age_seconds) not in (int,float) or not math.isfinite(max_age_seconds) or max_age_seconds<=0:
            raise ValueError("eligibility maximum age is invalid")
        try:
            expected_key=self._proposal_adapter.context_key(observation)
            if proposal is None or proposal.key!=expected_key:
                return MediaAutomationDecision.OBSERVATION_MISMATCH
            if not isinstance(proposal,MediaSegmentProposal) or proposal.observation!=observation:
                return MediaAutomationDecision.EVIDENCE_MISMATCH
            if proposal.action!="skip":
                return MediaAutomationDecision.ACTION_UNSUPPORTED
            age=now_monotonic-observation.observed_monotonic
            if age<0 or age>max_age_seconds:
                return MediaAutomationDecision.STALE_EVIDENCE
            if self._memory.proposal_is_current(proposal) is not True:
                return MediaAutomationDecision.PROPOSAL_INVALID
            if self._memory.is_pinned(expected_key) is not True:
                return MediaAutomationDecision.NOT_PINNED
            if self._memory.lifecycle_stage(expected_key) is not DirectiveLifecycleStage.AUTOMATE:
                return MediaAutomationDecision.NOT_AUTOMATE
            return MediaAutomationDecision.ALLOW
        except Exception:
            return MediaAutomationDecision.PROPOSAL_INVALID

class MediaAutomationCandidateNormalizer:
    def __init__(self,eligibility_gate: MediaAutomationEligibilityGate):
        if not isinstance(eligibility_gate,MediaAutomationEligibilityGate):
            raise ValueError("media automation eligibility gate is invalid")
        self._eligibility_gate=eligibility_gate

    def normalize(self,observation,proposal,*,now_monotonic: float,max_age_seconds: float):
        decision=self._eligibility_gate.evaluate(observation,proposal,now_monotonic=now_monotonic,max_age_seconds=max_age_seconds)
        if decision is not MediaAutomationDecision.ALLOW:
            return None
        extension_proposal=ExtensionProposal(
            extension_id="aqss.media.segment",
            capability="playback.position.set",
            target_id=observation.device_id,
            operation="SET_PLAYBACK_POSITION",
            parameters={
                "playback_position_seconds":observation.segment_end_seconds,
                "observation_id":observation.observation_id,
                "evidence_digest":observation.evidence_digest,
                "observed_monotonic":observation.observed_monotonic,
                "evidence_expires_monotonic":observation.observed_monotonic+float(max_age_seconds),
                "evidence_clock_domain_id":observation.clock_domain_id,
                "segment_start_seconds":observation.segment_start_seconds,
                "segment_end_seconds":observation.segment_end_seconds,
                "directive_key":proposal.key,
                "directive_version":proposal.version,
            },
        )
        return normalize_proposal(extension_proposal)

class MediaAutomationCandidateAdmission:
    def __init__(self,normalizer,observation,proposal,*,monotonic_clock,max_age_seconds):
        if not isinstance(normalizer,MediaAutomationCandidateNormalizer):
            raise ValueError("media candidate normalizer is required")
        if not isinstance(observation,MediaSegmentObservation):
            raise ValueError("media segment observation is required")
        if not isinstance(proposal,MediaSegmentProposal):
            raise ValueError("evidence-bound media proposal is required")
        if not callable(monotonic_clock):
            raise ValueError("monotonic clock is required")
        if type(max_age_seconds) not in (int,float) or not math.isfinite(max_age_seconds) or max_age_seconds<0:
            raise ValueError("max evidence age must be a finite nonnegative number")
        self._normalizer=normalizer
        self._observation=observation
        self._proposal=proposal
        self._monotonic_clock=monotonic_clock
        self._max_age_seconds=float(max_age_seconds)

    def __call__(self,candidate) -> bool:
        try:
            currently_eligible=self._normalizer.normalize(self._observation,self._proposal,now_monotonic=self._monotonic_clock(),max_age_seconds=self._max_age_seconds)
        except Exception:
            return False
        return currently_eligible is not None and candidate==currently_eligible

