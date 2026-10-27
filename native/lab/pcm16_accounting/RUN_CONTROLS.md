# Scripted run admission, retry and cleanup

This extends the [accounting lab](README.md) with phone-independent implementation
of the [already reviewed ownership rules](../../../docs/mobile-output-backend-research-2026-10-27.md#proposed-ownership-and-stopping-rules).
`Pcm16RunOwner` drives a scripted backend. There is no AudioTrack/AAudio/iOS
binding, native output resource, application dependency or new installer.
Passing tests qualify this model's ordering only; they do not complete N2b.

## Explicit admission and one occupied slot

A start request needs a valid immutable plan and synthetic declarations of
foreground status, immediately granted focus, idle input and the same positive
route revision. Unknown, denied, delayed or mismatched declarations reject
without calling any backend method. These declarations are trusted lab inputs,
not observations, authentication, input leases or actual audio focus authority.
Actual app/resource coordination and native event collection remain pending.

The plan supplies every channel/count, attempt, clock, delay and trace parameter.
It selects no real sample rate, buffer, route, signal, volume or physical trial.
Malformed source, reused/non-increasing work labels, occupied slots, full history
or inadequate trace reservation also reject before acquisition. One backend
object is supplied by the driver and must not acquire a resource on construction.

The model retains at most two run histories. Tokens match by object identity;
numeric work/ordinal labels alone cannot authorize a task or notification. A
fresh explicit Start with a newer work label is possible only after the model's
prior slot is released and registry space remains. Histories are not evicted,
and old accepted prefixes/outcome uncertainty survive. A third run rejects.
This is a fixture bound, not a production journal or persistence solution.

## Externally driven worker and retry policy

There is at most one pending task or one entered call. `execute(task, tick)`
checks the exact current pending ticket before any clock comparison, invokes
one scripted backend method and records its actual return or ordinary exception.
It does not account that observation. `record(task, tick)` is a separate stage;
only it can advance the accepted sample prefix or progress cleanup. Duplicate,
old, foreign and reentrant execution/accounting cannot create another call.

The injected clock has one positive domain and nonnegative ticks; its unit is
unspecified. The exclusive deadline is fixed at Start. Ordinary task dispatch
and return accounting check the domain, nondecreasing value and deadline.
Different domains are never compared. A late or faulty accounting clock closes
new admission while the actual returned prefix is still recorded. No dispatch
time is invented as a call-return timestamp; traces retain only explicitly
supplied control observations. They do not measure native or acoustic latency.

Zero and valid partial progress retain the exact immutable suffix. A subsequent
write is issued once, with a positive explicit delay based on the last accounting
observation. Its ready time is capped at the original deadline using subtraction
before addition, so Long overflow cannot wrap or extend the run. An early task
delivery neither dispatches nor issues a replacement ticket. Repeated zero
reaches the configured limit of 1–8 writes and closes admission.

This is a policy model, not an OS scheduler, timer, thread, wakeup or real-time
deadline guarantee. The test driver delivers ticks/tasks and reports actual
observations. It must call `poll` to exercise a deadline when no work is queued.
A blocked native call cannot be cancelled by this model. Resource/latency/battery
budgets for actual threads and timer delivery remain unmeasured.

## Stopping, exceptions and cleanup ownership

Stop, focus loss/duck, foreground loss, route change, input-busy notification,
clock fault, deadline, exhausted attempts, invalid return or backend exception
closes admission. A queued write ticket is withdrawn immediately. An entered
call remains outstanding through its real return and explicit accounting, even
after a hold. Positive focus/foreground/route notifications never restart work.
The first stop reason stays fixed; later call results retain their own raw value
or exception flag. Exceptions retain no throwable/message or external data.

Cleanup is a scripted contract, not a declaration of any native API's semantics:

| Recorded state | Next permitted scripted cleanup |
| --- | --- |
| No acquisition entered | Cancel the reservation without any backend call |
| Acquisition succeeded, activation never entered | Release only |
| Activation entered, including an activation exception | Quiesce, then discard, then release |
| Entered or returned call still awaiting accounting | Wait; do not release the slot or dispatch another operation |
| Acquisition exception with uncertain allocation | Quarantine; no assumed handle or manufactured cleanup completion |
| Exception in any cleanup stage | Quarantine; do not run subsequent stages or free the slot |

Each cleanup stage has entry, return and accounting events. Even a successful
release return does not free the slot until that return is recorded. Cleanup
remains possible with an unavailable/wrong-domain clock: timing uncertainty
cannot become a reason to skip existing cleanup. Neither a timeout nor a
positive callback releases a pending or quarantined slot. There is no reset,
retry-cleanup or recovery API. An unhandled Throwable leaves an unreported
entered call outstanding rather than inventing its return.

The real backend review must independently choose valid cleanup operations,
resource handles and exception recovery. Model `RELEASED` means only that this
scripted sequence was accounted; it is not physical retirement, silence,
NOT_APPLIED, callback quiescence or successor readiness. Starting a new model
instance is fresh fixture storage, never a way to recover a quarantined resource
or resolve missing process history. Production readiness remains closed.

## Bounded records and evidence

Before acquisition, reserve all events for the plan's maximum writes, two
startup calls, three cleanup calls and three owner events. This needs
`3 * (maxAttempts + 5) + 3` slots: 42 at eight writes. Up to 64 may be configured;
no event is evicted. Cleanup and quarantine records stay available at capacity.
Each returned snapshot is an immutable copy. The underlying accounting trace
retains its independent 26-event limit and all raw count classifications.

Two histories bound the model-owned PCM payload to 16 KiB and run traces to
128 allocated event slots, plus the existing accounting records and bounded
pending/entered references. Driver/backend state, retained snapshots and payload
copies are external and require their own integration bounds. The stable model
and histories remain alive during stale deliveries. No native metadata is freed
and no producer-unregistration/quiescence contract is supplied.

The 31 added scenarios exercise failed admission, startup/cleanup ownership,
exact delayed suffix retries, configured attempt/deadline limits, both call
accounting windows, negative/invalid/exceptional results, injected clock faults,
overflow, interruption/positive events, foreign tickets, bounded history and
full trace capacity. They run with the original 18 accounting cases. The
tests-first revision `f04ff5f9fafe13744a5b3d1ad25e9a6b87649df2` is recorded in
[run 40599185852](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40599185852).
Exact implementation results and source identity belong to the associated
draft pull request. Actual phone inventory, adapter selection, real concurrency,
native timestamps, output observation and both mobile qualifications remain pending.
