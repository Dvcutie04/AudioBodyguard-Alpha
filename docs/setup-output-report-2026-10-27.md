# Setup notes with an output snapshot — 0.35

October 27, 2026. The owner is testing 0.34 and requested the next roadmap
build. N2b still needs the actual phone/output/observer inventory before an
adapter. The existing Android output report and two-phone worksheet currently
require two separate shares. This increment joins their already researched
intake without adding an OS/audio API or a physical experiment.

## Decision before implementation

From Sound → Output inventory → Refresh outputs → Review output report,
choose Add setup notes. The worksheet includes that exact dated output copy
alongside six optional user notes. Review setup report freezes both, then a
separate Share sends exactly the displayed text. The direct Sound → Test setup
entry remains a notes-only form. iPhone/iPad stays at 0.34.0 because acquiring
iOS output information needs its own backend review and signed delivery.

The [approved phone-output research](phone-output-research-2026-10-24.md),
[output-report contract](output-inventory-report-2026-10-27.md) and
[worksheet contract](test-setup-worksheet-2026-10-27.md) already specify the
metadata, uncertainty, bounds, optional notes and native text-sharing rules.
This increment implements their composition. Genuinely new backend research
still follows the roadmap's model-switch requirement and actual inventory.

| Choice | Resource and truth implications | Decision |
| --- | --- | --- |
| Two separate reports | No new implementation, but the owner must manually relate their dates and content | Combine on explicit request |
| Reread outputs when adding notes or sharing | Changes an already reviewed snapshot; extra framework work | Retain the original immutable copy |
| Carry raw device descriptors or arbitrary text in an Intent | Adds data/parsing lifetime and identity problems | Pass a one-use ticket to one typed in-memory snapshot |
| Persist the attachment or draft | More storage, retention and restoration obligations | Discard on Close/process restart; preserve bounded plain data across configuration |

These are design comparisons, not phone performance measurements. No purchase,
playback, route selection, capture, automatic refresh or automatic upload is
introduced. This is partial intake, not all eight verified N2b rows.

## Contract and bounds

The attached output text remains byte-for-byte the original report, including
its phone-clock capture time, advertisement bounds, omissions and physical
unknowns. The notes keep their separate phone-clock review time. Neither clock
is a monotonic latency measurement. An output snapshot from a different
installed build is rejected. Notes retain the 160 UTF-16-unit field limits,
quoting/normalization and original standalone 4 Ki/8 KiB bounds. A combined
report is at most 32 Ki UTF-16 units and 64 KiB UTF-8, including the existing
24 Ki/48 KiB output snapshot. No partial report is silently substituted.

The private, non-exported worksheet activity consumes a one-use ticket from
a main-thread handoff containing at most one typed output snapshot. Replacement
retires the old ticket; a failed launch discards only its own ticket. A ticket
alone restores nothing in a new process. The attachment and frozen review
join the existing bounded notes in configuration retention; no Activity/View
is retained. Normal consumption, Remove output details, Close and process exit
release the corresponding state. An unconsumed launch ticket retains at most
one snapshot until replacement, cancellation or process exit.

The form labels the attachment as a snapshot and allows Remove output details.
Clear notes clears only the six notes. Back from review retains both for
editing; closing discards both. The combined preview keeps both the unverified
setup notice and the outputs-may-have-changed notice visible above Share.
Returning from the worksheet cannot repopulate the parent's live output list.
Native Cancel and recipient return keep the exact frozen combined report.
The app writes no report/draft file or preference. An explicitly chosen share
target can retain the shared text under the existing contracts.

Actual routing, negotiated format, ownership, independent capture, calibration,
clock mapping and consent remain unknown or pending. N2b–N5 and signed iPhone
installation remain pending. No playback adapter or protection claim follows.

## Verification before handoff

Preserve a tests-only source. Native Android must reach the old reviewed output
screen and fail at its missing Add setup notes action. Kotlin tests must reject
the missing combined-report and handoff APIs. Candidate tests cover unchanged
standalone behavior, separate dates, exact attachment, foreign-build rejection,
immutable review, maximum payloads and one-use/replaced/discarded tickets.

Native UI verifies exact preview/receiver text and text-only extras, no delivery
on Cancel, Back/edit, independent Clear/remove, background, rotation, large
text, direct reopening and process clearing. The existing output freshness,
worksheet, input/photo/permission and callback regressions still run. Downloaded
receipts, screenshots, installed build, signature, source identity, artwork and
test-code exclusion must be inspected before the 0.35 APK handoff. Actual
source-bound red/green results and installer identity belong to the draft PR.
