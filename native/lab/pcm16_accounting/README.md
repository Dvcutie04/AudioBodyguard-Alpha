# PCM16 write-accounting lab

This isolated Kotlin/JVM model implements the count, suffix and hold-accounting
part of the [mobile backend paper review](../../../docs/mobile-output-backend-research-2026-10-27.md).
It is not an Android module, an AudioTrack binding or an iOS implementation.
Neither mobile app depends on it. It opens no audio resource and runs no signal.
The actual phone report remains necessary before choosing an adapter.

Run with the repository's existing Gradle 8.13 / Java 17 toolchain:

```sh
gradle -p native/lab/pcm16_accounting test
```

The [dedicated workflow](../../../.github/workflows/pcm16-accounting.yml) runs
that command and retains JUnit receipts. There is no APK or app version bump
for this lab. The implementation uses Kotlin 2.1.0, matching the Android
source toolchain, without Android framework dependencies.

## Contract and bounds

One model copies one interleaved PCM16 source of 1–4096 samples. The 8192-byte
payload ceiling is a synthetic lab bound, not a device buffer, selected channel
layout, negotiated rate or recommended trial duration. A positive channel count
must divide the source length. Caller-provided work IDs are trusted fixture
labels, not authenticated run or cross-process identities.

`Pcm16Span.checked` rejects negative/empty/out-of-range or unaligned requests
before a driver can dispatch them. Its subtraction check avoids `offset + count`
overflow, and its byte quantities widen to Long before multiplying. Samples,
frames and bytes remain separate units. The model's source is copied once;
request payload access returns a copy, so a caller cannot rewrite a later suffix.

The scripted driver performs these separate stages:

1. `beginWrite()` checks admission, pending work, remaining samples and the
   fixed call limit, then records an entered call and returns its exact suffix.
2. `returned(ticket, rawValue)` reports an observed integer return. A positive
   aligned count within the request is an accepted prefix; zero is no progress.
   Every negative value is terminal and retains its raw integer. In particular,
   the model does not reinterpret Android-style integers as errno/EAGAIN.
   An oversized or unaligned count is invalid; no accepted count is invented.
3. `recordReturn(ticket)` accounts the result once. An accepted prefix advances
   the offset even if a hold arrived after entry. There is no second call while
   an entered/returned call still awaits its return/accounting.

`failed(ticket)` records the driver's observation that a call ended with an
exception. It retains no throwable or exception text. It is not a timeout or
cancellation API. If a call has not returned, it stays outstanding; the driver
must not manufacture a completion to release it. This model cannot authenticate
the driver's observations or prevent code from bypassing it.

`hold()` closes future admission. `acknowledgeHold()` only acknowledges this
model's completed call accounting; it waits for an entered call's return and
recording. It says nothing about native pause/flush/release, buffered effects,
callback quiescence, silence, physical retirement or successor readiness.
The first inhibition reason remains fixed while each later observed return
retains its own classification. Exact object identity rejects stale/foreign
tickets even when their numeric work/call labels match.

At most eight caller-driven calls can start. There is no scheduler, busy loop,
wall-clock deadline or automatic retry. Each call reserves three events; two
additional slots are reserved for the one hold and its acknowledgement. The
26-event trace never evicts history. Returned trace snapshots are immutable
copies. Payload copies and snapshots retained by an external driver are outside
the per-model storage bound and must be bounded by any future integration.

This is a single-thread fixture. Its API calls and the scripted driver run
serially; it supplies no synchronization, independent admission thread, native
cleanup, focus/route callbacks, resource lease, process persistence or clock
mapping. Trace sequence numbers express software order only. A future adapter
still needs the full separately reviewed ownership and scheduling contract.

## Checks and evidence limits

The cases cover checked unit conversion and overflow; malformed admission;
immutable source/suffix copies; multichannel partial progress; zero followed by
an explicit retry or hold; negative and invalid results; both in-flight hold
windows; stale/foreign/repeated tickets; observed exception accounting; sticky
first inhibition; full trace capacity; and finite repeated-zero attempts.

After the first call enters, `outcomeUnknown` remains true, including after zero,
error, completion or acknowledged hold. Before any entry it only describes the
absence of a modelled call, not physical NOT_APPLIED evidence. Test results are
synthetic accounting evidence. They cannot establish speaker output, containment,
latency, TV control or either mobile product's qualification. Production gates
and N2b–N5 remain unchanged.

## Verification provenance

The tests-first revision `35876410ff15f0b276df097454d389e7adf4d3bb`
failed at `compileTestKotlin` in
[run 40597544817](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40597544817)
because the model's types did not yet exist. Java/Gradle setup succeeded.
The implementation suite contains 18 test cases. Exact implementation run,
JUnit results and source identity are recorded in
[draft PR #73](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/73).
