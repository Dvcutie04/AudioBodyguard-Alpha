# Repository bug audit — September 28–29, 2026

## Scope and outcome

Audited the latest AudioBodyguard-Alpha working tree at `2c591c369809ac819d4e8755a9cf1b7eb309f140`, including the unmerged options, tutorial, themed interface and launch-artwork work in PR #28. This is a repository audit of that development tree, not a claim that these changes were already on `main`.

Ten confirmed bug areas were corrected in the reference Python implementation. New regression cases were run before the corresponding fixes to reproduce the failures. The final local suite has **1,786 passing tests and 14 passing subtests**, compared with **1,709 tests and 14 subtests** at baseline: **77 additional collected regression cases**. No existing failing assertion was removed to achieve this result.

The iOS and Android shells remain read-only simulations. The production factory rejects construction and `EndpointHandoffBarrier.is_ready()` remains closed. No native control path, recording permission, service enrollment, subscription or physical actuation was introduced.

## Confirmed findings and corrections

Severity is relative to the intended safety boundary in the reference code; these findings do not establish exploitation or exposure in a deployed app.

| ID | Priority | Finding and impact | Correction and regression evidence |
|---|---|---|---|
| A01 | High | `ReplayWindow` admitted the same sequence repeatedly while it remained inside the window. Two duplicate class definitions also obscured which implementation ran. | One implementation, bounded bitmap, locked update, exact nonnegative integer sequence validation. Tests cover duplicate and out-of-order sequences, expired entries, invalid window sizes and a sequence jump of one trillion. `tests/test_replay_window.py` |
| A02 | High | The ordinary Intent Firewall did not independently verify the capability lease signature, accepted nonfinite validity times, future intents and exact-expiry requests, and did not bind protocol versions. The controller-bound firewall also accepted nonfinite capability windows and protocol mismatches. Malformed HMAC signatures could raise errors. | Validate the lease and issuer, finite validity windows, start/expiry boundaries, containment within the lease and protocol equality before consuming a nonce. Lock ordinary nonce admission. Reject malformed/non-ASCII signatures. `tests/test_intent_firewall_crypto.py`, `tests/test_controller_bound_intent_firewall.py` |
| A03 | High | Nonfinite deadlines and freshness budgets bypassed comparison-based preconditions or caused type errors. | Reject malformed, nonfinite, negative and boolean numeric controls before dispatch. Keep the existing zero-value disabled-budget convention for compatibility. Regressions assert **zero adapter calls**. `tests/test_physical_commit_gate_behavior.py` |
| A04 | High | Boolean coercion made the string `"false"` turn power or mute on. Legacy volume values could be invalid or nonfinite; input/channel values were silently stringified. Nonfinite attenuation parameters could reach a mock adapter. | Validate exact boolean types, 0–100 volume, nonempty input/channel strings, expected keys and JSON-compatible finite parameters. All malformed-control regressions assert **zero adapter calls**. `tests/test_repository_audit_boundaries.py` |
| A05 | High | General transport errors, task cancellation, failed/mismatched receipts and failed post-state observations could leave the protection supervisor ACTIVE after submission. Timeout already recorded uncertainty; adjacent failure paths did not. | Record the unresolved transaction with authorization/capability lineage and interrupt the supervisor to UNKNOWN_PHYSICAL_STATE. Preserve cancellation propagation. Apply the correction to current commit and legacy compatibility paths. Tests simulate an applied action followed by lost completion, verify persisted lineage and block a follow-up call. `tests/test_repository_audit_boundaries.py` |
| A06 | Medium | The feedback server checked profile restrictions during batch sync but bypassed them for direct feedback and page rendering. Server construction accepted a missing profile. | Apply the same profile binding to direct writes and render, and require a valid bound profile before creating the server store. Offline/unbound local rendering remains supported. This is profile scoping, not a replacement for authentication. `tests/test_tv_selection_web.py` |
| A07 | Medium | Identifiers were HTML-escaped in visible text but directly JSON-embedded inside an inline script. An identifier containing `</script>` could break out of the script element. | Escape HTML-sensitive characters in script JSON independently of HTML text escaping. A hostile identifier cannot introduce an extra script element. `tests/test_tv_selection_web.py` |
| A08 | Medium | Sensor quality checks could report healthy for NaN or infinite energy, or throw on malformed data. | Reject malformed/nonfinite/negative statistics, out-of-range clipping and nonboolean fault flags. These checks establish input validity, not microphone qualification. `tests/test_repository_audit_boundaries.py` |
| A09 | Medium | Model-cache memory accounting accepted NaN, infinity, booleans and other invalid budget/accounting values. NaN could poison resident-memory totals and budget enforcement. | Require nonnegative integer megabytes; only an explicitly unlimited overall budget accepts `None`. Reject invalid registration before changing cache state. `tests/test_edge_model_cache.py` |
| A10 | Medium, dormant | The unused legacy `CausalFreshnessValidator` returned fresh for every input despite containing no implementation. No live callers were found in the repository. | Preserve imports but make this documented placeholder always fail closed. Tests include empty, nonfinite and forged input. Actual causal validation remains a separate research/qualification task. `tests/test_repository_audit_boundaries.py` |

A stale-world-state test previously moved the shared wall clock to a hard-coded September 3 date while creating a lease at the current time. Its fixture now places the stale observation relative to that lease. It still asserts the same stale-state rejection and zero adapter calls, without accidentally testing a future lease instead.

## Coverage and verification

| Area | Work performed / result |
|---|---|
| Python source | Parsed and compiled all 436 tracked/new Python sources after changes; checked duplicate top-level definitions and internal imports. No remaining parse error or duplicate top-level definition was reported. |
| Python behavior | Repository-wide pytest suite, including Hypothesis/property cases, safety boundaries, persistence/recovery, native content contracts and negative adapter-call assertions: **1,786 passed; 14 subtests passed**. |
| Structured resources | Parsed 13 JSON files and 7 XML/storyboard/scheme files. All succeeded. |
| Generated native content | Native feedback, interface/contrast and tutorial generators all pass `--check`. |
| C11 owned-output lab | **45 deterministic cases** passed normally and with address/undefined-behavior sanitizers. Local LeakSanitizer cannot operate under this execution environment's tracing restrictions, so the local sanitizer pass used `ASAN_OPTIONS=detect_leaks=0`. Hosted CI retains its unmodified full sanitizer command. |
| Native apps | Inspected lifecycle/hint handling, read-only state, options/tutorial navigation, shared contracts, theme and startup configuration. No new native-source correction was made in this audit. Swift/Xcode/Android SDK execution requires hosted runners here. The audit PR checks provide the new hosted results; no physical-device execution is claimed. |
| Workflow/build scripts | Reviewed CI, simulator smoke and unsigned-device preflight workflows; shell syntax and `git diff --check` pass. |
| Legacy integrations | Traced quarantined TV-controller entry points and reference-only dispatch helpers. Unsafe historical driver content remains quarantined; formatting a command or returning a reference status is not hardware evidence. |

The new report and changes are proposed on an audit branch. A PR against `main` includes the earlier unmerged PR #28 stack so the existing native CI gates can run. Review the audit delta relative to `2c591c3` to isolate these fixes. No merge has been performed.

## Research charter: evidence and design choice

Threat model: malformed or replayed inputs, a valid signer supplying invalid values, cross-profile web requests, HTML/script boundary confusion and lost completion after a possible physical submission. The immediate measurable requirements are deterministic rejection before dispatch, no profile mutation on rejection, once-only sequence admission and persisted uncertainty after ambiguous completion.

| Primary source | What it establishes | Authority / recency / reproducibility / relevance / limits |
|---|---|---|
| [RFC 6479](https://www.rfc-editor.org/rfc/rfc6479.html) | Sliding-window anti-replay tracking needs received-sequence membership, not just a high-water mark. | IETF informational specification, 2012; stable mechanism; algorithmically reproducible; high relevance. AQSS's compact bitmap is its own implementation, not an IPsec compliance claim. |
| [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) | JSON numbers exclude NaN and infinity. | IETF standard, 2017; precise/reproducible data boundary; high relevance to serialized intent parameters. Does not by itself authorize a finite value. |
| [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Authorization must be applied consistently to requests and tested at the relevant boundary. | Maintained primary security guidance, retrieved September 28–29, 2026; high relevance, reproducible here via cross-profile tests. Guidance is not a formal proof. |
| [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) | Output encoding must match the output context; HTML and JavaScript contexts differ. | Maintained primary guidance, retrieved September 29, 2026; high relevance; reproduced with a script-closing identifier. Does not certify the entire web service. |
| [Python asyncio task cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation) | Cancellation raises `CancelledError`, which derives from `BaseException`, and should normally propagate after cleanup. | Primary implementation documentation, retrieved September 29, 2026; high reproducibility and direct relevance. AQSS decides what recovery evidence cleanup must preserve. |

Selected synthesis: retain the existing authority and physical-commit architecture; combine strict boundary validation, bounded duplicate tracking and the existing durable recovery/supervisor mechanism. This is a narrow repair, not a new background engine.

- **Source-established:** comparison/encoding/cancellation semantics and standard anti-replay requirements.
- **AQSS inference:** if completion or verification is lost after submission, unchanged physical state cannot be assumed; automation must be gated pending qualified recovery.
- **AQSS-specific integration:** bind the recovery record to the same transaction, intent, target/pre-state, authorization and capability lineage already used by the bridge.
- **Optimization:** no new polling, radio activity or continuous task. Replay storage is bounded by a configured window capped at 65,536 bits plus object overhead. New validation work is local; recovery writes occur on failure. No latency, battery or hardware measurement gain is claimed.
- **Empirical debt:** persistent crash/power-loss behavior on target hardware, malicious-native-adapter containment, on-phone latency/battery measurements and independent output observation still need qualification.

Implementation stages completed: reproduce failures; fix minimal deterministic contracts; run focused suites; run full regressions and generated-content/C checks; submit the reviewable change set for hosted platform gates.

## Remaining limits and follow-up work

1. A passing audit is not proof that every possible bug is absent. Manual review concentrated on trust, actuation, persistence, native lifecycle and integration boundaries; synthetic/research modules received structural and existing-test coverage, not a new scientific validation of every model.
2. Physical output, protection, background operation, signed iPhone installation and independent observation remain unqualified. Native simulator checks cannot clear those gates.
3. The ordinary nonce set is process-local and has no durable retention policy. Endpoint transaction/fence/finality machinery remains necessary; this audit does not turn the ordinary firewall into a production replay database.
4. The local feedback server remains a development utility. Profile binding does not provide remote-client authentication, TLS or a complete hostile-network security design. Those require a dedicated research and deployment review before exposing the service beyond its trusted local setting.
5. Dependency version ranges are broad, and this pass is not a comprehensive third-party vulnerability scan. Reproducible dependency locking and supply-chain review should be a separate, measured change.
6. Actual VoiceOver/TalkBack use, device-specific launch rendering, long-running lifecycle behavior and physical interruption/audio-route tests still need installed-device testing.
