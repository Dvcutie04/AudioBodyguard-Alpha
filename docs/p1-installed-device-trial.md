# P1 installed-device trial: iPhone and Android

**Scope:** the read-only simulation apps at `native/ios-app` and
`native/android/app`. This procedure exercises UI and visible foreground OS
hints only. It cannot verify output, audio safety, continuous protection,
controller handoff, store readiness, N2b, N3, N4 or N5. Neither app has a
supported playback path. Run the protocol separately on a named iPhone and a
named Android handset and report the exact source revision and OS build. A
simulator or emulator run is useful for debugging but is not this device trial.

## Install without expanding app authority

Use an Xcode host with a connected iPhone. Open
`native/ios-app/AQSSReadOnly.xcodeproj`, select `AQSSReadOnly`, configure a
development team and a non-conflicting prototype bundle identifier as needed,
select the physical device, and Run. Preserve the checked-out git commit SHA in
the trial record. The hosted simulator build is unsigned and cannot itself be
installed on the iPhone from a-Shell.

Use a JDK 17 / Android API 36 build host with a connected test Android device:

```sh
gradle -p native/android :app:assembleDebug
```

```sh
adb install -r native/android/app/build/outputs/apk/debug/app-debug.apk
```

Launch `Audio Bodyguard — Simulation` on the handset. Confirm that `adb devices`
identified a physical test device before recording evidence. The Android debug
APK is only a prototype build and is not a Play release. Do not enable microphone
access or claim control of another app during this read-only trial.

## Observe and record

Copy `p1-device-trial.template.json` to a separate private trial directory for
each platform. Fill fields with **observed** values, not expected values. Each
case needs a reference to a separate, time-aligned screen recording or concise
OS/event trace, with timestamps and an explanation of the external action.
Leave absent callbacks absent: `callback_observed: false` is an important result.
An Android added callback can be the initial connected-device inventory.
The iOS hint refers only to this app's audio-session notifications; the Android
hint refers to connected-device inventory. Neither verifies a selected route.

| Case | Action and question to answer |
| --- | --- |
| `fresh_launch` | Open the app from a stopped process. Is the simulation label visible, coverage UNKNOWN, and output unobserved? |
| `foreground_attach` | While the app is visible, attach a test audio device. Record the external event time, any callback display time, and a miss if no callback appears. |
| `foreground_detach` | While visible, detach it; record the same evidence and keep the UI UNKNOWN even if a callback appears. |
| `background_resume` | Show a foreground hint, hide the app, change the device set, and return. Check whether a previous-visit hint was reused; absence of callbacks while hidden establishes no continuity. |
| `process_restart` | Terminate and relaunch the app, not merely hide and reopen it. Does it avoid restoring a previous hint or showing ACTIVE? |
| `accessible_large_text` | On iOS use VoiceOver and enlarged text; on Android use TalkBack and enlarged font. Read the simulation, coverage, source-scope and handoff text, and check clipping/reading order. Record any confusion or inability to operate the screen. |

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

Run the same command on the Android record. The unfilled template should return
`INCOMPLETE_RECORD`. The checker returns `UNSAFE_REPORTED_UI` for reported
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
