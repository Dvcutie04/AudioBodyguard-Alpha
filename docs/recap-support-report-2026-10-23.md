# Review support reports from recent checks — 0.25

October 23, 2026. Add Review support report to the shared Recent sound checks
presentation on Android and iPhone/iPad. Review opens the existing private
report preview from the visible, completed recap snapshot. The user can exclude
checks, inspect the exact text and then explicitly Share. Back returns to the
same recaps; closing recaps returns to their caller.

## Existing research and scope

This reuses the [private report boundary](private-support-report-2026-10-22.md),
[report contents choice](support-report-choice-2026-10-22.md), and
[Insights recap navigation](insights-sound-checks-2026-10-22.md). The same native
dialog/sheet and text-sharing mechanisms are used. No new platform API,
permission, recorder, service, stored preference, report field or network
client is introduced. Existing research supplies the navigation and snapshot
contract; this is not a new output or recognition subsystem.

The preview contains installed build details and up to five typed completed
meter observations. Active drafts, audio, recognized words, photos, TV/network
details, timestamps, identifiers and arbitrary logs remain excluded. Review
does not open the native share sheet. Sharing does not establish recipient
delivery, physical sound, protection or TV control.

## Test-first contract

Keep 0.24 production and versions while native Android, iPhone and iPad checks
fail at the missing Review support report entry. Preserve their source and
failure evidence before production changes. Then cover empty and actually
completed recaps, report exclusion without deletion, repeat preview resetting
its choice, Back returning to recaps, and Close returning to Insights. Retain
all existing sharing, consent, cleanup, meter and photo assertions. The iPhone
completed-recap case also uses native Copy, independently checked against the
compiled metadata and allowlisted completed row. No input or speech events are
injected to manufacture a completed recap.

The existing formatter and immutable snapshot remain the data boundary; no
duplicate formatter is added. Opening, closing, excluding or sharing a report
cannot start capture, request consent, clear recaps, release microphone cleanup
or authorize output. Clearing recaps and process restart retain their existing
semantics. Exact red/green source, native results and final artifact identity
belong to the candidate's draft pull request.

Signed iPhone delivery, installed-phone accessibility/usability and speech
accuracy, continuous protection, TV control and N2b–N5 remain unqualified.

## Recorded red baseline and implementation

The tests-only source `9a223ecd15877e21f70c647e967eaf15d891fc28`, tree
`c1b3744b90e8a784ea076ecdc97f1c9018465dc6`, retained 0.24 production and
version metadata. [Core run 40019822846](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40019822846)
passed all four jobs. [Android run 40019823042](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40019823042)
job 120641144167 reached a stable launcher and failed with `Missing tap target:
Review support report`. [Apple run 40019822853](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40019822853)
failed at the intended missing entry on iPhone (job 120641142283) and iPad
(job 120641142707), with `AQSSRecapReport Code 1`. The isolated speech-permission
job passed. These three intended failures were recorded before production
changes began.

Android extracts its existing package metadata and report dialog into one
shared view, called by both Settings and the recap list. iPhone extracts the
existing bundle metadata and report contents, with a child report sheet owned
by the recap presentation. Both callers supply the visible completed rows to
the existing immutable formatter. Dismissing the report leaves its parent
recaps intact. A new presentation starts with Include enabled; toggling it
never mutates the recap store.

Candidate identity is Android version code 25 / `0.25-recap-support-report-live-input`
and iPhone/iPad version `0.25.0`, build 1. The final source revision, green native
results, independently received shared text and APK/archive provenance are
recorded in [draft PR #57](https://github.com/Dvcutie04/AudioBodyguard-Alpha/pull/57).
