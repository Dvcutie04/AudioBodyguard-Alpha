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
