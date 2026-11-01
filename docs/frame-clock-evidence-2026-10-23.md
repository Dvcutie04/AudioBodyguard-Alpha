# Responsiveness evidence clock ordering — 0.26

October 23, 2026. This increment resumes the
[existing responsiveness investigation](latency-follow-up-2026-09-30.md) from
the verified 0.25 source. The native app behavior remains 0.25; the work repairs
an evidence qualification gap and captures the existing renderer diagnostics
around Recent sound checks → Review support report and Back.

## Stage 0 finding

The existing parser checks each snapshot's frame timestamps against its own
uptime and a 60-second diagnostic horizon, but does not compare the two dump
uptimes. A baseline at uptime 2,000 ms with a frame starting at 1,000 ms and a
later snapshot reporting uptime 1,000 ms with a frame starting at 1,500 ms
currently produces one qualified 10 ms sample. Both rows are locally plausible;
the recorded uptime regression still invalidates cross-snapshot attribution.
This does not diagnose a reboot, device change or the user's jitter.

The tests-first contract covers completed and in-flight baseline frames. A
known uptime regression must retain the fact that baseline/clock headers were
present, report invalid uptime ordering, withhold attributed frames and all
latency summaries, and leave the raw snapshots available. Existing equal or
advancing clocks, duplicate rows, missing baselines/clocks and malformed timing
retain their separate semantics. Record the intended red failure before
changing the parser.

## Existing research and bounded scope

This reuses the already researched `dumpsys gfxinfo … framestats` collection
and Python parser used by the native walkthrough. It adds no OS/driver API,
input permission, recording backend, model, persistence or output authority.
The Android live-input verification will retain bounded raw before/after dumps
and source/build-labelled comparisons for the report-open and report-Back
transitions, with empty and actually completed recaps. Functional UI and share
assertions remain independent of timing qualification or sample count.

These are hosted rendered-frame observations. UI automation and evidence
collection occur in the interval; touch-to-response, physical latency, energy,
handset smoothness and the cause of jitter remain unmeasured. Missing or invalid
evidence stays unknown. No performance threshold, speculative rendering change
or claimed responsiveness improvement is introduced. iPhone/iPad retain the
same app behavior and native regression suite; this increment adds no iOS
performance instrumentation. N2b–N5 and signed iPhone delivery remain pending.

Candidate identities will advance to Android code 26 /
`0.26-frame-clock-evidence-live-input` and Apple 0.26.0 build 1. Exact source,
red/green checks, observed sample counts and APK/archive identity belong to
the candidate's draft pull request after verification.

## Recorded red and implementation

Tests-only source `21029381f1dfed4ce8e65d506569e4f5ff3fa506`, tree
`25fce440e5e70dd0fe652aa39bf9b234fc1f1ecb`, retains the verified 0.25 parser,
app production and versions. The two new cases failed locally at the intended
`timing_qualified` assertion; all five existing frame cases passed.
[Hosted red run 40029402514](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40029402514),
Python job 120673611916, reproduced exactly those two failures while the other
1,879 tests and 19 subtests passed. That log was inspected before the parser
was changed.

The parser now retains each observed uptime, reports `uptime_order_valid`,
and discards cross-snapshot frame attribution when both headers are present
and the after uptime is lower. Header presence remains separate from ordering.
Missing clocks still withhold summaries while retaining their existing raw
diagnostic treatment; equal/advancing uptime is not proof of device identity
or uninterrupted clock continuity. Existing local plausibility limits remain.

The live-input runner captures four labelled transitions: report Open and
Back, each with empty and completed recaps. Each dump has a 10-second collection
limit and a 2 MiB retained-output limit. A timeout, command failure or over-limit
dump becomes explicit unavailable evidence; it does not bypass a functional
UI assertion or turn into a zero-latency claim. Comparisons carry the workflow
source/run/attempt and actual installed package/version/build. The native app
and the private support report contain none of these diagnostics.

Final verification and artifact identity are recorded in
[draft PR #58](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/58).

The first 0.26 iPhone run, job 120675224401 in run 40029882079, stopped in
the unchanged native photo-replacement test before later sharing/input cases.
It repeated the 0.25 `kAXErrorCannotComplete` failure: XCTest computed a
(-1, -1) hit point while trying to scroll an on-screen, uniquely dated Photos
thumbnail into view. The test now uses the existing coordinate-tap technique
when the identified image is fully inside the app viewport and at least 44
points wide/high; offscreen images keep the existing native scroll-and-tap.
Unique date/asset matching and every photo OCR, replacement, cancellation and
unknown-state assertion remain. This is a test-only correction; Android app
code, frame collection/parser, iPhone app sources and version identities are
unchanged. Final evidence records both the original implementation revision
and the corrected test revision explicitly.
