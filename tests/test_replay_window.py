import unittest
from audio_engine.symmetric_auth import ReplayWindow

class TestReplayWindow(unittest.TestCase):
    def test_window(self):
        rw = ReplayWindow(window_size=4)
        self.assertTrue(rw.check_and_update(1))
        self.assertTrue(rw.check_and_update(2))
        self.assertTrue(rw.check_and_update(5))

if __name__ == "__main__":
    unittest.main()
