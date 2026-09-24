# AQSS development roadmap

Checkpoint: September 24, 2026. Continue from the restored a-Shell baseline and the existing native endpoint qualification research. iPhone/iOS and Android remain equal product targets.

**INFERENCE IS NOT REALITY. AI proposes. Policy authorizes. Physical Commit verifies.**

## Current checkpoint

The restoration merged into `main`, followed by the deterministic test-clock correction in [PR #3](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/3). Its [main verification run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/36070023701) passed 1,625 Python tests plus Swift and Android conformance. The [source manifest](a-shell-sync-manifest.json) accounts for the 441 exported a-Shell paths; additions in this development increment are outside that historical snapshot.

N1 now adds a bounded, explicitly unqualified fake endpoint and eight behavioral tests. The local Python 3.12 suite passed **1,633 tests**, including **27** focused native-contract, work-ordering, and handoff checks. These counts overlap; do not sum them. [Hosted CI](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/ci.yml) records the result for each published revision.

The production factory guard and `EndpointHandoffBarrier.is_ready()` remain closed. No physical device was actuated by this increment.

## N0 inventory

| Target | Inspected repository configuration | Evidence boundary |
| --- | --- | --- |
| Python reference | `pytest.ini` collects `src` and `tests`; CI uses Python 3.13 | Local Python 3.12 and hosted Python regression execution |
| iPhone/iOS contract | `native/ios/Package.swift`: Swift tools 5.9, iOS 15 declaration, library and test targets | Hosted macOS Swift package tests; no installed iPhone application or measured output path |
| Android contract | `native/android/build.gradle.kts`: Android library, minSdk 26, compileSdk 35, Java 17 | Hosted Gradle unit tests; no application targetSdk, service, or measured phone output established |
| Shared endpoint vectors | `contracts/endpoint_native_boundary_v1.json` and its Markdown contract | 18 synthetic vectors consumed by Python, Swift, and Kotlin |
| Endpoint handoff | `src/device_fabric/endpoint_handoff_barrier.py`: schema-3 resource holds and pinned verifier identity | Reference ordering and admission inhibition; no qualified native retirement certificate |

These are inspected build settings, not new supported-device or release recommendations.

## N1 work-ordering increment

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

Accepted, published, submitted, simulated-applied, simulated-observed, and native-settled events are distinct. A submitted frame may still apply after admission closes; the fake deliberately does not equate a hold with cancellation. Registering a child precedes settling its parent. Each accepted item emits at most six events and one generation-close event is allowed; repeated rejected operations append nothing. Retention is bounded by the configured work limit, and the fake never evicts unresolved records.

The fake returns fresh snapshots and immutable trace events. Its native qualification, authorized evidence, authenticated history, route enforcement, native cut, and production readiness remain false. A fully settled simulated trace still fails the existing shared eligibility oracle. Explicitly injected settlement and observation are test controls, not evidence from an OS, driver, speaker, or microphone.

Red-green evidence: the new tests first failed collection because the fake module did not exist; after the minimal test-only implementation, the focused gate and full suite passed. All original assertions and production modules were preserved, all 441 historical manifest paths retained their recorded status, and no `.py.tmp` staging files remained.

## Remaining native gates

The sequence follows `AQSS_Native_Endpoint_Qualification_Research_2026-09-24.md` and the master continuation handoff. That research already authorizes N0/N1 implementation; it does not qualify a real backend.

| Stage | Status and next work | Exit gate |
| --- | --- | --- |
| N0 — Inventory | Repository/native contract inventory complete; exact physical hardware and measurement setup still unselected | Pin real build hosts and device/route details before a hardware experiment |
| N1 — Shared conformance | Shared 18-vector contract and first sequenced work simulation implemented | Continue sequencing runtime restart, delayed route notification, and invalidation between activation and submission; keep production readiness unavailable |
| N2 — Owned native trace harness | Pending | Bounded gain path, explicit callback ownership/lifetime, one inspected real backend candidate, and no raw-handle bypass |
| N3 — Exact output qualification | Pending | Named hardware/driver/route and reproducible output measurement, including residual buffered work |
| N4 — Conditional evidence and activation | Pending, dependent on N3 | Authenticated native retirement evidence; reject stale, replayed, conflicting-successor, and invalid-at-submission evidence |
| N5 — Both mobile products | Pending | Independently qualified iPhone/iOS and Android lifecycle/output paths, resource budgets, consent, and packaging |

The next small increment is **N1 context invalidation sequencing** using the already researched route, runtime, and final-submission counterexamples. Keep it test-only. The current work fake does not simulate process persistence, route atomicity, clocks, signing, or competing handoffs.

Later work completes native protection events on both platforms, supported device capabilities and truthful UI, one qualified sound/caption path, manual priority and Undo & Teach, then measured pilots and release evidence. There is no selected customer hub requirement or store-readiness claim.

## Standing working rules

- Use small red-green increments, inspect current signatures, and apply guarded atomic edits. Phone commands remain one physical line.
- Failed pre-dispatch authorization must leave the actual mutating adapter uncalled. Preserve unknown outcomes and strictly newer evidence requirements.
- Before genuinely new substantive AQSS research, request the user's switch to **6 Astra Max** and wait for confirmation. Recovering existing research and implementing an already researched increment do not restart that warning.
- Optimize latency, battery, and bounded memory/storage within cryptographic, privacy, truthful-state, deterministic authorization, and platform constraints. Performance targets require measurements; test counts do not establish them.
