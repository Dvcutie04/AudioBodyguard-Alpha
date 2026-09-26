# P1 read-only native simulation shells

The iOS SwiftUI target in `native/ios-app` and Android Views app module in
`native/android/app` display the same limited message at launch: **SIMULATION —
no audio path connected**, **Unknown physical state**, and **No output
observation**. Both use the existing native read-only session projector with
no evidence sample. They show only explanatory coverage, capability, caption,
history and next-step text. There is no player, OS audio capture, microphone
permission, endpoint command, live history, background service, automatic
recovery, cross-platform handoff, or ability to actuate from these shells.

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
