from dataclasses import dataclass

@dataclass(frozen=True)
class ContextProfile:
    name: str
    sensitivity_offset: float = 0.0
    attenuation_multiplier: float = 1.0
    persistence_weight: float = 1.0

class ContextProfileManager:
    DEFAULT_PROFILES = {
        "home": ContextProfile("home", sensitivity_offset=-5.0, attenuation_multiplier=0.9, persistence_weight=1.0),
        "vehicle": ContextProfile("vehicle", sensitivity_offset=10.0, attenuation_multiplier=1.2, persistence_weight=1.5),
        "outdoor": ContextProfile("outdoor", sensitivity_offset=15.0, attenuation_multiplier=1.5, persistence_weight=1.2),
        "sleeping": ContextProfile("sleeping", sensitivity_offset=-20.0, attenuation_multiplier=0.5, persistence_weight=2.0),
        "unknown": ContextProfile("unknown", sensitivity_offset=0.0, attenuation_multiplier=1.0, persistence_weight=1.0)
    }
    def __init__(self, active_context: str = "unknown"):
        self._active_context = active_context if active_context in self.DEFAULT_PROFILES else "unknown"
    @property
    def active_context(self) -> str:
        return self._active_context
    def set_context(self, context_name: str) -> None:
        if context_name in self.DEFAULT_PROFILES:
            self._active_context = context_name
    def get_active_profile(self) -> ContextProfile:
        return self.DEFAULT_PROFILES[self._active_context]
