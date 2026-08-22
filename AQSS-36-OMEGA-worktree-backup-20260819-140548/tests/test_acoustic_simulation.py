import unittest
from src.sim.acoustic_environment import MultiMicSimulator
from src.voice.orchestrator import SpatialVoiceEngine

class TestMultiMicAcousticSim(unittest.TestCase):
    def setUp(self):
        self.sim = MultiMicSimulator(seed=1337)
        self.engine = SpatialVoiceEngine()

    def test_approaching_threat_trajectory(self):
        start_pos = [5.0, 5.0, 0.0]
        res1 = self.engine.process_frame(self.sim.generate_frame(start_pos, signal_amplitude=0.2))
        close_pos = [1.0, 1.0, 0.0]
        res2 = self.engine.process_frame(self.sim.generate_frame(close_pos, signal_amplitude=0.8))
        self.assertEqual(res2["status"], "processed")
        self.assertEqual(res2["trajectory"], "RISING_THREAT")
        self.assertGreater(res2["risk_score"], res1["risk_score"])
