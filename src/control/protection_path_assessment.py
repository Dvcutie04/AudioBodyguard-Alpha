from dataclasses import dataclass
from enum import Enum

from src.control.protection_resource_assessment import ProtectionResourceAssessment,ProtectionResourceReason
from src.control.protection_storage_assessment import PlatformSettingsDestination,ProtectionStorageAssessment


class ProtectionPathReason(str,Enum):
    ELIGIBLE="ELIGIBLE"
    RESOURCE_INELIGIBLE="RESOURCE_INELIGIBLE"
    STORAGE_INELIGIBLE="STORAGE_INELIGIBLE"
    INVALID_ASSESSMENT="INVALID_ASSESSMENT"


@dataclass(frozen=True,slots=True)
class ProtectionPathAssessment:
    eligible: bool
    reason: ProtectionPathReason

    @classmethod
    def from_assessments(cls,resource,storage) -> "ProtectionPathAssessment":
        invalid=cls(False,ProtectionPathReason.INVALID_ASSESSMENT)
        if not isinstance(resource,ProtectionResourceAssessment) or not isinstance(storage,ProtectionStorageAssessment):
            return invalid
        if type(resource.eligible) is not bool or type(storage.eligible) is not bool:
            return invalid
        if resource.eligible is True and (resource.reason is not ProtectionResourceReason.ADMITTED or resource.remediation_actions!=()):
            return invalid
        if resource.eligible is False and resource.reason is ProtectionResourceReason.ADMITTED:
            return invalid
        if storage.eligible is True and (storage.shortage_bytes!=0 or storage.remediation_actions!=() or storage.settings_destination is not PlatformSettingsDestination.NONE or storage.requested_bytes!=0):
            return invalid
        if resource.eligible is False:
            return cls(False,ProtectionPathReason.RESOURCE_INELIGIBLE)
        if storage.eligible is False:
            return cls(False,ProtectionPathReason.STORAGE_INELIGIBLE)
        return cls(True,ProtectionPathReason.ELIGIBLE)
