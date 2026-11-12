# Voice Skip: next builds and acceptance criteria

**November 10, 2026 — resumed interactive software work.** Supplements the dated
[long-term roadmap](long-term-roadmap-2026-11-10.md) and
[voice acceptance record](voice-skip-2026-11-10.md); does not replace their history.
Both iPhone and Android remain targets. No new recurring schedule, physical trial,
TV access, pairing, store submission or distribution is authorized by this plan.

## Current evidence, not a finished hands-free feature

The prior candidate `ad047d68cea8477f8e2907de9ba8ec1b72a0b540` (tree
`b4ad755bdced5d5431fef6485d8049cdaaee51b9`) passed its selected
[core](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42917184915),
[manual native button UI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42917184873)
and [unsigned preflight](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/42917198114)
workflows. The native code connects final recognition events to `requestFinal`.
The tests exercised supplied final text and manual authored-button taps separately,
not an acoustic utterance through an OS recognizer to playback. A button callback
is REQUESTED, not independently verified media progress. These older results do
not verify a new commit merely because it is in the same PR.

The current prototype is a user-started foreground listening check, with at most
one action per listening run. It is not yet a persistent hands-free TV remote.
Future listening-mode work must preserve explicit consent, a visible microphone
state and an immediate Stop; no silent background/cloud fallback is implied.

## Immediate repair: listening-run ownership

Focused tests reproduced two deterministic policy edge cases in all three mirrors:

1. A denied final-result callback attributed to an old run could call `stop()` on
   a newer run before checking which run owned the event.
2. In the split proposal/request API, a current-run permission or foreground loss
   could be ignored when another validation failed first. Restoring state and
   permission could then reuse the old proposal without an explicit fresh Start.

The repair checks run identity first, then current-run consent, then proposal and
control state. Old-run callbacks have no effect on a newer run. Current-run loss
revokes pending work even when the same request also has a missing proposal or
changed snapshot. No denied event calls the owned button; recovery requires a new
run identifier. Exact grammar, at-most-once behavior, native permissions, and
external-control boundaries remain unchanged.

Evidence: source bytes used locally match the Git blob IDs at the parent. Isolated
Python tests went from 8 failing / 2 passing to 10 passing. Three Swift XCTest
methods went from two failing methods (28 assertion failures) to all passing.
Kotlin's same three test bodies, compiled in a standalone JVM harness without the
JUnit annotations, went from two failing methods to all passing. These are isolated
policy tests, not a full checkout, Android instrumentation, iOS simulator or speech
trial. Hosted results for the eventual commit must be recorded in the PR separately.
The native controllers already have additional callback/session protections; these
policy failures alone do not establish a real-device exploit or observed app action.

## Next implementation sequence

| Milestone | Smallest useful deliverable | Observable acceptance / current limit |
| --- | --- | --- |
| **V2 — OS speech input to an owned action** | On both platforms, exercise authored speech audio through an actual available on-device recognizer and the same final-result handler used by the app. Follow with separately authorized, explicitly started real-microphone trials. | Each requested phrase activates only its matching owned button once. Record input method, actual transcript, locale, OS/runtime, recognition availability, run identity and observed control change. Partial, negative, Stop, background, stale-run and permission-loss cases produce zero action. File input is not a microphone trial; unavailable recognition is BLOCKED/UNRUN, never a transcript injection counted as speech success. |
| **V3 — observable owned playback** | Replace a button-only demonstration with an authored local media fixture containing independently known intro/recap segments and distinct corresponding controls. | The voice request selects the intended control and a separate readback observes the expected playback transition. Wrong content, expired control, duplicates and manual competition have no unintended effect. No arbitrary Next Episode, ad bypass or guessed seek substitution. Measure recognition and action latency separately; do not claim a sub-200 ms result without measurements. |
| **V4 — one documented supported external integration** | Investigate one named player/device API and its explicit semantic Skip Intro/Recap capabilities. Implement a capability adapter only where documented support and authorization exist. | Unsupported players say unavailable; no generic UI-coordinate clicking. Independent identity, authenticated target control, scoped consent and fresh state precede any separately authorized physical trial. No current Netflix, VIZIO or universal-player support is implied. |
| **V5 — usable listening modes and phone coverage** | Define a clear opt-in listening window and supported voice-entry method for each phone/OS. Evaluate repeated utterances using separate utterance identities without reusing a consumed command. | Foreground/background/lock behavior, interruptions, false activations, Stop responsiveness, device/language availability, battery and privacy retention are tested on named configurations. Do not remove safeguards just to keep the microphone open; do not claim any-phone or always-on operation from two simulators. |
| **V6 — integrated candidate and pilot** | Combine the verified voice route with reliable setup, accessible controls and reviewed report handling. | Resolve or explicitly block release on relevant #120 Share/navigation failures. Exercise compact/older-system paths and user trials. Publish a compatibility matrix and exact source/artifact evidence. Merging, signing, distribution and pilots require separate approval. |

The original long-term audio roadmap continues alongside the voice track:
**T1** independently established identity and consent; **N2b** a named owned
output path; **N3** independent output/Stop/buffer measurements; **N4** verified
conditional activation and controller handoff; **N5** separately qualified iOS
and Android lifecycle/resource/release behavior. Caption and sound capabilities,
manual priority, Pause, Undo & Teach, recovery/history and measured pilots remain
behind their own capability and evidence gates. Voice fixture success cannot
close physical audio-protection gates.

## Platform evidence consulted for V2 (November 10, 2026)

- [Apple speech request types](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest): an existing file can use `SFSpeechURLRecognitionRequest`; live audio uses the buffer request. These are different test inputs.
- [Apple on-device request](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition): require both `supportsOnDeviceRecognition` and `requiresOnDeviceRecognition` rather than silently falling back to a remote service. Availability and permission still need runtime checks.
- [Android audio-source contract](https://developer.android.com/reference/android/speech/RecognizerIntent#EXTRA_AUDIO_SOURCE): API 33 adds an audio descriptor and format extras. An implementation that does not support the extra may open its microphone instead. Therefore merely attaching a file descriptor is not proof the intended audio source was consumed. A test must establish service support and actual input provenance, and refuse an unexpected input mode.

These sources describe available API mechanisms, not proof that the hosted runner
has the required speech model/service or that a user's phone is supported.
Historical #114/#115 downloads remain unchanged and do not contain this newer
voice work. Known native Share and setup failures are not repaired by this change.


## November 10, ~17:30 Pacific — V3 native local-video candidate (new source, not yet CI-approved)

A new controlled **8-second, silent, authored H.264 MP4 fixture** has been included
in the iOS and Android application source. Four equal color segments give a
known timeline: Intro 0–2 seconds, middle 2–4, Recap 4–6, continuation 6–8.
This is **not** streamed, licensed, third-party, DRM-protected or a TV recording.
The two files are byte-identical. SHA-256 of the authored binary is
`6215d320cd022c808c3f1732aa47ae411b0b7d0df95c843a9768220f73dc931e`
(1,829 bytes, H.264 baseline 64×64 at two frames/second, 8.0s, keyframes
at 0/2/4/6). Their Git blob SHA is
`ea6a3fa26be4be533a8462404197562e407a8e82`.

A new optional **Local video trial** within the existing voice check prepares
either Intro at 0s or Recap at 4s in the currently owned test clip. It only
enables the corresponding action when the initial position has been read
back. The **same authored Skip button handler** invoked by final admitted
voice intent requests native playback seek to 2s or 6s. Its immediate result
is merely REQUESTED. A separate asynchronous AVPlayer/MediaPlayer completion
callback then reads the player's actual current time/position before publishing
a local-video observation; an interrupted/incorrect seek does not produce that
observation. Consumption disables the control and increments its generation;
new selection/reset invalidates old callbacks and changes its generation. The
old manual button fixture remains separate, with original tests retained.
No on-device speech-input result is implied by this new video path.

A dedicated iPhone XCUITest and Android emulator smoke extension exercise both
real local video seeks, native position readbacks, independent action states,
reset and microphone-off state. Explicit SHA checks and provenance are in the
focused UI workflow. **The new source requires exact-source hosted verification**;
prior 7/7 jobs are not counted as passes for it. The newly authored MP4 is a
local testing asset, not a release media feature. Playback position readback in
a paused local decoder is software evidence only: it is not physical output,
acoustic measurement, a third-party streaming Skip capability or a complete
spoken-voice end-to-end trial.

Actual V2 OS speech recognition remains unrun on this revision. No availability
of an on-device speech recognizer or model has yet been established on hosted
iOS/Android simulators. Do not inject a string and report a microphone result.


## November 10 ~19:30 Pacific — V2 on-device service availability probes

Native CI now adds two **observation-only** probes alongside the already verified
manual local-video tests. An iOS Simulator XCTest directly queries
`SFSpeechRecognizer(locale: en_US)` availability, on-device support and
authorization, with a printed provenance line and explicit `XCTSkip` if any
requirement is unavailable. The Android API 36 emulator uses a *separate
test-only instrumentation APK* to call the actual
`SpeechRecognizer.isOnDeviceRecognitionAvailable` API without invoking
`startListening`; it records the API result and demands a completed
instrumentation receipt. These probes do not open a microphone, provide an audio
source, run a recognition task, inject final text or activate any button.
An unavailable service is an evidence-backed blocker for V2 on that runner,
not a failure of the already verified V3 local-player actions. Neither an iOS
XCTest success nor an Android instrumentation success means an on-device speech
model actually recognized a phrase. Next V2 acceptance is an authored audio
sample consumed by the OS recognizer and a final result flowing through the
same gate to the owned player. No silent microphone fallback is permitted.
