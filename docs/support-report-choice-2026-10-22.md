# Choose the contents of a private support report

October 22, 2026. Version 0.20 follows completed 0.19, source
44cc5ccf27059d82e4dc7e500218abd9d7d9231d.

## Problem and boundary

A tester can already review the report, but cannot omit recent sound-check
summaries without clearing them. Add one local choice, Include recent sound
checks. Its initial checked state preserves 0.19 behavior. Turning it off
previews and shares only the installed four-field build details. It changes
the current preview, never the recap store. Close/reopen resets the choice.
Canceling the system share sheet preserves both the choice and preview.

The report remains input-only context. No output, TV connection, safety or
protection is established. No audio, words, photo/TV/network details,
identifiers, timestamps, arbitrary notes or generic logs are admitted.

## Recovered research and evidence matrix

This is a bounded refinement of the researched
[0.19 report](private-support-report-2026-10-22.md),
[0.18 native share](share-build-details-2026-10-22.md), and
[temporary recaps](sound-check-recaps-2026-10-20.md). It adds no capture,
permission, service, upload, file, retention, dependency or physical API.
It does not require a new substantive AQSS subsystem investigation.

| Evidence | Decision and limits |
| --- | --- |
| Existing typed, five-row recap formatter and process-only store | Freeze one bounded snapshot when opening. Selection changes only which frozen text is displayed and handed to the existing share presenter. No deletion or live resnapshot on selection. |
| [Android native checkbox guide](https://developer.android.com/develop/ui/views/components/checkbox), checked October 22 | Use an accessible native CheckBox and its checked-change callback. Label the data choice, rather than implying a connected-device setting. |
| [Apple Toggle](https://developer.apple.com/documentation/swiftui/toggle) and [tint](https://developer.apple.com/documentation/swiftui/view/tint(_:)), checked October 22 | Bind the local Boolean to a native Toggle, keep the iOS 15 target and cyan accent, and preserve native accessibility state. Documentation alone does not qualify layout or native sheet behavior. |
| Existing Android ACTION_SEND and iPhone/iPad activity presenters | Pass exactly the current preview text after Share. No stream, URL, report file or recipient preselection. Existing Cancel/Copy and iPad anchor checks remain required. |
| Charter priorities: latency, battery, bounded memory, platform rules | Selection is synchronous over two precomputed bounded strings. No timers, polling, microphone work, persistent preference or new dependency. These structural properties do not establish measured performance. |

Alternatives: deleting recaps before sharing is destructive and needlessly
loses useful test context; arbitrary field editing expands the privacy
boundary; a new upload service is unnecessary. Combine the existing immutable
snapshot, a Boolean presentation filter and native explicit sharing. This
composition is the AQSS design choice; the platform sources establish only
their individual UI and sharing mechanisms. Physical handset behavior,
recipient handling and audio qualification remain unproven.

## Staged tests and failure behavior

1. Retain 0.19 production and versions. Add native Android/iPhone/iPad tests
   requiring the missing choice. Record the intended red before production.
2. Prove a deterministic snapshot contract red in both native packages.
   Build-only must equal installed metadata exactly, with no recap heading,
   row, stop reason or footer. Included mode retains the existing bounded
   formatter. Store changes and Clear must not mutate a prepared snapshot.
3. Add the smallest immutable snapshot and local native selection controls.
   A selection round trip must restore the same snapshot. Sharing and Cancel
   must preserve the chosen mode; reopening starts with the default mode.
4. Observe real native sharing with empty and actual completed recaps.
   Android's independent receiver must see exact selected text and no stream.
   iPhone/iPad Cancel must preserve a host fixture; Copy must match compiled
   installed metadata. The app and UI tests never access the clipboard.
5. Verify exclusion leaves real completed recaps available, and preserve
   Clear/restart, consent, photo, Voice, meter, lifecycle, core and unsigned
   archive regressions. Review preview and native-sheet screenshots.

Record exact source/tree, red/green jobs and final APK identity in the draft
PR. Keep signed iPhone distribution, physical handset compatibility,
recipient delivery and N2b–N5 unqualified. Production activation stays closed.
