#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${1:?pass an artifact directory}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$artifact_dir"

simulator_id="$(xcrun simctl list -j devices available | python3 -c '
import json, sys
devices = json.load(sys.stdin)["devices"]
matches = [device["udid"] for runtime, entries in devices.items() if "iOS" in runtime
           for device in entries if device["name"].startswith("iPhone") and device.get("isAvailable", True)]
if not matches:
    raise SystemExit("No available iPhone Simulator on the hosted macOS runner")
print(matches[-1])
')"
xcrun simctl boot "$simulator_id"
trap 'xcrun simctl shutdown "$simulator_id" > /dev/null 2>&1 || true' EXIT
xcrun simctl bootstatus "$simulator_id" -b

derived="$artifact_dir/aqss-ios-derived"
xcodebuild -project "$repo_root/native/ios-app/AQSSReadOnly.xcodeproj" \
    -scheme AQSSReadOnly -configuration Debug \
    -destination "platform=iOS Simulator,id=$simulator_id" \
    -derivedDataPath "$derived" -parallel-testing-enabled NO \
    CODE_SIGNING_ALLOWED=NO test

# A screenshot and .app make the run reviewable, and can later be uploaded to
# a browser simulator if the owner chooses to create an account there.
xcrun simctl launch "$simulator_id" com.aqss.bodyguard.prototype
xcrun simctl io "$simulator_id" screenshot "$artifact_dir/aqss-ios-simulation.png"
(cd "$derived/Build/Products/Debug-iphonesimulator" &&
    ditto -c -k --keepParent AQSSReadOnly.app "$artifact_dir/aqss-ios-simulator-app.zip")
echo "IOS_SIMULATION_UI_VISIBLE_PHYSICAL_UNVERIFIED"
