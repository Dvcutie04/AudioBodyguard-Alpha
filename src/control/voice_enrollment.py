import json
class VoiceEnrollmentEngine:
    def __init__(self, profile_path="voice_profile.json", freq_tolerance=100.0, db_tolerance=15.0):
        self.profile_path = profile_path
        self.freq_tolerance = freq_tolerance
        self.db_tolerance = db_tolerance
        self.signature = None
        self._load_profile()
    def _load_profile(self):
        try:
            with open(self.profile_path, "r") as f:
                self.signature = json.load(f)
        except Exception:
            self.signature = None
    def enroll(self, sample_features):
        avg_freq = sum(f.get("freq", 0) for f in sample_features) / len(sample_features)
        avg_db = sum(f.get("db", 0) for f in sample_features) / len(sample_features)
        self.signature = {"avg_freq": avg_freq, "avg_db": avg_db}
        with open(self.profile_path, "w") as f:
            json.dump(self.signature, f)
        return self.signature
    def verify(self, ev):
        if not self.signature:
            self._load_profile()
            if not self.signature:
                return False
        freq, db = ev.get("freq", 0), ev.get("db", 0)
        freq_diff = abs(freq - self.signature["avg_freq"])
        db_diff = abs(db - self.signature["avg_db"])
        return freq_diff <= self.freq_tolerance and db_diff <= self.db_tolerance
