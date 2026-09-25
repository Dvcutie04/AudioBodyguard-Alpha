# AQSS development roadmap

Checkpoint: September 25, 2026. Continue from the restored a-Shell baseline and the existing native endpoint qualification research. iPhone/iOS and Android remain equal product targets.

**INFERENCE IS NOT REALITY. AI proposes. Policy authorizes. Physical Commit verifies.**

## Current checkpoint

The restoration merged into `main`, followed by the deterministic test-clock correction in [PR #3](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/3). Its [main verification run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36070023701) passed 1,625 Python tests plus Swift and Android conformance. The [source manifest](a-shell-sync-manifest.json) accounts for the 441 exported a-Shell paths; additions in this development increment are outside that historical snapshot.

N1 now includes a bounded, explicitly unqualified fake endpoint with eight work-ordering and eight context-invalidation behavioral cases. The local Python 3.12 suite passed **1,641 tests**, including **35** focused native-contract, work-ordering, context, and handoff checks. These counts overlap; do not sum them. [Hosted CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) records the result for each published revision.

The production factory guard and `EndpointHandoffBarrier.is_ready()` remain closed. No physical device was actuated by this increment.

N2a now compiles a separate C11 lab with **35 deterministic cases**: six owner, five callback, four child, six acknowledgement, five retirement, and nine retry/invalidation cases. These are additional native test cases, not part of the 1,641-test Python count. Its scripted backend exercises no audio API or hardware. The [lab contract](../native/lab/owned_output/README.md) defines the call phases, bounded registries, identity/deadline matching, retry/fault rules, and remaining ownership debt; hosted CI has a separate native-lab job.

The user verified the separate iPhone a-Shell clone at `38d273e1abec4b979950290ed1bac8cf640a8161`: generated contracts current, **1,641 passed with the existing dateutil warning in 7.50s**, and empty `lg2 status -s` output. This is the phone baseline before the retry/invalidation increment below; it is not evidence of phone execution of later changes or of the compiled C cases.

## N0 inventory

| Target | Inspected repository configuration | Evidence boundary |
| --- | --- | --- |
| Python reference | `pytest.ini` collects `src` and `tests`; CI uses Python 3.13 | Local Python 3.12 and hosted Python regression execution |
| iPhone/iOS contract | `native/ios/Package.swift`: Swift tools 5.9, iOS 15 declaration, library and test targets | Hosted macOS Swift package tests; no installed iPhone application or measured output path |
| Android contract | `native/android/build.gradle.kts`: Android library, minSdk 26, compileSdk 35, Java 17 | Hosted Gradle unit tests; no application targetSdk, service, or measured phone output established |
| Shared endpoint vectors | `contracts/endpoint_native_boundary_v1.json` and its Markdown contract | 18 synthetic vectors consumed by Python, Swift, and Kotlin |
| Endpoint handoff | `src/device_fabric/endpoint_handoff_barrier.py`: schema-3 resource holds and pinned verifier identity | Reference ordering and admission inhibition; no qualified native retirement certificate |
| Owned-output lab | `native/lab/owned_output`: standalone C11 owner, callback/child context, hold matching, retirement pool, retry/invalidation, and scripted backends | 35 software cases and warning-clean compiler gate; no ALSA SDK, device, native application, or physical qualification |

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

## Remaining native gates

The sequence follows the native qualification brief, `AQSS_N2_Owned_Output_Lab_Research_2026-09-24.md` with its September 25 ownership continuation, and the master handoff. The bounded N2a research authorizes the implementation steps below; it does not qualify a real backend.

| Stage | Status and next work | Exit gate |
| --- | --- | --- |
| N0 — Inventory | Repository/native contract inventory complete; exact physical hardware and measurement setup still unselected | Pin real build hosts and device/route details before a hardware experiment |
| N1 — Shared conformance | Shared 18-vector contract, bounded work sequencing, and test-only context invalidation implemented | Preserve the unresolved native and persistence questions; keep production readiness unavailable |
| N2a — Portable owned-output lab | Partial-transfer/hold accounting, callback/child lifetime, scoped acknowledgement matching, bounded metadata retirement, scripted zero/EAGAIN retries, and runtime invalidation implemented | Continue exact gain arithmetic, format validation, and bounded trace detail; real backend-specific recovery and scheduling belong to N2b |
| N2b — Real owned output | Pending; Linux/ALSA is the researched first lab candidate | Inventory available hardware, exact driver/route/format, independent capture, and instrumented native calls before physical experiments |
| N3 — Exact output qualification | Pending | Named hardware/driver/route and reproducible output measurement, including residual buffered work |
| N4 — Conditional evidence and activation | Pending, dependent on N3 | Authenticated native retirement evidence; reject stale, replayed, conflicting-successor, and invalid-at-submission evidence |
| N5 — Both mobile products | Pending | Independently qualified iPhone/iOS and Android lifecycle/output paths, resource budgets, consent, and packaging |

The next small increment is **exact attenuation arithmetic and format validation**. Define the supported signed-16-bit format, range-checked integer gain, rounding, and intermediate width before applying gain to immutable work; preserve the original context of an already accepted prefix. These bounded N2a obligations are already researched. New native API, driver, real synchronization, or physical experiments still require the corresponding research review. Cleanup after closure must continue to release existing references without creating new mutating work.

N2b still requires available hardware and independent acquisition inventory. Refresh exact backend/driver/route questions before that physical implementation; no hardware purchase or native deployment follows from the C fixture. Keep real crash persistence and competing handoffs separate from deterministic in-memory sequencing.

Later work completes native protection events on both platforms, supported device capabilities and truthful UI, one qualified sound/caption path, manual priority and Undo & Teach, then measured pilots and release evidence. There is no selected customer hub requirement or store-readiness claim.

## Standing working rules

- Use small red-green increments, inspect current signatures, and apply guarded atomic edits. Phone commands remain one physical line.
- Failed pre-dispatch authorization must leave the actual mutating adapter uncalled. Preserve unknown outcomes and strictly newer evidence requirements.
- Before genuinely new substantive AQSS research, request the user's switch to **6 Astra Max** and wait for confirmation. Recovering existing research and implementing an already researched increment do not restart that warning.
- Optimize latency, battery, and bounded memory/storage within cryptographic, privacy, truthful-state, deterministic authorization, and platform constraints. Performance targets require measurements; test counts do not establish them.
