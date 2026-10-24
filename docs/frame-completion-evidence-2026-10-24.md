# Unreadable renderer completion evidence — 0.28

October 24, 2026. Continue the existing responsiveness evidence investigation
from verified 0.27 source `30fd051e0f6e2edeaa8c2833adf80cf01a0fa489`, tree
`430baf910efb9c437f38a1c86360457303b16749`.

## Stage 0 finding

The parser converts Flags, IntendedVsync and FrameCompleted together. A
conversion failure discards the entire row, including a readable eligible
start. With matching process headers and advancing uptime, a valid new 10 ms
frame plus a newer row ending in `unreadable` produces a qualified 10 ms
summary with zero invalid timings. The unreadable new timing was silently
omitted. This synthetic case does not diagnose the user's jitter.

The same discard can erase a baseline watermark. If a start was already seen
but its completion was unreadable, its later completion can be counted as new
when an older valid baseline row exists. Without another baseline row, the
observed start is incorrectly reported unavailable. The already implemented
in-flight rule requires keeping a valid eligible start independent of whether
its completion is usable.

## Tests-first evidence

Tests-only source `4723a1c7362cf37bd3ae7c04838fdaaa4a69367c`, tree
`5634962ca134fae7eb2f5b188f9a4b5a76fa8886`, changes only the frame-test file.
All 0.27 production, versions and prior test assertions remain. Sixteen cases
fail at the intended invalid-count, baseline-availability or new-frame-count
assertion; the 25 existing cases and two benign controls pass locally.

[Hosted red run 40103274833](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40103274833),
Python job 120899612343, reproduced exactly those 16 failures while the other
1,901 tests and 19 subtests passed. The actual failure log was inspected before
editing the parser. Cases cover text, fractional, empty and missing completions
with completed/in-flight baselines and single/later unreadable baseline starts.
The controls preserve exclusion of flagged rows and rows at/before the cutoff.

## Bounded repair and compatibility

Read and validate Flags and IntendedVsync first. Parse completion separately;
an unreadable value stays unknown, rather than becoming zero or a duration.
The existing timestamp horizon still rejects implausible starts before they
can set a watermark. Otherwise preserve the observed eligible start even when
its completion is unreadable, and retain one deduplicated invalid-completion
marker for that start. A new invalid marker withholds the median/maximum and
timing qualification. Existing valid-subset durations remain diagnostic data.
An invalid completion at/before the baseline does not poison later timings.

No new report fields, capture API, permission, app storage, upload or physical
output authority are introduced. Existing identity, uptime ordering, timestamp
plausibility, deduplication and raw-capture limits remain. The four recap/report
Open and Back captures keep their ten-second collection deadline, 2 MiB raw
limit and actual source/run/attempt/build labels. Functional native assertions
remain independent of timing qualification and frame counts.

The 43 focused cases and full local suite of 1,917 Python tests plus 19 subtests
pass after the repair. Reprocessing the four retained
0.27 intervals preserves all 14 comparison fields exactly, with frame counts
12/2 for empty Open/Back and 9/2 for completed Open/Back. Their archive digest
was checked before extraction. This is compatibility evidence, not a measured
responsiveness improvement.

This repairs the already researched diagnostic contract in
[the existing investigation](latency-follow-up-2026-09-30.md), reusing the same
gfxinfo fields and parser. No new substantive platform research or OS API is
needed. App behavior remains 0.25; both Android and iPhone/iPad retain their
full input/photo/navigation/sharing regression lanes. Candidate identities are
Android code 28 / `0.28-frame-completion-evidence-live-input` and Apple 0.28.0
build 1. Final exact source, native results and APK/archive identity belong to
the candidate's draft PR after verification.

Hosted renderer samples do not establish touch-to-response latency,
installed-phone smoothness, energy use, calibrated sound, protection or TV
control. Signed iPhone installation and N2b–N5 remain pending.
