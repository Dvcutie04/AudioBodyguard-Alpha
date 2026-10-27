# Queued callbacks and retained children

This implements the callback/child portion of the existing
[C fixture contract](../owned_output/README.md#callback-lifetime-and-five-deterministic-cases)
and [mobile ownership review](../../../docs/mobile-output-backend-research-2026-10-27.md#proposed-ownership-and-stopping-rules)
inside the isolated Kotlin lab. It introduces no OS API, selected playback
backend, real producer, thread, mobile dependency or installer. Actual native
registration, synchronization and quiescence remain separate obligations.

## One stable registry per run

One run can attach one `LabCallbackFamily` with one borrowed metadata object.
It cannot replace that family, including after metadata transfer. Every scripted
producer calls `queue()` before scheduling a callback. There are eight callback
slots and eight retained-child slots for the family's entire lifetime; no slot
is reused. Overflow closes the owner's admission without discarding existing
references. Tokens bind exact run and ticket object identity. Matching numeric
labels, forged values and tickets from another family cannot consume a reference.
These are fixture identities, not authentication or cross-process authority.

Queueing retains data even with zero active callbacks. `deliver()` accepts each
queued ticket once. While admission is open, it marks the callback active before
passing metadata to the body and records the body's exit in `finally`. A body
failure closes admission while the active reference still exists, records an
exception flag and propagates the failure; it retains no throwable or message.
Nested callbacks each retain their own active reference.

After admission closes, a queued delivery consumes only its queued reference.
It does not read/pass metadata or invoke the body. Stale, consumed, active,
foreign or malformed tickets reject without changing another reference. A
timeout, unregister request or positive lifecycle notification cannot manufacture
delivery or drain a reference. The real producer must eventually supply an
independently reviewed delivery/cancellation contract; no forced drain is added.

## Children and the final cleanup gate

Only an active current callback under open admission can retain a child. Register
that reference before handing metadata to child work. A child may outlive its
parent and still obtain its retained data after a hold. It must finish its last
use before `releaseChild()`. Repeated, foreign or forged release cannot consume
another child's reference. No grandchildren or untracked references are allowed.
The lab cannot prevent arbitrary caller code from violating that protocol.

Child release and cleanup-only callback delivery perform bookkeeping only. They
do not call the backend, queue a task, restart output or free the occupied slot.
When final cleanup is waiting for references, the worker must explicitly call
`resumeCleanup(run)` after observing their drain. The owner still requires its
entered call's actual return and separate accounting before that check can progress.

The scripted owner may perform quiesce/discard while data stays retained. Final
release waits until queued, active and retained-child counts are all zero. A
reservation with no entered acquisition also waits for those references before
becoming free. The actual native backend must separately establish which cleanup
operations are valid and who may call them; this model supplies no such guarantee.

`takeMetadata()` transfers the borrowed object only after all references drain
and the owner's final release/reservation cleanup is recorded. A release return
still awaiting accounting is insufficient. A quarantined resource cannot transfer
metadata even at zero references. Stable registry/run contexts and consumed
tickets remain alive for later rejection. Transfer changes no accepted prefix,
physical uncertainty, production gate or successor qualification.

## Bounds and evidence limits

The callback trace has 42 reserved events: up to 24 for eight queue/entry/exit
triples, 16 child retain/release events and two attachment/transfer events.
Cleanup-only delivery needs fewer events. Invalid/replayed calls append nothing;
history is never evicted. Snapshots contain immutable record copies and counts,
not the metadata object. The existing owner and accounting trace bounds stay
unchanged, including cleanup capacity with all eight writes used.

There are at most two families across the owner's two retained run histories.
The PCM payload ceiling remains 16 KiB per owner. Metadata has a two-object
reference bound, not a byte budget; the driver must bound its actual contents.
Driver/backend state and retained snapshot/payload copies remain outside these
local bounds. This is serial code, not a synchronized native lifetime boundary.
Constructing a new owner is fresh fixture storage, not recovery or retirement.

The JVM tests transfer a managed object and mark a test sentinel unusable before
replaying stale deliveries. They demonstrate that a stale body was not invoked;
they do not demonstrate native `free`, garbage collection, OS producer quiescence,
physical silence or authentic retirement evidence. The portable C fixture's
separate raw-allocation tests remain unchanged.

## Verification scope

Nineteen cases cover queued/active/nested references, child last use, exact
ticket lineage, callback/child exhaustion, full traces, propagated body failures,
quarantine, cleanup accounting, stale successors and a callback during an
entered write whose return still needs recording. They run with the existing
50 cases, including the 108-scenario interruption sweep.

The initial 18-case tests-first revision
`f34b1320319c9dbc1aa1fe9a9fa3198257f7f99f` is recorded in
[run 40601021504](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40601021504).
The combined in-flight-write case was subsequently added. The associated draft
pull request records exact implementation results and source identity. Android
remains 0.35/build 38 and iPhone/iPad remains 0.34.0; actual inventory, adapter
selection, physical trials and N2b–N5 remain pending.
