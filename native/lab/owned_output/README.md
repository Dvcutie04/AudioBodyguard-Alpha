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
caller only after the owner acknowledges its cut and both queued and active
counts reach zero. The caller can then free the allocation. The stable context
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
attempt stale delivery under the same normal and sanitizer runner. There are
**11 native cases in total: six owner cases and five callback cases**. Both test
executables run in the existing C11 CI job; Python collection remains unchanged.

The context's closed acquisition and complete ticket registry cover only this
scripted, single-thread family. They are not an OS callback-quiescence contract.
Callback bodies must not free or retain/escape the borrowed metadata. A child
reference API, context recycling, cross-runtime identity, actual producers, and
native shutdown evidence remain separate obligations. Visible struct fields
and ticket values are trusted lab inputs, not cryptographic authority.

## Evidence boundary and next work

This is a deterministic, single-thread lab. Reentrant test hooks expose an
in-flight phase; they do not establish real thread synchronization or callback
quiescence. Struct fields are visible for stack allocation and inspection; they
are not a tamper-resistant isolation boundary. There are no signing keys,
controller leases, runtime/request acknowledgement transport, OS routes,
physical observations, or native output handles here.

The source, owner, backend context, and callback delivery context remain live
until the test ends. Only the separate callback metadata allocation exercises
reclamation. The next researched increment adds retained child references, so a
parent callback's return cannot end a child's lifetime. Stale runtime/request
acknowledgements and actual process recovery remain subsequent increments.
OS-specific EAGAIN/error classifications, gain arithmetic, and format validation
also remain open. The current conservative negative-return handling must not be
relabeled an implemented ALSA recovery policy.

An acknowledged owner cut never cancels already copied frames, establishes
silence or `NOT_APPLIED`, or grants readiness. `outcome_unknown` becomes true
when a call enters and never clears in this fixture, even for a zero-frame
return. A real endpoint will need separately qualified observations and
future-effect exclusion. The existing production factory guard and false
`EndpointHandoffBarrier.is_ready()` stay in force. Both iPhone/iOS and Android
remain equal product targets; Linux is an owned lab candidate, not a customer
hardware requirement.
