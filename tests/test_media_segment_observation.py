from dataclasses import FrozenInstanceError

import pytest

from src.edge.media_segment_observation import MediaEvidenceSource,MediaSegmentKind,MediaSegmentObservation


def test_high_confidence_intro_observation_is_immutable_authority_free_evidence():
    observation=MediaSegmentObservation(
        observation_id="observation-1",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="a"*64,
    )
    assert observation.segment_kind is MediaSegmentKind.INTRO
    assert observation.source is MediaEvidenceSource.METADATA
    assert observation.grants_physical_authority is False
    assert not hasattr(observation,"adapter")
    assert not hasattr(observation,"execute")
    with pytest.raises(FrozenInstanceError):
        observation.confidence=0.5

@pytest.mark.parametrize("field,value",(
    ("observation_id",""),
    ("profile_id"," "),
    ("device_id",None),
    ("provider_id",""),
    ("content_id","\t"),
    ("segment_kind","INTRO"),
    ("source","METADATA"),
    ("observed_monotonic",True),
    ("observed_monotonic",-1.0),
    ("observed_monotonic",float("nan")),
    ("observed_monotonic",float("inf")),
    ("confidence",True),
    ("confidence",-0.01),
    ("confidence",1.01),
    ("confidence",float("nan")),
    ("segment_start_seconds",True),
    ("segment_start_seconds",-0.1),
    ("segment_start_seconds",float("inf")),
    ("segment_end_seconds",True),
    ("segment_end_seconds",0.0),
    ("segment_end_seconds",float("inf")),
    ("evidence_digest","a"*63),
    ("evidence_digest","A"*64),
    ("evidence_digest","g"*64),
    ("evidence_digest",None),
    ("clock_domain_id",""),
    ("clock_domain_id","   "),
    ("clock_domain_id",None),
    ("clock_domain_id",7),
))
def test_invalid_media_segment_observation_is_rejected(field,value):
    values={
        "observation_id":"observation-1",
        "profile_id":"profile-1",
        "device_id":"living-room-tv",
        "provider_id":"provider-1",
        "content_id":"series-alpha-episode-1",
        "segment_kind":MediaSegmentKind.INTRO,
        "source":MediaEvidenceSource.METADATA,
        "observed_monotonic":100.0,
        "confidence":1.0,
        "segment_start_seconds":0.0,
        "segment_end_seconds":45.0,
        "evidence_digest":"a"*64,
    }
    values[field]=value
    with pytest.raises(ValueError):
        MediaSegmentObservation(**values)

def test_intro_observation_maps_to_authority_free_adaptive_proposal():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    from src.edge.media_segment_observation import MediaSegmentProposalAdapter

    observation=MediaSegmentObservation(
        observation_id="observation-2",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=101.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="b"*64,
    )
    memory=AdaptiveDirectiveMemory(max_entries=16)
    adapter=MediaSegmentProposalAdapter(memory)
    key=adapter.context_key(observation)
    assert key==("profile-1","living-room-tv","show_intro:provider-1","series-alpha-episode-1")
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    proposal=adapter.propose(observation,context_match=1.0,now_monotonic=101.25,max_age_seconds=0.5)
    assert proposal is not None
    assert proposal.key==key
    assert proposal.action=="skip"
    assert proposal.confidence==observation.confidence
    assert proposal.grants_physical_authority is False
    assert not hasattr(adapter,"physical_adapter")
    assert not hasattr(adapter,"execute")
    assert not hasattr(adapter,"commit")

@pytest.mark.parametrize("now_monotonic",(99.9,101.0))
def test_stale_or_future_media_observation_never_produces_proposal(now_monotonic):
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    from src.edge.media_segment_observation import MediaSegmentProposalAdapter

    observation=MediaSegmentObservation(
        observation_id="observation-3",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="c"*64,
    )
    memory=AdaptiveDirectiveMemory(max_entries=16)
    adapter=MediaSegmentProposalAdapter(memory)
    key=adapter.context_key(observation)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    assert adapter.propose(observation,context_match=1.0,now_monotonic=now_monotonic,max_age_seconds=0.5) is None

def test_stale_media_observation_never_calls_adaptive_memory(monkeypatch):
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    from src.edge.media_segment_observation import MediaSegmentProposalAdapter

    observation=MediaSegmentObservation(
        observation_id="observation-4",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="d"*64,
    )
    memory=AdaptiveDirectiveMemory(max_entries=16)
    adapter=MediaSegmentProposalAdapter(memory)
    key=adapter.context_key(observation)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    calls=[]
    def forbidden_propose(*args,**kwargs):
        calls.append((args,kwargs))
        raise AssertionError("stale evidence reached adaptive memory")
    monkeypatch.setattr(memory,"propose",forbidden_propose)
    assert adapter.propose(observation,context_match=1.0,now_monotonic=101.0,max_age_seconds=0.5) is None
    assert calls==[]

def test_media_automation_requires_pinned_automate_directive():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    from src.edge.media_segment_observation import MediaAutomationDecision,MediaAutomationEligibilityGate,MediaSegmentProposalAdapter

    observation=MediaSegmentObservation(
        observation_id="observation-5",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="e"*64,
    )

    unpinned_memory=AdaptiveDirectiveMemory(max_entries=16)
    unpinned_adapter=MediaSegmentProposalAdapter(unpinned_memory)
    key=unpinned_adapter.context_key(observation)
    unpinned_memory.remember(key,action="skip")
    unpinned_memory.feedback(key,approved=True)
    for stage in (DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        unpinned_memory.advance_lifecycle(key,target=stage)
    unpinned_proposal=unpinned_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    unpinned_gate=MediaAutomationEligibilityGate(unpinned_memory,unpinned_adapter)
    assert unpinned_gate.evaluate(observation,unpinned_proposal,now_monotonic=100.1,max_age_seconds=0.5) is MediaAutomationDecision.NOT_PINNED

    pinned_memory=AdaptiveDirectiveMemory(max_entries=16)
    pinned_adapter=MediaSegmentProposalAdapter(pinned_memory)
    pinned_memory.remember(key,action="skip",pinned=True)
    observe_proposal=pinned_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    pinned_gate=MediaAutomationEligibilityGate(pinned_memory,pinned_adapter)
    assert pinned_gate.evaluate(observation,observe_proposal,now_monotonic=100.1,max_age_seconds=0.5) is MediaAutomationDecision.NOT_AUTOMATE

    for stage in (DirectiveLifecycleStage.SUGGEST,DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        pinned_memory.advance_lifecycle(key,target=stage)
    automate_proposal=pinned_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    assert pinned_gate.evaluate(observation,automate_proposal,now_monotonic=100.1,max_age_seconds=0.5) is MediaAutomationDecision.ALLOW
    assert automate_proposal.grants_physical_authority is False
    assert not hasattr(pinned_gate,"execute")
    assert not hasattr(pinned_gate,"commit")
    assert not hasattr(pinned_gate,"physical_adapter")

def test_eligible_media_automation_normalizes_to_evidence_bound_candidate():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    from src.edge.media_segment_observation import MediaAutomationCandidateNormalizer,MediaAutomationEligibilityGate,MediaSegmentProposalAdapter
    from src.extensions.normalization import NormalizedCandidate

    observation=MediaSegmentObservation(
        observation_id="observation-6",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="f"*64,
    )
    memory=AdaptiveDirectiveMemory(max_entries=16)
    proposal_adapter=MediaSegmentProposalAdapter(memory)
    key=proposal_adapter.context_key(observation)
    memory.remember(key,action="skip",pinned=True)
    for stage in (DirectiveLifecycleStage.SUGGEST,DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        memory.advance_lifecycle(key,target=stage)
    proposal=proposal_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    gate=MediaAutomationEligibilityGate(memory,proposal_adapter)
    normalizer=MediaAutomationCandidateNormalizer(gate)
    candidate=normalizer.normalize(observation,proposal,now_monotonic=100.1,max_age_seconds=0.5)
    assert isinstance(candidate,NormalizedCandidate)
    assert candidate.extension_id=="aqss.media.segment"
    assert candidate.target_id==observation.device_id
    assert candidate.operation=="SET_PLAYBACK_POSITION"
    assert candidate.parameters["playback_position_seconds"]==observation.segment_end_seconds
    assert candidate.parameters["observation_id"]==observation.observation_id
    assert candidate.parameters["evidence_digest"]==observation.evidence_digest
    assert candidate.parameters["observed_monotonic"]==observation.observed_monotonic
    assert candidate.parameters["evidence_expires_monotonic"]==observation.observed_monotonic+0.5
    assert candidate.parameters["evidence_clock_domain_id"]==observation.clock_domain_id
    assert candidate.parameters["segment_start_seconds"]==observation.segment_start_seconds
    assert candidate.parameters["segment_end_seconds"]==observation.segment_end_seconds
    assert candidate.parameters["directive_key"]==proposal.key
    assert candidate.parameters["directive_version"]==proposal.version
    for authority_name in ("capability","issuer_id","signature","lease_id","capability_lease_digest","authorization_digest","transaction_id","commit_authority","physical_authority"):
        assert not hasattr(candidate,authority_name)
    assert not hasattr(normalizer,"execute")
    assert not hasattr(normalizer,"commit")
    assert not hasattr(normalizer,"physical_adapter")

def test_substituted_media_evidence_never_reaches_normalization(monkeypatch):
    from dataclasses import replace
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    import src.edge.media_segment_observation as media_module
    from src.edge.media_segment_observation import MediaAutomationCandidateNormalizer,MediaAutomationDecision,MediaAutomationEligibilityGate,MediaSegmentProposalAdapter

    original=MediaSegmentObservation(
        observation_id="observation-7",
        profile_id="profile-1",
        device_id="living-room-tv",
        provider_id="provider-1",
        content_id="series-alpha-episode-1",
        segment_kind=MediaSegmentKind.INTRO,
        source=MediaEvidenceSource.METADATA,
        observed_monotonic=100.0,
        confidence=1.0,
        segment_start_seconds=0.0,
        segment_end_seconds=45.0,
        evidence_digest="1"*64,
    )
    substituted=replace(original,observation_id="observation-8",evidence_digest="2"*64)
    memory=AdaptiveDirectiveMemory(max_entries=16)
    proposal_adapter=MediaSegmentProposalAdapter(memory)
    key=proposal_adapter.context_key(original)
    memory.remember(key,action="skip",pinned=True)
    for stage in (DirectiveLifecycleStage.SUGGEST,DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        memory.advance_lifecycle(key,target=stage)
    proposal=proposal_adapter.propose(original,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    gate=MediaAutomationEligibilityGate(memory,proposal_adapter)
    assert gate.evaluate(substituted,proposal,now_monotonic=100.1,max_age_seconds=0.5) is MediaAutomationDecision.EVIDENCE_MISMATCH
    calls=[]
    def forbidden_normalization(*args,**kwargs):
        calls.append((args,kwargs))
        raise AssertionError("substituted evidence reached normalization")
    monkeypatch.setattr(media_module,"normalize_proposal",forbidden_normalization)
    normalizer=MediaAutomationCandidateNormalizer(gate)
    assert normalizer.normalize(substituted,proposal,now_monotonic=100.1,max_age_seconds=0.5) is None
    assert calls==[]

def test_media_candidate_admission_revalidates_exact_candidate_and_live_evidence():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    from src.edge.media_segment_observation import MediaAutomationCandidateAdmission,MediaAutomationCandidateNormalizer,MediaAutomationEligibilityGate,MediaEvidenceSource,MediaSegmentKind,MediaSegmentObservation,MediaSegmentProposalAdapter

    observation=MediaSegmentObservation(observation_id="observation-admission-1",profile_id="profile-1",device_id="living-room-tv",provider_id="provider-1",content_id="episode-1",segment_kind=MediaSegmentKind.INTRO,source=MediaEvidenceSource.METADATA,observed_monotonic=100.0,confidence=1.0,segment_start_seconds=0.0,segment_end_seconds=45.0,evidence_digest="c"*64)
    memory=AdaptiveDirectiveMemory(max_entries=16)
    proposal_adapter=MediaSegmentProposalAdapter(memory)
    key=proposal_adapter.context_key(observation)
    memory.remember(key,action="skip",pinned=True)
    for stage in (DirectiveLifecycleStage.SUGGEST,DirectiveLifecycleStage.SHADOW,DirectiveLifecycleStage.AUTOMATE):
        memory.advance_lifecycle(key,target=stage)
    proposal=proposal_adapter.propose(observation,context_match=1.0,now_monotonic=100.1,max_age_seconds=0.5)
    normalizer=MediaAutomationCandidateNormalizer(MediaAutomationEligibilityGate(memory,proposal_adapter))
    candidate=normalizer.normalize(observation,proposal,now_monotonic=100.1,max_age_seconds=0.5)
    now=[100.1]
    admission=MediaAutomationCandidateAdmission(normalizer,observation,proposal,monotonic_clock=lambda:now[0],max_age_seconds=0.5)
    assert admission(candidate) is True
    tampered_parameters=dict(candidate.parameters)
    tampered_parameters["playback_position_seconds"]=46.0
    tampered=candidate.__class__(extension_id=candidate.extension_id,target_id=candidate.target_id,operation=candidate.operation,parameters=tampered_parameters)
    assert admission(tampered) is False
    now[0]=100.6
    assert admission(candidate) is False

