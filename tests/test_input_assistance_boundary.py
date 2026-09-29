"""Native assistance must stay local and isolated from output authority."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_voice_and_photo_have_no_output_or_network_adapter():
    files = [ROOT / 'native/ios-app/Sources/InputAssistance.swift', ROOT / 'native/android/app/src/main/kotlin/com/aqss/bodyguard/prototype/InputAssistanceActivity.kt']
    for path in files:
        source = path.read_text()
        for forbidden in ('URLSession', 'HttpURLConnection', 'OkHttp', 'EndpointHandoffBarrier', 'PhysicalCommit', 'setStreamVolume', 'adjustStreamVolume'):
            assert forbidden not in source
        assert '30' in source

def test_native_privacy_configuration_is_explicit_and_foreground_only():
    ios = (ROOT / 'native/ios-app/AQSSReadOnly.xcodeproj/project.pbxproj').read_text()
    android = (ROOT / 'native/android/app/src/main/AndroidManifest.xml').read_text()
    for permission in ('NSMicrophoneUsageDescription', 'NSSpeechRecognitionUsageDescription', 'NSCameraUsageDescription'):
        assert permission in ios
    assert 'android.permission.RECORD_AUDIO' in android
    assert 'FOREGROUND_SERVICE' not in android
    assert 'UIBackgroundModes' not in ios
