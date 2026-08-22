import json
from src.control.hysteretic_engine import AQSSSafetyEngine
from src.control.voice_enrollment import VoiceEnrollmentEngine
from src.control.action_dispatcher import ActionDispatcher

class AQSNgressRouter:
    def __init__(self, profile_path="voice_profile.json", webhook_url=None): 
        self.hysteretic = AQSSSafetyEngine()
        self.voice = VoiceEnrollmentEngine(profile_path=profile_path)
        self.dispatcher = ActionDispatcher(webhook_url=webhook_url)

    def process_event(self, ev):
        if not self.voice.signature:
            try:
                with open(self.voice.profile_path, "r") as f:
                    self.voice.signature = json.load(f)
            except Exception:
                pass
                
        # 1. Verify authorized speaker voice
        is_authorized_voice = self.voice.verify(ev)
        
        # 2. Evaluate environmental safety telemetry
        safety_res = self.hysteretic.update(ev)
        
        accel = ev.get("accel_vector", {"x": 0.0, "y": 0.0, "z": 1.0})
        motion_magnitude = (accel["x"]**2 + accel["y"]**2 + accel["z"]**2)**0.5
        safety_res["telemetry_state"] = {"motion_magnitude": motion_magnitude}

        # 3. Voice Command Intent Mapping & Action Dispatch
        command_intent = ev.get("command_intent", None)
        
        if is_authorized_voice:
            safety_res["fusion_state"] = "AUDIO_VOICE_FUSED"
            if command_intent:
                safety_res["decision"] = f"VOICE_COMMAND_EXECUTED: {command_intent.upper()}"
                safety_res["action_result"] = self.dispatcher.dispatch(safety_res["decision"], safety_res["telemetry_state"])
            elif safety_res["weights"]["p_threat"] < 0.8:
                safety_res["decision"] = "LEVEL_0: FALSE_POSITIVE_SUPPRESSED_AUTHORIZED_VOICE"
                
        return safety_res
