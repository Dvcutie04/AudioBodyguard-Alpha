# Shared iPhone microphone ownership and voice lifecycle

## Scope and research decision

October 20, 2026 UTC. This increment follows the separately reviewed
[iPhone sound check](ios-live-sound-check-2026-10-19.md). Inspection found that
Voice check unconditionally deactivated the app-wide audio session when closed,
even without owning capture, while the meter had a separate owner. Voice check
also reused an engine across resets and could start from permission callbacks.
These are concrete input-tool lifecycle gaps; no physical output work is implied.

| Primary source refreshed | Implementation consequence |
| --- | --- |
| [Apple AVAudioSession](https://developer.apple.com/documentation/avfaudio/avaudiosession) | The audio session is app-wide. Voice and meter now share one main-actor lease gate; neither configures or deactivates the session without its current lease. |
| [Session activation/deactivation](https://developer.apple.com/documentation/avfaudio/avaudiosession/setactive(_:options:)) | Stop and remove the tool's engine/tap before deactivation. Failed deactivation latches the shared gate closed until process exit; idle/stale cleanup never invokes the session API. This is a conservative app rule, not evidence of a physical cutoff. |
| [Speech authorization](https://developer.apple.com/documentation/speech/sfspeechrecognizer/requestauthorization(_:)) | Permission callbacks return to the main queue and only update consent status. Microphone and speech permission each require a fresh Start before progressing to capture. Leaving/inactivity invalidates pending callbacks. |
| [On-device requirement](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition) and [device support](https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition) | Check support/availability before creating a capture run and require on-device recognition. Unavailable assets/languages/services stop with an explanation; no cloud fallback is added. |
| [Apple media reset guidance QA1749](https://developer.apple.com/library/archive/qa/qa1749/_index.html) | Dispose each run's engine and recognition objects after reset/loss. A notification never reactivates capture; a later explicit Start creates new objects. |
| [Audio interruptions](https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions), [route changes](https://developer.apple.com/documentation/avfaudio/responding-to-audio-route-changes) and [audio tap](https://developer.apple.com/documentation/avfaudio/avaudionodetapblock) | Voice now stops on inactivity, interruption, changed selected input, service loss/reset or invalid input. Framework callbacks publish into per-run slots instead of per-buffer/per-result main-thread closures. |

The existing AVAudioEngine/Speech combination is retained to avoid a new recording
backend or external service. Both tools use the input-only record category with
measurement mode requested and disclose possible interruption of phone playback.

## Behavior and bounds

- One process-local owner across Voice check, Live sound check and any app scenes.
  Lease identity changes for every run. Missing/stale leases cannot activate or
  release another run. The gate is not an output capability or physical lease.
- Start is explicit. Permission grants, foreground return, route return and media
  recovery cannot start recording. System consent sheets may make the scene
  inactive and invalidate the pending prompt result; Start re-reads OS consent.
- Voice uses the meter's finite Float32 arithmetic, 65,536-frame callback limit,
  750 ms freshness window, monotonic-clock checks, three-second missing-input
  timeout and 30-second run limit. Its graph retains at most 40 summaries and is
  empty while stopped/stale. Zero means quiet or blocked, never measured silence.
- One latest numeric summary and one latest recognition update per run; the
  display timer runs every 100 ms in common run-loop modes. Recognized text is
  bounded to 500 Unicode scalars (at most 2,000 UTF-8 bytes), including combining
  marks and emoji. Terminal speech events cannot be overwritten by late partials.
- The app-owned audio ingress uses a nonwaiting lock attempt on publication.
  Stop closes ingress before ending speech audio, serializing append/endAudio.
  The existing summary mailbox can drop contended publications/error indications.
  Speech's internal buffering, callback scheduling and append latency are not
  bounded or measured by this change. No hard real-time cutoff is claimed.
- Stop closes old result slots, discards the engine and cancels recognition.
  Pending/late words cannot repopulate the view. Explicit Stop leaves the bounded
  words visible for review; clear/close/inactivity removes them.
- No audio file, transcript persistence, upload, background capture, new permission,
  TV command, automatic protection or production output authorization is added.
  The OS/Speech framework owns its own audio storage and lifecycle; this app does
  not claim to erase that storage or qualify speech accuracy.

## Verification record

The tests-only revision `ffdec2be536a2907727332e4edb05d5754d9e1c2`
[failed in Swift compilation](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39358127713)
because the shared microphone gate and speech mailbox did not exist. The red
job was `118417680104`; Python and scripted C passed at that tests-only revision.
Green results must be tied to the subsequent exact source revision in the PR.

Ten new Swift cases cover exclusive ownership, idle/stale cleanup, repeated
activation/release, activation failure, sticky cleanup failure, latest-only text,
terminal-event retention, closed-slot rejection and Unicode byte bounds. The
focused Simulator workflow adds voice idle/navigation, denied microphone and
speech consent without deferred capture, alongside the existing meter checks.
Unavailable Simulator microphone input is an explicit skip, not a physical pass.

Real iPhone speech, route changes, media reset behavior, scheduling latency and
battery cost still require installed-device trials. Package/fake-session tests
establish the app's arbitration policy, not the OS's physical behavior. N2b–N5,
TV output and automatic protection remain pending.
