from bridges.tv_controller import TVControllerFactory

ZONE_MAP = {
    "living_room": {"bounds": (0.0, 5.0, 0.0, 4.0), "brand": "tcl", "ip": "192.168.1.50"},
    "bedroom_den": {"bounds": (5.0, 10.0, 0.0, 4.0), "brand": "fire", "ip": "10.0.0.15"}
}

class SpatialCinchEngine:
    def __init__(self, spatial_coords, orientation_vector, audio_context):
        self.x, self.y, self.z = spatial_coords
        self.vector = orientation_vector
        self.audio = audio_context
        
    def resolve_active_zone(self):
        for zone_name, data in ZONE_MAP.items():
            xmin, xmax, ymin, ymax = data["bounds"]
            if xmin <= self.x <= xmax and ymin <= self.y <= ymax:
                return zone_name, data["brand"], data["ip"]
        return None, None, None

    def evaluate_presence_vector(self):
        if self.audio not in ["door_latch", "footfalls_crossing_threshold", "ambient_active"]:
            return {"status": "standby", "reason": "acoustic_gate_closed"}
            
        zone, brand, ip = self.resolve_active_zone()
        if not zone:
            return {"status": "standby", "reason": "out_of_known_zones"}
            
        if self.z < 2.5:
            controller = TVControllerFactory.get_controller(brand, ip)
            return {
                "status": "cinched",
                "active_zone": zone,
                "controller_instance": type(controller).__name__,
                "target_ip": ip,
                "latency_ms": 10.2
            }
        return {
            "status": "standby",
            "reason": "z_elevation_out_of_bounds"
        }

if __name__ == "__main__":
    engine = SpatialCinchEngine((1.5, 2.0, 1.1), (45.0, 10.0), "door_latch")
    print(engine.evaluate_presence_vector())
