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
