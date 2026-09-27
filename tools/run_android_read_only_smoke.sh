#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${1:?pass an artifact directory}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$artifact_dir"

# Run the existing unsigned debug APK in Google's Android Emulator. No audio
# input, output, live endpoint, third-party cloud account, or protection claim.
sdkmanager "emulator" "system-images;android-35;google_apis;x86_64" > /dev/null
printf 'no\n' | avdmanager create avd -n aqss_readonly -k "system-images;android-35;google_apis;x86_64" -f > /dev/null
emulator_bin="${ANDROID_HOME:?Android SDK not configured}/emulator/emulator"
if [[ ! -x "$emulator_bin" ]]; then
    echo "Installed Android Emulator executable not found at $emulator_bin" >&2
    exit 1
fi

if [[ ! -e /dev/kvm ]]; then
    echo "Android Emulator acceleration is unavailable on this CI runner" >&2
    exit 1
fi
sudo chmod a+rw /dev/kvm
"$emulator_bin" -avd aqss_readonly -no-window -no-audio -no-snapshot -no-boot-anim -gpu swiftshader > "$artifact_dir/aqss-android-emulator-startup.log" 2>&1 &
emulator_pid=$!
cleanup() {
    adb emu kill > /dev/null 2>&1 || true
    kill "$emulator_pid" > /dev/null 2>&1 || true
    wait "$emulator_pid" > /dev/null 2>&1 || true
}
trap cleanup EXIT

connected=0
for _ in $(seq 1 120); do
    if ! kill -0 "$emulator_pid" 2>/dev/null; then
        echo "Android Emulator exited before connecting to adb" >&2
        tail -60 "$artifact_dir/aqss-android-emulator-startup.log" >&2
        exit 1
    fi
    if adb devices | awk '$1 ~ /^emulator-/ && $2 == "device" {found = 1} END {exit !found}'; then
        connected=1
        break
    fi
    sleep 2
done
if [[ "$connected" != "1" ]]; then
    echo "Android Emulator did not connect to adb" >&2
    tail -60 "$artifact_dir/aqss-android-emulator-startup.log" >&2
    exit 1
fi
for _ in $(seq 1 120); do
    if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
        booted=1
        break
    fi
    sleep 2
done
if [[ "${booted:-0}" != "1" ]]; then
    echo "Android Emulator did not finish booting" >&2
    tail -60 "$artifact_dir/aqss-android-emulator-startup.log" >&2
    exit 1
fi

adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb install -r "$repo_root/native/android/app/build/outputs/apk/debug/app-debug.apk"
adb shell am start -W -n com.aqss.bodyguard.prototype/.ReadOnlyHomeActivity

for _ in $(seq 1 8); do
    if timeout 45 adb shell uiautomator dump /sdcard/aqss-screen.xml > /dev/null 2>&1 &&
       adb exec-out cat /sdcard/aqss-screen.xml > "$artifact_dir/aqss-android-screen.xml" &&
       python3 "$repo_root/tools/check_android_simulation_screen.py" "$artifact_dir/aqss-android-screen.xml"; then
        adb exec-out screencap -p > "$artifact_dir/aqss-android-simulation.png"
        exit 0
    fi
    sleep 2
done
echo "Android read-only screen did not show its required uncertainty labels" >&2
exit 1
