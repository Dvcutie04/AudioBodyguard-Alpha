import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class RoomState:
    room_name: str
    occupants: List[str]
    devices_active: Dict[str, str]
    current_profile: str
    anomalies: List[str]

class EnvironmentalMemory:
    def __init__(self):
        self.state_graph: Dict[str, RoomState] = {}

    def update_room(self, room_name: str, occupants: List[str], devices: Dict[str, str], profile: str):
        self.state_graph[room_name] = RoomState(
            room_name=room_name,
            occupants=occupants,
            devices_active=devices,
            current_profile=profile,
            anomalies=[]
        )

    def flag_anomaly(self, room_name: str, anomaly_desc: str):
        if room_name in self.state_graph:
            self.state_graph[room_name].anomalies.append(anomaly_desc)

    def get_state_json(self, room_name: str) -> str:
        if room_name in self.state_graph:
            return json.dumps(asdict(self.state_graph[room_name]), indent=2)
        return "{}"

if __name__ == '__main__':
    memory = EnvironmentalMemory()
    memory.update_room(
        room_name="Living Room",
        occupants=["David"],
        devices={"TV": "ON", "HVAC": "72F"},
        profile="Evening_Focus"
    )
    print("Current Room State (No Raw Audio Stored):")
    print(memory.get_state_json("Living Room"))
