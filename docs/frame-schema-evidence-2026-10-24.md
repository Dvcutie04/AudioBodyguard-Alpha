# Unambiguous renderer frame columns — 0.30

October 24, 2026. Continue the existing responsiveness evidence investigation
from verified 0.29 source `642510569684badffac77e51cb8c078fdef23e7a`, tree
`a72f238ac1a187ef57828459657a2b348bf59bc8`.

## Stage 0 finding

The parser builds its column dictionary without checking for duplicate required
names. A header containing FrameCompleted twice, followed by one row with
100 ms and 10 ms completion interpretations, silently selects the last field
and qualifies a 10 ms summary. An incomplete later header can also leave the
previous column indices active. The dump is no longer an unambiguous basis
for frame attribution, even if some individual rows remain plausible.
These synthetic examples do not diagnose the user's jitter or establish a
malformed capture on an installed phone.

## Tests-first evidence

Primary tests-only source `847d61b872868bf2a4bcc3abae0dc947ef51fc51`, tree
`66927498574086ded5e2426a5ad15f8cb872c34e`, leaves all 0.29 production,
versions and prior assertions unchanged. Twenty-four cases fail locally at
the retained frame-count assertion: duplicate or missing Flags, IntendedVsync
or FrameCompleted, in either snapshot, before or after a valid table.
All 63 existing cases and seven controls pass before the parser edit.

Four controls retain native and reordered headers, unrelated duplicate/empty
columns, and repeated valid tables. Three others preserve an unreadable numeric
timing row whose completion text happens to equal a required column name.
Such a row is not a new header; it retains the existing invalid-completion and
valid-subset diagnostic treatment.

[Hosted red run 40121222687](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40121222687),
Python job 120952964752, reproduced all 24 intended frame-count failures while
1,944 tests and 19 subtests passed. Its actual failure log was inspected before
the parser edit; none of these failures depended on a new-field lookup.

The preliminary tests-only source `5044dc8ba950e0522248b0b648bb2cfe96194a80`
in [run 40121023225](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40121023225)
failed 22 timing-qualification assertions and two new-field lookups. The
primary source above moves the existing frame-attribution assertion first,
so every intended red failure tests behavior independently of field presence.
The preliminary C, Swift and Android jobs passed; the record is retained.

## Bounded repair

Recognize a nonnumeric header row containing an existing required column name.
Require exactly one Flags, IntendedVsync and FrameCompleted column in every
observed header. Their order and unrelated columns remain unrestricted.
An invalid header clears the active mapping, so following rows cannot inherit
indices from an earlier table. A later valid header permits parsing known
rows again, but cannot erase the snapshot's structural ambiguity.

The diagnostic JSON adds `frame_schema_available`: true only when both dumps
have at least one complete unambiguous header and no malformed observed header.
If either schema is unavailable, withhold attributed frames, durations and
timing summaries. Preserve known baseline starts and independent process/clock
facts. Missing or malformed schema is separate from an invalid completion in
an otherwise known table; existing valid-subset timing behavior remains.

The new field belongs only to the existing diagnostic artifacts. It is not
added to the app's private support report. No new platform API, input/output
permission, storage, capture format or physical authority is introduced.

All 94 focused cases and the full local suite of 1,968 Python tests plus
19 subtests pass after the repair. The five generated-content checks, Python
compilation and diff checks pass. Reprocessing the four retained 0.29 intervals
preserves all 14 prior comparison fields exactly, with the new schema flag true.
Empty Open/Back counts remain 9/2; completed Open/Back counts remain 12/2.
This is compatibility evidence, not a responsiveness improvement.

This implements the already researched field-mapping and attribution contract
in [the existing investigation](latency-follow-up-2026-09-30.md), using only
the three existing CSV field names. No new substantive platform research is
needed. App flow remains 0.25; Android and iPhone/iPad retain their full native
regression lanes. Candidate identities are Android code 30 /
`0.30-frame-schema-evidence-live-input` and Apple 0.30.0 build 1. Exact final
source, hosted results and artifact identities belong to the draft PR after
verification.

The four report Open/Back captures retain their ten-second collection deadline,
2 MiB raw limit and exact source/run/attempt/installed-build labels. Functional
native assertions remain independent. These tiny hosted rendered-frame samples
include automation and do not qualify action latency, handset smoothness,
energy, calibrated sound, protection or TV control. Signed iPhone installation
and N2b–N5 remain pending.
