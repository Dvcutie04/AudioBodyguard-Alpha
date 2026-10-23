# Input startup cleanup — 0.22

October 23, 2026. This reliability increment follows the 0.21 Insights entry.
It changes the shared iPhone microphone gate used by Voice check and Live sound
check. Android teardown behavior and both platforms' user flows are unchanged.

## Failure and existing research

The gate previously marked a session active only after its configuration closure
returned successfully. If configuration threw, release skipped deactivation and
made the gate available again. The production closure configures the app-wide
session category and then requests activation; it is not a transaction with an
application-controlled rollback.

The [existing iPhone ownership research](ios-microphone-lifecycle-2026-10-20.md)
already requires ownership through cleanup and sticky cleanup failure. The
existing [Apple activation/deactivation documentation](https://developer.apple.com/documentation/avfaudio/avaudiosession/setactive(_:options:))
was refreshed for this failure path. Apple documents activation failure under
higher-priority audio and a deactivation case that changes session state while
returning an error. The resulting application rule is conservative: a throwing
configuration closure does not prove that all session effects were undone.
This is an inference used for policy, not an observed iPhone activation fault.
No new OS API, recording backend or substantive platform subsystem is introduced.

## Resulting behavior

Record cleanup responsibility before invoking configuration. A thrown closure
retains that responsibility and rejects repeated activation with the same lease.
Only successful deactivation releases the reservation for a later explicit Start.
If deactivation throws, both tools remain blocked until the app process exits.
An acquired reservation that never entered configuration still releases without
touching the audio session. Missing, stale and foreign leases retain their
existing rejection behavior.

This does not report whether the microphone is physically active or stopped.
No timer, permission, persistence, automatic retry, input capture path or output
authority is added. Android already retains its meter lease until recorder
cleanup and blocks after speech cleanup failure; its production logic is retained.

## Test-first evidence

Tests-only source `a548033cb2c31247cdf60db6353bc2fe3c379fe8`, tree
`199f7ca50a25da56e143c20580b8d30955469499`, retained 0.21 production.
[Core run 39960771765](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39960771765),
Swift job `120437896457`, compiled then failed only the new configuration-effects
case: cleanup count was zero rather than one and the simulated change remained.
The suite executed 89 cases with two assertions failing in that one case.

The implementation retains the new regression and replaces the former
no-deactivation-on-throw expectation with sticky cleanup-failure assertions.
Successful cleanup, repeated-activation rejection, untouched reservations,
foreign/stale owners and both input tools' shared gate remain covered.
Exact final Swift/native run results, source tree and Android artifact identity
are recorded in [draft PR #54](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/54).

## Delivery boundary

The candidate uses Android code 22 / `0.22-input-startup-cleanup-live-input` and
Apple `0.22.0` / build 1. Android packaging advances the shared candidate identity;
the behavioral repair is iPhone-specific. Existing permission, lifecycle, photo,
recap, Insights and native-share regressions remain required on both platforms.
No native activation fault is injected into the delivered app or claimed as a
real handset observation. Signed iPhone installation, handset compatibility,
continuous protection, TV control and N2b–N5 remain unqualified.
