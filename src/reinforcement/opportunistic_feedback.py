import time
from dataclasses import dataclass, field

@dataclass
class PromptingController:
    fatigue_threshold: int = 5
    cooldown_seconds: float = 60.0
    recent_prompt_timestamps: list = field(default_factory=list)
    consecutive_prompts: int = 0

    def should_prompt(self, impact: float, novelty: float, uncertainty: float, in_high_stress_episode: bool = False) -> bool:
        if in_high_stress_episode:
            return False
        
        now = time.time()
        self.recent_prompt_timestamps = [t for t in self.recent_prompt_timestamps if now - t < self.cooldown_seconds]
        
        if self.consecutive_prompts >= self.fatigue_threshold or len(self.recent_prompt_timestamps) >= 3:
            return False
        
        score = (0.4 * impact) + (0.3 * novelty) + (0.3 * uncertainty)
        return score >= 0.5

    def record_prompt(self):
        self.consecutive_prompts += 1
        self.recent_prompt_timestamps.append(time.time())

    def reset_fatigue(self):
        self.consecutive_prompts = 0
        self.recent_prompt_timestamps.clear()
