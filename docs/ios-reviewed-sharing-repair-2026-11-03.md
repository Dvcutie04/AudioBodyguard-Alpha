# iPhone and iPad reviewed sharing repair

The owner requested repair and a new installable friends-trial iPhone build.
Release run `41635108415` used source
`682081b4635ebcbb49ca5cc43ea5b47230e9316f`, tree
`0e6009f78d59e3df2f257961049efcf0d38b34ff`. Its tools gate failed once in
each of two attempts; signed upload was skipped in both. These are native UI
failures before upload, with no new Apple processing evidence.

- Attempt 1, job `125928586324`: `testTestSetupShareStartsWhenReviewAppears`
  failed at line 305 waiting for the system Copy cell.
- Attempt 2, job `125983549420`: `testTestSetupWorksheetCopySharesExactReviewedText`
  failed at line 253 waiting for the same cell. 24 of 25 tools cases passed.

Both failure hierarchies contain `ActivityListView` and
`ShareSheet.RemoteContainerView` with empty children. The attempt-2 screenshot
shows a dimmed report with no usable native share controls. This establishes
that a native presentation began, not why the remote sharing UI stayed empty.
The source also enabled Share again after one main-queue turn if the activity
had not yet acquired a presenting controller. That inference can precede actual
presentation completion; the failed Copy test recorded Share as enabled while
the native activity container existed.

## Research and design

The standing research charter prioritizes latency, battery, bounded resources
and platform rules without weakening privacy or evidence. Primary Apple sources
were refreshed before implementation:

- [Native activities](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller):
  configure the explicit items and present modally on iPhone, in a popover on iPad.
- [Controller presentation](https://developer.apple.com/documentation/uikit/uiviewcontroller/present(_:animated:completion:)):
  UIKit can forward a child presentation to a containing controller; its
  completion occurs after the presented controller appears.
- [Activity completion](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller/completionwithitemshandler-swift.typealias):
  native completion or cancellation is the result boundary, not one main-loop turn.
- [SwiftUI controller bridge](https://developer.apple.com/documentation/swiftui/uiviewcontrollerrepresentable):
  SwiftUI owns the embedded view's layout and calls teardown before removal.

The repair waits for the local anchor to appear in its window and presents from
its attached containing controller after any parent transition. One retained
activity owns the immutable reviewed String until UIKit completes or dismisses
it. Identity checks reject stale completion; teardown retires the callback and
dismisses only that activity. The iPad popover still anchors to the visible
Share control. The transparent anchor is hidden from accessibility so there
is one labeled Share button. No sleep, polling, automatic Copy/send, network
work, added library or new report retention is introduced. This is a targeted
presentation-lifetime repair; native validation must establish its outcome.

## Required validation

Preserve all existing Copy, Cancel, exact clipboard comparison, review privacy,
Back, lifecycle, rotation and large-text assertions. Add three native Cancel
and reopen cycles at largest text and require Share to remain disabled while
its native activity is owned. The ordinary release suite includes this new
case. Fresh PR jobs also run the existing worksheet and output-detail checks
on both iPhone and iPad, with independent host comparisons of the real native
Copy bytes against the actual reviewed snapshots and compiled build metadata.

Final pass counts, screenshots, source/tree and signed distribution evidence
belong to the published PR and release run. Earlier tree successes cannot
verify this repair. All signing, Apple validation/upload and cleanup gates stay
required. External review, tester assignment and installation remain separate.
This trial does not qualify TV identity, pairing/control or protected audio;
N2b–N5 remain open.

## Follow-up verification repair (November 4)

Worksheet run `41746484592` passed the iPhone native Copy UI case, but the
independent host comparison stopped before reading the clipboard: Xcode 26.3
requires `--legacy` when exporting the attachment object. All three reviewed
clipboard checkers now explicitly select that export mode. They still compare
the actual Simulator clipboard bytes to the actual reviewed XCTest attachment,
retain unique-attachment checks, and reject mismatches or failed exports.

Five local standard-library regression tests (13 scenarios) cover exact payloads,
changed clipboard bytes, ambiguous reviewed attachments, failed export, and a
changed included original snapshot. The original code failed the export-flag
regressions before the fix. These mock host commands and do not constitute a
native app or clipboard pass. Full Python CI and fresh iPhone/iPad native
verification remain required on the published commit.

The iPad Cancel failure also assumed the review heading was outside the native
popover; the retained screenshot shows it covered. Cancel now chooses an
observed app point outside the popover and still requires the same reviewed
snapshot and Share control to return. The combined-report form test alternated
full-height swipes past its field; bounded viewport drags retain the reachability
assertion without overshooting the short iPad sheet.

The largest-text iPad and combined-report iPhone failures show an empty native
ShareSheet remote container, not an offscreen Copy action. Their eight-second
failure boundary remains intact, with explicit screenshot and hierarchy
attachments added. No app presenter change, simulated Copy, retry-to-pass,
release dispatch, or delivery is established by this follow-up. Fresh native
results must determine whether the empty native activity remains a blocker.

## Wrapped-button hit area (November 4)

Current-source native run `41758028231`, tools job `126338660746`, passed
all 20 `AQSSReadOnlyUITests` and failed one of six output-detail cases. The
failure was the second, largest-text worksheet entry in
`testCombinedSetupClearRemoveLifecycleAndLargestText`, not native Copy.
The retained XCResult hierarchy shows the reviewed output screen still open.
Its recorded synthesized tap was `(201.17, 307.67)` inside the visible
`Add setup notes` button rectangle `(19.5, 236.5, 363.33, 142.33)`. The
retained screen recording shows that point between the two wrapped text lines.
The custom button style painted a rounded background without declaring a
content shape for the padded label.

The style now explicitly gives the complete rounded button a hit-test shape,
including padding and inter-line space. Apple documents
[`contentShape`](https://developer.apple.com/documentation/swiftui/view/contentshape(_:eofill:))
as the shape used for hit testing. The native worksheet test still taps the
centre once and requires the same worksheet and original output details within
the existing five-second bound; it now retains the entry screenshot and, on
failure, the resulting screenshot/hierarchy. No repeated tap or longer timeout
is introduced. This is a source-supported hit-area repair; a fresh native run
must establish whether it resolves the observed missed action.

The separate iPhone output-details job `126338660586` in run `41758028165`
failed `testOutputDetailsCancelPreservesReviewedSnapshot`: its screenshot
still shows a dimmed review with no usable native share controls, and its
hierarchy contains an empty `ShareSheet.RemoteContainerView`. Its underlying
cause is not established. The iPad job passed five Cancel/lifecycle cases and
both exact native clipboard receipts on this tree, which does not validate the
failed iPhone case. No retry of either sharing or worksheet failure is justified
as transient by that evidence. The connected-appearance job `126338660623`
separately recorded an explicit simulator accessibility IPC timeout. All
current-source gates, including native sharing on both devices, remain required
before merge or a new signed release. This follow-up does not establish a new
installable build.
