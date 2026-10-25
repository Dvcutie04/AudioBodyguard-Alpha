# N2b owned-output lab qualification record

26 September 2026. **Unfilled research and test protocol, not a qualification certificate.** The C11 fixture at `native/lab/owned_output` has no ALSA device, independently observed playback, native concurrency proof, or authority to release an endpoint handoff. `EndpointHandoffBarrier.is_ready()` remains false; production endpoint construction still requires a qualified execution boundary.

The researched first experiment is an AQSS-owned Linux playback service with one specifically named ALSA PCM resource and an independent capture of its selected physical output. This is a lab candidate, not a mandatory customer accessory or a claim that consumer TV controls can be made equivalent. iPhone/iOS and Android remain equal product targets for later native qualification.

## Available equipment update — October 24, 2026

The owner answered the computer-versus-phones question with **two phones**.
The earlier October 17 account identifies one Android and one iPhone; this
update confirms the phone-only constraint without rechecking their models,
OS builds, routes or network state. A computer is outside the reported setup.
No purchase is required by this record.

The recovered September 24–25
`AQSS_N2_Owned_Output_Lab_Research_2026-09-24.md`, section 5, explicitly
allows an owned iOS or Android lab path when only phones are available,
with a refresh of that exact backend's details and the same measurement
obligations. Linux/ALSA remains a historical candidate rather than a
prerequisite for this owner's next step.

The next research package is an owned mobile-output experiment. Android is
the first candidate to review because its test APK is already deliverable;
iPhone remains an equal product target, with signed installation separately
pending. Review app-owned playback and bounded stopping, lifecycle/route
changes, residual buffers, trace retention and the second phone's possible
observer role before choosing an API or implementing an adapter. No test
signal or live endpoint is started by this plan.

Two phones establish availability only. Their exact current builds, output
route, acquisition configuration, calibration and clock relationship remain
unknown. A second phone's microphone reading cannot by itself establish
calibrated output, end-to-end latency, containment or TV control. N2b–N5 stay
pending. The owner subsequently confirmed **Ready** for that research step.
The [completed bounded research](phone-output-research-2026-10-24.md) selects
the 0.32 Android read-only inventory before a playback adapter. Its metadata
can supply current phone observations; it does not select or verify a route.

## Available TV observations — October 18, 2026

User-supplied photographs confirm a VIZIO **V505M-K09** and these visible
connectors: white/red L/R RCA **AUDIO OUT**, **AUDIO OUT OPTICAL**, Ethernet,
three HDMI sockets (one green-marked) and USB. The rear audio outputs and
Ethernet are visibly unoccupied. These are connector observations; neither
their signal operation nor native ownership has been tested.

The user's reported listening route is the TV's built-in speakers. The prior
TV settings screenshot reports firmware `1.720.9.1-1`, and the last checked
guest-network address was `192.168.1.105`. Both phones failed to connect through
VIZIO Mobile. Single-host TCP attempts from the iPhone timed out or reported
no route; Android displayed address unreachable. These observations support a
reachability problem but do not establish the guest router's exact policy.

The Android VL68 Pro/Android 16 microphone videos establish a changing live
input display only, as scoped in the [input trial record](android-live-sound-check-2026-10-15.md).
They provide neither calibrated independent output capture nor evidence that
the app can change TV volume. An existing computer, capture interface and
compatible cables have not yet been inventoried. No adapter implementation
or equipment purchase follows from the photographs; the Linux experiment
fields below remain unknown.

Photo identities (SHA-256) for the user-retained source files:

- `IMG_543E6F3A-AD7F-42E9-9822-4F09C226081B.jpeg`:
  `a990d3d923be03a048f2b4376d2ef5916f74e117afcdeffc3fa882b63db1bf46`.
- `IMG_E532E656-8918-4ACE-A7D9-B5410C474BF9.jpeg`:
  `c1ada6668bfe546eb6f965ab3642b3a58b0dbe527d626870f42257a91a0fd77b`.
- `IMG_13F615DB-6BFD-4F2D-BE4B-53C8C91F0494.jpeg`:
  `5265f7d73b38cc5e3ec833005a05273195630b6facf7da88d76d744478729eb3`.

## Pin the scope before writing an adapter

Record actual values and links to immutable instrument output. Leave a field **unknown** rather than guessing.

The [private inventory template and checker](n2b-inventory-preparation-2026-10-24.md)
record these eight rows and check the hashes of referenced local evidence.
An unfilled template stays incomplete; even a complete record remains
unverified and leaves N2b–N5 pending.

| Field | Actual lab value / evidence |
| --- | --- |
| Owner, date, host OS/kernel/build, compiler, chosen backend library and driver versions | Two phones reported October 24; Android/iPhone identified in the earlier October 17 account. Exact current mobile builds/backend unknown; no computer in the reported setup. |
| Output device make/model/firmware and exact physical route, mixer and PCM device name | Unknown |
| Input/output negotiated format, channels, sample rate, periods/buffer sizes, write mode, conversion/plugins | Unknown |
| Separate capture interface, loopback/acoustic path, calibration and capture clock provenance | Second phone available; acquisition path, calibration and clock provenance unknown. |
| Exclusive owner process, service start/stop, process identity and one authoritative admission/hold cut | Unknown |
| Background jobs, callbacks, ramps, queued descendants, native buffers and inherited route ownership | Unknown |
| Monotonic clock epochs, trace storage bound, crash recovery and tamper/rollback protection | Unknown |
| Privacy/consent for capture, safe volume and secure test environment | Unknown |

Do not acquire access to a live home endpoint or schedule a potentially disruptive playback trial from an incomplete form. Inventory the available mobile path and capture arrangement under the research refresh; no purchase is assumed. The Linux-specific API examples below describe the historical candidate and must not be treated as a mobile implementation contract.

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
