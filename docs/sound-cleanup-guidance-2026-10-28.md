# Android 0.40 microphone availability and recovery guidance

October 28, 2026. Continues the owner's request to finish the next build while
0.39 is being tested. Candidate Android is `0.40-sound-cleanup-live-input`,
build 43. iPhone/iPad application source remains 0.38.0/build 1.

## Research and selected design

The existing process gate correctly refuses another owner during audio work
or unresolved cleanup. The microphone screen, however, can look idle and ask
for microphone permission before discovering that refusal. Its worker's busy
message also omits waiting for cleanup. Cleanup recovery asks for force stop
before explaining how to preserve temporary reports.

Primary Android documentation was refreshed before implementation:

| Source | Consequence for this increment |
| --- | --- |
| [Request runtime permissions](https://developer.android.com/training/permissions/requesting) and [permission overview](https://developer.android.com/guide/topics/permissions/overview) | Request access in the context of an explicit usable feature. Inspect app-owned availability before a new permission prompt; a permission response updates guidance only. A future explicit Start still checks actual permission. |
| [AudioRecord](https://developer.android.com/reference/android/media/AudioRecord) | Blocking reads and native resource release remain the worker's responsibility. A presentation snapshot cannot reserve the resource, release another owner, establish physical retirement or justify an automatic restart. |

The selected design combines a synchronized read-only state observation, the
existing identity-checked acquire/release authority and the existing immutable
support report preview. Observing AVAILABLE is not a reservation. A competing
tool may acquire before the worker starts, and the worker must still reject
that attempt without allocating a recorder or inventing a completed recap.

OCCUPIED explains stopping the other tool and waiting for it to close before
another explicit Start. Start stays available for a deliberate later retry;
this screen introduces no polling or automatic retry. BLOCKED takes precedence
over permission guidance, hides its Settings shortcut and disables Start.
Recent sound checks, report review, exact text sharing and Clear recaps remain
available. The recovery message asks the owner to preserve any needed reports
before force stopping, because those recaps are held only in process memory.

Resume, recreation, permission callbacks and report actions never request a
capture. An old permission response cannot replace current cleanup guidance
or clear quarantine. Native admission failure and actual worker cleanup failure
use the same recovery language as an already blocked entry. Audio read/stop/
release ordering, ownership, retention, permissions and report format stay as
before. No new API, background task, wakeup loop, dependency, network request
or persistent data is introduced. Device latency, battery and physical output
remain unmeasured; this is not evidence for the charter's response-time target.

## Tests-first evidence and verification contract

Tests-only source `9b3d38b63415ea95b8502cf1c364b842cc8aebd4` precedes the
implementation. Core run [40778061427](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40778061427)
fails Android job `123132388035` at the missing `state`/`State` observation API.
Its other three core jobs passed. Focused native run
[40778061487](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40778061487),
job `123132387448`, built the native app and observer and failed on busy entry:
the actual status was `Microphone off`, with the expected wait-for-cleanup
guidance missing. This is a missing-behavior receipt, not a real cleanup failure.

Four new Kotlin cases check nonmutating observations, shared input/output
ownership with no optimistic reservation, stale/foreign cleanup rejection and
sticky quarantine across later successful-release claims. Native fixtures
inspect occupied and blocked entry with both granted and missing microphone
permission, explicit denied UI/worker starts, recreation, a stale permission
response, manual-only retry, exact historical report sharing and Clear recaps.
The same cases run at font scales 1.0 and 1.5. They retain screenshots and the
actual reviewed report text; installed version/build and permission state must
match independently observed package details.

The occupied lease, cleanup failure and historical recap in those fixtures are
explicitly synthetic and confined to the separate observer APK. They are not
an actual delayed native call, cleanup exception, phone observation or physical
qualification. Force stop between cases discards the quarantined test process;
no production reset API is added. The full APK lane must also pass prior input,
photo, navigation, report, quiet-check, exact sharing and private intake checks,
unit tests, lint, source/signature/artwork checks and observer exclusion.

Final source/run identities, observed counts, visual review and APK bytes/hash
belong to the draft PR and delivery checkpoint after those checks complete.
The first implementation's core Android checks passed. Its focused run
`40793282194` reached the exact historical support sharing checks, then failed
on the observer's report Back lookup. The existing compact button exposes
`Back` as its accessibility description, with no text. The observer now matches
that description and scrolls backward to the header after a long report, while
retaining actual visible/enabled button clicks, exact sharing and quarantine
assertions. This is an observer correction; application navigation and sharing
are unchanged. Subsequent complete source-bound checks are required.
N2b–N5 qualification, actual phone reports and signed iPhone delivery remain
pending. No connection, continuous protection or physical silence is inferred.
