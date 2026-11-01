# Android 0.41 Voice availability and cleanup recovery

October 28, 2026. The owner requested 0.41 while testing the delivered 0.40.
Planned Android identity is `0.41-voice-cleanup-live-input`, build 44.
iPhone/iPad application source remains 0.38.0/build 1; its signing and physical
qualification requirements remain separate.

## Research and selected design

Voice check shares the existing app-owned input/output exclusion gate, but
still presents its older idle and cleanup text. Idle entry can conceal an
occupied owner; Start can report speech availability or request permission
before explaining that audio work is already occupied. Sticky cleanup disables
Start, but its message asks for force stop without a direct way to preserve
existing temporary meter reports. This follows the already tested 0.40 meter
guidance rather than introducing a new recognition or audio backend.

Primary documentation was refreshed before implementation:

| Source | Consequence |
| --- | --- |
| [SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer) | Keep the existing on-device availability check and factory, main-thread API calls, and destruction of an unused recognizer. A read-only resource snapshot cannot authorize service creation or prove native quiescence. |
| [RecognitionListener](https://developer.android.com/reference/android/speech/RecognitionListener) | Retain current run identity, foreground/focus, actual permission and elapsed-time checks for callbacks. UI recovery does not accept words or synthesize levels. |
| [Runtime permissions](https://developer.android.com/training/permissions/requesting) | Keep permission requests tied to explicit Start. Check app-owned availability before presenting that request; a response or Settings return updates guidance only. |

The selected combination is the existing synchronized read-only gate snapshot,
native acquire/release admission, manual-only retry and the existing immutable
support report review/share. Occupied guidance precedes speech availability and
permission presentation. It asks the user to stop the other tool and wait for
it to close. AVAILABLE remains an observation, not a reservation; the later
native input acquire must still win. No observer resets quarantine.

Blocked cleanup takes precedence over permission, ordinary Stop/Clear and stale
permission responses. It hides the permission shortcut, disables Start, and
offers **Recent sound checks** during recovery only. This is the existing
process-local meter history, not a new history of recognized words or Voice
runs. Ordinary Voice entry retains its uncluttered view. Review, Share and Clear
recaps cannot release quarantine. The report says when no completed meter
checks exist. Recovery puts saving any wanted temporary reports before force
stop. Voice words continue to clear through the existing lifecycle policy.

No new permission, dependency, network request, service fallback, model download,
background task, polling timer or persisted data is introduced. Existing speech
availability, recognizer cancellation/destruction, the shared gate's authority,
the 30-second lifetime and callback admission remain. Event-driven presentation
adds bounded reads only. Latency, battery and physical shutdown on an actual
phone are unmeasured; the charter's physical response target is not qualified.

## Tests-first and verification scope

The existing native availability fixture is parameterized for the actual Voice
Activity, keeping the meter cases. It establishes synthetic output ownership,
then observes the native busy entry and explicit Start before permission or
speech-service work. Without a recognizer/model dependency, it checks no service,
microphone lease, active Voice lifetime or words are created. It directly checks
that the shared input gate rejects occupied output; it does not claim to have
executed a recognizer on an unavailable service. A new available entry must
remain idle and keep the recovery-only report button hidden.

Synthetic quarantine then exercises recreation, a stale permission response,
Clear words, visible/reachable report actions, exact historical text sharing,
Back and Clear recaps without releasing the block. Both missing and granted
microphone permission run at font scales 1.0 and 1.5. Reports and screenshots are
retained. The original meter fixture still checks actual worker admission.

The occupied leases, failed cleanup and historical recap are explicitly
synthetic observer-only fixtures, not real delayed platform calls, cleanup
exceptions, recognized words, speech accuracy or physical qualification. The
test observer remains outside the delivered app. A tests-only source precedes
implementation; its native busy-entry failure and final source-bound receipts
belong to the draft PR and delivery checkpoint.

Tests-only source `427113cf15c94f5b853b7369af6a0f2ce2bacc93` passed all four
core jobs in [run 40814993814](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40814993814),
as expected for this UI-only gap. The focused native candidate and observer
built successfully, passed the existing combined setup-report observations,
then [run 40814993816](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40814993816),
job `123253863772`, failed on actual Voice busy entry: `Microphone off` rather
than the wait-for-cleanup message. No production/version change preceded that
receipt. It establishes the missing entry guidance, not an isolated native
failure for every later recovery assertion.

Final delivery also requires the complete existing Android regression, unit
tests, lint, quiet checks, exact sharing and private intake, four core CI jobs,
APK source/run/package/version/build/hash/signature/artwork checks and visual
review. Tests do not supply N2b–N5 observations, consent, real output/silence,
protection, calibration, latency, phone installation or signed iPhone delivery.
