# TV photo result window — October 21, 2026

## Scope and primary research

This increment follows the full Android camera-photo capture in candidate
0.10 while the owner tests it on the handset. A selected picture must not
produce an accepted review at or after a 15-second elapsed boundary. The
window starts when the app accepts the selected image for import/reading,
not while the user chooses a photo, takes a picture or answers camera consent.
Brand/model/IP remain provisional hints; there is no pairing or output authority.

| Primary source | Consequence for this increment |
| --- | --- |
| [Android SystemClock](https://developer.android.com/reference/android/os/SystemClock) | `elapsedRealtime` includes device sleep; inject it into the native result policy. |
| [Android Handler](https://developer.android.com/reference/android/os/Handler) | Delayed messages use uptime and can execute later after sleep. A timer alone cannot authorize publication. |
| [Apple mach_time.h](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/mach_time.h) | `mach_continuous_time` advances during sleep and is available before the app's iOS 15 deployment floor. Convert using the system timebase. |
| [Apple uptimeNanoseconds](https://developer.apple.com/documentation/dispatch/dispatchtime/uptimenanoseconds) | This uptime clock excludes sleep; do not use it as the iPhone result window's clock. |
| [Android ContentProvider.openFile](https://developer.android.com/reference/android/content/ContentProvider#openFile(android.net.Uri,%20java.lang.String)) | A separate test-only provider can delay a real image read without replacing the app's decoder or clock. |
| [Apple file representation loading](https://developer.apple.com/documentation/foundation/nsitemprovider/loadfilerepresentation(forTypeIdentifier:completionHandler:)) | Decode the provider's temporary file inside its completion; dismissing the picker does not extend that file's lifetime. |

Research inspected October 21. These sources describe OS APIs, not measured
handset behavior or cancellation guarantees. The 15-second window is an app
interaction policy, not an OCR latency qualification.

## Result ownership and native integration

Both native `PhotoReviewRun` implementations accept a caller-supplied clock.
`beginReading` samples it only for the current, still-selecting token. A
reading window ends at elapsed time **greater than or equal to 15 seconds**,
or on a negative, non-finite (Swift) or backward clock observation. The end
latches: subsequent callbacks cannot revive it, even if a later clock value
would have fitted the original interval. A new selection resets ownership.
Foreign or stale identities are rejected before sampling the clock, so an old
callback cannot end a replacement. `complete` checks the window itself;
publication never depends on the UI timer having fired first.

Android checks before decoding, before submitting OCR, at terminal callbacks,
on resume and on a 250-millisecond main-thread watchdog. Expiration clears all
hints and the suggested-brand action, closes its temporary camera capture,
and offers “Choose the picture again.” The original worker still owns cleanup
for any decoder/recognizer resources it already acquired.

iPhone starts the window when a gallery result is accepted, dismisses that
picker immediately, and then loads its temporary representation. Camera
results start the window on return. Image normalization and Vision results
are admitted only for the same current window. A common-run-loop watchdog and
an active-scene check show the retry state when the app can execute again.
Clear, Close, replacement, cancellation and prior selection ownership remain.

The watchdog is a UI notification, not a wakeup guarantee. A busy/suspended
main thread may show the end later; terminal admission still samples elapsed
time before accepting a result. Neither platform forcibly cancels an OS
provider, decoder or OCR task at this boundary. Outstanding framework work,
queue depth, memory consumption and completion latency are **not** qualified
or bounded by this increment. The previous image-size target and OCR text
limits remain separate policies.

## Red-first evidence and required verification

Tests-only clock plumbing plus the new behavioral assertions were published
as `42a831985c0110ecb5c46e732714ec3363e7d997` (tree
`4731529f814f6665193e7d73c3f924ba7ad474cd`). Existing selection tests remain.

- Android focused run `39694140347`, job `119547294471`: **68 tests, 4 failed**.
  The new cases exposed acceptance at the boundary, callback-only late
  completion, clock rollback and an invalid start. The failures were runtime
  assertions, not missing APIs or compiler errors.
- iPhone focused run `39694140478`, job `119547295228`: **70 tests, 16 assertion
  failures across four new cases**, covering the same behavior plus non-finite
  clocks. The prior package cases passed. Its app/UI stages did not execute.
- Main run `39694140442` retains the parallel regression results. These red
  attempts are preserved separately from implementation verification.

The green gate must retain the boundary tests, then run the normal Python,
scripted C, Kotlin, Swift and app compilation checks. The Android native
observer must hold a real content-provider read open through the timeout,
observe all hints unknown, release the old picture and wait for that decoder
job to return, verify it cannot publish, then recognize a fresh image using
ML Kit and clear it. Its provider and observation code belong only to the
`testOnly` observer APK and must be absent from the delivered app. Native
window screenshots must follow a committed frame and differ between timeout
and the successful retry.

The focused iPhone workflow must re-run its real Photos-picker/Vision review,
replacement Cancel, reselect, Clear, denied/granted microphone and navigation
cases. The unsigned device archive remains a distinct compilation gate.
Exact green revisions, run IDs, failed attempts, artifact hashes, signature
and final APK provenance are recorded in the draft PR after inspection.

## Remaining gates

Actual Android camera/provider compatibility, real-photo recognition, memory
and battery use remain handset observations. The timer cannot infer that OS
work physically stopped. A forced provider stall on iPhone is not claimed
from the Android observer. Signed iPhone/TestFlight distribution still awaits
Apple API-key resolution. Physical output, TV connection/control and N2b–N5
remain pending; production readiness and handoff gates stay closed.
