# Mobile output backend review

October 27, 2026. The owner replied **Ready** after the requested model-switch
step. This records the authorized next research increment. It completes the
paper review described in the [preparation brief](n2b-mobile-output-review-2026-10-27.md),
with a conditional lab recommendation and implementation obligations. The
owner's actual 0.35 report has not been received. No adapter has been selected
for that setup, no native output code has been added, and no trial has run.

## Scope and decision

The inspected Android app has minSdk 26, compile/target SDK 36 and an existing
Kotlin/Java build; iPhone deployment remains a separate native product. The
Android 16 source below is a reproducible reference baseline, not the owner's
unobserved vendor build. Current API documentation can describe later APIs;
any implementation must check availability against this build configuration
and the reported handset version.

**Research recommendation, conditional on the actual inventory:** first assess
one foreground AudioTrack streaming owner with explicit nonblocking writes as
the smallest accounting lab. It makes the boundary between a supplied block
and a returned transfer count directly inspectable in the current app stack.
This is a design inference, not an Android performance recommendation or a
latency result. Keep Oboe/AAudio as a separate candidate if the actual route or
measured latency needs justify its native ownership and build work. Do not
choose a format, sample rate, route, signal level or trial duration here.

| Candidate | Evidence relevant to the lab | Design inference and remaining cost |
| --- | --- | --- |
| AudioTrack streaming, nonblocking writes | [AT] defines bounded transfer counts and explicit write/stop operations | Leading accounting-lab candidate within the current Kotlin stack. Requires its own units/error translation, owner thread, bounded retry policy, admission cut and cleanup tests. Low latency is unmeasured |
| Oboe/AAudio | [AA], [LL] describe native streams/callbacks and a low-latency path | Retain for a measured latency comparison. Add NDK/JNI/ABI packaging and callback/stream reclamation review. The portable C fixture is not already a safe concurrent native binding |

The official low-latency checklist favors Oboe and data callbacks, and says an
exclusive MMAP request may be denied [LL]. Therefore a smaller Java accounting
experiment must not be marketed as the fastest path. Neither API choice proves
physical containment, whole-device exclusivity, TV control or the under-200-ms
aspiration. These are project decisions and evidence limits, not measurements.

## Primary-source findings

The following are source-supported API facts. Proposed AQSS policies follow
in separate sections. Retrieved October 27, 2026; no source is a measurement
of the owner's phones.

| Source | Finding that affects the contract |
| --- | --- |
| [AT] AudioTrack reference and [AS] pinned Android 16 source | Nonblocking writes return the amount queued. The short-array overload reports shorts, aligned to channel count. A successful partial transfer can precede a dead-object error reported on the next write. Streaming stop drains written buffers; pause/flush is the documented discard sequence. Flush requires paused/stopped streaming state and does not promise that every former buffer slot is immediately reusable. Minimum buffer size is an estimate that omits the eventual route/sink |
| [RF] AudioRouting | Preferred device is not guaranteed to be actual routing. Actual-route queries require playback; the plural query is API 36. Listeners report routing changes on the specified handler |
| [FO] Focus guide; [FB] FocusRequest builder | Focus requests and losses interact with other apps. A target of API 35+ needs top-app status or a foreground service to request it. Delayed focus is optional, and callbacks have an explicit handler option |
| [SC] StreamEventCallback | Data-request and presentation-ended callbacks are for offloaded tracks. They are not a general PCM streaming readiness/completion interface |
| [TS] AudioTimestamp | AudioTrack position uses a wrapping low 32-bit frame count. Its presentation time is an estimate for an already presented or committed frame, in MONOTONIC time. BOOTTIME includes suspend and corresponds to elapsedRealtimeNanos; it is a different domain |
| [AA] AAudio guide | Writes can be nonblocking. Start/stop/pause/flush requests change state asynchronously. Closing concurrently with direct I/O is unsafe; an error callback must not perform its own stop/close. Requested sharing and buffer settings need inspection after opening |
| [AP] Apple player node; [PS] node stop; [PC] played-back callback | Stopping a node clears scheduled events and resets its timeline; it does not stop the engine/hardware. Stopping inside its completion callback can deadlock. The played-back callback accounts for downstream processing/device latency, but is still a framework callback rather than independent acquisition |

## Translation contract if AudioTrack is selected

The [existing C fixture](../native/lab/owned_output/README.md) operates on mono
frames with errno-style scripted results. It cannot receive raw AudioTrack
return integers unchanged. The following proposed profile applies only if
the later review selects PCM16 and the short-array overload. ByteBuffer,
float and offload paths require their own scoped units contract. Define a
typed adapter result before porting the fixture's retry/hold logic:

| Observed result | Proposed AQSS treatment |
| --- | --- |
| Positive, within the request, divisible by the configured channel count | Record the returned sample count and derived accepted frames. Advance only that prefix of the immutable source block. Retain that it may still have an effect |
| Zero | Record no progress and preserve the exact suffix. Do not relabel it as an observed POSIX EAGAIN or spin on the owner/UI thread |
| Documented Android error or any other negative value | Record the raw result plus its Android classification; close new admission. Preserve earlier accepted work. A later recreation cannot replay the old suffix |
| Invalid request bounds/alignment or arithmetic overflow | Reject before any native call |
| Returned count beyond the request or not aligned to channel count | Record an invalid result and inhibit further writes. Do not invent a transfer count |
| Hold after entry and before return/accounting | Retain the entered call and its source until the return is recorded. A positive result still counts even though admission has now closed |

Use checked conversion for samples, frames and bytes. Capture requested counts,
offset, returned value, run/route revision and clock domain in the trace. A
positive result is local acceptance evidence only. The next-call error example
is an explicit counterexample to treating a successful prefix as a healthy or
completed physical transaction. These policies are design deductions from
[AT]/[AS] and the fixture obligations, not an implemented native binding.

## Proposed ownership and stopping rules

Use one app-local output owner and one serialized worker for a bounded run.
Before each mutating call, bind a current run/context to call entry and reserve
its trace capacity. A control-side hold closes future admission without
waiting behind the worker's pending writes. Calls already entered remain
outstanding until their real return and accounting. This does not make the
final OS routing decision atomic with application authorization.

Use a finite scheduling policy with at most one pending retry and an explicit
attempt/time bound. Select those bounds only with the actual format, buffer
and trial plan. Do not apply offload callbacks to ordinary PCM [SC], or keep
an unbounded silent stream warm. The latency guide explicitly notes the power
cost of continuous output [LA]. Resource decisions need handset measurements.

On Stop, focus/lifecycle loss, route invalidation, clock fault or native error,
close admission first. For the conditional streaming candidate, account for
any entered write, then execute the reviewed pause/discard/release sequence on
the owner. Record entry/return/failure of cleanup too. A cleanup exception keeps
the resource quarantined; a timeout cannot free an owner or certify silence.
No callback, focus gain, route return or lifecycle resume restarts old work.
A new run needs a fresh explicit Start and the full admission checks.

The focus proposal accepts only an immediate grant, declines delayed start,
and handles duck/loss as terminal for the first lab run. Use the same accurate
audio-use description for the focus request and track; a game-specific tuning
example is not permission to misclassify this app. This foreground lab adds
no background service or system-wide volume control. These are AQSS choices
based on [FO]/[FB], not platform guarantees of silence or exclusivity.

Repository inspection found that ForegroundMicrophoneGate arbitrates input
tools only; its own contract explicitly denies output authority. The existing
capture worker retains its recorder through cleanup, and iOS input configures
the shared audio session. A future output increment needs reviewed admission
across these resources; it cannot reuse an input lease as output authority or
change the shared session while input is active/closing. Keep the first lab's
input/output roles separate unless a later review admits full duplex.

Queued callbacks must carry a stable run identity and reject closed/stale
work. Unregistering is not assumed to drain already queued delivery. Retain
callback/child metadata through its actual last use. Neither a Java object
being reachable nor a native release request proves physical retirement.
Process restart creates missing-history uncertainty; it cannot reconstruct
NOT_APPLIED or grant successor readiness.

## Route, clocks and the second phone

Keep requested configuration, constructed stream configuration, reported route,
native progress and independent observation as separate facts. An advertised
phone output or successful route preference cannot fill the actual-route row.
Any observed relevant change invalidates the run, while unobserved changes
remain an acknowledged limitation [RF]. The production handoff barrier stays
closed; this lab is not an atomic enforcement boundary.

If timestamps are used later, record their named clock domain and wrap/reset
handling. Do not subtract a phone-clock report date, BOOTTIME timestamp or
second-phone time from an AudioTrack MONOTONIC timestamp. An estimated
presentation event is not an acoustic measurement [TS]. Define any conversion
and its uncertainty before computing a duration.

The other phone can at most be a qualitative witness until its actual mode,
processing, placement, interruptions and retention settings are reviewed.
Clock mapping, calibration, detector/window and sensitivity remain missing.
The [earlier acquisition research](phone-output-research-2026-10-24.md#observer-and-later-playback-obligations)
still applies. No recording or upload is requested by this paper review.

For iOS, independently review the actual device/OS, session ownership,
interruptions/routes, engine lifetime and callback types before selecting its
backend. [AP]/[PS]/[PC] make clear why Android return codes and stop sequences
cannot serve as the iOS contract. Its microphone ownership logic remains
unchanged, and signed iPhone distribution is a separate dependency.

## Falsifiable implementation checks after inventory review

These are pending tests for an eventual selected adapter, not executed results:

| Scenario | Required observation |
| --- | --- |
| Failed admission or focus; input active/closing | No native output allocation, play or write; focus denial cannot create a deferred start |
| Partial prefix, then a hold | The accepted prefix is retained and the exact suffix is never submitted again |
| Zero, then a permitted later attempt | No duplicate prefix or busy loop; the suffix survives only within the original finite run bounds |
| Positive prefix followed by dead-object error | Earlier acceptance survives; the run is invalidated and a replacement cannot replay its work |
| Hold during an entered write | No premature acknowledgement/reclamation; actual return is recorded even when positive |
| Stop/discard/release failure or worker delay | New runs stay blocked through actual ownership resolution; a timeout does not stand in for return |
| Delayed focus gain, old route callback or stale retry | No playback or fresh descendants; closed run identity remains closed |
| Full trace or reference registry | Reserve before dispatch; reject fresh work while preserving old records and cleanup capacity |
| Unavailable timestamp, wrap/reset or wrong clock domain | Keep timing unknown; omit derived latency rather than stitching incompatible clocks |
| Restart with missing history; observer unavailable | Keep physical outcome unresolved and production/successor gates closed |

Before later trials, pin the exact source/APK, actual setup, selected API,
signal/volume/consent plan and bounded resource/trace protocol. Instrument
control/entry/return/accounting stages independently. Measure failures and
residual effects as well as successful traces. A native test or emulator can
verify software ordering, not speaker output containment or calibrated latency.

## Phone-independent implementation prerequisite

The owner subsequently requested continued work that does not require the
unavailable phone report. The [isolated Kotlin/JVM accounting lab](../native/lab/pcm16_accounting/README.md)
implements the units, immutable suffix and staged hold/return-accounting portion
of this reviewed contract using synthetic observations. It has no native API,
audio resource, scheduler or mobile-app dependency. The adapter-specific and
physical checks above remain pending. This is implementation of the existing
review, not a new backend selection or research approval request.

The subsequent [scripted run-controls extension](../native/lab/pcm16_accounting/RUN_CONTROLS.md)
implements declared admission, bounded pending-task policy and staged cleanup
observations on a mock backend. It supplies no native handle, real scheduler,
resource lease, concurrent cut or physical retirement evidence. The exact
backend, worker/callback lifetime and actual phone trials remain separate.

## Source register

All URLs below are primary publisher sources. Kotlin reference URLs were used
where the Java reference fetch timed out. Apple indexed documentation was used
where the live page required JavaScript; its API facts must be checked against
the selected Xcode/device availability before implementation.

- **AT:** [AudioTrack API reference](https://developer.android.com/reference/kotlin/android/media/AudioTrack), especially write(short[], offset, size, mode), stop, pause, flush and minimum buffer size.
- **AS:** [AOSP AudioTrack.java at commit 99b01a65cc4c104933788b3143285ab6bae65827](https://github.com/aosp-mirror/platform_frameworks_base/blob/99b01a65cc4c104933788b3143285ab6bae65827/media/java/android/media/AudioTrack.java). Resolved android-16.0.0_r1 through annotated tag 2e7c3f260cbaef2052cdf2c1c84d8442549e0063. This is a reference release, not evidence of the owner's firmware.
- **RF:** [AudioRouting](https://developer.android.com/reference/android/media/AudioRouting).
- **FO:** [Manage audio focus](https://developer.android.com/media/optimize/audio-focus).
- **FB:** [AudioFocusRequest.Builder](https://developer.android.com/reference/android/media/AudioFocusRequest.Builder).
- **SC:** [AudioTrack.StreamEventCallback](https://developer.android.com/reference/kotlin/android/media/AudioTrack.StreamEventCallback).
- **TS:** [AudioTimestamp](https://developer.android.com/reference/android/media/AudioTimestamp).
- **AA:** [AAudio guide](https://developer.android.com/ndk/guides/audio/aaudio/aaudio).
- **LL:** [Low latency audio checklist](https://developer.android.com/games/sdk/oboe/low-latency-audio).
- **LA:** [Audio latency guide](https://developer.android.com/ndk/guides/audio/audio-latency).
- **AP:** [AVAudioPlayerNode](https://developer.apple.com/documentation/avfaudio/avaudioplayernode).
- **PS:** [AVAudioPlayerNode.stop](https://developer.apple.com/documentation/avfaudio/avaudioplayernode/stop%28%29).
- **PC:** [AVAudioPlayerNodeCompletionCallbackType.dataPlayedBack](https://developer.apple.com/documentation/avfaudio/avaudioplayernodecompletioncallbacktype/dataplayedback).

## Result and remaining dependency

The bounded backend paper review is complete. The owner confirmation is
recorded; no repeat confirmation is needed for follow-ups within this review
or implementation of its already researched contract. The standing rule
continues to apply to genuinely new research beyond this scope. The actual 0.35 setup report is
still needed before choosing the adapter for the owner's setup. No 0.36 APK
has been built. Android remains 0.35/build 38 and iPhone/iPad remains 0.34.0;
N2b–N5, physical output/protection and signed iPhone distribution stay pending.
