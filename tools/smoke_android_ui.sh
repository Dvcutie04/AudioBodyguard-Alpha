#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${AQSS_UI_ARTIFACT_DIR:-artifacts/ui/android}"
mkdir -p "$artifact_dir"

adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity | tee "$artifact_dir/launch.txt"

capture_ui() {
    local label="$1"
    local attempt dump_attempt coordinates x y
    for attempt in 1 2 3; do
        # UiAutomator can report a null root immediately after a cold launch.
        # Never interpret its missing output as an AQSS screen observation.
        for dump_attempt in 1 2 3 4; do
            adb shell rm -f /sdcard/aqss-ui.xml
            adb shell uiautomator dump /sdcard/aqss-ui.xml || true
            adb exec-out cat /sdcard/aqss-ui.xml > "$artifact_dir/$label.xml" || true
            if python3 tools/check_android_simulation_ui.py --valid-hierarchy "$artifact_dir/$label.xml"; then
                break
            fi
            if [[ "$dump_attempt" -eq 4 ]]; then
                adb exec-out screencap -p > "$artifact_dir/$label.png"
                echo "Android UI hierarchy unavailable after four captures" >&2
                return 1
            fi
            sleep 2
        done
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

# Inspect the user-opened menu separately so its extra rows cannot mask the
# original coverage and handoff checks above.
for _ in 1 2 3; do adb shell input swipe 500 300 500 1600 350; done
capture_ui options_start
coordinates="$(python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/options_start.xml" "Options")"
if [[ -z "$coordinates" ]]; then echo "Options button not visible" >&2; exit 1; fi
read -r x y <<< "$coordinates"
adb shell input tap "$x" "$y"
capture_ui options_top

coordinates=""
for attempt in 1 2 3 4 5 6; do
    capture_ui "options_middle_$attempt"
    coordinates="$(python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/options_middle_$attempt.xml" "Advanced options")"
    if [[ -n "$coordinates" ]]; then break; fi
    adb shell input swipe 500 1600 500 250 350
done
if [[ -z "$coordinates" ]]; then echo "Advanced options button not visible" >&2; exit 1; fi
read -r x y <<< "$coordinates"
adb shell input tap "$x" "$y"
capture_ui advanced_top
adb shell input swipe 500 1600 500 250 350
capture_ui advanced_middle
adb shell input swipe 500 1600 500 250 350
capture_ui advanced_bottom
python3 tools/check_android_simulation_ui.py --options-menu \
    "$artifact_dir/options_top.xml" "$artifact_dir"/options_middle_*.xml \
    "$artifact_dir/advanced_top.xml" "$artifact_dir/advanced_middle.xml" "$artifact_dir/advanced_bottom.xml"
