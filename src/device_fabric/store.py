import json, os
from typing import Dict, Any

class StateStore:
    def __init__(self, filepath: str = "device_store.json"):
        self.filepath = filepath

    def save_states(self, states: Dict[str, Any]) -> None:
        serialized = {}
        for dev_id, state in states.items():
            serialized[dev_id] = {"power_state": state.power_state, "power": state.power, "volume": state.volume, "muted": state.muted, "channel": state.channel, "input_source": state.input_source, "payload": state.payload, "metadata": state.metadata}
        with open(self.filepath, "w") as f:
            json.dump(serialized, f, indent=2)

    def load_states(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            return {}
        with open(self.filepath, "r") as f:
            return json.load(f)
