#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${AQSS_UI_ARTIFACT_DIR:-artifacts/ui/android}"
mkdir -p "$artifact_dir"

adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity | tee "$artifact_dir/launch.txt"

capture_ui() {
    local label="$1"
    local attempt coordinates x y
    for attempt in 1 2 3; do
        adb shell uiautomator dump /sdcard/aqss-ui.xml
        adb exec-out cat /sdcard/aqss-ui.xml > "$artifact_dir/$label.xml"
        adb exec-out screencap -p > "$artifact_dir/$label.png"
        coordinates="$(python3 tools/check_android_simulation_ui.py --launcher-close-coordinates "$artifact_dir/$label.xml")"
        if [[ -z "$coordinates" ]]; then return 0; fi

        mv "$artifact_dir/$label.xml" "$artifact_dir/$label-launcher-overlay-$attempt.xml"
        mv "$artifact_dir/$label.png" "$artifact_dir/$label-launcher-overlay-$attempt.png"
        if [[ "$attempt" -eq 3 ]]; then
            echo "System launcher dialog persisted after two bounded dismissals" >&2
            return 1
        fi
        read -r x y <<< "$coordinates"
        adb shell input tap "$x" "$y"
        adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity
        if [[ "$label" == bottom ]]; then
            adb shell input swipe 500 1600 500 250 350
            adb shell input swipe 500 1600 500 250 350
        fi
    done
}

capture_ui top

# The handoff explanation is below the initial viewport on a typical phone.
adb shell input swipe 500 1600 500 250 350
adb shell input swipe 500 1600 500 250 350
capture_ui bottom

python3 tools/check_android_simulation_ui.py "$artifact_dir/top.xml" "$artifact_dir/bottom.xml"
