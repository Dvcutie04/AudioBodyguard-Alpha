#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${AQSS_UI_ARTIFACT_DIR:-artifacts/ui/android}"
mkdir -p "$artifact_dir"

collect_failure_diagnostics() {
    local status=$?
    if [[ "$status" -ne 0 ]]; then
        adb logcat -b crash -d > "$artifact_dir/crash-log.txt" 2>&1 || true
        adb shell dumpsys activity activities > "$artifact_dir/activity-state.txt" 2>&1 || true
        adb shell dumpsys window windows > "$artifact_dir/window-state.txt" 2>&1 || true
    fi
    return "$status"
}
trap collect_failure_diagnostics EXIT

adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
adb logcat -c
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
            adb shell input swipe 500 1600 500 250 900
            adb shell input swipe 500 1600 500 250 900
        fi
    done
}

capture_ui top

# Inspect after each bounded gesture: a cold emulator may not process two
# back-to-back short swipes reliably. Keep the required UI assertion unchanged.
for attempt in 1 2 3 4 5 6; do
    adb shell input swipe 500 2200 500 450 900
    capture_ui bottom
    if python3 tools/check_android_simulation_ui.py --assert-label \
        "$artifact_dir/bottom.xml" "Moving a session between phones is not available here" 2>/dev/null; then
        break
    fi
done

python3 tools/check_android_simulation_ui.py "$artifact_dir/top.xml" "$artifact_dir/bottom.xml"

# Inspect the user-opened menu separately so its extra rows cannot mask the
# original coverage and handoff checks above.
for _ in 1 2 3; do adb shell input swipe 500 300 500 1600 900; done
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
    adb shell input swipe 500 1600 500 250 900
done
if [[ -z "$coordinates" ]]; then echo "Advanced options button not visible" >&2; exit 1; fi
read -r x y <<< "$coordinates"
adb shell input tap "$x" "$y"
capture_ui advanced_top
adb shell input swipe 500 1600 500 250 900
capture_ui advanced_middle
adb shell input swipe 500 1600 500 250 900
capture_ui advanced_bottom
python3 tools/check_android_simulation_ui.py --options-menu \
    "$artifact_dir/options_top.xml" "$artifact_dir"/options_middle_*.xml \
    "$artifact_dir/advanced_top.xml" "$artifact_dir/advanced_middle.xml" "$artifact_dir/advanced_bottom.xml"

tap_tutorial_label() {
    local label="$1" capture="$2" coordinates x y
    capture_ui "$capture"
    coordinates="$(python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/$capture.xml" "$label")"
    if [[ -z "$coordinates" ]]; then echo "Tutorial target not visible: $label" >&2; return 1; fi
    read -r x y <<< "$coordinates"
    adb shell input tap "$x" "$y"
}

assert_tutorial_label() {
    python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/$1.xml" "$2"
}

tap_tutorial_label "Help & tutorials" tutorial_help
tap_tutorial_label "Sound options" tutorial_topics
capture_ui tutorial_sound_first
assert_tutorial_label tutorial_sound_first "Step 1 of 4"
tap_tutorial_label "Next" tutorial_next
capture_ui tutorial_sound_second
assert_tutorial_label tutorial_sound_second "Step 2 of 4"
assert_tutorial_label tutorial_sound_second "Volume needs a supported output"
tap_tutorial_label "Back" tutorial_back
capture_ui tutorial_sound_back
assert_tutorial_label tutorial_sound_back "Step 1 of 4"
tap_tutorial_label "Close tutorial" tutorial_close

tap_tutorial_label "Help & tutorials" tutorial_help_again
tap_tutorial_label "Advanced and privacy" tutorial_topics_again
tap_tutorial_label "Next" tutorial_advanced_first
tap_tutorial_label "Next" tutorial_advanced_second
capture_ui tutorial_advanced_physical
assert_tutorial_label tutorial_advanced_physical "Step 3 of 5"
assert_tutorial_label tutorial_advanced_physical "Unknown physical state"
tap_tutorial_label "Close tutorial" tutorial_advanced_close

tap_tutorial_label "Help & tutorials" tutorial_help_captions
tap_tutorial_label "Captions" tutorial_caption_topics
tap_tutorial_label "Next" tutorial_captions_first
capture_ui tutorial_captions_last
assert_tutorial_label tutorial_captions_last "Step 2 of 2"
tap_tutorial_label "Done" tutorial_captions_done

tap_tutorial_label "Help & tutorials" tutorial_help_replay
tap_tutorial_label "Sound options" tutorial_topics_replay
capture_ui tutorial_replay
assert_tutorial_label tutorial_replay "Step 1 of 4"
tap_tutorial_label "Close tutorial" tutorial_finish
echo "ANDROID_TUTORIAL_OBSERVED: manual navigation, close, completion and replay passed"
