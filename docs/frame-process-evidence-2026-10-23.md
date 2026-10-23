# Renderer process attribution — 0.27

October 23, 2026. Continue the existing responsiveness evidence investigation
from verified 0.26 source `e80b7eb97186ebe71478fd37e1d73146ada4fbbd`.
The native app flow remains 0.25. This increment repairs comparison scope in
the existing Python diagnostic; no rendering optimization or new OS API is
introduced.

## Stage 0 finding and contract

The comparator checks local frame timestamps and dump uptime ordering but
ignores each retained `Graphics info for pid … [name]` header. A baseline naming
PID 1234 and a later dump naming PID 5678, with advancing uptime and locally
plausible rows, currently produce one qualified 10 ms sample. The recorded
process change makes that attribution invalid. This synthetic reproduction
does not diagnose a restart or invalidate 0.26's captured pairs, whose observed
headers match within each interval.

Before changing the parser, test missing, mismatched, ambiguous and malformed
process identity with completed and in-flight baselines. Each snapshot must
contain one unambiguous positive PID/name pair, and both pairs must match.
Repeated identical headers remain acceptable. Otherwise withhold attributed
frames, durations and summaries; keep baseline/clock facts and raw captures
available. The existing seven timing cases gain realistic matching process
headers without changing their assertions or intended timing semantics.

Matching observed headers is only a necessary comparison check. It cannot
authenticate a device, detect every PID reuse, prove uninterrupted process or
clock continuity, or establish touch-to-response or physical latency. Missing
identity stays unknown rather than becoming an apparently fast measurement.

## Bounded scope and verification

Reuse the existing gfxinfo capture API, four recap/report Open and Back
intervals, 10-second collection deadlines and 2 MiB retained-output limits.
The diagnostic JSON will expose identity availability and matching separately
from clock ordering and timing qualification. No process data enters the app
UI or private support report. Functional native assertions remain independent
of sample count or timing qualification.

Candidate identities will be Android code 27 /
`0.27-frame-process-evidence-live-input` and Apple 0.27.0 build 1. Record the
source-bound red/green runs and final APK/archive identity in the draft PR.
Recompute retained renderer comparisons and inspect Android and Apple native
sharing receipts. Both platforms retain the full input/photo/navigation suite.

This is an audit and repair under the existing responsiveness research. It
adds no input permission, recording backend, app persistence, upload, output
authority or physical experiment. Installed-phone smoothness, calibrated sound,
protection, TV control, signed iPhone delivery and N2b–N5 remain unqualified.

## Recorded red and implementation

Tests-only source `f1bb7ffed05cf0bac0904fb874c6de3784472cc4`, tree
`511ac118d4103ddcdf529cf2166088ca75da7736`, retains all 0.26 production files
and versions. Eighteen local cases failed at the intended `timing_qualified`
assertion; the seven existing timing cases passed with matching process headers.
[Hosted red run 40039827064](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40039827064),
Python job 120708019435, reproduced exactly those 18 failures while the other
1,881 tests and 19 subtests passed. The failure log was inspected before the
production parser changed.

The parser now recognizes the retained graphics-process headers and requires
one unique positive-PID/nonempty-name pair per dump. Repeated identical headers
are accepted. A malformed additional header or more than one distinct pair
makes identity unavailable. Both pairs must match before durations or frames
are attributed. JSON exposes `process_identity_available` and
`process_identity_matches` separately from the existing clock facts.

All existing timestamp/uptime guards remain required. Missing clock evidence
with matching process headers retains its previous diagnostic treatment and
withholds summaries. Existing raw capture bounds, UI assertions and native app
code are unchanged. Reprocessed 0.26 observations are compatibility evidence,
not a new performance comparison; final 0.27 captures and artifact identities
are recorded in the candidate's draft PR after verification.
