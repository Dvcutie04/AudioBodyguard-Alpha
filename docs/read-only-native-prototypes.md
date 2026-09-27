# P1 read-only native simulation shells

The iOS SwiftUI target in `native/ios-app` and Android Views app module in
`native/android/app` display the same limited message at launch: **SIMULATION —
no audio path connected**, **Unknown physical state**, and **No output
observation**. Both use the existing native read-only session projector with
no evidence sample. They show explanatory coverage, capability, caption,
history and next-step text. An additional foreground-only hint is sourced
from this app's iOS audio-session notifications or Android's connected-device
inventory callback. A notification can be missing, late, or unrelated to any
owned player. The hint does not enter the session projector and cannot change
**Unknown physical state**. There is no player, OS audio capture, microphone
permission, endpoint command, live session history, background service,
automatic recovery, cross-platform handoff, or ability to actuate from these
shells.

Both shells also invoke their native read-only capability projector with six
explicitly unknown prerequisites: hardware, qualification, permission, route,
runtime and independent observation. The checklist therefore displays six
unknowns and cannot offer a control. The move-session explanation says that
no handoff path is available; it is a static statement about this disconnected
prototype, not a live evaluation or opening of the endpoint handoff barrier.

## Read-only native hints

| Shell | What can be displayed while the screen is active | What cannot be concluded |
| --- | --- | --- |
| iOS | `AVAudioSession` route-change, interruption, or media-services-reset notification received in this app | Another app's route, playback, output level, physical effect, or uninterrupted notification delivery |
| Android | `AudioDeviceCallback` delivers an added or removed connected-device callback while the Activity is visible; an added callback may contain an initial inventory | Which app is playing, the playback route, output level, physical effect, or uninterrupted notification delivery |

Observers are removed when the iOS scene is inactive or leaves the screen, or
when the Android Activity stops. A new foreground visit clears the previous
hint; callbacks from a prior visit cannot repopulate it. At most one volatile
hint is displayed, with no audio or device identifier stored. There is no
assertion that an added callback is a new connection, no current-route
assertion, background service, polling, mic permission, or claim of
notification completeness. The iOS and Android
events have different scopes, despite the shared uncertainty vocabulary.

The shared `session_evidence_view_v1.json` adds a `REFERENCE_ONLY` case for a
software-only report. This reason remains UNKNOWN on both platforms; a future
native source must independently qualify its observation before it can report
ACTIVE. Synthetic `fresh_active` vectors only test rendering given a trusted
input and do not establish such a source.

## Build gates

- iOS: `swift test --package-path native/ios`; then `xcodebuild -project
  native/ios-app/AQSSReadOnly.xcodeproj -scheme AQSSReadOnly -configuration
  Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator'
  CODE_SIGNING_ALLOWED=NO build` on a macOS Xcode host.
- Android: `gradle -p native/android testDebugUnitTest :app:assembleDebug` with
  JDK 17, Gradle 8.13, Android Gradle Plugin 8.13.2 and Android API 36 SDK.
- Python: `python tools/generate_native_feedback_contracts.py --check` and
  `PYTHONPATH=. python -m pytest -q` in an environment with requirements.

The simulator and APK builds establish that packages compile, not that they
run on actual devices. Native app IDs and minimum OS values are provisional.
No signing, store submission or mic/audio authorization occurs in CI. The
repository's production endpoint factory still rejects, and
`EndpointHandoffBarrier.is_ready()` still returns false. A functional release
requires N2b physical endpoint/observer inventory, N3 qualification, N4
future-effect exclusion for handoff, and N5 lifecycle, permissions, device,
accessibility and store work for **both** iPhone and Android.

The separate [read-only UI smoke workflow](../.github/workflows/read-only-ui-smoke.yml)
checks a narrower next step after compilation: an iPhone Simulator XCUITest
launches the app and checks the uncertainty and handoff wording; an API 35
Android emulator installs and launches the APK and checks the corresponding
UI hierarchy. [PR #22's passing run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36288934014)
retains XCUITest results and Android screenshots/hierarchies. An earlier iOS
launch found a missing bundle version, since fixed. Neither test exercises a
physical phone, audio output, route changes, VoiceOver/TalkBack, or the
installed-device trial protocol.

## Source notes and empirical debt

Apple documents a SwiftUI `App`/`WindowGroup` application entry point and
Xcode simulator versus signed-device runs; Android documents app namespace,
application ID, exported launcher components and accessible Views. Android's
[target API requirements](https://developer.android.com/google/play/requirements/target-sdk)
currently require new phone submissions to target API 36 or later. The existing
Android 8.7 build tooling could compile no higher than API 35; the prototype
uses [Android Gradle Plugin 8.13](https://developer.android.com/build/releases/agp-8-13-0-release-notes)
and Gradle 8.13 for API 36 support. These are build and policy constraints,
not a certificate of app approval or real-world accessibility.

After a hosted build, install signed builds on real iPhone and Android devices
and inspect VoiceOver/TalkBack, large text, contrast, lifecycle/background
changes, startup/memory/battery and absence of misleading ACTIVE status.
No coverage duration or percentage may be inferred from missing callbacks.
The [P1 installed-device trial](p1-installed-device-trial.md) gives a separate
record for each platform and a checker that rejects incomplete or misleading
manual status reports. Its structurally complete result does not qualify the
native app or a physical output route.

Before using this as a product event source, test active/inactive transitions,
headphone connect/disconnect, interruptions, media-service reset where
available, screen rotation, process death, denied permissions, and OEM route
behavior on installed devices. Compare event and UI timestamps to independent
observations; measure latency distribution, missing and stale callback rates,
battery and wakeups in each state. A physical route or acoustic claim still
requires a separately qualified endpoint and observation path.

Official API basis: [Apple route-change](https://developer.apple.com/documentation/avfaudio/responding-to-audio-route-changes),
[Apple interruptions](https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions),
[Apple media reset](https://developer.apple.com/documentation/avfaudio/avaudiosession/mediaserviceswereresetnotification),
[Android AudioManager](https://developer.android.com/reference/android/media/AudioManager#registerAudioDeviceCallback(android.media.AudioDeviceCallback,%20android.os.Handler)),
and [Android Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle).
