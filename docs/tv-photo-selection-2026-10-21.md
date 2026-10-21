# TV photo selection ownership — October 21, 2026

## Scope and observed defect

A photo review is a provisional hint, never TV identity, pairing or output
authority. In 0.8, opening and canceling a replacement picker left the previous
brand/model/IP visible. On iPhone the provider completion also called `scan`,
which created a fresh generation: closing or clearing the view while the file
was loading did not invalidate that future scan.

Candidate 0.9 binds one selection identity before the picker or camera permission
request begins. Only that selection can enter recognition once, and only its
first terminal result can update the review. Clear, Close or replacement invalidates
both import and recognition callbacks. A stale cancel cannot cancel a newer
selection. Starting another selection clears the old hints immediately, including
when the user cancels or a picker is unavailable. The page explains that behavior.

Android uses a distinct 16-bit request code for each selection in the Activity;
codes are not reused. Exhaustion asks the user to reopen the screen. Recreation
starts empty and cannot accept an old Activity's request. A returned result can
arrive before `onResume`, so the review does not incorrectly require resumed state
inside that callback. iPhone sheet disappearance cancels only its still-selecting
identity: dismissing after successful import must not cancel the recognition that
has just begun. Late permission completions cannot present a picker after Close.

## Primary-source research

Reviewed October 21, 2026 before changing this asynchronous failure boundary:

- [Apple: loadFileRepresentation](https://developer.apple.com/documentation/foundation/nsitemprovider/loadfilerepresentation%28fortypeidentifier%3Acompletionhandler%3A%29)
  is asynchronous and supplies a temporary file removed after its completion
  handler returns. The existing bounded image decode stays inside that handler;
  only the decoded image reaches the main-thread selection check.
- [Apple: picker didFinishPicking](https://developer.apple.com/documentation/photosui/phpickerviewcontrollerdelegate-5yntc/picker%28_%3Adidfinishpicking%3A%29)
  reports completed selection or Cancel. Interactive sheet dismissal also closes
  the still-selecting identity; an old provider callback cannot reopen it.
- [Android: Activity](https://developer.android.com/reference/android/app/Activity)
  documents the identifying result request code and delivery before `onResume`.
  Retain the existing API-26-compatible result path in this increment.
- [Google: Task listeners](https://developers.google.com/android/reference/com/google/android/gms/tasks/Task)
  run on the main application thread by default. Activity-scoped listeners are
  removed on Stop; resource cleanup must remain attached to task completion
  independently of whether a result still owns the display.

Invalidation rejects publication; it does not promise cancellation or a deadline
for provider/framework work already running. ML Kit bitmap/scanner cleanup still
runs at task completion even when the selection is obsolete. No background-stop,
OS memory/latency bound, camera full-resolution upgrade or physical cutoff is
claimed. Android's existing external camera thumbnail behavior is unchanged.

## Verification contract

The tests-only commit first adds a real Android picker regression: recognize the
synthetic VIZIO label, open another picker, Cancel and require unknown details.
The red commit `326f76527bf36f32b2ebd7e42733eff014b8df67` failed in
[Android run 39642935827](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39642935827),
job `119370914754`: after replacement Cancel, the required simultaneous unknown
labels were missing. Its `live-input-verification` artifact `12366975214`
retains the picker, result and failure evidence. Do not weaken that assertion
to accept the old review.

Both native policy suites cover Clear before import, replacement before import,
Clear during recognition, exactly one import/result, Cancel and fresh selection,
foreign-owner rejection and stale result/cancel during a newer recognition.
These deterministic callback orderings do not emulate actual framework scheduling.

Android imports the hash-checked synthetic fixture through MediaStore, the system
picker, decoder, ML Kit and review UI, verifies replacement/Cancel clears all
hints, then selects it again and verifies Clear. The over-budget image and all
existing microphone/recap checks remain in the focused workflow.

The focused iPhone workflow imports the hash-checked synthetic label into a fresh
Simulator Photos library. The new UI case requires exactly one observed picker
cell, recognizes it through the real provider and Vision, cancels a replacement,
requires unknown details, then recognizes and clears it again. A missing or
ambiguous picker fails rather than guessing a fixture. Existing permission,
input-lifecycle and unverified-connection checks remain required.

Exact commit, red/green outcomes, test counts, APK identity and any failed attempts
belong in the draft PR. An unsigned Simulator or device-target build is not an
installed iPhone/TestFlight release. No phone has qualified this increment yet.

## Remaining gates

N2b still needs the real owned host/device/driver/route/format and independent
capture inventory. N3–N5 remain pending; factory and handoff readiness remain
closed. Apple API-key download support is a separate pending distribution issue.
