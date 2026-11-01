# Reviewable private support report

October 22, 2026. Version 0.19, stacked on the completed 0.18 source.

The existing planned Private support report entry becomes a reviewable,
explicitly shared text snapshot in Settings > Advanced Settings. It contains
the installed build details and at most five completed sound-meter summaries,
most recent first. Each summary contains only an input-observed boolean and
an existing allowlisted stop reason. An empty process says that no completed
checks exist. This is input-only reporting, not a connection, safety,
continuous-listening, output or protection claim.

## Research and evidence matrix

This increment reuses the researched [0.18 native sharing](share-build-details-2026-10-22.md)
and [0.5 bounded input recaps](sound-check-recaps-2026-10-20.md). No new OS API,
permission, recorder, service, network client or storage is introduced. Recovering these decisions does not introduce a new platform behavior.

| Evidence | Decision and limitation |
| --- | --- |
| Existing SoundCheckRecaps types on both platforms | The only recap fields are a boolean and a fixed enum. Render those fields directly; never export a runtime object, generic log or exception text. The store already retains at most five completed rows. |
| Existing installed package/main-bundle lookup | Reuse the same four-line metadata formatter as Build details, including Unavailable fallbacks. Version/build are tester context, not authenticated binary provenance. |
| [Android sharing guide](https://developer.android.com/develop/ui/compose/sharing/send) refreshed October 22 | Reuse ACTION_SEND, text/plain, EXTRA_TEXT and createChooser. No URI, stream, file, recipient preselection or permission grant. |
| [Apple UIActivityViewController](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller) and existing native proof | Reuse the iOS 15-compatible String presenter and actual iPad anchor; preserve the existing coordinator's repeat-presentation and dismissal behavior. The docs are JavaScript-rendered in this environment; the prior record and native 0.18 tests supply the implementation evidence. |
| [Apple completion contract](https://developer.apple.com/documentation/uikit/uiactivityviewcontroller/completionwithitemshandler) | Returning from a system activity does not establish recipient delivery or retention. No Sent or retraction claim. |

Alternatives: metadata-only sharing already exists in 0.18 and remains intact.
Exporting the whole journal, raw audio, recognized words, photo hints, TV model,
IP/network data, timestamps, identifiers or arbitrary notes would expand the
data boundary without helping this narrow meter-test report. Those sources
are excluded by construction. A custom upload service or background diagnostic
collector is outside this increment.

## Acceptance and failure behavior

Open creates one immutable preview from the current installed metadata and
completed recap snapshot. The native Share activity receives exactly that
snapshot only after Share support report is tapped. Cancel preserves the
preview; Back returns to Advanced Settings, then Back returns to ordinary
Settings. Reopening creates a fresh snapshot. Clearing recaps or restarting
the process leaves a subsequently opened report empty. Opening, canceling or
sharing does not clear recaps, request a permission, start capture, release
the shared microphone gate, or create output authority.

The preview explains the fields before sharing. It contains no editable
free-text field. No app clipboard write or report file is added. Once the user
chooses an OS activity, its retention belongs to that activity; the app does
not promise confidential recipient handling or retractability.

The formatter defensively uses only the first five typed rows even if its
caller supplies more. Completed rows exclude active drafts. Missing input is
reported as No input samples observed, never silence. Recap provenance remains
the existing app's display observations; it is not independent sound evidence.

## Staged verification

1. Keep production at 0.18. Add native Android/iPhone/iPad checks that reach
   the existing entry and fail at the missing Share support report control.
   Retain exact source, job and failure evidence before production edits.
2. Prove a focused formatter behavior red on both native packages, then add
   the minimal allowlisted formatter and UI snapshot. Cover empty, ordered,
   five-row bounds, typed stop reasons and independent snapshots.
3. On Android, require the actual system chooser, Cancel, an unchanged prior
   receipt, the independent test receiver's exact Intent, and return to the
   preview/caller with no running microphone app-op. The receiver never ships.
4. On iPhone and iPad, run separate native Cancel and Copy cases. The CI host
   checks the actual Simulator clipboard: Cancel preserves a synthetic fixture;
   Copy matches the expected report bytes from compiled Info.plist metadata.
   Neither app nor UI runner accesses the clipboard.
5. Verify a report made from actual completed meter checks, and empty reports
   after Clear/process restart. Preserve all prior input, consent, lifecycle,
   photo, sharing, core and unsigned archive checks. Inspect screenshots for
   readable scroll behavior and native iPad presentation.

Work is tap-triggered; no polling, sensor work, persisted report or dependency
is added. Bounded fields support latency/battery/memory priorities without
claiming measurements. Physical handset trials, signed iPhone distribution,
recipient delivery and N2b-N5 remain separate unqualified gates. Production
factories stay closed. Exact red/green results and APK identity will be added
to the draft PR before delivery.


## Native and formatter red evidence

Native red-only source 161a5d7f938d98bb3335d64474adee3ab36c467c, tree
edf95306d6f75f8131ef3b5bdf9a24ef00c8c901, preserved all 0.18 production
code and version metadata. Android run 39885155469/job120191505389 passed
its prior actual build-details share checks, reached the planned report entry,
and failed Missing tap target: Share support report. Apple run39885155387
failed Missing Share support report action / AQSSBuildShare Code2 on iPhone
job120191505688 and iPad job120191505706. Both devices passed their prior
build-share cases; the isolated speech-Settings job passed.

The next tests-only source f35f330720c6202c458bd80fed16608419c152aa, tree
83e96fdc7560fd263ceecab6646e2be6f81f9743, specified that an active draft
must not become a completed report row. Core run39886147261 failed exactly
at missing soundCheckSupportReportSection in Kotlin job120194667526 and
Swift job120194667616. Python and scripted C passed. Production edits began
only after those native and typed-formatter red proofs.

The implementation uses the existing package/main-bundle lookup plus one
immutable String snapshot of the completed, typed recap list. Native sharing
reuses the 0.18 presenters, with a separate report button label/identifier.
The preview can be reached by the existing help control or the report row.
Build details keeps its original four-field payload. The Android live-input
version is 0.19-private-support-report-live-input/code19. The Apple default
is 0.19.0/build1, retaining signing overrides. Final green results, source/tree,
artifact bytes and remaining physical limits belong to draft PR #51.
