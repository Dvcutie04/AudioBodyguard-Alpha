from src.control.protection_path_assessment import ProtectionPathAssessment,ProtectionPathReason
from src.control.protection_resource_assessment import ProtectionResourceAssessment,ProtectionResourceReason
from src.control.protection_storage_assessment import PlatformSettingsDestination,ProtectionStorageAssessment


def test_storage_ineligibility_fail_closes_an_otherwise_eligible_protection_path():
    resource=ProtectionResourceAssessment(eligible=True,reason=ProtectionResourceReason.ADMITTED,remediation_actions=())
    storage=ProtectionStorageAssessment(eligible=False,shortage_bytes=200,remediation_actions=(),settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0)
    assessment=ProtectionPathAssessment.from_assessments(resource,storage)
    assert assessment.eligible is False
    assert assessment.reason is ProtectionPathReason.STORAGE_INELIGIBLE


def test_internally_inconsistent_assessments_fail_closed():
    eligible_storage=ProtectionStorageAssessment(eligible=True,shortage_bytes=0,remediation_actions=(),settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0)
    contradictory_resource=ProtectionResourceAssessment(eligible=True,reason=ProtectionResourceReason.MEMORY_BUDGET_EXCEEDED,remediation_actions=())
    resource_result=ProtectionPathAssessment.from_assessments(contradictory_resource,eligible_storage)
    assert resource_result.eligible is False
    assert resource_result.reason is ProtectionPathReason.INVALID_ASSESSMENT
    admitted_resource=ProtectionResourceAssessment(eligible=True,reason=ProtectionResourceReason.ADMITTED,remediation_actions=())
    contradictory_storage=ProtectionStorageAssessment(eligible=True,shortage_bytes=200,remediation_actions=(),settings_destination=PlatformSettingsDestination.NONE,requested_bytes=0)
    storage_result=ProtectionPathAssessment.from_assessments(admitted_resource,contradictory_storage)
    assert storage_result.eligible is False
    assert storage_result.reason is ProtectionPathReason.INVALID_ASSESSMENT
