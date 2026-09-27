# Free, bounded read-only native simulation

The existing public-repository GitHub Actions jobs compile the iOS and Android
read-only shells. They now also boot one iPhone Simulator and one Android
Emulator and assert that the visible UI says **SIMULATION — no audio path
connected**, **Unknown physical state**, **No output observation**, and
**Six setup checks unknown**. The iOS job uses an XCTest UI target; Android
uses the Android SDK emulator plus UIAutomator's visible XML dump. No app
permission, media playback, OS audio capture, hardware command, or external
account is involved. No third-party testing action or external binary upload
is needed to run these checks. GitHub documents that standard hosted runners
are [free for public repositories](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

## Inspect a completed run from an iPhone

1. Open the [CI workflow](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml)
   in Safari. Select the run for the exact commit under review.
2. Confirm the separate Python, C11, Swift, and Android jobs. The Swift and
   Android jobs must show their UI check steps passing, not just their builds.
3. In the run's **Artifacts** section, download `aqss-ios-simulation` or
   `aqss-android-simulation`. These contain screenshots of virtual screens,
   and respectively a zipped unsigned iOS Simulator `.app` or Android debug
   APK. GitHub deletes these CI artifacts after **three days**. Screenshots
   are software evidence; an Android emulator startup log is also retained
   to diagnose startup failures. Inspect the job logs if an artifact is missing.

These artifact names and screens describe only read-only prototypes. An
XCTest UI assertion or UIAutomator dump is a check of displayed text on a
virtual device, and a screenshot captures that device's screen at one moment.
Neither establishes app behavior on an installed phone, OS audio-event
completeness, independent physical output observation, accessibility on real
devices, hearing benefit, or continuous protection. In particular the
production endpoint factory and handoff barrier remain closed.

## Optional browser view

[Appetize](https://support.appetize.io/may-i-test-appetize.io-for-free-before-paying-for-an-account)
advertises a limited free account without a credit card. Its [iOS upload
instructions](https://docs.appetize.io/platform/app-management/uploading-apps/ios)
accept the CI zipped Simulator `.app`, and its [Android upload
instructions](https://docs.appetize.io/platform/app-management/uploading-apps/android)
accept the CI APK. This can put an interactive virtual screen in Safari on
an iPhone. **It requires an account and sending the app binary to Appetize**;
the CI does not do that automatically. Check the current account's minutes,
visibility and deletion settings before using it. Do not upload any build
containing signing credentials, private endpoint addresses or test secrets.

[BrowserStack's open-source program](https://www.browserstack.com/open-source)
is application-based. Its page advertises Live, Automate and Percy, but does
not explicitly establish whether the native-app App Live product is included.
Do not assume that approval, free native-app coverage, iOS signing, or a
physical-output observation facility is available without confirmation.

[Firebase Test Lab's quota page](https://firebase.google.com/docs/test-lab/usage-quotas-pricing)
lists a no-cost Spark allowance for Android tests, while its [Firebase
console setup instructions](https://firebase.google.com/docs/test-lab/android/firebase-console)
require a billing-linked Blaze project. Do not enroll or rely on a no-card
console flow until that discrepancy and the intended access path are resolved.

## Independent gates

The separate [P1 installed-device trial](p1-installed-device-trial.md)
requires actual iPhone and Android installs, fresh-launch and lifecycle
observations, accessibility inspection, and honest missed-event records.
N2b still requires an inventoried real backend, route, and independent
acquisition path. N3 qualifies real physical effects; N4 qualifies
future-effect exclusion; N5 covers installed native lifecycle and platform
delivery. No CI result or browser emulator substitutes for those gates.
