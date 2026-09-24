from src.control.protection_storage_assessment import PlatformSettingsDestination,ProtectionStorageAssessment,StoragePlatform,StorageRemediationAction,StorageSnapshot


def test_android_storage_shortage_offers_cache_cleanup_and_supported_storage_manager():
    snapshot=StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50)
    assessment=ProtectionStorageAssessment.from_snapshot(snapshot)
    assert assessment.eligible is False
    assert assessment.shortage_bytes==200
    assert assessment.remediation_actions==(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER)
    assert assessment.settings_destination is PlatformSettingsDestination.ANDROID_MANAGE_STORAGE
    assert assessment.requested_bytes==200


def test_ios_storage_shortage_uses_supported_in_app_recovery_without_private_deep_link():
    snapshot=StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=50)
    assessment=ProtectionStorageAssessment.from_snapshot(snapshot)
    assert assessment.eligible is False
    assert assessment.shortage_bytes==200
    assert assessment.remediation_actions==(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS)
    assert assessment.settings_destination is PlatformSettingsDestination.NONE
    assert assessment.requested_bytes==0


def test_storage_boundary_is_eligible_and_malformed_boolean_measurement_fails_closed():
    boundary=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.IOS,available_bytes=300,required_bytes=300,reclaimable_cache_bytes=0))
    assert boundary.eligible is True
    assert boundary.shortage_bytes==0
    assert boundary.remediation_actions==()
    assert boundary.settings_destination is PlatformSettingsDestination.NONE
    assert boundary.requested_bytes==0
    malformed=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=True,required_bytes=300,reclaimable_cache_bytes=0))
    assert malformed.eligible is False
    assert malformed.shortage_bytes==0
    assert malformed.remediation_actions==()
    assert malformed.settings_destination is PlatformSettingsDestination.NONE
    assert malformed.requested_bytes==0


def test_reclaimable_cache_never_counts_as_available_before_fresh_observation():
    before=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=100,required_bytes=300,reclaimable_cache_bytes=500))
    assert before.eligible is False
    assert before.shortage_bytes==200
    assert before.remediation_actions==(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER)
    after=ProtectionStorageAssessment.from_snapshot(StorageSnapshot(platform=StoragePlatform.ANDROID,available_bytes=600,required_bytes=300,reclaimable_cache_bytes=0))
    assert after.eligible is True
    assert after.shortage_bytes==0
    assert after.remediation_actions==()
    assert after.settings_destination is PlatformSettingsDestination.NONE
    assert after.requested_bytes==0
