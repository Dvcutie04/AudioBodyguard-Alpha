from dataclasses import replace

import pytest

from src.control.protection_storage_assessment import PlatformSettingsDestination,ProtectionStorageAssessment,StoragePlatform,StorageRemediationAction,StorageSnapshot
from src.control.protection_storage_recovery import ProtectionStorageRecoveryDispatcher,ProtectionStorageRecoveryGuide,ProtectionStorageRecoveryPlan,StorageRecoveryRequest


def test_android_recovery_plan_is_non_authoritative_and_requires_fresh_evidence():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    plan=ProtectionStorageRecoveryPlan.from_assessment(assessment)
    assert plan.requests==(StorageRecoveryRequest(action=StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0),StorageRecoveryRequest(action=StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER,settings_destination=PlatformSettingsDestination.ANDROID_MANAGE_STORAGE,requested_bytes=200))
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_ios_recovery_plan_uses_instructions_without_private_settings_destination():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    plan=ProtectionStorageRecoveryPlan.from_assessment(assessment)
    assert plan.requests==(StorageRecoveryRequest(action=StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0),StorageRecoveryRequest(action=StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS,settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0))
    assert all(request.settings_destination is PlatformSettingsDestination.NONE for request in plan.requests)
    assert all(request.requested_bytes==0 for request in plan.requests)
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_inconsistent_android_recovery_metadata_fails_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,settings_destination=PlatformSettingsDestination.NONE)
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_incomplete_android_recovery_sequence_fails_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,remediation_actions=(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,))
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_incomplete_ios_recovery_sequence_fails_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,remediation_actions=(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,))
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_duplicate_recovery_actions_fail_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,remediation_actions=assessment.remediation_actions+(StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER,))
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_reordered_android_recovery_actions_fail_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,remediation_actions=tuple(reversed(assessment.remediation_actions)))
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_reordered_ios_recovery_actions_fail_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    forged=replace(assessment,remediation_actions=tuple(reversed(assessment.remediation_actions)))
    plan=ProtectionStorageRecoveryPlan.from_assessment(forged)
    assert plan.requests==()
    assert plan.restores_eligibility is False
    assert plan.requires_fresh_evidence is True


def test_recovery_plan_cannot_claim_restored_eligibility():
    with pytest.raises(ValueError):
        ProtectionStorageRecoveryPlan(requests=(),restores_eligibility=True,requires_fresh_evidence=False)


def test_android_settings_request_rejects_non_android_destination():
    with pytest.raises(ValueError):
        StorageRecoveryRequest(action=StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER,settings_destination=PlatformSettingsDestination.NONE,requested_bytes=200)


def test_recovery_plan_rejects_untyped_requests():
    with pytest.raises(ValueError):
        ProtectionStorageRecoveryPlan(requests=(object(),),restores_eligibility=False,requires_fresh_evidence=True)


def test_direct_plan_construction_rejects_reordered_requests():
    cache=StorageRecoveryRequest(action=StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0)
    settings=StorageRecoveryRequest(action=StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER,settings_destination=PlatformSettingsDestination.ANDROID_MANAGE_STORAGE,requested_bytes=200)
    with pytest.raises(ValueError):
        ProtectionStorageRecoveryPlan(requests=(settings,cache),restores_eligibility=False,requires_fresh_evidence=True)


def test_android_recovery_guide_is_user_controlled_and_non_authoritative():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    plan=ProtectionStorageRecoveryPlan.from_assessment(assessment)
    guide=ProtectionStorageRecoveryGuide.from_plan(plan)
    assert guide.tips==("Clear only regenerable AQSS cache.","Free at least 200 bytes in Android storage settings.")
    assert guide.settings_destination is PlatformSettingsDestination.ANDROID_MANAGE_STORAGE
    assert guide.requested_bytes==200
    assert guide.requires_user_action is True
    assert guide.restores_eligibility is False
    assert guide.requires_fresh_evidence is True


def test_ios_recovery_guide_uses_public_instructions_without_deep_link():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    plan=ProtectionStorageRecoveryPlan.from_assessment(assessment)
    guide=ProtectionStorageRecoveryGuide.from_plan(plan)
    assert guide.tips==("Clear only regenerable AQSS cache.","Open Settings > General > iPhone Storage and free space.")
    assert guide.settings_destination is PlatformSettingsDestination.NONE
    assert guide.requested_bytes==0
    assert guide.requires_user_action is True
    assert guide.restores_eligibility is False
    assert guide.requires_fresh_evidence is True


def test_recovery_guide_cannot_claim_restored_eligibility():
    with pytest.raises(ValueError):
        ProtectionStorageRecoveryGuide(tips=(),settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0,requires_user_action=False,restores_eligibility=True,requires_fresh_evidence=False)


def test_android_recovery_dispatch_requires_explicit_user_confirmation():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    guide=ProtectionStorageRecoveryGuide.from_plan(ProtectionStorageRecoveryPlan.from_assessment(assessment))
    class CountingPlatform:
        def __init__(self):
            self.calls=[]
        def open_settings(self,*,destination,requested_bytes):
            self.calls.append((destination,requested_bytes))
    platform=CountingPlatform()
    dispatcher=ProtectionStorageRecoveryDispatcher(platform)
    assert dispatcher.open_supported_settings(guide,user_confirmed=False) is False
    assert platform.calls==[]


def test_confirmed_android_recovery_opens_supported_settings_exactly_once():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    guide=ProtectionStorageRecoveryGuide.from_plan(ProtectionStorageRecoveryPlan.from_assessment(assessment))
    class CountingPlatform:
        def __init__(self):
            self.calls=[]
        def open_settings(self,*,destination,requested_bytes):
            self.calls.append((destination,requested_bytes))
    platform=CountingPlatform()
    dispatcher=ProtectionStorageRecoveryDispatcher(platform)
    assert dispatcher.open_supported_settings(guide,user_confirmed=True) is True
    assert platform.calls==[(PlatformSettingsDestination.ANDROID_MANAGE_STORAGE,200)]
    assert guide.restores_eligibility is False
    assert guide.requires_fresh_evidence is True


def test_ios_guidance_never_dispatches_unsupported_settings_link():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    guide=ProtectionStorageRecoveryGuide.from_plan(ProtectionStorageRecoveryPlan.from_assessment(assessment))
    class CountingPlatform:
        def __init__(self):
            self.calls=[]
        def open_settings(self,*,destination,requested_bytes):
            self.calls.append((destination,requested_bytes))
    platform=CountingPlatform()
    dispatcher=ProtectionStorageRecoveryDispatcher(platform)
    assert dispatcher.open_supported_settings(guide,user_confirmed=True) is False
    assert platform.calls==[]
    assert guide.settings_destination is PlatformSettingsDestination.NONE
    assert guide.restores_eligibility is False
    assert guide.requires_fresh_evidence is True


def test_truthy_non_boolean_cannot_confirm_settings_dispatch():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    guide=ProtectionStorageRecoveryGuide.from_plan(ProtectionStorageRecoveryPlan.from_assessment(assessment))
    class CountingPlatform:
        def __init__(self):
            self.calls=[]
        def open_settings(self,*,destination,requested_bytes):
            self.calls.append((destination,requested_bytes))
    platform=CountingPlatform()
    dispatcher=ProtectionStorageRecoveryDispatcher(platform)
    assert dispatcher.open_supported_settings(guide,user_confirmed=1) is False
    assert platform.calls==[]


def test_android_settings_dispatch_failure_fails_closed():
    assessment=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50))
    guide=ProtectionStorageRecoveryGuide.from_plan(ProtectionStorageRecoveryPlan.from_assessment(assessment))
    class FailingPlatform:
        def __init__(self):
            self.calls=[]
        def open_settings(self,*,destination,requested_bytes):
            self.calls.append((destination,requested_bytes))
            raise RuntimeError("settings unavailable")
    platform=FailingPlatform()
    dispatcher=ProtectionStorageRecoveryDispatcher(platform)
    assert dispatcher.open_supported_settings(guide,user_confirmed=True) is False
    assert platform.calls==[(PlatformSettingsDestination.ANDROID_MANAGE_STORAGE,200)]
    assert guide.restores_eligibility is False
    assert guide.requires_fresh_evidence is True
