# Insights sound checks — 0.21

## Scope and research

Make the existing process-only recent sound checks available directly from Insights. Reuse the existing five-row recap store and presentation; keep Audio trends and Session history separate and unqualified. No new capture, permission, storage, report fields or output authority.

The existing [recap research and limits](sound-check-recaps-2026-10-20.md) apply. Apple documents presenting a Boolean-controlled sheet and returning through dismissal; Android supports a custom view in an AlertDialog. This increment adds a second entry to those existing presentations, not a new capture subsystem.

- https://developer.apple.com/documentation/SwiftUI/View/sheet(isPresented:onDismiss:content:)
- https://developer.android.com/develop/ui/views/components/dialogs

## Test-first contract

Before production changes, native Android, iPhone and iPad checks must fail at the missing Recent sound checks entry in Insights. Then verify empty recaps without opening the meter, completed recaps made from actual native input, Close/Back returning to Insights, cross-route Clear, and empty recaps after process restart. Preserve the microphone cleanup guard in the original meter route and all 0.20 share, permission, lifecycle and photo regressions.

Recaps are snapshots of completed checks. An in-flight cleanup may finish after a snapshot. Clear affects the recap store; it does not settle microphone ownership or authorize capture. The existing bounded store tests remain the authority for those races.

## Evidence

Pending source-bound red and green native runs. Simulator and emulator checks do not qualify physical input or output, continuous coverage, sound safety, TV control or signed iPhone delivery.
