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

The first Android run, 40040421603/job 120709929060 on implementation source
`7ed589f498033801edd00f351878815f47564aba`, failed the unchanged native support
report handoff assertion. The pre-click hierarchy marked the receiver visible
but placed its label at `[11,2142][205,2186]` outside the ancestor GridView
`[0,2208][1080,2340]`; an earlier chooser snapshot had it fully in view. A
reported successful accessibility click was followed by the app preview, not
the independently checked receiver. The run is retained as a failure, not
accepted as share evidence or an APK candidate.

The Android test now waits for one unambiguous system receiver label fully
inside all ancestor bounds in two consecutive fresh observations, within six
attempts, before the existing native accessibility click. A failure to settle
retains a screenshot and fails the test. Exact Intent/ClipData, receiver-Activity,
Cancel, content, URI/stream exclusion and return assertions remain. This is a
test-only synchronization correction; app sources, versions and the frame
parser are unchanged from the implementation revision. Final evidence records
both source identities explicitly.

The corrected-source Apple run 40041309685/job 120712994552 stopped at the
first photo result: its ten-second wait did not observe `Brand: VIZIO`.
Subsequent expected model/IP assertions passed, and the retained screenshot
`Native photo review before replacement` shows VIZIO and the complete expected
result. Artifact 12539528643 (ZIP SHA-256
`92a974f3ce4587938b086cc6c8be2d2e1c5348e6fddd2e9243a8e8e9f50fd414`)
was inspected before the next edit. This does not determine whether OCR,
presentation or accessibility observation caused the delay.

Only the first expected result after each selected fixture now receives a
35-second test wait: the app's existing 30-second import/OCR acceptance window
plus five seconds for presentation. Other label waits stay at ten seconds.
Every expected brand/model/IP, partial/unknown result, cancellation, replacement
and Clear assertion remains; the test neither retries a read nor injects OCR.
App result deadlines, app sources, Android verification and version identities
are unchanged. Android run 40041309673 passed on source
`5dad9cb6ed80ea8e67053f1bdd5dbc750de43d05`; final evidence binds that APK
source separately from the subsequent iPhone test-only correction.

The next Apple run 40042575273/job 120716822907 failed before reaching the
photo result wait. The uniquely dated native image was reported at
`{{-0.0, 352.7}, {129.7, 129.7}}`; the test took its native accessibility
scroll-and-tap branch, which computed `{-1, -1}` and failed with
`kAXErrorCannotComplete`. Artifact 12539962367 (ZIP SHA-256
`ce9788da2c6667beba7f145bb6a96d4af48dcb2db5e87f6f67fb6a5a9b1c464a`)
was inspected, including its decompressed native picker inventory and runtime
log. The inventory identifies the expected image and the app frame is
`{{0, 0}, {393, 852}}`. The rounded negative-zero horizontal image edge is
consistent with a fractional boundary failing the strict containment guard;
this is an inference, not proof of every underlying Photos geometry detail.
The separate iPad eight-test and speech-permission one-test jobs passed.

The existing coordinate-tap guard now permits at most half a point of
horizontal frame rounding. It still requires a 44-point image and visible
intersection, and full vertical containment with the existing 24-point inset.
The tap uses the center of the strict viewport intersection, anchored to one
app-frame snapshot; genuinely offscreen images retain native scroll-and-tap.
Each selection records its exact geometry and an on-screen picker screenshot.
Unique imported-date matching, the result wait, and all photo content,
replacement, cancellation, unknown-state and Clear assertions remain. No app
source, Android source or version identity changes.
