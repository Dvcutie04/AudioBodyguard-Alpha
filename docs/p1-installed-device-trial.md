# P1 installed-device trial: iPhone and Android

**Scope:** the read-only simulation apps at `native/ios-app` and
`native/android/app`. This procedure exercises UI and visible foreground OS
hints only. It cannot verify output, audio safety, continuous protection,
controller handoff, store readiness, N2b, N3, N4 or N5. Neither app has a
supported playback path. Run the protocol separately on a named iPhone and a
named Android handset and report the exact source revision and OS build. A
simulator or emulator run is useful for debugging but is not this device trial.

## Install without expanding app authority

For the iPhone, choose one of two installation methods:

- With a connected iPhone and an Xcode host, open
  `native/ios-app/AQSSReadOnly.xcodeproj`, select `AQSSReadOnly`, configure a
  development team and a non-conflicting prototype bundle identifier as
  needed, select the physical device, and Run. Use the schema 1
  `p1-device-trial.template.json` and `xcode_signed_device` installation.
- With only the iPhone, use an **actual signed build delivered through internal
  TestFlight** after an Apple Developer Program team configures signing and App
  Store Connect. Use schema 2 `p1-testflight-trial.template.json` and
  `testflight` installation. Keep the build's exact source revision, CI run ID
  and attempt, Xcode and iPhoneOS SDK versions, bundle ID, version, build number,
  SHA-256 of the *submitted signed IPA*, and App Store Connect/TestFlight build
  ID. The CI run number and a screenshot of the TestFlight install are useful
  independent references; the record checker cannot verify either. Never put
  credentials, provisioning profiles, private keys or signing certificates in
  a public artifact or trial record.

The [iPhone device preflight](../.github/workflows/iphoneos-device-preflight.yml)
archives an **unsigned** device app and records its build provenance without
Apple credentials. A green preflight only establishes that the source compiled
for `iphoneos` arm64 and passed the archive identity checks. Its archive ZIP
hash is **not** the signed IPA hash required by the TestFlight record; it cannot
be installed on the iPhone, uploaded to TestFlight or substituted for an
observed device trial. The hosted simulator build is also unsigned and cannot
itself be installed on the iPhone from a-Shell.

Use a JDK 17 / Android API 36 build host with a connected test Android device:

```sh
gradle -p native/android :app:assembleDebug
```

```sh
adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
```

Launch `Audio Bodyguard — Simulation` on the handset. Confirm that `adb devices`
identified a physical test device before recording evidence. The Android debug
APK is only a prototype build and is not a Play release. Keep microphone tools
closed during the six core cases below. Test the optional Voice check and TV
photo setup separately; neither can verify or control another app's output.

## Observe and record

Copy `p1-device-trial.template.json` for an Xcode iPhone/Android trial, or
`p1-testflight-trial.template.json` for a TestFlight iPhone trial, into a
separate private trial directory. Fill fields with **observed** values, not
expected values. Each case needs a reference to a separate, time-aligned
screen recording or concise OS/event trace, with timestamps and an explanation
of the external action.
Leave absent callbacks absent: `callback_observed: false` is an important result.
An Android added callback can be the initial connected-device inventory.
The iOS hint refers only to this app's audio-session notifications; the Android
hint refers to connected-device inventory. Neither verifies a selected route.

The current Home screen says **Connection not verified**. Dismiss or exit the
first-visit guide, return to Home and open **Status details** before recording
each case. Check **Unknown physical state**, **No output observation** and
**This preview has no verified TV connection. Setup pictures explain the
official apps.** Reopen details after a restart if needed. The existing record
field `simulation_label_visible` means that this preview explanation was
actually visible; it does not require a literal `SIMULATION` banner. Keep the
field names unchanged for the existing checker. A connected-appearance
Simulator demonstration cannot be substituted for a physical-device trial.

| Case | Action and question to answer |
| --- | --- |
| `fresh_launch` | Open the app from a stopped process. Is Connection not verified shown? Open Status details and record the preview explanation, unknown physical state and no output observation. |
| `foreground_attach` | While the app is visible, attach a test audio device. Record the external event time, any callback display time, and a miss if no callback appears. |
| `foreground_detach` | While visible, detach it; record the same evidence and keep the UI UNKNOWN even if a callback appears. |
| `background_resume` | Show a foreground hint, hide the app, change the device set, and return. Check whether a previous-visit hint was reused; absence of callbacks while hidden establishes no continuity. |
| `process_restart` | Terminate and relaunch the app, not merely hide and reopen it. Does it avoid restoring a previous hint or showing ACTIVE? |
| `accessible_large_text` | On iOS use VoiceOver and enlarged text; on Android use TalkBack and enlarged font. Open Status details and read the preview, coverage, source-scope and handoff text. Check clipping/reading order and record any confusion or inability to operate the screen. |

For every case, record `performed: true` only after doing the action;
`simulation_label_visible` and `no_output_observation_visible` reflect what was
actually shown. `hint_source` is `app_session` for iOS and
`connected_device_inventory` for Android; it describes the **scope** of a hint,
even when no callback occurred. `prior_visit_hint_reused` on resume must be
measured, not inferred from a lack of notifications. Avoid personal device IDs,
raw audio, media titles, contacts, locations, or unredacted system logs in a
shared record. Keep sensitive recordings private and refer to them by redacted
local filenames. An external capture can demonstrate what the screen showed;
it cannot prove physical output isolation.

## Check the record

Run from the repository root, replacing the path and exact build revision:

```sh
python3 tools/p1_device_trial_record.py /path/to/private/ios-trial.json --expected-revision=<exact-40-character-SHA>
```

Run the same command on the Android or TestFlight record. Both unfilled
templates should return `INCOMPLETE_RECORD`. For TestFlight, the structural
check requires schema 2, a physical iOS install method and named signed build
and delivery provenance. These fields must describe the **signed upload**, not
the unsigned preflight. The checker returns `UNSAFE_REPORTED_UI` for reported
positive coverage, lost simulation/no-observation labels, misattributed callback
scope or a previous-visit hint reused after resume. A structurally complete
manual record returns `STRUCTURE_COMPLETE_PHYSICAL_UNVERIFIED`; this is **not**
a claim that the recording exists, the device was installed, the UI was
accessible to participants, an OS callback arrived on time, or a physical
sound path was qualified. An independent reviewer must inspect the cited
traces, note misses and counterexamples, and make any separate gate decision.

The existing [N2b qualification record](n2b-lab-qualification-record.md) has
empty hardware, driver, output route, independent capture and time-domain
fields. Populate those from an actual owned lab host before designing a real
output adapter. This P1 trial does not fill them by implication.

## Separate connection and input-tool checks

After the core cases, record a separate usability trial from a fresh launch:
select the actual TV system and phone type, follow the numbered guide, try
Help and My screen looks different, leave and resume a step, and return to
Home. A beginner should be able to do this without someone explaining where
to tap. Record wrong turns, unclear pictures and any assistance required;
passing source checks does not establish junior-high usability or exact
firmware screen matches.

For Voice check and TV photo setup, exercise permission denial, cancellation,
background/foreground, interruption and reopening. Confirm listening stops
on exit and that unavailable on-device recognition gives an explanation.
Try an unclear image and conflicting brand text: neither should become a
verified connection. Check that the user confirms the suggested TV brand and
that closing the tools clears displayed input details. Keep these observations
separate from the six-case schema; they do not establish physical protection.
