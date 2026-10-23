# AQSS development roadmap

Checkpoint: October 22, 2026. Continue from the restored a-Shell baseline and the existing native endpoint qualification research. iPhone/iOS and Android remain equal product targets.

**INFERENCE IS NOT REALITY. AI proposes. Policy authorizes. Physical Commit verifies.**

## Current checkpoint

October 22 Insights access: the [0.21 record](insights-sound-checks-2026-10-22.md)
adds Recent sound checks directly to Insights, reusing the bounded process-only
recap store and presentation. Close returns to Insights; Clear is shared with
the original meter entry. This route opens no microphone tool and adds no
permission, persistence or output authority. Audio trends and Session history
retain their separate unknown states. Native results and APK identity belong
to draft PR #53; physical handset, signed iPhone and N2b–N5 remain unqualified.

October 22 report contents choice: the
[0.20 record](support-report-choice-2026-10-22.md) adds one Include recent
sound checks control in the private report preview. Excluding checks shares
only installed build details and preserves the app's completed recaps.
Selection operates on one immutable snapshot; native Cancel preserves it,
and closing/reopening resets the choice. No capture, upload, persistence or
output authority is introduced. Exact native results and APK identity belong
to draft PR #52; physical handset, signed iPhone and N2b–N5 remain unqualified.

October 22 private support report: the
[reviewable report record](private-support-report-2026-10-22.md) implements the
planned entry in Advanced Settings. Candidate 0.19 previews installed build
metadata and at most five completed input-only meter summaries before an
explicit native Share. Cancel preserves the snapshot; Back returns to the
caller. Audio, words, photos, TV/network details and generic logs are excluded.
No capture, upload, report file or output authority is added. Exact native
results and APK identity belong to its draft PR; handset compatibility, signed
iPhone distribution, recipient delivery and N2b-N5 remain unqualified.

October 22 explicit build sharing: the
[share design and native test record](share-build-details-2026-10-22.md)
adds Share build details inside the installed-metadata preview on Android and
iPhone/iPad. Candidate 0.18 hands only the previewed product, platform,
version and build to the native share sheet after a tap. Cancel preserves
the preview and Back returns to Settings. The complete support report stays
planned. Exact native results and APK identity belong to its draft PR;
recipient delivery, handset compatibility, signed iPhone distribution and
N2b-N5 remain unqualified.

October 22 installed-build details: the
[build identity record](build-details-2026-10-22.md) adds a Build details action
in ordinary Settings on both platforms. Candidate 0.17 reads the installed
package or main-bundle version and build so phone-test feedback can identify
the app being used. Metadata is separate from source authentication, exact
binary provenance and physical qualification. Existing input/photo behavior
and N2b–N5 gates remain required; exact native results and APK identity belong
to its draft PR.

October 22 Voice permission guidance: the
[Voice Settings recovery record](voice-permission-settings-2026-10-22.md)
extends app-specific Settings help to Android microphone access and the
distinct iPhone microphone and speech permissions. Candidate 0.16 rechecks
native status on return, distinguishes restricted speech, and keeps listening
off until another explicit Start. Existing availability, cleanup and ownership
gates remain required. Exact native validation and APK identity belong to its
draft PR; actual handset behavior, signed iPhone distribution and N2b–N5
remain pending.

October 21 sound-check permission guidance: the
[Settings shortcut record](sound-permission-settings-2026-10-21.md) adds an
app-specific Settings action after a denied microphone request in the dedicated
meter. Candidate 0.15 rechecks permission on return and keeps capture off until
another explicit Start. Existing cleanup and ownership gates remain required.
Exact native validation and APK identity belong to its draft PR; handset
behavior, signed iPhone distribution and N2b–N5 remain pending.

October 21 photo retry-guidance increment: the
[result guidance record](tv-photo-retry-guidance-2026-10-21.md) gives a clear
retry instruction when an accepted photo yields no supported TV details.
Partial hints keep the ordinary review notice. Candidate 0.14 retains the
existing recognition, ownership and physical-control boundaries. Native tests
cover blank, unrelated, brand-only and complete-label photos; exact validation
and APK identity belong to its draft PR. Handset accuracy and N2b–N5 remain
pending.

October 21 photo-readiness increment: the
[readiness record](tv-photo-ready-notice-2026-10-21.md) updates a waiting screen
after actual cleanup and on resume. Candidate 0.13 uses release events plus a
fresh availability query; the notice does not open a picker or submit a read.

October 21 photo-work ownership increment: the
[ownership record](tv-photo-work-ownership-2026-10-21.md) keeps one process-wide
photo read admitted until its actual worker and cleanup return. Candidate 0.12
rejects overlapping imports after timeout, Clear or screen replacement while
continuing to reject late results.

October 21 photo-reading deadline increment: the
[result-window record](tv-photo-deadline-2026-10-21.md) adds a 30-second elapsed
acceptance window on Android and iPhone. After an image is selected, stalled
reading leaves hints unknown and offers another selection; late results cannot
restore an expired review. iPhone dismisses its picker before provider loading.
Candidate 0.11 preserves the prior camera, sound tools and opening art. This is
an application result policy, not framework cancellation or a physical timing
measurement. Exact validation and APK identity belong to its draft PR; actual
handset behavior, TestFlight distribution and N2b–N5 remain pending.

October 21 Android camera-photo increment: the
[full-image capture record](android-full-camera-photo-2026-10-21.md) replaces
camera thumbnails with a unique private full-image output, decoded at the
existing 2048-pixel target. Temporary access and file cleanup are checked at
request termination; canceled or unreadable captures leave hints unknown.
Candidate 0.10 retains the prior input tools and opening art. This Android
capture improvement does not change iPhone production code or advance N2b–N5;
actual handset camera compatibility and real-photo accuracy remain pending.

October 21 TV photo-selection increment: the
[selection ownership record](tv-photo-selection-2026-10-21.md) assigns a selection
identity before importing a photo. Clear, Close and replacement invalidate old
imports and recognition results; canceling a replacement leaves all details
unknown. Candidate 0.9 preserves the prior sound tools and opening art. Exact
software validation belongs to its draft PR; physical output, real-photo
accuracy, signed iPhone installation and N2b–N5 remain pending.

October 21 TV photo text-boundary increment: the
[collection-limit record](tv-photo-text-bounds-2026-10-21.md) replaces silent
OCR row truncation with whole-collection rejection on both native platforms.
Over-limit or unreadable collections leave all hints unknown and ask for a
closer photo. Candidate 0.8 retains the existing input tools and opening art.
Exact software validation belongs to its draft PR; real-photo accuracy,
signed iPhone installation and N2b–N5 remain pending.

October 20 TV photo-label increment: the
[label normalization record](tv-photo-labels-2026-10-20.md) adds the Model Name
and IPv4 IP Address forms seen in the user's VIZIO screenshots on both mobile
platforms. Conflicting or unreadable labelled candidates remain unknown.
Native synthetic-image tests are separate from real-photo accuracy or device
identity. Candidate 0.7 retains the prior sound tools; N2b–N5 remain pending.

October 20 Android input-deadline increment: the
[window closure record](android-input-deadlines-2026-10-20.md) brings Android's
sound-meter clock/deadline latch into line with the existing iPhone policy.
Ended runs cannot restore a reading, and the Activity requests capture shutdown
on the latched reason. This is defensive software behavior; no clock failure
on the handset or physical cutoff measurement is claimed. Candidate 0.6 retains
the recap feature. Exact validation belongs to its draft PR; N2b–N5 remain pending.

October 20 input-recap increment: the [local sound-check recap record](sound-check-recaps-2026-10-20.md)
adds five temporary, input-only summaries on both mobile platforms, with observed
input and typed stop reasons. Clear and process restart discard display data;
neither can unlock microphone cleanup or produce protection evidence. This
advances native status reporting while the actual N2b host/route/capture
inventory remains unavailable. Exact build and UI results belong to the draft
PR for this increment; installed-phone validation and N2b–N5 remain pending.

October 20 input lifecycle checkpoint: the
[iPhone ownership record](ios-microphone-lifecycle-2026-10-20.md) and
[Android ownership record](android-microphone-lifecycle-2026-10-20.md) cover
one owner across the meter and Voice check on each platform, explicit Start,
bounded speech display, elapsed-time limits and interruption handling. The
combined 0.4 candidate includes both increments; exact native/Simulator/emulator
results and APK identity are recorded in draft PR #36, stacked on #35. Actual
handset speech/capture and N2b–N5 remain pending.


October 19 iPhone input-parity increment: the [foreground sound-check record](ios-live-sound-check-2026-10-19.md)
adds a separately started, bounded microphone meter without a speech-recognition
dependency. Its arithmetic/freshness tests and focused Simulator workflow are
distinct from a signed iPhone installation or physical input qualification.
The prior Android 0.3 source passed its Android/iOS navigation and connected-demo
UI jobs in [the completed UI run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39182899875),
as well as its already recorded CI and Android live-input checks. This iPhone
increment does not alter that delivered APK or advance N2b–N5. Real output work
still awaits the user's actual host/route/independent-capture inventory.

October 15 Android input increment: David reported a successful preview install
on a VL68 Pro running Android 16. The next separate test build adds a bounded,
user-started microphone sound check. Its [research and verification record](android-live-sound-check-2026-10-15.md)
distinguishes real digital input samples from output observation, calibrated
acoustics and protection. This product sensing step leaves N2b–N5 pending and
does not imply installed-device qualification of the new feature. iOS input
parity is now being implemented in the separate October 19 increment above;
installed-iPhone input validation remains pending.

September 28 interface increment (PR #28, following PR #27): five native pages
share Midnight/Daylight/System presentation, contextual help, truthful empty
insights and an explicitly synthetic example chart. Future feature cards
explain prerequisites. Appearance is the only new stored preference. See the
[interface design and source matrix](interface-design-research-2026-09-28.md)
for research, acceptance checks and remaining device/usability measurements.

September 27–28 native app review: the branch following options PR #25 and
tutorial PR #26 adds direct section navigation, a six-prerequisite explanatory
checklist, accessibility semantics/touch targets, and Android nested Back
handling. It also rejects construction or copying of a Kotlin read-only view
with `canActuate=true`. The [audit and source matrix](native-app-audit-2026-09-27.md)
record the bounded scope and verification results. This UI increment does not
change N2b–N5 or the unqualified installed-device status below.

The user fast-forwarded the separate a-Shell checkout to main
`b0ca6cfebdb51f4425b0980ac6b74b04112a6806` and reported
`NATIVE_CONTRACTS_CURRENT`, **1,685 Python tests passed in 5.08 seconds**
with one external dateutil warning, and an empty `lg2 status -s`.
The first pytest invocation in that scrollback showed no result; the
completed second invocation establishes the test count. This supersedes
older phone checkpoints below. The repository's subsequent PR #19 merged
as `22a3a5919cde9cc8f927f294a3564369f17b1333`; no phone execution
at that later revision or physical output has been reported.

P1 now develops equally scoped iPhone and Android **read-only simulation app
shells**. The [prototype contract](read-only-native-prototypes.md) specifies
what their builds prove and what must remain UNKNOWN. The repo's Swift and
Kotlin package tests, iOS simulator build, Android debug APK build and a-Shell
Python tests are distinct gates; no shell build implies installed real-device
qualification or permission to open production execution.
The [P1 installed-device trial protocol](p1-installed-device-trial.md) and
manual record checker are merged; no signed iPhone install, Android device
trial or independently observed sound path has been reported. PR #19's
[hosted run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36281531594)
passed Python, scripted C, Swift simulator and Android APK jobs. A
structurally complete self-reported trial still cannot qualify N2b–N5.

PR #22 added a separate UI smoke workflow. Its first iOS simulator launch
failed because the prototype app omitted `CFBundleVersion`, a defect that
the prior compile-only job could not detect. After setting the app version,
[both UI smoke jobs passed](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36288934014):
one XCUITest launched the iOS app in an iPhone Simulator and asserted the
uncertainty/handoff labels; the Android API 35 emulator installed and launched
the debug APK and checked its UI hierarchy. Screenshots and result artifacts
were retained. [The existing four-job CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36288934022)
also passed at that branch revision. These observations establish bounded
simulator behavior only. The separate a-Shell checkout remains at its last
reported `b0ca6cf` checkpoint, and no installed-phone or physical-output
trial is implied.

The merged product-software increment adds a bounded, read-only reference
session journal, a separate pause latch, capability cards, scoped change
wording, and owned-player authored-track reports. Python, Swift, and Kotlin
consume 20 shared synthetic coverage/capability vectors. Neither these
vectors nor player callbacks prove continuous capture, rendered captions,
acoustic output or user perception. See the
[session-view contract](session-evidence-reference.md) for the permitted
wording and missing native integration. The final PR revision passed **1,678 local Python tests** and [all four hosted CI jobs](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36276197278), including Swift and Android compilation. These are separate from the phone result and physical gates.

Subsequent P0 hardening found that an ACTIVE-to-stale `status()`
returned an old admission generation while the supervisor advanced it on
exit. A focused regression failed at that mismatch; the returned immutable
status now reflects the advanced generation, including the rejection returned
by `require_automation()`. The focused case and **1,679 full Python tests**
passed locally, and [main CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36277482304)
passed its Python, Swift, Android and scripted C jobs. The phone has not yet
run that revision or an installed native app.

A subsequent P0 increment added a **reference-only, in-process event producer**.
Its capture and publication are distinct, with one pending sample and
sequence gaps for known lost publications. A Python supervisor ACTIVE
snapshot is projected as UNKNOWN_PHYSICAL_STATE, never as qualified physical
coverage. Delayed changed snapshots, expired samples and rollback fail
closed; user pause is not inferred. Six new tests brought the local Python
suite to **1,685 passed**. [Main CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36278169070)
passed all four jobs. Native iOS/Android event adapters, durable
continuity and physical observers remain pending. The
[session-view contract](session-evidence-reference.md) defines its scope.

The restoration merged into `main`, followed by the deterministic test-clock correction in [PR #3](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/3). Its [main verification run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36070023701) passed 1,625 Python tests plus Swift and Android conformance. The [source manifest](a-shell-sync-manifest.json) accounts for the 441 exported a-Shell paths; additions in this development increment are outside that historical snapshot.

N1 now includes a bounded, explicitly unqualified fake endpoint with eight work-ordering and eight context-invalidation behavioral cases. The local Python 3.12 suite passed **1,641 tests**, including **35** focused native-contract, work-ordering, context, and handoff checks. These counts overlap; do not sum them. [Hosted CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) records the result for each published revision.

The production factory guard and `EndpointHandoffBarrier.is_ready()` remain closed. No physical device was actuated by this increment.

N2a now compiles a separate C11 lab with **45 deterministic cases**: six owner, five callback, four child, six acknowledgement, five retirement, nine retry/invalidation, six PCM attenuation, and four trace cases. These are additional native test cases, not part of the current 1,652-test Python count. Its scripted backend exercises no audio API or hardware. Local normal and AddressSanitizer/UBSan runs passed all eight executables; local sanitizer used `ASAN_OPTIONS=detect_leaks=0` because LeakSanitizer is unsupported in this traced workspace. The [lab contract](../native/lab/owned_output/README.md) defines the call phases, bounded registries, identity/deadline matching, retry/fault rules, attenuation profile, typed event trace, and remaining ownership debt. Hosted CI has a separate native-lab job; inspect the published revision's result separately.

The user verified the separate iPhone a-Shell clone at `38d273e1abec4b979950290ed1bac8cf640a8161`: generated contracts current, **1,641 passed with the existing dateutil warning in 7.50s**, and empty `lg2 status -s` output. This is the phone baseline before the retry/invalidation increment below; it is not evidence of phone execution of later changes or of the compiled C cases.

## N0 inventory

| Target | Inspected repository configuration | Evidence boundary |
| --- | --- | --- |
| Python reference | `pytest.ini` collects `src` and `tests`; CI uses Python 3.13 | Local Python 3.12 and hosted Python regression execution |
| iPhone/iOS prototype | `native/ios/Package.swift` retains the Swift contract library; `native/ios-app` adds a read-only SwiftUI app target with a provisional iOS 15 deployment setting | Hosted Swift contract tests and simulator compilation must pass; no signed iPhone install or measured output path |
| Android prototype | `native/android` retains the contract library and adds an app module with target/compile SDK 36 and provisional minSdk 26 and application ID | Hosted Gradle contract tests and APK compilation must pass; no Android device install, native service or measured output path |
| Shared endpoint vectors | `contracts/endpoint_native_boundary_v1.json` and its Markdown contract | 18 synthetic vectors consumed by Python, Swift, and Kotlin |
| Endpoint handoff | `src/device_fabric/endpoint_handoff_barrier.py`: schema-3 resource holds and pinned verifier identity | Reference ordering and admission inhibition; no qualified native retirement certificate |
| Owned-output lab | `native/lab/owned_output`: standalone C11 owner, callback/child context, hold matching, retirement pool, retry/invalidation, exact fixture PCM attenuation, typed trace, and scripted backends | 45 local software cases and warning-clean compiler gate; no ALSA SDK, device, native application, or physical qualification |
| Read-only session views | `src/control/session_evidence_view.py`, authored-track finder, Swift/Kotlin projectors and prototype app shells | Synthetic snapshots and product wording only; no installed real-device qualification or continuous native observation |

These are inspected build settings, not new supported-device or release recommendations.

## N1 work-ordering and context-invalidation increments

`tests/native_endpoint_fake.py` models one resource and one handoff with an explicit event order. `tests/test_native_endpoint_work_conformance.py` checks the following behaviors:

| Scenario | Required result |
| --- | --- |
| Application queue empties after native submission | Old work remains unsettled until its explicit native disposition; observing an effect does not settle a buffer |
| A generation-7 parent settles before its descendant during generation-8 retirement | The descendant retains generation 7 and continues to block settlement |
| A pre-hold claim publishes late, or a callback tries to create a child | Publication and new descendants are rejected after closure; new successor admission also stays blocked |
| Native disposition is partial or unknown | Work remains unsettled; no completion is invented |
| Effect, observation, or settlement is replayed | No duplicate simulated effect/observation; conflicting terminal settlement is rejected |
| Work registry reaches its configured limit | Existing records survive, further acceptance fails, and inhibition still succeeds |
| Work identity is reused with another generation | The existing binding cannot be replaced |
| The application runtime changes while a native frame is submitted | The application queue appears empty but retained native work can still apply; a previously activated pending submission is rejected |
| Actual output route changes before a cached route notification arrives | The stale candidate cannot submit, even while the cached route still matches; notification cannot revive it |
| A newer successor replaces the activated one | The stale predecessor request cannot submit under its old candidate |
| Protection is revoked and later restored | Both revocation and restoration invalidate the earlier candidate; it cannot be reused |
| A candidate expires, has a forged/missing token, or is submitted before activation | Final submission is rejected; a current synthetic candidate can still submit only inside its original window |
| Unbound legacy work tries to submit after context changes | No alternate path bypasses the synthetic context hold |

Accepted, published, submitted, simulated-applied, simulated-observed, and native-settled events are distinct. A submitted frame may still apply after admission closes; the fake deliberately does not equate a hold with cancellation. Registering a child precedes settling its parent. Each accepted item emits at most six events and one generation-close event is allowed; repeated rejected operations append nothing. Retention is bounded by the configured work limit, and the fake never evicts unresolved records.

The fake returns fresh snapshots and immutable trace events. Its native qualification, authorized evidence, authenticated history, route enforcement, native cut, and production readiness remain false. A fully settled simulated trace still fails the existing shared eligibility oracle. Explicitly injected settlement and observation are test controls, not evidence from an OS, driver, speaker, or microphone.

Context candidates are immutable, in-memory test tokens. A synthetic runtime-incarnation change retains old work in the same fake instance but hides the prior application's queue. An actual-route change precedes its separate cached notification; final submission compares the candidate with the current actual route, runtime, successor, protection state, context revision, and explicit test time. A positive synthetic submission records no physical effect. This fixture does not implement process persistence, OS route atomicity, secure time, signing, revocation across processes, or competing real handoffs.

Red-green evidence: the original eight tests first failed collection because the fake module did not exist. The eight context cases first failed at the missing candidate API, then exposed an unbound-submission bypass before that path was closed. The focused gate passed **35** checks and the full suite passed **1,641** tests locally. All original assertions and production modules were preserved. The historical 441-path manifest describes the earlier a-Shell export; the changed test-only files are additions outside it. No `.py.tmp` staging files remained.

## N2a partial-write and owner-accounting increment

The September 24 partial-write research and September 25 ownership continuation are complete for this bounded step. `native/lab/owned_output/` holds one borrowed mono S16 block and a stable scripted backend context on one test thread. It distinguishes `CALL_ENTERED`, `CALL_RETURNED`, and `RETURN_RECORDED`. Acknowledging a hold requires closed admission and an accounted return; already accepted frames remain possibly effective.

The first regression compiled and failed at `backend.calls == 1`: an acknowledged hold had allowed the suffix into a second backend call. The minimal closed-admission check made that regression pass. The positive control transfers the exact remaining suffix without repeating its prefix. Four further cases check an in-flight hold, delayed recording, trace capacity, and invalid backend results. Eight call reservations plus two independent hold entries bound the trace; no history is evicted. Zero progress is recorded, and invalid results preserve prior accepted frames and inhibit new calls.

The six C cases pass with warnings treated as errors. The local container's LeakSanitizer reports that it cannot operate under tracing; local address/undefined-behavior checking therefore uses `ASAN_OPTIONS=detect_leaks=0`. The separate hosted job keeps default sanitizer behavior. Consult the revision's CI result for hosted execution evidence.

This is an in-memory, single-thread fixture with live test objects. It does not implement general callback reclamation, synchronized producer threads, persistence, scoped acknowledgement transport, gain processing, or real backend recovery. The later increment below recognizes scripted errno-style EAGAIN returns. No production module or shared eligibility vector is changed. Compiled code and clean sanitizer runs do not qualify native physical containment.

## N2a queued-callback metadata increment

`callbacks.h`/`callbacks.c` add one stable delivery context for an owner's scripted callback family. Value tickets bind that context and a sequence, with eight slots and no reuse. Queueing retains metadata before callback entry. Delivery transfers the reference from queued to active before invoking a body. A held delivery is consumed as cleanup without touching metadata or running the body; invalid and replayed tickets consume nothing.

This increment added the queued count to the active-reference reclamation gate. The first regression failed when only active callbacks were checked: one queued callback still existed when metadata was released. The queued-count gate fixed it. Five tests cover that interval, live progress, an active callback's nested hold/reclaim attempt, foreign/invalid tickets, and cleanup with both callback capacity and the owner trace full. Tests actually free the released heap allocation and replay stale tickets under the sanitizer runner. The original six owner cases remain unchanged.

Only the metadata allocation is reclaimed; the owner, delivery context, and ticket states remain alive for the entire test. Every producer is the scripted queue API. This establishes the tested C lifetime ordering, not real-thread synchronization, native API quiescence, or reusable runtime identity. The retained-child increment below extends the original no-escape contract through explicit registration. Reclamation leaves accepted-frame accounting, unknown physical outcome, and production denial unchanged.

## N2a retained-child increment

An active callback can retain metadata for a child before handing it the pointer. The value reference binds context, child sequence, and parent callback sequence. The bounded eight-slot registry never reuses a slot. New references require open owner admission and an active parent; exhaustion closes admission. A child must stop accessing metadata before releasing its reference. Release works after closure but performs bookkeeping only, without dispatch, queueing, or reactivation.

Reclamation now requires an acknowledged owner cut and zero queued, active, and retained-child references. The first regression failed because the old queued/active gate released metadata after the parent returned while a child still held it. Adding the child count fixed the failure. Four C cases verify this lifetime, acquisition before/after closure, invalid and repeated release, and cleanup with all child slots and the owner trace full. They free the allocation and reject stale releases through the still-live registry. The existing eleven C cases remain unchanged; all fifteen passed normally and with local address/undefined-behavior instrumentation.

The test API registers one level of child references; it does not execute children or register grandchildren. The outer context and owner stay alive, and callers must not free or pass out untracked metadata. The next increment below adds the bounded retirement pool; real producer synchronization and native shutdown evidence remain absent. A child's release does not erase an accepted prefix or resolve physical uncertainty.

## N2a acknowledgement and retirement increments

The user authorized both next steps and continuing research if needed. The existing September 24–25 ownership research already specifies these bounded obligations; no additional substantive research was required.

`hold.c` binds acknowledgements to endpoint/resource, runtime, request, owner admission revision, and accounted status. Its injected clock domain and exclusive deadline remain fixed. Wrong identities and unrelated notifications do not satisfy the cut. Expiry and rollback are terminal for the wait; accounting may still complete for cleanup. One-time binding of both the control and owner prevents reinitialization from refreshing a deadline. IDs are trusted fixture inputs, not cryptographic or durable identities.

The first acknowledgement case failed on a previous request ID; complete matching fixed it. A further regression failed when begin could refresh an expired deadline; rejecting repeated binding fixed that path. Six cases now cover identity/status, positive exact replay, call accounting, clock/deadline rejection, malformed inputs, and rebinding.

`retirement.c` reserves one of two slots before metadata allocation or backend entry. It distinguishes reserved/current/retiring state, rejects further admission at capacity, and releases a retiring descriptor only after the existing metadata gate permits reclamation. Monotonically increasing runtime ordinals and exact handles reject stale use after slot reuse. External owners, contexts, and physical history remain alive; only metadata and the pool descriptor may be released.

The first retirement case failed when a full pool selected an occupied slot. Explicit capacity rejection fixed it. Five cases cover retained-child capacity, safe same-slot reuse with old handle/ack rejection, pending accounting, reservation cancellation and ordinal exhaustion, and invalid handles. This is a two-block fixture bound, not a product byte budget, native shutdown proof, or durable restart implementation.

The [a-Shell continuation guide](a-shell-continuation.md) creates a separate clone of public main, records its revision, and runs the existing generator/Python checks. It preserves the original Documents checkout and unexported phone edits. Cloud verification is not evidence that these commands have run on the phone.

## N2a retry and runtime-invalidation increment

The scripted owner now recognizes `-EAGAIN` separately from fatal/invalid returns. EAGAIN and zero advance no frames; both preserve the exact suffix, require accounting, and allow only a later explicit attempt through the existing admission checks. No retry loop or deadline refresh was added. Other negative or oversized results inhibit as soon as the backend returns, closing the callback-acquisition window before the caller performs bookkeeping.

An explicit fault notification closes the owner and retains its first invalidation reason. XRUN, suspension, disconnect, route change, format change, and unknown state cannot revive old work when the backend becomes usable again. Entered/returned calls still require accounting; accepted prefixes and physical uncertainty survive. Cleanup may release queued/child references and retire metadata, but does not reset that runtime or replay its suffix.

Nine new C cases cover positive retry progress, immediate fatal-return inhibition, recovery without old-work replay, hold after no progress, pre-dispatch faults, both call-accounting windows, full-trace fault retention, and callback/child retirement after invalidation. The EAGAIN and immediate-inhibition tests each exposed an actual failure before their fixes; the explicit invalidation test was initially red at the missing API. All original 26 C cases remain unchanged. Normal and local address/undefined-behavior runs pass 35 cases; hosted CI runs the same six executables. Python and shared mobile contracts are unchanged.

This retains one sticky first reason rather than a complete fault-event history. It uses trusted fixture objects on one thread and does not implement an event scheduler, actual route monitoring, native cancellation/recovery, or fresh-work authorization. Exact OS/backend mapping remains a separate N2b obligation.

## N2a exact attenuation and event trace increment

The existing N2 research covers the bounded arithmetic and trace obligations in this step; no new physical API or platform behavior was introduced. `pcm.c` accepts only mono, signed 16-bit little-endian, 48 kHz fixture blocks with 1–256 frames and integer gain from 0 to 1000 permille. It decodes bytes explicitly, uses a signed 32-bit intermediate, divides toward zero, and rejects malformed format, size, gain, work identity, and overlapping buffers before writing output. The input is preserved. The caller must keep the prepared block unchanged and alive across partial acceptance and retries; a later profile preparation does not rewrite it. The exposed C struct does not enforce immutability.

Six PCM cases cover exact representative rounding and extremes, exhaustive signed-16 input values across all supported gains, format and range rejection, malformed and aliased buffers, capacity and unaligned input, and retry stability. This is a deterministic fixture transform; it is not an equal-loudness algorithm, production DSP, negotiated device format, clipping-quality study, or live audio path.

The owner trace now emits typed result kinds for no progress, accepted prefixes, zero, would-block, and invalid returns. Schema version 2 adds contiguous event sequence, call index, admission revision, and accepted frame count. Four tests cover mixed result ordering, fatal-return accounting after an accepted prefix, an in-flight hold cut, and bounded trace saturation. The accepted frame count is software accounting and must not be presented as proof of audible output.

Local verification on September 26: after the optical proposal boundary correction, the full Python suite passed **1,652 tests in 3.71 seconds**, and the generator reported `NATIVE_CONTRACTS_CURRENT`. The normal and local ASan/UBSan C runners each passed **45 C cases**. The workspace has no Swift or Gradle executable, so those suites were not rerun here; hosted runs must be inspected after publication. No user phone execution of this increment has been reported.

## Remaining native gates

The sequence follows the native qualification brief, `AQSS_N2_Owned_Output_Lab_Research_2026-09-24.md` with its September 25 ownership continuation, and the master handoff. The bounded N2a research authorizes the implementation steps below; it does not qualify a real backend.

| Stage | Status and next work | Exit gate |
| --- | --- | --- |
| N0 — Inventory | Repository/native contract inventory complete; exact physical hardware and measurement setup still unselected | Pin real build hosts and device/route details before a hardware experiment |
| N1 — Shared conformance | Shared 18-vector contract, bounded work sequencing, and test-only context invalidation implemented | Preserve the unresolved native and persistence questions; keep production readiness unavailable |
| N2a — Portable owned-output lab | Partial-transfer/hold accounting, callback/child lifetime, scoped acknowledgement matching, bounded metadata retirement, scripted zero/EAGAIN retries, runtime invalidation, fixture attenuation arithmetic, and typed trace implemented | Freeze these as fixture contracts; real backend-specific format negotiation, recovery, scheduling, and output observation belong to N2b |
| N2b — Real owned output | Pending; Linux/ALSA is the researched first lab candidate | Inventory available hardware, exact driver/route/format, independent capture, and instrumented native calls before physical experiments |
| N3 — Exact output qualification | Pending | Named hardware/driver/route and reproducible output measurement, including residual buffered work |
| N4 — Conditional evidence and activation | Pending, dependent on N3 | Authenticated native retirement evidence; reject stale, replayed, conflicting-successor, and invalid-at-submission evidence |
| N5 — Both mobile products | Pending | Independently qualified iPhone/iOS and Android lifecycle/output paths, resource budgets, consent, and packaging |

The next engineering gate is **N2b: inventory a real owned output path before implementing an adapter**. The [N2b qualification record](n2b-lab-qualification-record.md) supplies the scope, required inventory, event distinctions, and falsifiable trials. Fill its actual host/device/route/capture fields before any hardware claim. Do not purchase or require customer hardware by assumption. Before adding any new OS or driver API, refresh research under the charter. Cleanup after closure must continue to release existing references without creating new mutating work.

The legacy optical remote mapper now reports a remote-button hypothesis as `NOT_EXECUTED` and requires review at every eligible confidence band; invalid confidence fails closed. An 11-case regression covers these proposal-only semantics. The mapper does not discover actual hardware capability, authenticate a command, invoke an adapter, or verify a physical result. It must not be used to infer current TV caption state from an unknown IR toggle.

N2b still requires available hardware and independent acquisition inventory. Refresh exact backend/driver/route questions before that physical implementation; no hardware purchase or native deployment follows from the C fixture. Keep real crash persistence and competing handoffs separate from deterministic in-memory sequencing.

Later work completes native protection events on both platforms, supported device capabilities and truthful UI, one qualified sound/caption path, manual priority and Undo & Teach, then measured pilots and release evidence. There is no selected customer hub requirement or store-readiness claim.

## Standing working rules

- Use small red-green increments, inspect current signatures, and apply guarded atomic edits. Phone commands remain one physical line.
- Failed pre-dispatch authorization must leave the actual mutating adapter uncalled. Preserve unknown outcomes and strictly newer evidence requirements.
- Before genuinely new substantive AQSS research, request the user's switch to **6 Astra Max** and wait for confirmation. Recovering existing research and implementing an already researched increment do not restart that warning.
- Optimize latency, battery, and bounded memory/storage within cryptographic, privacy, truthful-state, deterministic authorization, and platform constraints. Performance targets require measurements; test counts do not establish them.
