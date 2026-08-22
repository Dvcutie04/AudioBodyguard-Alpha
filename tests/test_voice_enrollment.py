import pytest
from src.control.voice_enrollment import VoiceEnrollmentEngine

def test_voice_enrollment_and_filtering():
    engine = VoiceEnrollmentEngine(profile_path="test_profile.json")
    
    # Enrolling user baseline voice samples (e.g., typical speech frequency and loudness)
    user_samples = [
        {"freq": 1800.0, "db": 75.0},
        {"freq": 1850.0, "db": 76.0},
        {"freq": 1820.0, "db": 74.0}
    ]
    signature = engine.enroll(user_samples)
    assert signature is not None
    
    # Verify exact user signature match
    exact_match = engine.verify({"freq": 1825.0, "db": 75.0})
    assert exact_match == True
    
    # Test filtering out TV audio, guests, or ambient noise variables
    tv_noise = {"freq": 450.0, "db": 82.0}
    guest_voice = {"freq": 3200.0, "db": 88.0}
    
    assert engine.verify(tv_noise) == False
    assert engine.verify(guest_voice) == False
