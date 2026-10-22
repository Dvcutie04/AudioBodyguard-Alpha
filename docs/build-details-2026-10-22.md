# Installed build details — October 22, 2026

The phone-testing roadmap needs feedback tied to the app actually installed.
The current Settings pages show no version or build. A downloaded APK's name
alone does not establish which app the user opened. Version 0.17 adds one
**Build details** action in ordinary Settings on Android and iPhone.

## Research and selected design

| Primary source | Relevant contract | Application decision |
| --- | --- | --- |
| [Android PackageInfo](https://developer.android.com/reference/android/content/pm/PackageInfo) | `versionName` describes the installed package and may be null; the long version code includes the major component. | Query this app's own package at opening. Show the complete version and build, without deriving them from an APK filename or a UI constant. |
| [AndroidX PackageInfoCompat](https://developer.android.com/reference/androidx/core/content/pm/PackageInfoCompat) | `getLongVersionCode` supports the older-platform representation and the Android P major component. | Use the existing AndroidX Core dependency, preserving API 26 support. No new dependency is required. |
| [Apple bundle version](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleshortversionstring) and [build](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion) | The short version identifies a release; the build identifies an iteration. The release format uses three numeric components. | Read both actual main-bundle values. The iPhone default release becomes `0.17.0`; its existing first-build number remains `1`. TestFlight overrides must display their own actual values. |
| [Apple Bundle lookup](https://developer.apple.com/documentation/foundation/bundle/object(forinfodictionarykey:)) | Information-property-list lookup returns an optional value. | Accept nonempty strings; otherwise show `Unavailable` for that field. Do not fabricate a version. |

The action opens a readable details view containing Version, Build and a short
request to include those values in a problem report. Back returns to Settings.
Android retains its app version name including the live-input suffix; its
version code advances to 17. Build numbers belong to each platform's package
scheme and need not equal one another.

These values are package metadata, not an authenticated source revision or a
unique binary identity. Exact APK SHA-256, source and workflow provenance remain
separate build evidence. Displaying them does not establish a TV connection,
physical output, phone usability or protection. N2b–N5 remain pending.

The change introduces no permission, dependency, network operation, clipboard
write, saved setting or support-log collection. Existing microphone and photo
ownership, privacy, availability and cleanup behavior remain required.

## Verification contract

Introduce one native behavior test per platform before implementing the screen.
On unchanged 0.16 production code, each test must reach Settings, obtain the
actual package metadata and fail at the absent Build details action.

Android derives expectations from the installed package's OS dump, then checks
the native view's version and build together, Back to Settings and unchanged
unverified Home state. Its later APK provenance must match those same values.
iPhone expectations come from the compiled app's Info.plist, passed only to
the UI-test runner. The app receives no injected version or build. The test
opens the real Settings view, checks both values, observes no system consent
prompt, returns through Back and checks the unverified Home state.

Retain the existing native input, permission, photo, camera and recap checks.
The iPhone focused run has ten prior UI tests plus the new case, with no skipped
checks accepted as a pass. Review actual Android and iPhone details screenshots
and retain artifact/source identity. Exact red and final results belong to the
increment's draft PR; physical phone testing remains separate.

Red source `fd93fe2510fbf57034aeb9238d5d21847fbeae6e` retained 0.16 production
code. Android run 39869764683, job 120140954875, compiled and read the installed
metadata before failing `Missing tap target: Build details`. iPhone run
39869764705, job 120140955080, compiled and obtained the actual app metadata
before failing `Missing Build details action` and its Code 2 sentinel for that
one missing control. The five existing navigation, photo and denied-input
cases passed. The isolated speech-Settings test also passed. Implementation
began only after both intended missing-control failures were confirmed.
