# Unambiguous renderer uptime evidence — 0.29

October 24, 2026. Continue the existing responsiveness evidence investigation
from verified 0.28 source `cb25b947667bbbddbc28264e88b099997cab57b9`, tree
`b922209c7f00b6cd9de7a19c44008595e9609119`.

## Stage 0 finding

The parser searches only for the first numeric prefix after `Uptime:`. It
accepts fractional, suffixed and exponent tokens as integers, and its whitespace
match can borrow digits from the next line. It also ignores later conflicting
or unreadable uptime headers. With matching process headers and plausible frame
rows, an after header of `Uptime: 2100.5` or two headers recording 2100 and
1900 ms produces a qualified 10 ms summary against a 2000 ms baseline.
These synthetic examples expose a qualification gap; they do not explain the
user's jitter or establish a clock failure on a phone.

## Tests-first evidence

Tests-only source `14cc123a3a9d1597f57263a467520babecf9601a`, tree
`3199a317d1ba38763d2d654cc8d8f40fd2ef3197`, leaves all 0.28 production,
versions and prior assertions unchanged. Sixteen new cases fail at the intended
clock-availability assertion: eight malformed/ambiguous forms in either the
before or after dump. The 43 existing cases and four valid-clock controls pass.
Controls cover a native header, uptime alone, horizontal whitespace and an
identical repeated header.

[Hosted red run 40118382935](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40118382935),
Python job 120944409133, reproduced exactly those 16 failures while the other
1,921 tests and 19 subtests passed. Its actual failure log was inspected before
changing the parser.

## Bounded repair and compatibility

Read a complete nonnegative decimal integer uptime token on its own header
line. A malformed observed header makes the clock unavailable. Multiple
headers must agree on the numeric uptime; identical repeats remain valid.
No value is rounded, clipped, inferred from a later line, or chosen from
conflicting observations. Realtime remains outside the existing uptime-based
comparison contract.

An unknown clock keeps the existing valid-subset frame diagnostics but withholds
uptime ordering, timing qualification, median and maximum. A known regressed
clock retains its separate attribution rejection. Baseline starts, unreadable
completions, process scope, timestamp plausibility, duplicates and in-flight
rows retain their existing treatment. No new report fields or platform APIs
are introduced.

All 63 focused cases and the complete local suite of 1,937 Python tests plus
19 subtests pass. The five generated-content checks and Python compilation
also pass. Reprocessing the four retained 0.28 intervals preserves all 14
comparison fields exactly: empty Open/Back counts 11/2 and completed Open/Back
counts 16/2. This establishes compatibility, not a responsiveness improvement.

This implements the already researched diagnostic contract in
[the existing investigation](latency-follow-up-2026-09-30.md). It needs no new
substantive platform research. App behavior remains 0.25; Android and iPhone/iPad
retain their full native regression lanes. Candidate identities are Android
code 29 / `0.29-frame-uptime-evidence-live-input` and Apple 0.29.0 build 1.
Exact final source, hosted results and artifact identities belong to the
candidate's draft PR after verification.

The four report Open/Back captures retain their ten-second collection deadline,
2 MiB raw bound and exact source/run/attempt/installed-build labels. They include
automation and describe rendered frames, not touch-to-response latency, handset
smoothness, battery use or physical response. Signed iPhone installation and
N2b–N5 remain pending.
