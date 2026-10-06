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
    local label="$1" capture="$2" evidence="${3:-}" reset_counters="${4:-}" coordinates x y
    capture_ui "$capture"
    coordinates="$(python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/$capture.xml" "$label")"
    if [[ -z "$coordinates" ]]; then echo "Tutorial target not visible: $label" >&2; return 1; fi
    read -r x y <<< "$coordinates"
    if [[ -n "$evidence" ]]; then
        adb shell dumpsys gfxinfo com.aqss.bodyguard.prototype framestats > "$artifact_dir/$evidence-before.txt"
    fi
    if [[ -n "$reset_counters" ]]; then
        adb shell dumpsys gfxinfo com.aqss.bodyguard.prototype reset > "$artifact_dir/roku-frames-reset.txt"
    fi
    adb shell input tap "$x" "$y"
}

complete_frame_evidence() {
    local evidence="$1"
    adb shell dumpsys gfxinfo com.aqss.bodyguard.prototype framestats > "$artifact_dir/$evidence-after.txt"
    python3 tools/android_frame_evidence.py "$artifact_dir/$evidence-before.txt" "$artifact_dir/$evidence-after.txt" --output "$artifact_dir/$evidence.json"
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
    for attempt in {1..12}; do
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
assert_settings_controls() {
    tap_tutorial_label "Exit tutorial" settings_initial_exit
    tap_tutorial_label "Settings" settings_initial_open
    # Nested Settings Back must return to Settings, then to the previous page.
    tap_scroll_label "Advanced Settings" advanced_open
    capture_ui advanced_settings
    assert_tutorial_label advanced_settings "Captions"
    assert_tutorial_label advanced_settings "About Captions"
    python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/advanced_settings.xml" "Captions" false
    tap_scroll_label "Captions" setting_attempt
    adb exec-out screencap -p > "$artifact_dir/setting_attempt_cyan.png"
    capture_ui setting_attempt_state
    python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/setting_attempt_state.xml" "Captions" true
    assert_tutorial_label setting_attempt_state "Not connected."
    sleep 2
    capture_ui setting_attempt_reset
    python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/setting_attempt_reset.xml" "Captions" false
    if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setting_attempt_reset.xml" "Not connected." 2>/dev/null; then exit 1; fi
    tap_scroll_label "About Captions" setting_help
    capture_ui setting_caption_help
    assert_tutorial_label setting_caption_help "verified connection"
    adb shell input keyevent KEYCODE_BACK
    capture_ui setting_help_return
    python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/setting_help_return.xml" "Captions" false
    adb shell input keyevent KEYCODE_BACK
    capture_ui setting_nested_back
    assert_tutorial_label setting_nested_back "SETTINGS"
    assert_tutorial_label setting_nested_back "Appearance"
    adb shell input keyevent KEYCODE_BACK
    capture_ui setting_previous_back
    assert_tutorial_label setting_previous_back "Connection not verified"
}

# Check the changed switch controls before the longer guide walkthrough.
assert_settings_controls
adb shell pm clear com.aqss.bodyguard.prototype
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity
capture_ui beginner_step_1
assert_tutorial_label beginner_step_1 "Step 1 of 6"
assert_only_guide beginner_step_1
assert_tutorial_label beginner_step_1 "Both connections are required"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/beginner_step_1.xml" "What we're building" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/beginner_step_1.xml" "does not monitor or change TV audio" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/beginner_step_1.xml" "Planned controls" 2>/dev/null; then exit 1; fi
assert_tutorial_label beginner_step_1 "1. Connect to your TV or home device"
assert_tutorial_label beginner_step_1 "2. Connect to your phone"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/beginner_step_1.xml" "Skip series intros" 2>/dev/null; then exit 1; fi
assert_tutorial_label beginner_step_1 "Start picture setup"
tap_scroll_label "More features" welcome_more_features
capture_ui welcome_features
assert_tutorial_label welcome_features "Planned"
assert_scroll_label "Skip series intros" welcome_features
assert_scroll_label "Lower volume during commercials" welcome_features_commercials
assert_scroll_label "Universal remote control" welcome_features_remote
assert_scroll_label "Voice input display and recognized words" welcome_features_last
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/welcome_features_last.xml" "Picture guides and photo-assisted setup" 2>/dev/null; then exit 1; fi
tap_tutorial_label "Start picture setup" beginner_begin
capture_ui beginner_step_2
assert_only_guide beginner_step_2
if python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/beginner_step_2.xml" "Next" | grep -q '[0-9]'; then exit 1; fi
tap_scroll_label "Samsung" beginner_tv
capture_ui beginner_tv_selected
assert_tutorial_label beginner_tv_selected "Selected: Samsung"
tap_tutorial_label "Next" beginner_to_home
capture_ui beginner_step_3
assert_only_guide beginner_step_3
if python3 tools/check_android_simulation_ui.py --text-tap-coordinates "$artifact_dir/beginner_step_3.xml" "Next" | grep -q '[0-9]'; then exit 1; fi
tap_scroll_label "Amazon Alexa" beginner_home_choice
tap_tutorial_label "Next" beginner_to_plan
capture_ui beginner_step_4
assert_tutorial_label beginner_step_4 "1. Connect to your TV or home device"
tap_scroll_label "Show Amazon Alexa steps" setup_alexa_scoped
capture_ui setup_alexa_for_samsung
assert_tutorial_label setup_alexa_for_samsung "Samsung / SmartThings → Alexa"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_alexa_for_samsung.xml" "LG ThinQ → Alexa" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_alexa_for_samsung.xml" "Roku TV → Alexa" 2>/dev/null; then exit 1; fi
tap_tutorial_label "Back to Tutorial" setup_alexa_close
capture_ui setup_alexa_plan_return
assert_tutorial_label setup_alexa_plan_return "Step 4 of 6"
tap_tutorial_label "Exit tutorial" tutorial_exit_home
capture_ui rose_home
assert_tutorial_label rose_home "Connection not verified"
assert_tutorial_label rose_home "AI head. Connection not verified. Black and white."
tap_scroll_label "Back to Tutorial" tutorial_resume
capture_ui tutorial_exact_resume
assert_tutorial_label tutorial_exact_resume "Step 4 of 6"
tap_scroll_label "Show Samsung steps" setup_from_plan
tap_scroll_label "Samsung — TV shows OK approval" setup_samsung_route
tap_tutorial_label "Start guide" setup_samsung_begin
capture_ui setup_pair_step_1
assert_tutorial_label setup_pair_step_1 "Step 1 of 17"
for step in {2..15}; do tap_tutorial_label "Next" "setup_samsung_next_$step"; done
capture_ui setup_tv_approval
assert_tutorial_label setup_tv_approval "Approve on the television"
tap_scroll_label "Need help?" setup_approval_details
tap_scroll_label "My screen looks different" setup_mismatch_open
capture_ui setup_mismatch
assert_tutorial_label setup_mismatch "Find the right screen"
tap_tutorial_label "Return to step" setup_mismatch_return
capture_ui setup_approval_retained
assert_tutorial_label setup_approval_retained "Step 15 of 17"
tap_tutorial_label "Next" setup_after_approval
tap_tutorial_label "Next" setup_result
capture_ui setup_last
assert_tutorial_label setup_last "Check the actual result"
tap_tutorial_label "Finish guide" setup_finish
capture_ui setup_plan_return
assert_tutorial_label setup_plan_return "Step 5 of 6"
assert_tutorial_label setup_plan_return "2. Connect to your phone"
assert_tutorial_label setup_plan_return "follow the pictures"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_plan_return.xml" "Show Samsung steps" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_plan_return.xml" "Show Amazon Alexa steps" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_plan_return.xml" "Not connected · Audio protection is not active" 2>/dev/null; then exit 1; fi
tap_scroll_label "Need help?" phone_help_open
assert_scroll_label "official phone app" phone_help_limits
tap_scroll_label "Hide help" phone_help_close
tap_scroll_label "Phone pictures" phone_wifi_open
capture_ui pixel_wifi_intro
# The emulator identifies itself as a generic Android device on some images.
# That correctly opens the phone chooser instead of assuming Pixel menus.
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/pixel_wifi_intro.xml" "Phone Wi-Fi setup" 2>/dev/null; then
    if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/pixel_wifi_intro.xml" "iPhone — connect to your home Wi-Fi" 2>/dev/null; then exit 1; fi
    tap_scroll_label "Google Pixel — connect to your home Wi-Fi" pixel_wifi_choose
    capture_ui pixel_wifi_intro
fi
assert_tutorial_label pixel_wifi_intro "Google Pixel — connect to your home Wi-Fi"
tap_tutorial_label "Start guide" pixel_wifi_start
tap_tutorial_label "Next" pixel_wifi_settings
capture_ui pixel_wifi_picture
assert_tutorial_label pixel_wifi_picture "Network & internet"
tap_scroll_label "Need help?" pixel_wifi_details
tap_scroll_label "My screen looks different" pixel_wifi_mismatch
tap_scroll_label "Choose another model or menu" phone_wifi_choose_system
tap_scroll_label "Samsung Galaxy — connect to your home Wi-Fi" galaxy_wifi_open
tap_tutorial_label "Start guide" galaxy_wifi_start
tap_tutorial_label "Next" galaxy_wifi_settings
capture_ui galaxy_wifi_picture
assert_tutorial_label galaxy_wifi_picture "Connections"
tap_tutorial_label "Back to Tutorial" phone_wifi_close
capture_ui phone_wifi_plan_return
assert_tutorial_label phone_wifi_plan_return "Step 5 of 6"
tap_scroll_label "Need help?" phone_previous_steps_help
tap_scroll_label "Show Samsung steps" setup_from_phone
tap_scroll_label "Samsung — TV shows OK approval" setup_phone_route
tap_tutorial_label "Back to Tutorial" setup_phone_cancel
capture_ui phone_cancelled_return
assert_tutorial_label phone_cancelled_return "Step 5 of 6"
assert_tutorial_label phone_cancelled_return "Show Samsung steps"
tap_scroll_label "Hide help" phone_previous_steps_close
capture_ui phone_simple_again
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/phone_simple_again.xml" "Show Samsung steps" 2>/dev/null; then exit 1; fi
tap_tutorial_label "Back" beginner_phone_back
capture_ui beginner_tailored_plan
assert_tutorial_label beginner_tailored_plan "Step 4 of 6"
tap_tutorial_label "Back" beginner_plan_back
capture_ui beginner_home_retained
assert_tutorial_label beginner_home_retained "Selected: Amazon Alexa"
tap_tutorial_label "Next" beginner_plan_again
tap_tutorial_label "Next" beginner_connection_truth
capture_ui beginner_step_5
assert_tutorial_label beginner_step_5 "2. Connect to your phone"
assert_tutorial_label beginner_step_5 "follow the pictures"
tap_tutorial_label "Next" beginner_last
capture_ui beginner_step_6
assert_only_guide beginner_step_6
tap_tutorial_label "Open full app" beginner_finish
capture_ui beginner_finished
assert_tutorial_label beginner_finished "Connection not verified"
tap_tutorial_label "Replay connection guide" beginner_replay
capture_ui beginner_replayed
assert_tutorial_label beginner_replayed "Step 1 of 6"
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
assert_tutorial_label sound "SOUND"
tap_tutorial_label "Jump to" jump_volume_open
tap_tutorial_label "Sound options" jump_volume
capture_ui sound_options
tap_scroll_label "About Volume" volume_details
assert_scroll_label "No qualified device volume control" sound_volume_detail
adb shell input keyevent KEYCODE_BACK
assert_scroll_label "Dialogue preset" sound_presets
assert_scroll_label "Night preset" sound_night_preset
tap_tutorial_label "Devices" nav_devices
capture_ui devices
assert_scroll_label "No qualified device connected" devices
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
capture_ui readiness_back
assert_tutorial_label readiness_back "Step 5 of 6"
tap_tutorial_label "Exit tutorial" readiness_exit
capture_ui readiness_closed
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/readiness_closed.xml" "Exit tutorial" 2>/dev/null; then exit 1; fi

tap_tutorial_label "Jump to" handoff_open
tap_tutorial_label "Session transfer" handoff_jump
tap_scroll_label "About Move this session" handoff_help
capture_ui handoff
assert_tutorial_label handoff "No supported endpoint or verified transfer path"
adb shell input keyevent KEYCODE_BACK
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
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/settings.xml" "Make space for you." 2>/dev/null; then exit 1; fi
tap_tutorial_label "Help & tutorials" settings_help
tap_tutorial_label "About this page" settings_about
capture_ui settings_about_text
assert_tutorial_label settings_about_text "Choose an appearance or open Advanced Settings."
adb shell input keyevent KEYCODE_BACK
tap_tutorial_label "Daylight" theme_daylight
capture_ui daylight_settings
tap_tutorial_label "Home" theme_home
capture_ui daylight_home
assert_tutorial_label daylight_home "Connection not verified"
tap_tutorial_label "Settings" theme_settings
tap_tutorial_label "Midnight" theme_midnight
tap_scroll_label "Advanced Settings" future_open
tap_scroll_label "About Voice requests" future_voice
capture_ui future_voice_detail
assert_tutorial_label future_voice_detail "Voice control requires device authority and checked output"
tap_scroll_label "Show voice steps" future_voice_help
capture_ui setup_voice_first
assert_tutorial_label setup_voice_first "Step 1 of 9"
for step in 2 3 4 5; do tap_tutorial_label "Next" "setup_voice_next_$step"; done
capture_ui setup_voice_meter
assert_tutorial_label setup_voice_meter "Speak and watch the meter"
for step in 6 7 8 9; do tap_tutorial_label "Next" "setup_voice_next_$step"; done
tap_tutorial_label "Open Voice check" setup_voice_try
capture_ui setup_voice_ready
assert_tutorial_label setup_voice_ready "Microphone off"
tap_tutorial_label "Close" setup_voice_close
tap_tutorial_label "Jump to" privacy_open
tap_tutorial_label "Privacy and storage" privacy_jump
tap_scroll_label "About Privacy and storage" privacy_help
capture_ui privacy
assert_tutorial_label privacy "No audio files saved by this app"
assert_tutorial_label privacy "Appearance and guide dismissal stay on this phone"
adb shell input keyevent KEYCODE_BACK

tap_tutorial_label "Sound" input_sound
 tap_scroll_label "Voice check. See microphone activity and recognized words" input_voice
capture_ui voice_idle
assert_tutorial_label voice_idle "Microphone off"
assert_scroll_label "No words recognized yet" voice_words
tap_tutorial_label "Close" voice_close
tap_tutorial_label "Devices" input_devices
tap_scroll_label "TV photo setup. Read a model label or Network settings photo" input_photo
capture_ui photo_idle
assert_tutorial_label photo_idle "No photo selected"
assert_scroll_label "Brand: Not identified" photo_hints
tap_tutorial_label "Close" photo_close

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
python3 tools/check_android_simulation_ui.py --wait-background
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
assert_tutorial_label restored_home "Connection not verified"

tap_tutorial_label "Devices" roku_devices
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" roku_open
tap_scroll_label "TCL" roku_brand
tap_scroll_label "Need help?" roku_platform_help
tap_scroll_label "Help identify my TV" roku_identify
capture_ui tv_identification_intro
assert_tutorial_label tv_identification_intro "Start guide"
adb shell input keyevent KEYCODE_BACK
capture_ui tv_platform_help_return
assert_tutorial_label tv_platform_help_return "Roku TV"
assert_tutorial_label tv_platform_help_return "Help identify my TV"
tap_scroll_label "Hide help" roku_platform_help_close
tap_scroll_label "Roku TV" roku_platform
capture_ui roku_simple_picker
assert_tutorial_label roku_simple_picker "Start guide"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_simple_picker.xml" "Start TV setup" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_simple_picker.xml" "Find my exact model (Roku TV)" 2>/dev/null; then exit 1; fi
capture_ui roku_simple_intro
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_simple_intro.xml" "Open reference in browser" 2>/dev/null; then exit 1; fi
tap_scroll_label "Need help?" roku_details
tap_scroll_label "I’m already in Settings" roku_settings
capture_ui roku_settings_picture
assert_tutorial_label roku_settings_picture "Step 3 of 5"
adb shell input keyevent KEYCODE_BACK
capture_ui roku_back_to_intro
assert_tutorial_label roku_back_to_intro "I’m already in Settings"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_back_to_intro.xml" "Step 2 of 5" 2>/dev/null; then exit 1; fi
tap_scroll_label "I’m already in Settings" roku_settings_again
tap_tutorial_label "Next" roku_about roku-step-3-to-4-frames reset
capture_ui roku_about_picture
complete_frame_evidence roku-step-3-to-4-frames
assert_tutorial_label roku_about_picture "Step 4 of 5"
tap_tutorial_label "Close" roku_close
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" roku_reopen
tap_scroll_label "TCL" roku_rebrand
tap_scroll_label "Roku TV" roku_replatform
tap_tutorial_label "Resume guide" roku_resume roku-resume-frames
capture_ui roku_resumed
complete_frame_evidence roku-resume-frames
assert_tutorial_label roku_resumed "Step 4 of 5"
tap_tutorial_label "Next" roku_ip roku-step-4-to-5-frames
capture_ui roku_ip_picture
complete_frame_evidence roku-step-4-to-5-frames
assert_tutorial_label roku_ip_picture "Step 5 of 5"
tap_tutorial_label "Finish part one" roku_finish
capture_ui roku_phone_intro
assert_tutorial_label roku_phone_intro "2. Connect to your phone (Roku)"
adb shell input keyevent KEYCODE_BACK
capture_ui roku_phone_back_to_tv
assert_tutorial_label roku_phone_back_to_tv "Step 5 of 5"
tap_tutorial_label "Finish part one" roku_phone_again
tap_tutorial_label "Start part two" roku_phone_begin
capture_ui roku_phone_picture
assert_tutorial_label roku_phone_picture "Step 1 of 5"
tap_tutorial_label "Close" roku_phone_close
adb shell dumpsys gfxinfo com.aqss.bodyguard.prototype > "$artifact_dir/roku-frame-summary.txt"
tap_tutorial_label "Home" roku_home

# The alternate Roku model route must show System in picture 3. The Network
# picture belongs only to the IP-address route exercised above.
tap_tutorial_label "Devices" model_devices
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" model_open
tap_scroll_label "Roku-branded TV" model_brand
tap_scroll_label "Need help?" model_help
tap_scroll_label "Other setup options" model_options
tap_scroll_label "Find my exact model (Roku TV)" model_select
tap_tutorial_label "Start guide" model_start
tap_tutorial_label "Next" model_home_picture
tap_tutorial_label "Next" model_settings_picture
capture_ui roku_model_system_picture
assert_tutorial_label roku_model_system_picture "Step 3 of 5"
assert_tutorial_label roku_model_system_picture "Highlight System"
tap_tutorial_label "Close" model_close
tap_tutorial_label "Home" model_home

# Newer VIZIO TVs show the My Hub account QR sequence before phone pairing.
tap_tutorial_label "Devices" vizio_devices
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" vizio_open
tap_scroll_label "Vizio" vizio_brand
capture_ui vizio_choices
assert_tutorial_label vizio_choices "VIZIO newer TV — My Hub account, then phone"
tap_scroll_label "VIZIO newer TV — My Hub account, then phone" vizio_select
tap_tutorial_label "Start guide" vizio_start
tap_tutorial_label "Next" vizio_hub
capture_ui vizio_my_hub_picture
assert_tutorial_label vizio_my_hub_picture "Step 2 of 14"
tap_tutorial_label "Next" vizio_qr
capture_ui vizio_account_qr_picture
assert_tutorial_label vizio_account_qr_picture "Step 3 of 14"
tap_tutorial_label "Next" vizio_signin
capture_ui vizio_walmart_signin_picture
assert_tutorial_label vizio_walmart_signin_picture "Step 4 of 14"
tap_tutorial_label "Close" vizio_close
tap_tutorial_label "Home" vizio_home

# Reopening the main phone action resumes this user's already-selected Roku
# phone guide instead of sending them through a generic Wi-Fi walkthrough.
tap_scroll_label "TV & smart-home guide" roku_replay_guide
tap_tutorial_label "Start picture setup" roku_replay_begin
tap_scroll_label "TCL" roku_replay_tv
tap_tutorial_label "Next" roku_replay_home
tap_scroll_label "Neither / not sure" roku_replay_assistant
tap_tutorial_label "Next" roku_replay_plan
tap_scroll_label "Show TCL steps" roku_replay_pictures
capture_ui roku_remembered_system
assert_tutorial_label roku_remembered_system "Start guide"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_remembered_system.xml" "Google TV / Android TV" 2>/dev/null; then exit 1; fi
tap_scroll_label "Need help?" roku_replay_details
tap_scroll_label "I’m already in Settings" roku_replay_settings
tap_tutorial_label "Next" roku_replay_about
tap_tutorial_label "Next" roku_replay_ip
tap_tutorial_label "Finish part one" roku_replay_finish_tv
tap_tutorial_label "Back to Tutorial" roku_replay_pause_phone
capture_ui roku_main_phone_step
assert_tutorial_label roku_main_phone_step "Step 5 of 6"
tap_scroll_label "Phone pictures" roku_main_phone_open
capture_ui roku_main_phone_resume
assert_tutorial_label roku_main_phone_resume "2. Connect to your phone (Roku)"
assert_tutorial_label roku_main_phone_resume "Resume guide"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/roku_main_phone_resume.xml" "Google Pixel — connect to your home Wi-Fi" 2>/dev/null; then exit 1; fi
adb shell input keyevent KEYCODE_BACK
capture_ui roku_main_phone_back
assert_tutorial_label roku_main_phone_back "Step 5 of 6"
tap_tutorial_label "Exit tutorial" roku_replay_exit

# Page Back follows visited pages, not an expansion menu or the Home shortcut.
tap_tutorial_label "Devices" back_devices
capture_ui simple_devices
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/simple_devices.xml" "Six setup checks unknown" 2>/dev/null; then exit 1; fi
tap_tutorial_label "Sound" back_sound
capture_ui simple_sound
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/simple_sound.xml" "Dialogue preset" 2>/dev/null; then exit 1; fi
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/simple_sound.xml" "A qualified device and observed result" 2>/dev/null; then exit 1; fi
tap_scroll_label "Options" back_sound_options
tap_tutorial_label "Settings" back_settings
adb shell input keyevent KEYCODE_BACK
capture_ui page_back_sound
assert_tutorial_label page_back_sound "SOUND"
adb shell input keyevent KEYCODE_BACK
capture_ui page_back_devices
assert_tutorial_label page_back_devices "DEVICES"
tap_tutorial_label "Back to previous page" page_back_home_button
capture_ui page_back_home
assert_tutorial_label page_back_home "Connection not verified"

tap_tutorial_label "Devices" philips_devices
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" philips_open
tap_scroll_label "Philips" philips_brand
tap_scroll_label "Google TV / Android TV" philips_platform
tap_scroll_label "Need help?" philips_primary_help
tap_scroll_label "Other setup options" philips_other
tap_scroll_label "Philips Google TV — pair the voice remote" philips_route
tap_tutorial_label "Start guide" philips_start
tap_tutorial_label "Next" philips_profile
capture_ui philips_profile_picture
assert_tutorial_label philips_profile_picture "Step 2 of 10"
tap_tutorial_label "Close" philips_close
tap_tutorial_label "Home" philips_home

adb shell settings put system font_scale 2.0
capture_ui large_text_home
tap_scroll_label "TV & smart-home guide" large_beginner_open
capture_ui large_beginner
assert_tutorial_label large_beginner "Step 1 of 6"
tap_tutorial_label "Start picture setup" large_beginner_next
tap_tutorial_label "Exit tutorial" large_beginner_close
tap_tutorial_label "Pages · Home" large_pages
tap_tutorial_label "Devices" large_devices
capture_ui large_text_devices
tap_scroll_label "Illustrated setup guides. TV pairing, Google Home & Alexa · one picture at a time" setup_large_open
tap_scroll_label "TCL" setup_large_tcl
tap_scroll_label "Google TV / Android TV" setup_large_platform
tap_scroll_label "Need help?" setup_large_primary_help
tap_scroll_label "Other setup options" setup_large_more_options
tap_scroll_label "TCL QM851G / Q651G / QM891G — first setup" setup_large_route
tap_tutorial_label "Start guide" setup_large_start
capture_ui setup_large_step
assert_tutorial_label setup_large_step "Step 1 of 12"
if python3 tools/check_android_simulation_ui.py --assert-label "$artifact_dir/setup_large_step.xml" "Use your real device. This picture is an illustration." 2>/dev/null; then exit 1; fi
assert_tutorial_label setup_large_step "Close"
assert_tutorial_label setup_large_step "Next"
adb shell settings put system user_rotation 1
capture_ui setup_large_landscape
assert_tutorial_label setup_large_landscape "Step 1 of 12"
adb shell settings put system user_rotation 0
tap_tutorial_label "Close" setup_large_close
tap_tutorial_label "Help & tutorials" large_help
tap_scroll_label "Readiness checklist" large_topic
capture_ui large_text_tutorial
assert_tutorial_label large_text_tutorial "Step 1 of 6"
tap_tutorial_label "Exit tutorial" large_close
capture_ui large_text_closed
assert_tutorial_label large_text_closed "Pages · Home"
tap_tutorial_label "Back to previous page" large_return_previous
capture_ui large_previous_page
assert_tutorial_label large_previous_page "Pages · Devices"
tap_tutorial_label "Pages · Devices" large_settings_pages
tap_tutorial_label "Settings" large_settings
tap_scroll_label "Advanced Settings" large_advanced
capture_ui large_advanced_settings
python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/large_advanced_settings.xml" "Captions" false
tap_scroll_label "About Captions" large_setting_help
capture_ui large_setting_help_text
assert_tutorial_label large_setting_help_text "verified connection"
adb shell input keyevent KEYCODE_BACK
tap_scroll_label "Captions" large_setting_attempt
adb shell input keyevent KEYCODE_HOME
python3 tools/check_android_simulation_ui.py --wait-background
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity
capture_ui large_setting_background_reset
python3 tools/check_android_simulation_ui.py --assert-switch "$artifact_dir/large_setting_background_reset.xml" "Captions" false
adb shell input keyevent KEYCODE_BACK
capture_ui large_settings_back
assert_tutorial_label large_settings_back "Appearance"
echo "ANDROID_THEME_UI_OBSERVED: sequential six-step guide, simple defaults, optional details, choice gating, tailored plan, completion, replay, persisted exit, five pages, unknown coverage, unavailable controls, six readiness steps, labeled example, themes, future explanation, tutorial routing, previous-page Back, lifecycle, rotation and large text passed"
