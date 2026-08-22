import unittest
from audio_engine.dark_silicon_airgap import DarkSiliconAirgap

class TestDarkSiliconAirgap(unittest.TestCase):
    def test_initial_state(self):
        airgap = DarkSiliconAirgap("omega-1")
        self.assertEqual(airgap.get_status()["status"], "ACTIVE")
        self.assertFalse(airgap.get_status()["isolated"])

    def test_trigger_isolation(self):
        airgap = DarkSiliconAirgap("omega-1")
        self.assertTrue(airgap.trigger_isolation())
        self.assertEqual(airgap.get_status()["status"], "ISOLATED_DARK_SILICON")
        self.assertTrue(airgap.get_status()["isolated"])

if __name__ == "__main__":
    unittest.main()
