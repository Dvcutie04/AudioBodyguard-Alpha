# Read-only session evidence reference

This increment implements the researched P0 product vocabulary as **reference
software**. It does not install an iPhone or Android application or qualify an
audio path. `src/control/session_evidence_view.py` provides a bounded
privacy-side session journal, capability cards, and scoped change wording.
`src/control/authored_track_finder.py` reports authored option availability,
player selection, and presentation callbacks separately. Neither module has
access to a mutating adapter.

## What a view may say

| Input | Allowed user-facing claim | Explicit limit |
| --- | --- | --- |
| A fresh reported coverage sample in the same runtime and monotonic domain | The reported state at the sampled time | It does not establish continuous coverage between samples or real capture/output. |
| An expired sample, missing observation, new runtime/clock, or local clock rollback | Unknown physical state with a reason | A cached ACTIVE state cannot survive these boundaries. |
| An explicit user-pause sample after its evidence expires | Paused, with expired evidence as a secondary reason | The reference journal keeps a separate pause latch until explicit resume; the installed native event reducer still needs the same behavior. |
| Capability facts | Unsupported, not qualified, permission denied, route unavailable, unknown, or available for **review** | `AVAILABLE_FOR_REVIEW` grants no actuation or physical verification. A caller must separately authenticate and scope every fact. |
| Bridge execution receipt without matching physical verification and verified media state | Result uncertain | A signed receipt or accepted work is not a verified physical effect. |
| Matching reference verified media lineage | Verified on the declared path | This wording describes reference verification. Actual observer independence and native execution remain unqualified. |
| Owned-player authored track metadata | Player reports available/absent, selected, or callback reported | Selected captions may have no text on the current segment. No callback proves a person saw/heard output. |

The journal records a global sequence and the runtime and clock identity of
each sample. It rejects out-of-order events and rollback within a runtime,
counts skipped sequences and runtime discontinuities, and limits retained
samples to a configured maximum. Recaps deliberately have **no ACTIVE
duration or coverage percentage** because missing callbacks, suspension and
clock changes make those quantities unprovable from these samples. User-facing
history is in memory and can be discarded without changing the separate
protected authority/replay/finality journals. It is not a durable complete
transition stream; a native product must supply one before offering historical
duration claims.

`src/control/session_event_producer.py` adds one **in-process reference
producer** bound to a supervisor, journal, runtime and monotonic clock
domain. It captures one supervisor snapshot at a supplied monotonic time and
publishes it separately at receipt time. A newer capture supersedes the one
pending slot; failed publication retains it for retry, and the next capture
uses a new sequence so a known lost write remains visible. An append that
actually completed before reporting an error cannot be retried as a second
event. The producer caps sample expiry at the supervisor's configured age,
rejects rollback within its runtime, and downgrades a changed snapshot to
UNKNOWN before publication. It removes unrecognized reason codes before
retention. **Every software ACTIVE result becomes UNKNOWN_PHYSICAL_STATE with
REFERENCE_ONLY**: the Python supervisor has no native physical observer.
No manual user-pause or resume is inferred from a status reason. This is a
bounded sample publisher, not a complete OS callback feed, durable privacy
journal, or proof of a functioning protection path.

A separate in-memory user-pause latch survives later ACTIVE or unknown
observations. A later ACTIVE report stays PAUSED for display until an explicit
resume event; an unresolved physical state remains UNKNOWN with user pause as
a secondary reason. This UI latch is neither an authorization token nor a
replacement for the supervisor's own inhibition. Restart persistence remains
unimplemented.

`preview_redacted_export()` returns a derived JSON preview with no session,
runtime or clock identifiers, no absolute timestamps, and no audio, transcript,
media titles or device names. Only allowlisted reason codes survive; an
unrecognized code is replaced **before retention**. This is a preview, not a
signed audit bundle or a promise of encrypted mobile storage. The caller
chooses when and whether to save/share it. Delete/export UX and secure
platform storage remain N5 work.

`contracts/session_evidence_view_v1.json` contains 11 coverage and nine
capability vectors consumed by Python, Swift and Kotlin. The Swift package
and Android library each implement a read-only projector; their tests also
reject malformed local evidence. These are contract libraries, not app
targets, native event adapters, or real-device qualifications. Cross-platform
parity covers the defined synthetic vectors only.

The authored finder accepts metadata from an **owned player**. A complete
catalog can report a missing track; an incomplete or stale catalog says
UNKNOWN. A manual choice on the same content generation takes priority over
a competing recommendation. On a changed generation, it requests review;
there is no implicit replay, player selection call, or transfer of authority.

## Integration and remaining gates

The native supervisor must eventually produce trustworthy source, acquisition,
expiry and runtime facts on both iOS and Android. An event received after an
app resumes cannot backfill a time when the app was suspended. A durable event
publisher must distinguish publication failure from observation failure and
must not erase unresolved endpoint history when the user clears a recap.
P1 can render these read-only views in accessible installed prototypes once
actual app targets exist. P2–P4 require named endpoint and observer qualification
through N2b/N3; N4 handoff still needs future-effect exclusion. Both
`EndpointHandoffBarrier.is_ready()` and the production factory guard stay
closed. The existing [N2b qualification record](n2b-lab-qualification-record.md)
is the physical lab starting point.
