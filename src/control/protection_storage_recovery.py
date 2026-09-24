from dataclasses import dataclass

from src.control.protection_storage_assessment import PlatformSettingsDestination,ProtectionStorageAssessment,StorageRemediationAction


@dataclass(frozen=True,slots=True)
class StorageRecoveryRequest:
    action: StorageRemediationAction
    settings_destination: PlatformSettingsDestination
    requested_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.action,StorageRemediationAction) or not isinstance(self.settings_destination,PlatformSettingsDestination) or type(self.requested_bytes) is not int or self.requested_bytes<0:
            raise ValueError("invalid storage recovery request")
        if self.action is StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER:
            if self.settings_destination is not PlatformSettingsDestination.ANDROID_MANAGE_STORAGE or self.requested_bytes<=0:
                raise ValueError("Android storage manager requires its supported destination and positive requested bytes")
        elif self.action in (StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS):
            if self.settings_destination is not PlatformSettingsDestination.NONE or self.requested_bytes!=0:
                raise ValueError("non-Android recovery requests cannot carry a settings destination or byte request")
        else:
            raise ValueError("unsupported storage recovery action")


@dataclass(frozen=True,slots=True)
class ProtectionStorageRecoveryPlan:
    requests: tuple[StorageRecoveryRequest,...]
    restores_eligibility: bool
    requires_fresh_evidence: bool

    def __post_init__(self) -> None:
        if type(self.requests) is not tuple or any(not isinstance(request,StorageRecoveryRequest) for request in self.requests):
            raise ValueError("recovery plans require typed storage recovery requests")
        actions=tuple(request.action for request in self.requests)
        allowed=((),(StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER,),(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER),(StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS,),(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE,StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS))
        if actions not in allowed:
            raise ValueError("recovery plan request sequence is invalid")
        if self.restores_eligibility is not False or self.requires_fresh_evidence is not True:
            raise ValueError("recovery plans cannot restore eligibility and always require fresh evidence")

    @classmethod
    def from_assessment(cls,assessment) -> "ProtectionStorageRecoveryPlan":
        fail_closed=cls((),False,True)
        if not isinstance(assessment,ProtectionStorageAssessment) or type(assessment.eligible) is not bool:
            return fail_closed
        if assessment.eligible is True:
            return fail_closed
        if type(assessment.shortage_bytes) is not int or assessment.shortage_bytes<=0 or type(assessment.requested_bytes) is not int or assessment.requested_bytes<0:
            return fail_closed
        if not isinstance(assessment.settings_destination,PlatformSettingsDestination) or type(assessment.remediation_actions) is not tuple:
            return fail_closed
        if any(any(action is prior for prior in assessment.remediation_actions[:index]) for index,action in enumerate(assessment.remediation_actions)):
            return fail_closed
        if assessment.settings_destination is PlatformSettingsDestination.ANDROID_MANAGE_STORAGE and (StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER not in assessment.remediation_actions or assessment.remediation_actions[-1] is not StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER):
            return fail_closed
        if assessment.settings_destination is PlatformSettingsDestination.NONE and (StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS not in assessment.remediation_actions or assessment.remediation_actions[-1] is not StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS):
            return fail_closed
        requests=[]
        for action in assessment.remediation_actions:
            if action is StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE:
                requests.append(StorageRecoveryRequest(action,PlatformSettingsDestination.NONE,0))
            elif action is StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER:
                if assessment.settings_destination is not PlatformSettingsDestination.ANDROID_MANAGE_STORAGE or assessment.requested_bytes!=assessment.shortage_bytes:
                    return fail_closed
                requests.append(StorageRecoveryRequest(action,assessment.settings_destination,assessment.requested_bytes))
            elif action is StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS:
                if assessment.settings_destination is not PlatformSettingsDestination.NONE or assessment.requested_bytes!=0:
                    return fail_closed
                requests.append(StorageRecoveryRequest(action,PlatformSettingsDestination.NONE,0))
            else:
                return fail_closed
        return cls(tuple(requests),False,True)


@dataclass(frozen=True,slots=True)
class ProtectionStorageRecoveryGuide:
    tips: tuple[str,...]
    settings_destination: PlatformSettingsDestination
    requested_bytes: int
    requires_user_action: bool
    restores_eligibility: bool
    requires_fresh_evidence: bool

    def __post_init__(self) -> None:
        if type(self.tips) is not tuple or any(type(tip) is not str or not tip.strip() for tip in self.tips):
            raise ValueError("recovery guide tips must be nonempty strings")
        if not isinstance(self.settings_destination,PlatformSettingsDestination) or type(self.requested_bytes) is not int or self.requested_bytes<0 or type(self.requires_user_action) is not bool:
            raise ValueError("invalid recovery guide metadata")
        if self.requires_user_action is not bool(self.tips):
            raise ValueError("recovery guide user-action state is inconsistent")
        if self.settings_destination is PlatformSettingsDestination.ANDROID_MANAGE_STORAGE:
            if self.requested_bytes<=0 or self.requires_user_action is not True:
                raise ValueError("Android recovery guidance requires positive requested bytes and user action")
        elif self.settings_destination is PlatformSettingsDestination.NONE:
            if self.requested_bytes!=0:
                raise ValueError("guidance without a settings destination cannot request bytes")
        else:
            raise ValueError("unsupported recovery guide destination")
        if self.restores_eligibility is not False or self.requires_fresh_evidence is not True:
            raise ValueError("recovery guides cannot restore eligibility and always require fresh evidence")

    @classmethod
    def from_plan(cls,plan) -> "ProtectionStorageRecoveryGuide":
        if not isinstance(plan,ProtectionStorageRecoveryPlan):
            raise TypeError("plan must be ProtectionStorageRecoveryPlan")
        tips=[]
        destination=PlatformSettingsDestination.NONE
        requested_bytes=0
        for request in plan.requests:
            if request.action is StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE:
                tips.append("Clear only regenerable AQSS cache.")
            elif request.action is StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER:
                tips.append(f"Free at least {request.requested_bytes} bytes in Android storage settings.")
                destination=request.settings_destination
                requested_bytes=request.requested_bytes
            elif request.action is StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS:
                tips.append("Open Settings > General > iPhone Storage and free space.")
            else:
                raise ValueError("unsupported recovery guide action")
        return cls(tuple(tips),destination,requested_bytes,bool(plan.requests),False,True)


class ProtectionStorageRecoveryDispatcher:
    def __init__(self,platform):
        self._platform=platform

    def open_supported_settings(self,guide,*,user_confirmed: bool) -> bool:
        if not isinstance(guide,ProtectionStorageRecoveryGuide) or type(user_confirmed) is not bool or user_confirmed is not True:
            return False
        if guide.requires_user_action is not True or guide.settings_destination is not PlatformSettingsDestination.ANDROID_MANAGE_STORAGE or guide.requested_bytes<=0:
            return False
        opener=getattr(self._platform,"open_settings",None)
        if not callable(opener):
            return False
        try:
            opener(destination=guide.settings_destination,requested_bytes=guide.requested_bytes)
        except Exception:
            return False
        return True
