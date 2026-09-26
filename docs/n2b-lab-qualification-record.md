# N2b owned-output lab qualification record

26 September 2026. **Unfilled research and test protocol, not a qualification certificate.** The C11 fixture at `native/lab/owned_output` has no ALSA device, independently observed playback, native concurrency proof, or authority to release an endpoint handoff. `EndpointHandoffBarrier.is_ready()` remains false; production endpoint construction still requires a qualified execution boundary.

The researched first experiment is an AQSS-owned Linux playback service with one specifically named ALSA PCM resource and an independent capture of its selected physical output. This is a lab candidate, not a mandatory customer accessory or a claim that consumer TV controls can be made equivalent. iPhone/iOS and Android remain equal product targets for later native qualification.

## Pin the scope before writing an adapter

Record actual values and links to immutable instrument output. Leave a field **unknown** rather than guessing.

| Field | Actual lab value / evidence |
| --- | --- |
| Owner, date, host OS/kernel/build, compiler, ALSA library and driver versions | Unknown |
| Output device make/model/firmware and exact physical route, mixer and PCM device name | Unknown |
| Input/output negotiated format, channels, sample rate, periods/buffer sizes, write mode, conversion/plugins | Unknown |
| Separate capture interface, loopback/acoustic path, calibration and capture clock provenance | Unknown |
| Exclusive owner process, service start/stop, process identity and one authoritative admission/hold cut | Unknown |
| Background jobs, callbacks, ramps, queued descendants, native buffers and inherited route ownership | Unknown |
| Monotonic clock epochs, trace storage bound, crash recovery and tamper/rollback protection | Unknown |
| Privacy/consent for capture, safe volume and secure test environment | Unknown |

Do not acquire access to a live home endpoint or schedule a potentially disruptive playback trial from an empty form. The user can supply an existing lab host and capture arrangement later; no purchase is assumed.

## Separate event levels and failure traces

| Event | Minimum observation | Prohibited inference |
| --- | --- | --- |
| Admission | Owner and work ID, fencing generation, route/runtime identity, outstanding descendants, durable admission/hold sequence | Admission is not a physical effect or retirement. |
| Native submission | Bounded call entry, requested frames, return code, accepted count, captured errno/state/route, exact time domain | An accepted prefix is not yet a known acoustic output. |
| Native progress/stop | Driver positions, XRUN/suspend/disconnect and recovery, drain/drop scope, buffer and child job accounting | Draining or dropping one PCM queue does not cancel separately delegated work. |
| Independent observation | Captured timestamped output with named channel/route, synchronization error, calibration and retention limit | A loopback or acoustic capture is scoped to its sensors and cannot prove every hidden downstream effect. |
| Conditional retirement | Durable, bound evidence for all older generations and descendants; continued exclusion of old work within an explicitly enforced boundary | A fence install, queue snapshot, signature, cancellation request or timeout cannot by itself prove `NOT_APPLIED` or safe successor activation. |

The [ALSA PCM API](https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m.html) describes `snd_pcm_writei` and status/position methods; [ALSA's PCM guide](https://www.alsa-project.org/alsa-doc/alsa-lib/pcm.html) describes stream states, XRUN and drain behavior. They define candidate instrumentation points, not an AQSS measurement or guarantee of acoustic silence. Pin their versions and the chosen driver/route before implementation.

## Falsifiable lab trials, in order

1. With a benign identifiable signal, record native requested/accepted/position events and independent capture on the pinned route; measure timing uncertainty. Confirm that a partial prefix, zero and would-block remain distinct.
2. Race a hold against admission, a currently entered write, a queued callback and a child job. Preserve the trace of any effect after the hold and refuse successor readiness while it is possible.
3. Test route change, XRUN, suspend, disconnect, driver failure and stale/lost acknowledgements. Inhibit fresh work first; preserve the old transaction as unknown where output may have escaped.
4. Crash and restart before admission commit, between admission and dispatch, after an accepted prefix, and before an observation reaches durable storage. Detect missing or rolled-back histories; do not reconstruct `NOT_APPLIED` from missing rows.
5. Test A→B→C handoffs with unresolved A work, duplicate and conflicting identities, callback descendants, and changed route/runtime. Only a separately reviewed, scoped future-effect-exclusion result could permit a conditional N4 activation.
6. Measure p50/p95/p99 by event stage and full sensor-to-eligible-response definition, memory, CPU/wakeups, energy where instrumentable, journal growth and retention. Report both failures and missing observations, with named device/driver/route.

**Exit decision:** leave N2b and N3 pending unless the exact build, traces, independent measurement, bounded storage and observed counterexample handling are available for review. N4 requires its own authenticated scope and continuity argument. N5 further needs independently implemented and tested iOS and Android permission/lifecycle/output paths. Passing the fixture or this checklist cannot advance those gates.
