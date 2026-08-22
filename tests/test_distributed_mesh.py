from audio_engine.mesh_clock import MeshClock
def test_clock():
    c1 = MeshClock(1000, 10.0)
    c1.advance(1000)
    assert c1.now_ms() == 2000
