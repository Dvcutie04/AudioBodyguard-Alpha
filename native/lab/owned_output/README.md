# N2a owned-output lab

This C11 harness implements portable native increments from the September 24–25
N2 partial-write and ownership research. It links only to scripted test backends
and callback bodies. It opens no audio device and is not linked into the Python,
Swift, or Android production paths.

## Run

From the repository root on a host with a C11 compiler and a POSIX shell:

```sh
sh native/lab/owned_output/run_tests.sh
```

With GCC or another compiler supporting AddressSanitizer and UBSan:

```sh
AQSS_LAB_SANITIZE=1 sh native/lab/owned_output/run_tests.sh
```

`CC` may select the compiler executable. The runner treats warnings as errors,
stops on compilation/test failure, and places generated files under ignored
`build/`. No Python dependency, ALSA SDK, or hardware is required. These native
checks are separate from pytest; the a-Shell Python command does not run them.

## Owner contract and six deterministic cases

One owner borrows one immutable mono S16 block with a nonzero work ID. A single
test thread calls the API. The owner, source array, and backend context remain
alive for the whole test. Each operation checks its local admission/phase before
calling the scripted backend. A positive return advances exactly the accepted
prefix; offset and remaining length travel together.

| Case | Tested result |
| --- | --- |
| Partial transfer, acknowledged hold, suffix retry | Three of eight frames remain accepted/possibly effective; retry makes no second backend call and changes no trace entry |
| Partial transfer without hold | Both calls copy the exact original eight frames, without duplicating the prefix; transfer completion still leaves physical outcome unknown |
| Hold requested inside an entered call | Reentrant submission, premature recording, and acknowledgement reject; the call may still return an accepted prefix |
| Hold requested after return, before accounting | Admission closes immediately, but acknowledgement waits for explicit return recording |
| Trace capacity exhausted | Eight calls retain their 24 records; the ninth cannot dispatch; two reserved hold records allow inhibition and acknowledgement without eviction |
| Negative or oversized backend result | Previously accepted prefix survives; the result is recorded, subsequent calls are inhibited, and physical outcome stays unknown |

Each call exposes `CALL_ENTERED`, `CALL_RETURNED`, and `RETURN_RECORDED`.
`aqss_lab_submit()` returning true means a backend invocation occurred; inspect
and record its separate result. `aqss_lab_record_return()` returning true means
accounting occurred, including an invalid result. Neither means playback or
physical verification succeeded.

A hold request closes admission. Acknowledgement is idempotent and only possible
after any entered call has returned **and its result has been recorded**. The
trace is in-memory instrumentation, not a durable journal. It has room for at
most eight calls and one hold; no reset, release, successor, or eviction API
exists. Initialization is for fresh fixture storage, not revival of a held
owner. Trace exhaustion and invalid returns inhibit further calls.

The first regression failed at `backend.calls == 1` when the owner did not check
closed admission on retry. Adding that check made it and the positive progress
case pass. The remaining checks exercise the call-accounting and bounded-trace
obligations. They are six C test cases, not six additional Python tests.

## Callback lifetime and five deterministic cases

`callbacks.c` adds one bounded scripted callback family attached to a live owner.
Its delivery context and owner remain alive through all deliveries and replays.
Each value ticket contains the context identity and a sequence; it never points
into reclaimable metadata. There are eight slots, issued once each with no reuse.
Every scripted producer must acquire a ticket before scheduling a delivery.

Queueing takes a reference even when no callback is active. Delivery moves that
reference into the active state before entering a body, then consumes it on
return. Once the owner closes admission, a queued delivery only consumes its
reference for cleanup; it does not access metadata or invoke the body. Invalid,
foreign, active, or consumed tickets cannot consume another queued reference.

`aqss_lab_take_callback_metadata()` transfers the borrowed metadata back to the
caller only after the owner acknowledges its cut and queued, active, and retained
child counts reach zero. The caller can then free the allocation. The stable context
and consumed slots remain valid so a stale replay can reject before accessing
freed storage. There is no API to reclaim or reuse that delivery context.

| Case | Tested result |
| --- | --- |
| Queued delivery with zero active callbacks | Metadata stays retained after the hold; stale delivery consumes the queue reference without running the body; a replay after actual `free()` rejects |
| Live callback and replay | The body reads the expected work metadata once; metadata remains retained until hold acknowledgement; replay cannot rerun the body |
| Active callback requests a hold | A nested reclamation attempt fails until the body returns; reentrant replay and new acquisition also reject |
| Foreign or invalid ticket | The valid queued reference remains retained; zero, unissued, and out-of-range sequences do not index or consume it |
| Callback and owner-trace capacity | The ninth ticket inhibits new acquisition; all eight cleanup deliveries remain available with a full owner trace; history and physical uncertainty survive |

The first callback regression failed because an active-count-only check released
metadata with one queued reference. Adding the queued-count check made it pass.
The tests allocate real heap metadata, return it through the gate, free it, and
attempt stale delivery under the same normal and sanitizer runner. The five
callback cases and six owner cases remain unchanged by the child increment below.

The context's closed acquisition and complete ticket registry cover only this
scripted, single-thread family. They are not an OS callback-quiescence contract.
Callback bodies must not free metadata or pass out an unregistered reference.
Context recycling, cross-runtime identity, actual producers, and native shutdown
evidence remain separate obligations. Visible struct fields and ticket values
are trusted lab inputs, not cryptographic authority.

## Retained children and four deterministic cases

An active callback may call `aqss_lab_retain_child()` before handing its metadata
pointer to a child. The reference binds the stable context, a child sequence, and
the parent callback sequence. Eight child slots are available for the entire
context lifetime; they are never reused. A queued or returned parent, invalid
ticket, or closed admission cannot acquire a child reference. Exhaustion closes
owner admission while preserving all existing references.

A retained child keeps metadata alive after its parent returns. Each child must
finish its last pointer access before `aqss_lab_release_child()`. Release remains
available after a hold and only changes reference bookkeeping: it invokes no
callback, submits no output, and cannot reopen admission. Invalid or repeated
release cannot consume another child. This API does not schedule child work or
allow children to register grandchildren.

| Case | Tested result |
| --- | --- |
| Child outlives its parent | Zero queued/active callbacks does not permit reclamation; a held child still reads live metadata; release allows actual `free()` while the accepted prefix and unknown outcome survive |
| Acquisition around a hold | Queued, foreign, and invalid parents reject; an active parent cannot retain after closure; a queued peer continues to retain metadata after the child releases |
| Invalid and repeated release | Foreign, out-of-range, and mismatched-parent references leave both children intact; releasing one twice cannot release the other; replay after actual `free()` rejects |
| Child and owner-trace capacity | The ninth child closes admission; all eight releases remain available with a full owner trace; cleanup preserves history and makes no additional backend call |

The first child regression compiled and failed at the reclamation assertion:
the queued/active gate returned metadata while one child was still retained.
Adding the retained-child count to that gate made it pass.
The child checkpoint had **15 native cases: six owner, five callback, and four
child cases**. The increments below bring the current total to **26 cases in
five executables**, run in both normal and sanitizer CI steps. Python collection
remains unchanged.

## Scoped acknowledgements and six deterministic cases

`hold.c` binds an owner-produced acknowledgement to endpoint, resource, runtime,
request, admission revision, and accounted status. The owner's revision moves
from 1 to 2 at its single admission cut. A zero-initialized control and an owner
can each bind once. Repeating begin on either cannot extend an expired deadline.
Caller-issued IDs are trusted fixture values and must be unique within their
declared domain; this is internal matching, not authentication or secure identity
issuance.

The control uses an exclusive fixed deadline and explicit integer ticks in one
injected monotonic clock domain. Wrong-scope acknowledgements and unrelated
notifications remain false. Wrong-domain ticks are not compared. Expiry or clock
rollback becomes terminal for the waiter; a later acknowledgement may still
record owner completion for cleanup, but cannot restore the expired wait.
Producing an acknowledgement still requires the entered call's return to be
recorded. Neither production nor matching dispatches output or grants authority.

Six cases cover old request/runtime identity; remaining scope/status and exact
replay; returned-but-unrecorded work; fixed deadlines and rollback; malformed
begin requests; and attempts to rebind the same cut with a later deadline. The
old-request test failed before complete identity matching. A separate regression
then exposed deadline refresh through begin; one-time control/owner binding
closed that path.

## Metadata retirement and five deterministic cases

`retirement.c` contains a two-slot pool for one scripted endpoint/resource. A
slot is free, reserved, current, or retiring. Reserve before allocating metadata
or submitting work; only one reservation/current incarnation may exist. Bind a
fresh callback context to the reservation before using the pool's submission
API. Retiring closes its owner admission, while return accounting and reference
cleanup remain available.

Full capacity rejects a new incarnation without overwriting retained records.
Reclamation delegates to the existing owner/queued/active/child lifetime gate.
Only then may the caller free metadata and reuse that pool descriptor. Runtime
ordinals strictly increase and never wrap or reset; cancellation and reclamation
preserve the high-water mark. Handles include the pool, slot, and runtime ID, so
a stale handle cannot access a later occupant of the same slot.

The five cases cover full capacity with retained children; actual reclamation
and same-slot reuse while rejecting old handles/acknowledgements; pending return
accounting; reservation cancellation and ordinal exhaustion; and invalid handles
against a current incarnation. The first test failed because an exhausted search
selected an occupied slot. An explicit no-free-slot rejection fixed it.

This bounds two registered metadata blocks, not their byte size, copied PCM,
all runtime memory, or durable physical history. Owners and callback contexts
remain externally owned and alive through all replays; only pool descriptors
are reused. Callers must not reset these live objects or bypass pool submission
and reclamation for registered work. This is a tested fixture contract, not a
tamper-resistant allocator or a general asynchronous reclamation framework.

## Evidence boundary and next work

This is a deterministic, single-thread lab. Reentrant test hooks expose an
in-flight phase; they do not establish real thread synchronization or callback
quiescence. Struct fields are visible for stack allocation and inspection; they
are not a tamper-resistant isolation boundary. There are no signing keys,
controller leases, real acknowledgement transport, OS routes,
physical observations, or native output handles here.

The source, owner, backend context, and callback delivery context remain live
until the test ends. Only the separate callback metadata allocation exercises
reclamation. The next researched increment distinguishes backend zero progress,
retry eligibility, and recovery invalidation; exact gain arithmetic and format
validation follow. Actual process recovery, native clocks, durable incarnation
identity, real producer synchronization, and native quiescence remain open.
The current conservative negative-return handling must not be
relabeled an implemented ALSA recovery policy.

An acknowledged owner cut never cancels already copied frames, establishes
silence or `NOT_APPLIED`, or grants readiness. `outcome_unknown` becomes true
when a call enters and never clears in this fixture, even for a zero-frame
return. A real endpoint will need separately qualified observations and
future-effect exclusion. The existing production factory guard and false
`EndpointHandoffBarrier.is_ready()` stay in force. Both iPhone/iOS and Android
remain equal product targets; Linux is an owned lab candidate, not a customer
hardware requirement.
