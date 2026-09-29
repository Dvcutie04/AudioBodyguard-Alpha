#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${AQSS_UI_ARTIFACT_DIR:-artifacts/ui/android}"
mkdir -p "$artifact_dir"

collect_failure_diagnostics() {
    local status=$?
    if [[ -n "${original_font_scale:-}" ]]; then
        adb shell settings put system font_scale "$original_font_scale" || true
        adb shell settings put system user_rotation "$original_rotation" || true
        adb shell settings put system accelerometer_rotation "$original_auto_rotation" || true
    fi
    if [[ "$status" -ne 0 ]]; then
        adb logcat -b crash -d > "$artifact_dir/crash-log.txt" 2>&1 || true
        adb shell dumpsys activity activities > "$artifact_dir/activity-state.txt" 2>&1 || true
        adb shell dumpsys window windows > "$artifact_dir/window-state.txt" 2>&1 || true
    fi
    return "$status"
}
trap collect_failure_diagnostics EXIT

adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
adb shell pm clear com.aqss.bodyguard.prototype
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

tap_scroll_label() {
    local label="$1" capture="$2" coordinates x y
    for attempt in 1 2 3 4 5 6; do
        capture_ui "$capture"
        coordinates="$(python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/$capture.xml" "$label")"
        if [[ -n "$coordinates" ]]; then
            read -r x y <<< "$coordinates"
            adb shell input tap "$x" "$y"
            return 0
        fi
        adb shell input swipe 500 1600 500 450 900
    done
    echo "Content target not reached: $label" >&2; return 1
}

assert_scroll_label() {
    local label="$1" capture="$2"
    for attempt in 1 2 3 4 5 6; do
        capture_ui "$capture"
        if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/$capture.xml" "$label" 2>/dev/null; then return 0; fi
        adb shell input swipe 500 1600 500 450 900
    done
    echo "Content label not reached: $label" >&2; return 1
}

# A fresh install starts with only the current learning task.
assert_only_guide() {
    python3 - "$artifact_dir/$1.xml" <<'CHECK'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
labels = {n.get("content-desc") or n.get("text") for n in root.iter("node") if n.get("class") == "android.widget.Button"}
assert "Exit tutorial" in labels, labels
assert not labels.intersection({"Home", "Sound", "Devices", "Insights", "Settings", "Help & tutorials", "Jump to"}), labels
CHECK
}
capture_ui beginner_step_1
assert_tutorial_label beginner_step_1 "Step 1 of 7"
assert_only_guide beginner_step_1
tap_tutorial_label "Begin" beginner_begin
capture_ui beginner_step_2
assert_only_guide beginner_step_2
if python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/beginner_step_2.xml" "Next" | grep -q '[0-9]'; then exit 1; fi
tap_tutorial_label "Samsung" beginner_tv
capture_ui beginner_tv_selected
assert_tutorial_label beginner_tv_selected "Selected: Samsung"
tap_tutorial_label "Next" beginner_to_home
capture_ui beginner_step_3
assert_only_guide beginner_step_3
if python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/beginner_step_3.xml" "Next" | grep -q '[0-9]'; then exit 1; fi
tap_tutorial_label "Amazon Alexa" beginner_home_choice
tap_tutorial_label "Next" beginner_to_plan
capture_ui beginner_step_4
assert_tutorial_label beginner_step_4 "Your connection checklist"
assert_scroll_label "Amazon Alexa" beginner_tailored_plan
tap_tutorial_label "Back" beginner_plan_back
capture_ui beginner_home_retained
assert_tutorial_label beginner_home_retained "Selected: Amazon Alexa"
tap_tutorial_label "Next" beginner_plan_again
tap_tutorial_label "Next" beginner_connection_truth
capture_ui beginner_step_5
assert_tutorial_label beginner_step_5 "not connected to Audio Bodyguard"
tap_tutorial_label "Next" beginner_feature_example
tap_tutorial_label "Next" beginner_last
capture_ui beginner_step_7
assert_only_guide beginner_step_7
tap_tutorial_label "Open full app" beginner_finish
capture_ui beginner_finished
assert_tutorial_label beginner_finished "TOUR FINISHED"
tap_tutorial_label "Replay connection guide" beginner_replay
capture_ui beginner_replayed
assert_tutorial_label beginner_replayed "Step 1 of 7"
tap_tutorial_label "Exit tutorial" beginner_exit
adb shell am force-stop com.aqss.bodyguard.prototype
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity
capture_ui beginner_dismissal_persisted
assert_tutorial_label beginner_dismissal_persisted "Help & tutorials"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/beginner_dismissal_persisted.xml" "Exit tutorial" 2>/dev/null; then exit 1; fi
tap_tutorial_label "Jump to" initial_coverage_open
tap_tutorial_label "Coverage" initial_coverage
capture_ui coverage
assert_tutorial_label coverage "Unknown physical state"
assert_tutorial_label coverage "No output observation"
tap_tutorial_label "Sound" nav_sound
capture_ui sound
assert_tutorial_label sound "Sound, on your terms."
tap_tutorial_label "Jump to" jump_volume_open
tap_tutorial_label "Sound options" jump_volume
capture_ui sound_options
adb shell input swipe 500 1600 500 450 900
capture_ui sound_presets
assert_tutorial_label sound_presets "No qualified device volume control"
assert_tutorial_label sound_presets "Dialogue preset"
assert_tutorial_label sound_presets "Night preset"
tap_tutorial_label "Devices" nav_devices
capture_ui devices
assert_tutorial_label devices "No qualified device connected"
tap_tutorial_label "Jump to" jump_readiness_open
tap_tutorial_label "Readiness checklist" jump_readiness
capture_ui readiness
assert_tutorial_label readiness "Six setup checks unknown"
tap_tutorial_label "Help with readiness" readiness_help
readiness_titles=("Output hardware" "Qualified path" "Permission and authority" "Output route" "Runtime eligibility" "Independent observation")
for step in 1 2 3 4 5 6; do
    capture_ui "readiness_step_$step"
    assert_tutorial_label "readiness_step_$step" "Step $step of 6"
    assert_tutorial_label "readiness_step_$step" "${readiness_titles[$((step - 1))]}"
    if [[ "$step" -eq 1 ]]; then tap_tutorial_label "Begin" readiness_begin; elif [[ "$step" -lt 6 ]]; then tap_tutorial_label "Next" readiness_next; fi
done
adb shell input keyevent KEYCODE_BACK
capture_ui readiness_closed
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/readiness_closed.xml" "Exit tutorial" 2>/dev/null; then exit 1; fi

tap_tutorial_label "Jump to" handoff_open
tap_tutorial_label "Session transfer" handoff_jump
capture_ui handoff
assert_tutorial_label handoff "No supported endpoint or verified transfer path"
tap_tutorial_label "Insights" nav_insights
capture_ui insights
assert_tutorial_label insights "No measurements yet"
tap_tutorial_label "Explore an example" example_open
capture_ui example
assert_tutorial_label example "EXAMPLE · synthetic data"
assert_tutorial_label example "Relative level (0–100)"
tap_scroll_label "Read chart values" values_open
assert_scroll_label "Sample 4: 64 relative units" example_values
adb shell input keyevent KEYCODE_BACK
capture_ui example_closed
assert_tutorial_label example_closed "No measurements yet"
tap_tutorial_label "Settings" nav_settings
capture_ui settings
tap_tutorial_label "Daylight" theme_daylight
capture_ui daylight_settings
tap_tutorial_label "Home" theme_home
capture_ui daylight_home
assert_tutorial_label daylight_home "does not monitor or change audio"
tap_tutorial_label "Settings" theme_settings
tap_tutorial_label "Midnight" theme_midnight
tap_scroll_label "Hide advanced options" advanced_close
tap_scroll_label "Voice requests. Planned · proposal only" future_voice
capture_ui future_voice_detail
assert_tutorial_label future_voice_detail "This app is not listening for commands"
tap_tutorial_label "Got it" future_voice_close
tap_tutorial_label "Jump to" privacy_open
tap_tutorial_label "Privacy and storage" privacy_jump
capture_ui privacy
assert_tutorial_label privacy "No audio recorded by this app"
assert_tutorial_label privacy "Your appearance and guide dismissal are saved locally"

tap_tutorial_label "Home" return_home
tap_tutorial_label "Help & tutorials" guide_open
tap_tutorial_label "Home and coverage" guide_choose
capture_ui guide_1
assert_tutorial_label guide_1 "Step 1 of 4"
tap_tutorial_label "Begin" guide_next_1
capture_ui guide_2
assert_tutorial_label guide_2 "Step 2 of 4"
tap_tutorial_label "Next" guide_next_2
capture_ui guide_3
assert_tutorial_label guide_3 "Step 3 of 4"
tap_tutorial_label "Back" guide_back
adb shell input keyevent KEYCODE_HOME
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity
capture_ui guide_return
assert_tutorial_label guide_return "Step 2 of 4"
original_font_scale="$(adb shell settings get system font_scale | tr -d '\r')"
original_rotation="$(adb shell settings get system user_rotation | tr -d '\r')"
original_auto_rotation="$(adb shell settings get system accelerometer_rotation | tr -d '\r')"
adb shell settings put system accelerometer_rotation 0
adb shell settings put system user_rotation 1
capture_ui landscape_tutorial
assert_tutorial_label landscape_tutorial "Step 2 of 4"
assert_tutorial_label landscape_tutorial "Exit tutorial"
assert_only_guide landscape_tutorial
adb shell settings put system user_rotation 0
capture_ui portrait_tutorial
tap_tutorial_label "Exit tutorial" guide_close
capture_ui restored_home
assert_tutorial_label restored_home "does not monitor or change audio"

adb shell settings put system font_scale 2.0
capture_ui large_text_home
tap_scroll_label "TV & smart-home guide" large_beginner_open
capture_ui large_beginner
assert_tutorial_label large_beginner "Step 1 of 7"
tap_tutorial_label "Begin" large_beginner_next
tap_tutorial_label "Exit tutorial" large_beginner_close
tap_tutorial_label "Pages · Home" large_pages
tap_tutorial_label "Devices" large_devices
capture_ui large_text_devices
tap_tutorial_label "Help & tutorials" large_help
tap_scroll_label "Readiness checklist" large_topic
capture_ui large_text_tutorial
assert_tutorial_label large_text_tutorial "Step 1 of 6"
tap_tutorial_label "Exit tutorial" large_close
capture_ui large_text_closed
assert_tutorial_label large_text_closed "Pages · Devices"
echo "ANDROID_THEME_UI_OBSERVED: sequential seven-step guide, hidden later controls, choice gating, tailored plan, completion, replay, persisted exit, five pages, unknown coverage, unavailable controls, six readiness steps, labeled example, themes, future explanation, tutorial routing, Back, lifecycle, rotation and large text passed"
