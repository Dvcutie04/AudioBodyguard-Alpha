from abc import ABC, abstractmethod
from typing import Any, Dict
from .types import SpatialEvidence

class BaseSourceSeparator(ABC):
    @abstractmethod
    def separate(self, frame: Any, evidence: SpatialEvidence) -> Dict[str, Any]:
        pass

class NullSeparator(BaseSourceSeparator):
    def separate(self, frame: Any, evidence: SpatialEvidence) -> Dict[str, Any]:
        return {
            "status": "BYPASSED_NULL_SEPARATOR",
            "enhanced_frame": frame,
            "snr_gain_db": 0.0
        }

if __name__ == "__main__":
    separator = NullSeparator()
    print(f"[Separator Interface Ready] Default: {separator.__class__.__name__}")
