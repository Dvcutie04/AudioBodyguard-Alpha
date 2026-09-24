def test_feedback_activates_and_suspends_remembered_directive():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    assert memory.recall(key) is None
    assert memory.status(key) is DirectiveStatus.CANDIDATE
    memory.feedback(key,approved=True)
    directive=memory.recall(key)
    assert directive is not None
    assert directive.action=="skip"
    assert directive.status is DirectiveStatus.ACTIVE
    memory.feedback(key,approved=False)
    assert memory.recall(key) is None
    assert memory.status(key) is DirectiveStatus.SUSPENDED


def test_directive_memory_evicts_least_recently_used_entry_at_capacity():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    first=("profile_1","living_room_tv","show_intro","series_alpha")
    second=("profile_1","living_room_tv","commercial","channel_alpha")
    third=("profile_1","bedroom_tv","loud_transient","nighttime")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(first,action="skip")
    memory.feedback(first,approved=True)
    memory.remember(second,action="lower_volume")
    memory.feedback(second,approved=True)
    assert memory.recall(first) is not None
    memory.remember(third,action="reduce_dynamic_range")
    assert memory.status(first) is DirectiveStatus.ACTIVE
    assert memory.status(third) is DirectiveStatus.CANDIDATE
    with pytest.raises(KeyError):
        memory.status(second)


def test_touch_and_voice_use_same_typed_feedback_contract():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason, FeedbackSource
    touch_key=("profile_1","living_room_tv","show_intro","series_alpha")
    voice_key=("profile_1","bedroom_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(touch_key,action="skip")
    memory.remember(voice_key,action="lower_volume")
    touch=memory.feedback(touch_key,approved=True,source=FeedbackSource.TOUCH,reason=FeedbackReason.CORRECT_ACTION)
    voice=memory.feedback(voice_key,approved=True,source=FeedbackSource.VOICE,reason=FeedbackReason.CORRECT_ACTION)
    assert touch.source is FeedbackSource.TOUCH
    assert voice.source is FeedbackSource.VOICE
    assert touch.reason is voice.reason is FeedbackReason.CORRECT_ACTION
    assert touch.approved is voice.approved is True
    assert memory.recall(touch_key) is not None
    assert memory.recall(voice_key) is not None


def test_feedback_reason_menus_expose_stable_positive_and_negative_choices():
    from src.edge.adaptive_directive_memory import FeedbackReason, feedback_reasons
    positive=feedback_reasons(approved=True)
    negative=feedback_reasons(approved=False)
    assert positive==(FeedbackReason.CORRECT_ACTION,FeedbackReason.CORRECT_TIMING,FeedbackReason.RIGHT_AMOUNT,FeedbackReason.RIGHT_CONTEXT,FeedbackReason.HELPFUL_AUTOMATION,FeedbackReason.REMEMBER_THIS)
    assert negative==(FeedbackReason.WRONG_ACTION,FeedbackReason.TOO_EARLY,FeedbackReason.TOO_LATE,FeedbackReason.TOO_MUCH,FeedbackReason.TOO_LITTLE,FeedbackReason.WRONG_CONTEXT,FeedbackReason.ASKED_TOO_OFTEN,FeedbackReason.NEVER_AUTOMATE)
    assert FeedbackReason.NEVER_AUTOMATE not in positive
    assert negative[-1] is FeedbackReason.NEVER_AUTOMATE


def test_feedback_adapts_preference_strength_within_one_to_twenty_five():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    assert memory.strength(key)==13
    event=memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.strength(key)==14
    assert event.strength_before==13
    assert event.strength_after==14
    for _ in range(20):
        memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.strength(key)==25
    event=memory.feedback(key,approved=False,reason=FeedbackReason.TOO_MUCH)
    assert memory.strength(key)==23
    assert event.strength_before==25
    assert event.strength_after==23
    for _ in range(20):
        memory.feedback(key,approved=False,reason=FeedbackReason.TOO_MUCH)
    assert memory.strength(key)==1


def test_feedback_rejects_mismatched_reasons_and_never_automate_blocks_reactivation():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason
    mismatch=("profile_1","living_room_tv","show_intro","series_alpha")
    blocked=("profile_1","bedroom_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(mismatch,action="skip")
    with pytest.raises(ValueError):
        memory.feedback(mismatch,approved=True,reason=FeedbackReason.WRONG_ACTION)
    assert memory.status(mismatch) is DirectiveStatus.CANDIDATE
    assert memory.strength(mismatch)==13
    memory.remember(blocked,action="lower_volume")
    event=memory.feedback(blocked,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    assert event.strength_after==1
    assert memory.status(blocked) is DirectiveStatus.BLOCKED
    assert memory.recall(blocked) is None
    with pytest.raises(ValueError):
        memory.feedback(blocked,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.status(blocked) is DirectiveStatus.BLOCKED
    assert memory.strength(blocked)==1


def test_pinned_explicit_directive_survives_candidate_memory_pressure():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    pinned=("profile_1","living_room_tv","show_intro","series_alpha")
    candidate=("profile_1","living_room_tv","commercial","channel_alpha")
    incoming=("profile_1","bedroom_tv","loud_transient","nighttime")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(pinned,action="skip",pinned=True)
    assert memory.is_pinned(pinned) is True
    assert memory.status(pinned) is DirectiveStatus.ACTIVE
    memory.remember(candidate,action="lower_volume")
    memory.remember(incoming,action="reduce_dynamic_range")
    assert memory.is_pinned(pinned) is True
    assert memory.status(pinned) is DirectiveStatus.ACTIVE
    assert memory.status(incoming) is DirectiveStatus.CANDIDATE
    with pytest.raises(KeyError):
        memory.status(candidate)


def test_memory_rejects_new_directive_when_capacity_contains_only_pinned_entries():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    first=("profile_1","living_room_tv","show_intro","series_alpha")
    second=("profile_1","bedroom_tv","commercial","channel_alpha")
    incoming=("profile_1","kitchen_tv","loud_transient","nighttime")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(first,action="skip",pinned=True)
    memory.remember(second,action="lower_volume",pinned=True)
    with pytest.raises(MemoryError,match="only pinned"):
        memory.remember(incoming,action="reduce_dynamic_range")
    assert memory.status(first) is DirectiveStatus.ACTIVE
    assert memory.status(second) is DirectiveStatus.ACTIVE
    assert memory.is_pinned(first) is True
    assert memory.is_pinned(second) is True
    with pytest.raises(KeyError):
        memory.status(incoming)


def test_blocked_directive_requires_explicit_replacement_before_reactivation():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    with pytest.raises(ValueError,match="explicit replacement"):
        memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    replacement=memory.replace_blocked(key,action="mute_commercial")
    assert replacement.action=="mute_commercial"
    assert replacement.status is DirectiveStatus.ACTIVE
    assert replacement.strength==13
    assert replacement.pinned is True
    assert memory.recall(key)==replacement


def test_reason_ranking_learns_frequent_choice_for_exact_situation():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason, feedback_reasons
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    other=("profile_1","bedroom_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.remember(other,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    ranked=memory.ranked_feedback_reasons(key,approved=False)
    assert ranked[0] is FeedbackReason.TOO_LATE
    assert set(ranked)==set(feedback_reasons(approved=False))
    assert memory.ranked_feedback_reasons(other,approved=False)==feedback_reasons(approved=False)
    assert memory.ranked_feedback_reasons(key,approved=True)==feedback_reasons(approved=True)


def test_spoken_feedback_normalizes_into_typed_feedback_and_fails_closed():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason, FeedbackSource
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    negative=memory.feedback_from_voice(key,"That happened too late")
    assert negative.source is FeedbackSource.VOICE
    assert negative.approved is False
    assert negative.reason is FeedbackReason.TOO_LATE
    assert negative.strength_before==13
    assert negative.strength_after==11
    positive=memory.feedback_from_voice(key,"Perfect timing")
    assert positive.source is FeedbackSource.VOICE
    assert positive.approved is True
    assert positive.reason is FeedbackReason.CORRECT_TIMING
    assert positive.strength_after==12
    with pytest.raises(ValueError,match="unrecognized voice feedback"):
        memory.feedback_from_voice(key,"Maybe something different")
    assert memory.strength(key)==12


def test_ai_voice_candidate_requires_policy_confidence_before_feedback_commit():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason, FeedbackSource, VoiceFeedbackCandidate
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    accepted=VoiceFeedbackCandidate(approved=False,reason=FeedbackReason.TOO_MUCH,confidence=0.94)
    event=memory.accept_voice_candidate(key,accepted,min_confidence=0.90)
    assert event.source is FeedbackSource.VOICE
    assert event.reason is FeedbackReason.TOO_MUCH
    assert event.strength_before==13
    assert event.strength_after==11
    rejected=VoiceFeedbackCandidate(approved=True,reason=FeedbackReason.CORRECT_ACTION,confidence=0.89)
    with pytest.raises(ValueError,match="confidence below policy threshold"):
        memory.accept_voice_candidate(key,rejected,min_confidence=0.90)
    assert memory.strength(key)==11
    with pytest.raises(ValueError,match="confidence must be between zero and one"):
        VoiceFeedbackCandidate(approved=True,reason=FeedbackReason.CORRECT_ACTION,confidence=1.1)


def test_ordinary_remember_cannot_overwrite_never_automate_block():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    with pytest.raises(ValueError,match="explicit replacement"):
        memory.remember(key,action="mute_commercial")
    assert memory.status(key) is DirectiveStatus.BLOCKED
    assert memory.strength(key)==1
    assert memory.recall(key) is None


def test_never_automate_block_survives_non_candidate_memory_pressure():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason
    blocked=("profile_1","living_room_tv","commercial","channel_alpha")
    active=("profile_1","bedroom_tv","show_intro","series_alpha")
    incoming=("profile_1","kitchen_tv","loud_transient","nighttime")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(blocked,action="lower_volume")
    memory.feedback(blocked,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    memory.remember(active,action="skip")
    memory.feedback(active,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    memory.remember(incoming,action="reduce_dynamic_range")
    assert memory.status(blocked) is DirectiveStatus.BLOCKED
    assert memory.is_pinned(blocked) is True
    assert memory.status(incoming) is DirectiveStatus.CANDIDATE
    with pytest.raises(KeyError):
        memory.status(active)


def test_long_press_menu_exposes_direction_ranked_reasons_and_sensitivity():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackMenuDirection, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    positive=memory.long_press_menu(key,approved=True)
    negative=memory.long_press_menu(key,approved=False)
    assert positive.direction is FeedbackMenuDirection.DOWN
    assert negative.direction is FeedbackMenuDirection.UP
    assert positive.approved is True
    assert negative.approved is False
    assert negative.reasons[0] is FeedbackReason.TOO_LATE
    assert positive.strength==negative.strength==11
    assert 1 <= positive.strength <= 25


def test_ai_voice_candidate_cannot_commit_never_automate_without_explicit_user_confirmation():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason, VoiceFeedbackCandidate, feedback_reasons
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    candidate=VoiceFeedbackCandidate(approved=False,reason=FeedbackReason.NEVER_AUTOMATE,confidence=0.99)
    with pytest.raises(ValueError,match="explicit user confirmation"):
        memory.accept_voice_candidate(key,candidate,min_confidence=0.90)
    assert memory.status(key) is DirectiveStatus.CANDIDATE
    assert memory.strength(key)==13
    assert memory.is_pinned(key) is False
    assert memory.ranked_feedback_reasons(key,approved=False)==feedback_reasons(approved=False)


def test_long_press_menu_exposes_readable_accessible_ranked_items():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    menu=memory.long_press_menu(key,approved=False)
    assert tuple(item.reason for item in menu.items)==menu.reasons
    assert menu.items[0].reason is FeedbackReason.TOO_LATE
    assert menu.items[0].label=="Too late"
    assert menu.items[0].accessibility_identifier=="feedback_reason_too_late"
    assert all(item.label and item.accessibility_identifier for item in menu.items)
    assert len({item.accessibility_identifier for item in menu.items})==len(menu.items)


def test_strength_changes_future_proposal_sensitivity_without_granting_authority():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.strength(key)==14
    assert memory.proposal_threshold(key)==pytest.approx(12/25)
    assert memory.should_propose(key,confidence=0.40,context_match=1.0) is False
    for _ in range(5):
        memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.strength(key)==19
    assert memory.proposal_threshold(key)==pytest.approx(7/25)
    assert memory.should_propose(key,confidence=0.40,context_match=1.0) is True


def test_sensitivity_emits_typed_proposal_without_physical_authority():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveProposal, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.propose(key,confidence=0.47,context_match=1.0) is None
    proposal=memory.propose(key,confidence=0.48,context_match=1.0)
    assert isinstance(proposal,DirectiveProposal)
    assert proposal.key==key
    assert proposal.action=="lower_volume"
    assert proposal.confidence==pytest.approx(0.48)
    assert proposal.threshold==pytest.approx(12/25)
    assert proposal.strength==14
    assert not hasattr(proposal,"signature")
    assert not hasattr(proposal,"capability_lease")
    assert not hasattr(proposal,"execute")


def test_proposal_becomes_stale_after_feedback_changes_directive():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    assert proposal.version==memory.version(key)
    assert memory.proposal_is_current(proposal) is True
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    assert memory.version(key)>proposal.version
    assert memory.proposal_is_current(proposal) is False
    assert memory.propose(key,confidence=1.0,context_match=1.0) is None


def test_evicted_proposal_stays_stale_when_same_key_is_recreated():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    other=("profile_2","bedroom_tv","movie","channel_beta")
    memory=AdaptiveDirectiveMemory(max_entries=1)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    memory.remember(other,action="pause")
    assert memory.proposal_is_current(proposal) is False
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    assert memory.version(key)>proposal.version
    assert memory.proposal_is_current(proposal) is False


def test_recall_does_not_invalidate_current_proposal():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    version_before=memory.version(key)
    assert memory.recall(key) is not None
    assert memory.version(key)==version_before
    assert memory.proposal_is_current(proposal) is True


def test_version_metadata_remains_bounded_during_repeated_eviction():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(max_entries=2)
    for index in range(50):
        key=("profile_"+str(index),"device_"+str(index),"context","channel")
        memory.remember(key,action="lower_volume")
    assert len(memory._entries)==2
    assert len(memory._versions)==2


def test_feedback_ranking_metadata_remains_bounded_during_eviction():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    memory=AdaptiveDirectiveMemory(max_entries=2)
    for index in range(50):
        key=("profile_"+str(index),"device_"+str(index),"context","channel")
        memory.remember(key,action="lower_volume")
        memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    assert len(memory._entries)==2
    assert len(memory._reason_counts)==2
    live_keys=set(memory._entries)
    assert all(record[0] in live_keys for record in memory._reason_counts)


def test_replacing_existing_directive_clears_old_feedback_ranking():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.TOO_LATE)
    old_version=memory.version(key)
    assert (key,False,FeedbackReason.TOO_LATE) in memory._reason_counts
    memory.remember(key,action="mute")
    assert memory.version(key)>old_version
    assert (key,False,FeedbackReason.TOO_LATE) not in memory._reason_counts


def test_remembering_identical_directive_is_idempotent():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    version_before=memory.version(key)
    strength_before=memory.strength(key)
    memory.remember(key,action="lower_volume")
    assert memory.version(key)==version_before
    assert memory.strength(key)==strength_before
    assert memory.status(key) is DirectiveStatus.ACTIVE
    assert memory.proposal_is_current(proposal) is True


def test_proposal_freshness_rejects_confidence_below_captured_threshold():
    from dataclasses import replace
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    assert memory.proposal_is_current(proposal) is True
    altered=replace(proposal,confidence=proposal.threshold-0.01)
    assert memory.proposal_is_current(altered) is False


def test_replacing_blocked_directive_clears_old_feedback_ranking():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=False,reason=FeedbackReason.NEVER_AUTOMATE)
    assert (key,False,FeedbackReason.NEVER_AUTOMATE) in memory._reason_counts
    memory.replace_blocked(key,action="mute")
    assert (key,False,FeedbackReason.NEVER_AUTOMATE) not in memory._reason_counts


def test_proposal_freshness_rejects_nonnumeric_confidence():
    from dataclasses import replace
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    malformed=replace(proposal,confidence=None)
    assert memory.proposal_is_current(malformed) is False


def test_proposal_freshness_rejects_unhashable_key():
    from dataclasses import replace
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    malformed=replace(proposal,key=list(key))
    assert memory.proposal_is_current(malformed) is False


def test_boolean_confidence_is_rejected():
    from dataclasses import replace
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason
    key=("profile_1","living_room_tv","commercial","channel_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="lower_volume")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION)
    proposal=memory.propose(key,confidence=0.50,context_match=1.0)
    assert proposal is not None
    with pytest.raises(ValueError):
        memory.propose(key,confidence=True,context_match=1.0)
    with pytest.raises(ValueError):
        memory.should_propose(key,confidence=False,context_match=1.0)
    assert memory.proposal_is_current(replace(proposal,confidence=True)) is False


def test_explicit_negative_feedback_records_lifecycle_suspension_reason():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveLifecycleStage, DirectiveSuspensionReason, FeedbackReason
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    memory.feedback(key,approved=False,reason=FeedbackReason.WRONG_ACTION)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.SUSPEND
    assert memory.suspension_reason(key) is DirectiveSuspensionReason.EXPLICIT_NEGATIVE_FEEDBACK


def test_lifecycle_policy_advances_one_stage_and_rejects_skips_atomically():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveLifecycleStage
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.OBSERVE
    with pytest.raises(ValueError):
        memory.advance_lifecycle(key,target=DirectiveLifecycleStage.AUTOMATE)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.OBSERVE
    memory.feedback(key,approved=True)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.SUGGEST
    with pytest.raises(ValueError):
        memory.advance_lifecycle(key,target=DirectiveLifecycleStage.AUTOMATE)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.SUGGEST
    memory.advance_lifecycle(key,target=DirectiveLifecycleStage.SHADOW)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.SHADOW
    memory.advance_lifecycle(key,target=DirectiveLifecycleStage.AUTOMATE)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.AUTOMATE


def test_policy_suspends_automate_stage_and_invalidates_proposal():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveLifecycleStage, DirectiveStatus, DirectiveSuspensionReason
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    memory.advance_lifecycle(key,target=DirectiveLifecycleStage.SHADOW)
    memory.advance_lifecycle(key,target=DirectiveLifecycleStage.AUTOMATE)
    proposal=memory.propose(key,confidence=1.0,context_match=1.0)
    assert proposal is not None
    memory.suspend_for_policy(key)
    assert memory.lifecycle_stage(key) is DirectiveLifecycleStage.SUSPEND
    assert memory.suspension_reason(key) is DirectiveSuspensionReason.POLICY_BLOCK
    assert memory.status(key) is DirectiveStatus.SUSPENDED
    assert memory.propose(key,confidence=1.0,context_match=1.0) is None
    assert memory.proposal_is_current(proposal) is False


def test_model_confidence_cannot_substitute_for_context_match_or_authority():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    assert memory.propose(key,confidence=1.0,context_match=0.1) is None
    proposal=memory.propose(key,confidence=1.0,context_match=1.0)
    assert proposal is not None
    assert proposal.confidence==1.0
    assert proposal.context_match==1.0
    assert proposal.grants_physical_authority is False


def test_proposal_requires_explicit_context_match():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True)
    with pytest.raises(TypeError):
        memory.propose(key,confidence=1.0)
    with pytest.raises(TypeError):
        memory.should_propose(key,confidence=1.0)


def test_feedback_ledger_records_typed_privacy_preserving_context():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, FeedbackReason, ProfileConfidenceBand
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True,reason=FeedbackReason.CORRECT_ACTION,profile_confidence_band=ProfileConfidenceBand.HIGH,timestamp_bucket=12345)
    records=memory.feedback_ledger()
    assert len(records)==1
    record=records[0]
    assert record.context_ids==key
    assert record.action_code=="skip"
    assert record.reason is FeedbackReason.CORRECT_ACTION
    assert record.strength_delta==1
    assert record.profile_confidence_band is ProfileConfidenceBand.HIGH
    assert record.timestamp_bucket==12345
    assert record.grants_physical_authority is False
    assert not hasattr(record,"audio")
    assert not hasattr(record,"transcript")


def test_invalid_feedback_metadata_is_rejected_atomically():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, ProfileConfidenceBand
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=16)
    memory.remember(key,action="skip")
    memory.feedback(key,approved=True,profile_confidence_band=ProfileConfidenceBand.HIGH,timestamp_bucket=12344)
    before=memory.recall(key)
    ledger_before=memory.feedback_ledger()
    proposal=memory.propose(key,confidence=1.0,context_match=1.0)
    assert proposal is not None
    with pytest.raises(ValueError):
        memory.feedback(key,approved=True,profile_confidence_band="HIGH",timestamp_bucket=12345)
    with pytest.raises(ValueError):
        memory.feedback(key,approved=True,profile_confidence_band=ProfileConfidenceBand.HIGH,timestamp_bucket=True)
    assert memory.recall(key)==before
    assert memory.feedback_ledger()==ledger_before
    assert memory.proposal_is_current(proposal) is True


def test_feedback_ledger_is_bounded_and_immutable():
    from dataclasses import FrozenInstanceError
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, ProfileConfidenceBand
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=2)
    memory.remember(key,action="skip")
    for timestamp_bucket in (1,2,3):
        memory.feedback(key,approved=True,profile_confidence_band=ProfileConfidenceBand.HIGH,timestamp_bucket=timestamp_bucket)
    records=memory.feedback_ledger()
    assert isinstance(records,tuple)
    assert tuple(record.timestamp_bucket for record in records)==(2,3)
    with pytest.raises(FrozenInstanceError):
        records[0].timestamp_bucket=99
    assert tuple(record.timestamp_bucket for record in memory.feedback_ledger())==(2,3)


def test_eviction_prefers_unpinned_candidate_over_older_active_and_pinned_directives():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    active=("profile_1","tv_1","intro","series_active")
    pinned=("profile_1","tv_1","intro","series_pinned")
    candidate=("profile_1","tv_1","intro","series_candidate")
    incoming=("profile_1","tv_1","intro","series_incoming")
    memory=AdaptiveDirectiveMemory(max_entries=3)
    memory.remember(active,action="skip")
    memory.feedback(active,approved=True)
    memory.remember(pinned,action="skip",pinned=True)
    memory.remember(candidate,action="skip")
    memory.remember(incoming,action="skip")
    with pytest.raises(KeyError):
        memory.status(candidate)
    assert memory.status(active) is DirectiveStatus.ACTIVE
    assert memory.status(pinned) is DirectiveStatus.ACTIVE
    assert memory.is_pinned(pinned) is True
    assert memory.status(incoming) is DirectiveStatus.CANDIDATE


def test_session_only_ambiguous_directive_is_excluded_from_durable_snapshot():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectivePersistenceScope
    ambiguous=("ambiguous_profile","tv_1","intro","series_alpha")
    durable=("profile_1","tv_1","intro","series_beta")
    memory=AdaptiveDirectiveMemory(max_entries=4)
    memory.remember(ambiguous,action="skip",persistence_scope=DirectivePersistenceScope.SESSION_ONLY)
    memory.feedback(ambiguous,approved=True)
    memory.remember(durable,action="skip",persistence_scope=DirectivePersistenceScope.DURABLE)
    memory.feedback(durable,approved=True)
    assert memory.persistence_scope(ambiguous) is DirectivePersistenceScope.SESSION_ONLY
    proposal=memory.propose(ambiguous,confidence=1.0,context_match=1.0)
    assert proposal is not None
    assert proposal.grants_physical_authority is False
    snapshot=memory.durable_directives()
    assert tuple(item.key for item in snapshot)==(durable,)


def test_persistence_scope_changes_are_atomic_and_invalidate_stale_proposals():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectivePersistenceScope, DirectiveStatus
    key=("profile_1","tv_1","intro","series_alpha")
    memory=AdaptiveDirectiveMemory(max_entries=4)
    memory.remember(key,action="skip",persistence_scope=DirectivePersistenceScope.DURABLE)
    memory.feedback(key,approved=True)
    before=memory.recall(key)
    durable_before=memory.durable_directives()
    proposal=memory.propose(key,confidence=1.0,context_match=1.0)
    assert proposal is not None
    with pytest.raises(ValueError):
        memory.remember(key,action="skip",persistence_scope="SESSION_ONLY")
    assert memory.recall(key)==before
    assert memory.durable_directives()==durable_before
    assert memory.proposal_is_current(proposal) is True
    memory.remember(key,action="skip",persistence_scope=DirectivePersistenceScope.SESSION_ONLY)
    assert memory.status(key) is DirectiveStatus.CANDIDATE
    assert memory.durable_directives()==()
    assert memory.proposal_is_current(proposal) is False


def test_generated_proposals_require_both_confidence_dimensions():
    from hypothesis import given, settings, strategies as st
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    key=("profile_1","living_room_tv","show_intro","series_alpha")
    deep=__import__("os").environ.get("AQSS_HYPOTHESIS_PROFILE")=="deep"
    @settings(max_examples=1000 if deep else 200,deadline=None,database=None)
    @given(confidence=st.floats(min_value=0.0,max_value=1.0,allow_nan=False,allow_infinity=False),context_match=st.floats(min_value=0.0,max_value=1.0,allow_nan=False,allow_infinity=False))
    def verify(confidence,context_match):
        memory=AdaptiveDirectiveMemory(max_entries=4)
        memory.remember(key,action="skip")
        memory.feedback(key,approved=True)
        threshold=(26-memory.recall(key).strength)/25
        proposal=memory.propose(key,confidence=confidence,context_match=context_match)
        assert (proposal is not None)==(confidence>=threshold and context_match>=threshold)
        if proposal is not None:
            assert proposal.grants_physical_authority is False
            assert memory.proposal_is_current(proposal) is True
    verify()


def test_generated_feedback_state_machine_preserves_safety_invariants():
    from hypothesis import given, settings, strategies as st
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    deep=__import__("os").environ.get("AQSS_HYPOTHESIS_PROFILE")=="deep"
    @settings(max_examples=150 if deep else 50,deadline=None,database=None)
    @given(events=st.lists(st.booleans(),min_size=0,max_size=30 if deep else 20))
    def verify(events):
        key=("profile_1","living_room_tv","show_intro","series_alpha")
        memory=AdaptiveDirectiveMemory(max_entries=5)
        memory.remember(key,action="skip")
        expected=13
        assert memory.propose(key,confidence=1.0,context_match=1.0) is None
        for timestamp,approved in enumerate(events):
            old=memory.propose(key,confidence=1.0,context_match=1.0)
            event=memory.feedback(key,approved=approved,timestamp_bucket=timestamp)
            expected=min(25,expected+1) if approved else max(1,expected-2)
            assert event.strength_after==expected
            assert 1<=expected<=25
            assert len(memory.feedback_ledger())<=5
            if old is not None:
                assert memory.proposal_is_current(old) is False
            proposal=memory.propose(key,confidence=1.0,context_match=1.0)
            assert (proposal is not None)==(memory.status(key) is DirectiveStatus.ACTIVE)
            if proposal is not None:
                assert proposal.strength==expected
                assert proposal.grants_physical_authority is False
                assert memory.proposal_is_current(proposal) is True
    verify()


def test_feedback_is_isolated_across_profile_and_device_keys():
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory, DirectiveStatus
    memory=AdaptiveDirectiveMemory(max_entries=5)
    first=("profile_1","living_room_tv","show_intro","series_alpha")
    second=("profile_2","bedroom_tv","show_intro","series_alpha")
    memory.remember(first,action="skip")
    memory.remember(second,action="mute")
    memory.feedback(first,approved=True,timestamp_bucket=1)
    proposal=memory.propose(first,confidence=1.0,context_match=1.0)
    assert proposal is not None
    assert memory.propose(second,confidence=1.0,context_match=1.0) is None
    memory.feedback(second,approved=False,timestamp_bucket=2)
    assert memory.status(first) is DirectiveStatus.ACTIVE
    assert memory.status(second) is DirectiveStatus.SUSPENDED
    assert memory.proposal_is_current(proposal) is True
    assert [record.context_ids for record in memory.feedback_ledger()]==[first,second]


def test_remember_rejects_malformed_context_keys_without_mutation():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    valid=("profile_1","living_room_tv","show_intro","series_alpha")
    invalid=((),("p","d","e"),("p","d","e","c","extra"),("","d","e","c"),(1,"d","e","c"),["p","d","e","c"])
    memory=AdaptiveDirectiveMemory(max_entries=1)
    memory.remember(valid,action="skip",pinned=True)
    proposal=memory.propose(valid,confidence=1.0,context_match=1.0)
    assert proposal is not None
    for key in invalid:
        with pytest.raises(ValueError,match="context key"):
            memory.remember(key,action="mute")
        assert memory.proposal_is_current(proposal) is True


def test_feedback_rejects_malformed_context_key_without_mutation():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    valid=("p","d","e","c")
    memory=AdaptiveDirectiveMemory(5)
    memory.remember(valid,action="skip",pinned=True)
    proposal=memory.propose(valid,confidence=1.0,context_match=1.0)
    before=memory.feedback_ledger()
    with pytest.raises(ValueError,match="context key"):
        memory.feedback(["p","d","e","c"],approved=True,timestamp_bucket=1)
    assert memory.feedback_ledger()==before
    assert memory.proposal_is_current(proposal)


def test_propose_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.propose(["p","d","e","c"],confidence=1.0,context_match=1.0)


def test_should_propose_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.should_propose(["p","d","e","c"],confidence=1.0,context_match=1.0)


def test_recall_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.recall(["p","d","e","c"])


def test_status_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.status(["p","d","e","c"])


def test_strength_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.strength(["p","d","e","c"])


def test_version_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.version(["p","d","e","c"])


def test_is_pinned_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.is_pinned(["p","d","e","c"])


def test_lifecycle_stage_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.lifecycle_stage(["p","d","e","c"])


def test_suspension_reason_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.suspension_reason(["p","d","e","c"])


def test_proposal_threshold_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.proposal_threshold(["p","d","e","c"])


def test_persistence_scope_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.persistence_scope(["p","d","e","c"])


def test_ranked_feedback_reasons_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.ranked_feedback_reasons(["p","d","e","c"],approved=True)


def test_long_press_menu_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.long_press_menu(["p","d","e","c"],approved=True)


def test_suspend_for_policy_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.suspend_for_policy(["p","d","e","c"])


def test_replace_blocked_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.replace_blocked(["p","d","e","c"],action="lower_volume")


def test_advance_lifecycle_rejects_malformed_context_key():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,DirectiveLifecycleStage
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.advance_lifecycle(["p","d","e","c"],target=DirectiveLifecycleStage.SUSPEND)


def test_feedback_from_voice_rejects_malformed_context_key_first():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory
    memory=AdaptiveDirectiveMemory(5)
    with pytest.raises(ValueError,match="context key"):
        memory.feedback_from_voice(["p","d","e","c"],"unrecognized response")


def test_accept_voice_candidate_rejects_malformed_context_key_first():
    import pytest
    from src.edge.adaptive_directive_memory import AdaptiveDirectiveMemory,FeedbackReason,VoiceFeedbackCandidate
    memory=AdaptiveDirectiveMemory(5)
    candidate=VoiceFeedbackCandidate(True,FeedbackReason.NEVER_AUTOMATE,1.0)
    with pytest.raises(ValueError,match="context key"):
        memory.accept_voice_candidate(["p","d","e","c"],candidate,min_confidence=0.5)
