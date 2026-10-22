# Photo work ownership — October 21, 2026

Version 0.12 continues the 0.11 photo result window. An expired, cleared or
closed review does not prove that its provider, decoder or recognizer has
returned. Both native apps now admit one photo read per app process, retaining
that capacity independently of the screen and its 30-second publication window.

## Research and design

| Primary source inspected October 21 | Consequence |
| --- | --- |
| [Google Task APIs](https://developers.google.com/android/guides/tasks) | `Tasks.await` may block a separately managed background thread. Interruption of a wait does not establish completion of the underlying task. Keep the same task and its bitmap until completion, without submitting recognition again. |
| [Apple file representation loading](https://developer.apple.com/documentation/foundation/nsitemprovider/loadfilerepresentation(forTypeIdentifier:completionHandler:)) | Decode the provider's temporary file within its callback. Keep the work owner across that callback and the subsequent image/Vision closures. |
| [Apple NSLock](https://developer.apple.com/documentation/foundation/nslock) | Serialize slot admission and owner-checked release. The existing repository already uses this Foundation locking pattern. |
| [Swift extended lifetime](https://docs.swift.org/latest/documentation/swift/withextendedlifetime(_:_:)-59dz3) | Extend the captured owner within every asynchronous closure's own scope. Extending only the scheduling caller would not keep later work covered. |

The selected synthesis combines an identity-checked process slot, the existing
per-review elapsed deadline, and native cleanup ownership. A screen-local busy
flag would be lost on close/reopen. A timeout that simply frees capacity can
overlap an unfinished import. A single executor per Android Activity cannot
exclude readers in another Activity and does not itself cover asynchronous OCR.
No new runtime package, polling loop for admission, stored photo, network
service, or physical-control authority is introduced.

Latency: the slot uses a short lock only for admission and release. Busy taps
return a message without starting another picker/read. Battery: admission is
event driven, with the existing 250 ms watchdog limited to an active review.
Memory: at most one admitted app photo pipeline is outstanding; the previous
2048-pixel decode target and text limits remain. This is not a measured total
memory, OS buffering or completion-time bound. Native APIs and foreground
camera/Photos consent remain the platform integration.

## Ownership and UI behavior

Each slot admits one unique lease. Foreign, stale and duplicate releases cannot
free another read. Selecting a picture does not reserve work while the user
is still in the camera/picker. Actual import admission rechecks the slot, so
two screens returning selections cannot both start a read.

Android holds its lease across the queued job, provider access, decoding, ML
Kit completion, recognizer close, bitmap recycle and temporary-camera cleanup.
The worker waits for the same ML Kit task off the UI thread. If interrupted,
it continues waiting for that task and restores the interrupt flag afterward;
it does not start recognition again. Activity destruction invalidates result
publication and gracefully closes its executor, allowing admitted cleanup to
run. Rejected submission releases the never-started work.

iPhone gives the admitted pipeline a shared lifetime owner. Provider, main
queue image delivery, normalization and background Vision closures retain it;
explicit extended lifetimes keep it through their cleanup/return scopes.
Vision and provider decoding use autorelease pools. The result view does not
hold or release this owner. Clearing, closing or timing out invalidates result
publication while outstanding work continues to own capacity.

While occupied, camera/gallery taps say “The previous photo is still finishing.
Try again shortly.” Retry stays manual. Once the old work returns, the next tap
can select a fresh picture. If a platform operation never returns, capacity
remains occupied for the process; the app does not invent cancellation or a
successful result. No claim is made that a timeout forcibly stops framework
work. Brand/model/IP remain unverified hints and nothing is connected.

## Red-first evidence

The API scaffolds and seven ownership cases per platform were committed at
`d8c03b05f1661bdfc010eb4fd419899ff0e87456` before the implementation.

- Android run `39697806703`, job `119559360892`: **76 tests, 7 failed**.
  Every new ownership case failed with runtime assertions.
- Swift run `39697806704`, job `119559361277`: **78 tests, 118 assertions
  failed across the seven new ownership cases**; the existing cases passed.
  Simultaneous admission allowed 16 owners instead of one.

The slot implementation and stricter Android native regression were then
published at `f32a36c85507da21559ed5058921f3b09b6ee977`, before connecting
either native screen to the slot. The native regression holds a real provider
read through the 30-second timeout, then attempts Retry, Clear, camera and
closing/reopening the screen. Picker request counts and provider read counts
must remain unchanged while blocked. After release and worker termination,
the old image cannot publish and a fresh real ML Kit read must succeed.
No clock, OCR text, slot or result is injected into the app.

That intermediate revision passed main run `39699049691`, including all 78
Swift tests and the Kotlin build/tests, plus Python **1,879 tests and 19
subtests** and the normal/sanitized C gates. Android native run `39699049735`,
job `119563501474`, then failed at the first occupied-retry expectation:
`Missing camera review text: The previous photo is still finishing. Try again
shortly.` The app and observer compiled and the preceding gallery, dense-text
and camera checks reached this real delayed-provider test. This is the native
screen regression before integration, not a failing compiler or missing API.

## Verification gates and limits

Required final gates are native Kotlin/Swift tests, the Android provider and
camera regressions, the original dense-image text-limit check, Android lint,
the real iPhone Photos/Vision replacement/Cancel/reselect/Clear walkthrough,
unsigned iPhone device compilation, and the Python/C regression checks.
Delivered APK provenance must match the exact tested source, verified signature,
version 12, original opening poster, and exclusion of observer code/fixtures.
Final run IDs, failures and artifact identity are recorded in draft PR #44.

The forced stalled-provider experiment is Android-only. The iPhone workflow
checks real Photos/Vision and deterministic slot ownership; it does not prove
behavior of a forced stuck iPhone provider or physical camera hardware.
Real handset input, OS resource retention, battery and memory measurements
remain device observations. Physical audio, TV pairing/control and signed
iPhone/TestFlight distribution have not been qualified by this change.
