# Local sound-check recaps

October 20, 2026. This phone-independent increment follows the combined 0.4
microphone lifecycle candidate. It advances the roadmap's native status-reporting
work with a deliberately separate input-only recap. N2b still needs an actual
owned host/output route and independent capture inventory. No output adapter or
protection/session-evidence producer is introduced.

## Scope and research decision

| Primary source | Consequence for this increment |
| --- | --- |
| [Android process lifecycle](https://developer.android.com/guide/components/activities/process-lifecycle) | Process death and limited cached execution mean a memory-only recap cannot promise complete history. Do not reconstruct an unfinished check, assume `onDestroy` ran, or infer continuous listening from missing rows. |
| [Apple app lifecycle](https://developer.apple.com/documentation/uikit/managing-your-app-s-life-cycle) and [background transition](https://developer.apple.com/documentation/uikit/uiapplicationdelegate/applicationdidenterbackground(_:)) | Retain the existing foreground-only capture behavior. Recap navigation cannot resume capture; no background persistence task is added. |
| [Existing input ownership research](android-microphone-lifecycle-2026-10-20.md) and [iPhone record](ios-microphone-lifecycle-2026-10-20.md) | Keep microphone cleanup, consent and process ownership separate from derived display data. Clearing a recap cannot clear an input cleanup failure or grant authority. |

The retention policy and wording are product decisions, not claims made by those
platform sources. The recap has five completed rows, most recent first, plus one
unfinished draft consisting of an opaque identity and a boolean. Each completed
row contains only `inputObserved` and an allowlisted stop reason. It has no raw
audio, numeric levels, transcripts, device/route names, timestamps, runtime IDs,
duration or coverage percentage. Zero-valued PCM may still be an observed input;
neither it nor missing samples establishes acoustic silence.

The input flag means the foreground meter consumed a valid, fresh summary before
that recap was finalized. This is not a complete accounting of framework buffers,
callback delivery, the microphone's physical state or sound heard by a person.
The first stop request wins on Android; cleanup failure overrides it. iPhone
finalizes its current token once after app-owned teardown. Completion is a
software cleanup observation, never proof of physical quiescence.

Android completes from the recorder worker even when its Activity is gone;
there is no queued closure retaining that Activity. Swift keeps the store on
the main actor. Snapshot copies cannot mutate the store. Old, duplicate and
cleared tokens cannot append another row or change a newer run. Clear discards
presentation state only. The stores have no microphone gate or endpoint handle.
Process exit loses all rows; a new process starts empty. A process killed before
finalization leaves no invented successful end record.

## User flow

Open **Sound → Live sound check → Recent sound checks**. The control is disabled
while the check is starting/running or Android cleanup is pending. It lists the
input observation and stop reason, explains temporary retention, and offers
**Clear recaps** when rows exist. Returning, reopening the meter or clearing its
recaps never starts capture. Voice check words and runs do not enter this list.
Existing Session history and protection status remain separate.

## Verification

The tests-only revision `7e5cc08f2aca3f74f78797da71ab1f43c940652a`
[failed Swift and Kotlin compilation](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39504236832)
at the missing recap types. Five new cases on each platform cover unfinished and
duplicate runs, stale callbacks, five-row eviction and independent snapshots,
clear during a pending run, fresh stores, and separation from sticky microphone
cleanup failure.

The first implementation `6764ec4` passed the 42 Swift cases, Android build,
Python/C gates and unsigned iPhone device archive, but its focused UI jobs found
two reviewable defects. The Android landscape hierarchy hid the input label
below the new secondary control; move that control below the meter and reduce
the graph height on landscape screens. The iPhone observer selected the parent
sheet's identically named Close button; give the recap Close its own identifier
and target that exact control. Bounded scrolling keeps secondary controls
reachable without displacing the live input reading. A retained landscape
screenshot and the unchanged simultaneous stopped-state assertions verify the
layout correction.

The focused Android emulator and iPhone Simulator checks are extended to observe
empty recaps after denied permission, sample-observed manual stop, Home/focus
stop and the elapsed limit, retention across meter navigation, Clear and empty
recaps in a fresh app process. They consume real framework input when provided;
they do not inject recap rows into the app. Exact green checks, source and APK
identity are recorded in the draft PR after completion.

The Android candidate is a separate version 0.5 test build with the prior
application ID and approved Silicon Workforce opening poster. Real-phone input,
speech recognition, accessibility, energy and timing trials remain separately
unqualified. N2b–N5 stay pending.
