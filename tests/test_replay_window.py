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


def test_duplicate_and_out_of_order_sequences_are_admitted_only_once():
    window = ReplayWindow(window_size=4)
    assert window.check_and_update(5)
    assert not window.check_and_update(5)
    assert window.check_and_update(3)
    assert not window.check_and_update(3)
    assert not window.check_and_update(1)
    assert window.check_and_update(8)
    assert not window.check_and_update(3)
    assert not window.check_and_update(5)
    assert window.check_and_update(6)


def test_large_jump_keeps_a_bounded_window():
    window = ReplayWindow(window_size=4)
    assert window.check_and_update(1)
    assert window.check_and_update(10**12)
    assert not window.check_and_update(1)
    assert window.check_and_update(10**12 - 3)
    assert not window.check_and_update(10**12 - 4)


def test_invalid_sequences_do_not_advance_the_window():
    window = ReplayWindow(window_size=4)
    for value in (True, False, -1, 1.5, "9", None, float("nan")):
        assert window.check_and_update(value) is False
    assert window.check_and_update(1)


def test_invalid_window_size_is_rejected():
    import pytest
    for value in (0, -1, True, 1.5, "4"):
        with pytest.raises(ValueError):
            ReplayWindow(window_size=value)
