# Unreadable renderer CSV evidence — 0.31

October 24, 2026. Continue the existing responsiveness evidence investigation
from verified 0.30 source `1c94c6a30c3589331755e4bf4677c8a3975e88a3`, tree
`ef18ad281037d9ad37756afe55c39030fe879c23`.

## Stage 0 finding

The line-based CSV reader accepts malformed quoting in its default permissive
mode. An unterminated quoted timing row can be silently ignored while a valid
new row still produces a qualified 10 ms summary. Separately, a field exceeding
the reader's existing 131,072-character limit raises an uncaught CSV error,
even though the complete snapshot remains below the collector's 2 MiB bound.
That diagnostic exception can stop the verification runner before subsequent
functional UI assertions. Neither synthetic example diagnoses the user's jitter
or establishes a malformed capture on a phone.

## Tests-first evidence

Tests-only source `04577b3394e3ff18c6368489cd79e6fc51e92547`, tree
`249150a5d51c3771c183e1b082bd3a2bf7feaf27`, changes only the frame-test file.
All 0.30 production, versions and prior assertions remain. Sixteen new cases
cover an oversized field, an unclosed quoted row, an unclosed quoted header
and text after a closing quote, in either snapshot and before or after a valid
table. Four cases raise the old uncaught CSV error; twelve fail at retained
frame attribution. The 94 existing cases and four quoting controls pass.

[Hosted red run 40125137658](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40125137658),
Python job 120964833795, reproduces exactly those 16 failures while 1,972 tests
and 19 subtests pass. The actual failure log was inspected before parser edits.
No failure depends on a new field or an altered prior assertion.

## Bounded repair

Parse each line with strict CSV quoting and catch only the CSV reader's error.
An unreadable line can conceal a header or timing row, so clear the active
column mapping and latch schema unavailability for the entire snapshot. A
later readable table can preserve known starts but cannot erase this ambiguity.
The existing `frame_schema_available` field reports that the mapping could not
be established throughout the capture; no report field is added.

Withhold attributed frames, durations and timing summaries when either dump is
unreadable, while retaining independently known baseline/process/clock facts.
Keep the raw captures and return a normal unqualified diagnostic report so the
native functional checks can continue. Do not raise the process-global CSV
field limit or the collector's existing bounds.

Valid quoted numeric/header fields and comma-containing metadata remain valid.
A doubled quote inside an otherwise readable completion and a literal apostrophe
retain their existing invalid-integer treatment: the schema remains known,
the new invalid completion withholds summaries, and valid-subset durations
remain diagnostic data. All earlier timestamp, process, clock, duplicate and
in-flight rules remain.

All 114 focused cases and the full local suite of 1,988 Python tests plus
19 subtests pass. The five generated-content checks, Python compilation and
diff checks also pass. Reprocessing all four retained 0.30 intervals preserves
all 15 comparator fields exactly: empty Open/Back counts 13/2 and completed
Open/Back counts 8/2. This is compatibility evidence, not a speed improvement.

This repairs the already researched diagnostic contract in
[the existing investigation](latency-follow-up-2026-09-30.md), using the same
CSV fields and reader. No new substantive platform research or OS API is
needed. App flow remains 0.25. Android and iPhone/iPad retain their full native
regression lanes. Candidate identities are Android code 31 /
`0.31-frame-csv-evidence-live-input` and Apple 0.31.0 build 1. Exact final source,
hosted results and artifact identities belong to the draft PR after verification.

The four report Open/Back captures retain their ten-second collection deadline,
2 MiB raw bound and exact source/run/attempt/installed-build labels. Functional
assertions remain independent of timing qualification or frame counts. The app's
private support report contains none of these diagnostics. Hosted frame samples
include automation and do not qualify action latency, handset smoothness,
energy, sound safety, protection or TV control. Signed iPhone installation and
N2b–N5 remain pending.
