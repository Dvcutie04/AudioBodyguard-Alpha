from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PolicySnapshot:
    version: int
    parameters: Dict[str, Any]
    timestamp: float
    reason: str

class RollbackManager:
    def __init__(self):
        self.history: List[PolicySnapshot] = []
        self.stable_baseline_version: Optional[int] = None

    def commit_version(self, version: int, parameters: Dict[str, Any], reason: str = "standard_update") -> PolicySnapshot:
        snapshot = PolicySnapshot(version=version, parameters=parameters, timestamp=__import__("time").time(), reason=reason)
        self.history.append(snapshot)
        if self.stable_baseline_version is None:
            self.stable_baseline_version = version
        return snapshot

    def set_stable_baseline(self, version: int) -> bool:
        if any(s.version == version for s in self.history):
            self.stable_baseline_version = version
            return True
        return False

    def rollback_to(self, target_version: int, new_version: int) -> Optional[PolicySnapshot]:
        target_snapshot = next((s for s in self.history if s.version == target_version), None)
        if not target_snapshot:
            return None
        
        # Create new version reflecting rolled-back parameters without mutating history
        rolled_back_params = dict(target_snapshot.parameters)
        new_snapshot = self.commit_version(
            version=new_version,
            parameters=rolled_back_params,
            reason=f"Rollback to version {target_version}"
        )
        return new_snapshot
