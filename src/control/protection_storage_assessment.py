from dataclasses import dataclass
from enum import Enum


class StoragePlatform(str,Enum):
    ANDROID="ANDROID"
    IOS="IOS"


class StorageRemediationAction(str,Enum):
    CLEAR_REGENERABLE_AQSS_CACHE="CLEAR_REGENERABLE_AQSS_CACHE"
    OPEN_PLATFORM_STORAGE_MANAGER="OPEN_PLATFORM_STORAGE_MANAGER"
    SHOW_IOS_STORAGE_INSTRUCTIONS="SHOW_IOS_STORAGE_INSTRUCTIONS"


class PlatformSettingsDestination(str,Enum):
    NONE="NONE"
    ANDROID_MANAGE_STORAGE="ANDROID_MANAGE_STORAGE"


@dataclass(frozen=True,slots=True)
class StorageSnapshot:
    platform: StoragePlatform
    available_bytes: int
    required_bytes: int
    reclaimable_cache_bytes: int


@dataclass(frozen=True,slots=True)
class ProtectionStorageAssessment:
    eligible: bool
    shortage_bytes: int
    remediation_actions: tuple[StorageRemediationAction,...]
    settings_destination: PlatformSettingsDestination
    requested_bytes: int

    @classmethod
    def from_snapshot(cls,snapshot) -> "ProtectionStorageAssessment":
        invalid=cls(False,0,(),PlatformSettingsDestination.NONE,0)
        if not isinstance(snapshot,StorageSnapshot) or not isinstance(snapshot.platform,StoragePlatform):
            return invalid
        values=(snapshot.available_bytes,snapshot.required_bytes,snapshot.reclaimable_cache_bytes)
        if any(type(value) is not int or value<0 for value in values):
            return invalid
        shortage=max(0,snapshot.required_bytes-snapshot.available_bytes)
        if shortage==0:
            return cls(True,0,(),PlatformSettingsDestination.NONE,0)
        actions=[]
        if snapshot.reclaimable_cache_bytes>0:
            actions.append(StorageRemediationAction.CLEAR_REGENERABLE_AQSS_CACHE)
        if snapshot.platform is StoragePlatform.ANDROID:
            actions.append(StorageRemediationAction.OPEN_PLATFORM_STORAGE_MANAGER)
            return cls(False,shortage,tuple(actions),PlatformSettingsDestination.ANDROID_MANAGE_STORAGE,shortage)
        if snapshot.platform is StoragePlatform.IOS:
            actions.append(StorageRemediationAction.SHOW_IOS_STORAGE_INSTRUCTIONS)
            return cls(False,shortage,tuple(actions),PlatformSettingsDestination.NONE,0)
        return invalid
