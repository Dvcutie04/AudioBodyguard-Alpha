# Android 0.36 quiet output check

October 27, 2026. The owner explicitly authorized building the intended next
parts before the other phone arrives, with user testing deferred. This updates
the earlier inventory-before-adapter sequencing for software preparation: the
actual setup remains unknown, but it no longer blocks implementing a generic
diagnostic that validates its requested profile on the installed phone. The
existing Ready confirmation and mobile-backend review cover this implementation
and its focused API follow-up. No repeat model/permission confirmation is needed.

## Scope and selected profile

Implement an explicit foreground **Quiet output check** in the Android Live Test
build. It owns one streaming AudioTrack, requests zero app-level gain before
play, and supplies only 256 zero-valued mono PCM16 samples at a requested 48 kHz.
These are software diagnostic choices, not observed phone capabilities, hardware
format, named physical route or a calibrated signal. No real user trial has run.
The inventory, acquisition/calibration and production qualification gates stay
pending. No TV action, system-volume change, microphone capture or background
service is introduced by this check. iPhone remains an independent native target.

The app must validate minimum buffer size and the constructed track's state,
format and buffer metadata. Unsupported values stop before play. The requested
buffer is bounded to 256 KiB; the PCM payload is 512 bytes. Native/framework
internal memory is not covered by that application request bound. This is an
accounting/ownership diagnostic, not a perceptual sound or under-200-ms result.

## Refreshed primary sources

Reviewed the following official API references during the already authorized
backend review follow-up. Current docs include newer APIs; implementation is
limited to minSdk 26, with a version guard for the API 36 plural route query.

- [AudioTrack](https://developer.android.com/reference/kotlin/android/media/AudioTrack): nonblocking short-array results count samples; zero gain is an app-track gain request; minimum buffer is an estimate. Pause followed by flush discards queued stream data; release is the native resource operation. None is independent acoustic evidence.
- [AudioTrack.Builder](https://developer.android.com/reference/android/media/AudioTrack.Builder): incompatible/unavailable configuration may throw. Pin all requested format/stream/buffer values; inspect the returned track rather than treating the request as hardware negotiation.
- [Audio focus guide](https://developer.android.com/media/optimize/audio-focus) and [AudioManager](https://developer.android.com/reference/android/media/AudioManager): accept only immediate grant, use the same request for abandonment, and account for target-35 top-app restrictions. Delayed start is disabled. Use transient focus with the same MEDIA/UNKNOWN audio attributes as the diagnostic track; game-specific tuning is not applied.
- [AudioRouting](https://developer.android.com/reference/android/media/AudioRouting): route queries need active playback; plural routing is API 36. Listener delivery and route queries do not make routing atomic with admission. Returned type codes are framework observations, not acoustic-route verification.
- [SystemClock](https://developer.android.com/reference/android/os/SystemClock) and [Handler](https://developer.android.com/reference/android/os/Handler): elapsed realtime includes sleep; Handler delays use uptime and can be delayed/dropped. Every ordinary worker operation rechecks the elapsed-time budget; a UI watchdog is not a physical cutoff guarantee.
- [AtomicReference](https://developer.android.com/reference/java/util/concurrent/atomic/AtomicReference): use API-1 get/compareAndSet for the independent control-side cut. No newer VarHandle methods or OS/native atomic enforcement is assumed.

## Ownership and stopping

One worker alone owns focus/track creation, format reads, gain, play, nonblocking
writes and cleanup. The main thread and stable focus/route contexts can only
close an AtomicReference stop reason. They do not call into the track or reopen
work. In-flight calls retain their source and owner until actual return and
accounting. A successful prefix is recorded even if Stop arrived meanwhile.
Callbacks are retired before cleanup; late bodies use only their old control
object and never query a released track or affect a new run.

Foreground microphone and output tools share one process exclusion coordinator.
This is resource arbitration only, not output authority. The lease strongly
retains its owner and survives any cleanup uncertainty. Stale leases cannot
release/quarantine another run; failed cleanup blocks both kinds until process
exit. Existing input-only gate behavior and actual cleanup ownership are retained.

The diagnostic has at most eight write attempts, a positive 10-ms worker delay
between incomplete attempts, and a fixed 2000-ms elapsed-time admission budget.
There is no busy loop or continuous warm stream. OS calls/scheduling can exceed
the budget; timeout closes future admission and cannot free an entered owner.
These parameters are not handset latency/battery measurements. Stop, foreground
loss, focus loss/duck and route notices close admission; no positive event restarts.

Known track cleanup attempts pause, then flush only if pause returned, unregister
the retired routing listener, and release on the worker. Focus abandonment is
also attempted. Unlike the earlier serial fixture's stop-at-first-cleanup-error
profile, this concrete diagnostic attempts best-effort release/abandon after
an observed cleanup exception, without resuming data work. Any cleanup failure
remains sticky and quarantines the owner even if a later release returns.
An allocation exception without a known completed construction or an unreported
Throwable also quarantines; no timeout, GC or recreated controller resolves it.

## Reviewable observations

Only an explicit Start can request focus or create a stream. The separate
screen offers Stop and a brief explanation; opening, returning or rotation
cannot start again. Review freezes installed build fields, separately labelled
phone-clock UTC time, requested profile, constructed stream metadata, framework
route type codes, accepted sample counts, ending reason and bounded operation
trace. Native Share sends that exact preview. No names/addresses, raw input,
recordings, photos or arbitrary logs are included. Process restart recovers no
old report or output authority.

The worker trace reserves 96 entry/return/accounting events for a fixed finite
operation set. It never evicts events. Times are application-side elapsed
realtime observations, not individual internal JNI/HAL events, presentation
timestamps or acoustic latency. Full transfer and cleanup returns never change
the fixed **Physical output and protection: Not verified** report state.

Validation will include tests-first failure receipts, deterministic fake-port
and real-thread cutoff cases, native emulator UI/failure/lifecycle checks,
existing Android input/photo/navigation regression, source-bound APK identity,
signature/artwork/probe-exclusion checks, and core Kotlin/Swift/Python/C checks.
Exact runs, results and the delivered installer identity belong to the draft PR.
