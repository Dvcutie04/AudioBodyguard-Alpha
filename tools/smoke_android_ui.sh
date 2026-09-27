#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${AQSS_UI_ARTIFACT_DIR:-artifacts/ui/android}"
mkdir -p "$artifact_dir"

adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity | tee "$artifact_dir/launch.txt"

adb shell uiautomator dump /sdcard/aqss-ui.xml
adb exec-out cat /sdcard/aqss-ui.xml > "$artifact_dir/top.xml"
adb exec-out screencap -p > "$artifact_dir/top.png"

# The handoff explanation is below the initial viewport on a typical phone.
adb shell input swipe 500 1600 500 250 350
adb shell input swipe 500 1600 500 250 350
adb shell uiautomator dump /sdcard/aqss-ui.xml
adb exec-out cat /sdcard/aqss-ui.xml > "$artifact_dir/bottom.xml"
adb exec-out screencap -p > "$artifact_dir/bottom.png"

python3 tools/check_android_simulation_ui.py "$artifact_dir/top.xml" "$artifact_dir/bottom.xml"
