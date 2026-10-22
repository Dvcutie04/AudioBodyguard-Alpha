# Photo readiness notice — October 21, 2026

Version 0.13 follows the one-read ownership policy in 0.12. A busy screen can
currently keep saying that the earlier photo is finishing after that work has
returned. The next interaction should reflect actual availability without
requiring a guessing tap. Import/recognition still requires the user's action.

## Research and selected design

| Primary source | Application |
| --- | --- |
| [Android activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle) | Pair observation registration on resume with detachment on pause; query again after returning because completion can occur while detached. |
| [Apple NSLock](https://developer.apple.com/documentation/foundation/nslock) | Keep admission/release state under the existing lock. Copy observers while locked, then unlock on the same thread before invoking callbacks. |
| [Swift extended lifetime](https://docs.swift.org/latest/documentation/swift/withextendedlifetime(_:_:)-59dz3) | Preserve 0.12's independent read lifetime; a notification is produced by its real release, not by closing or expiring its view. |

The design combines a release notification, a fresh availability query on the
UI thread, and lifecycle-scoped observation. Polling would add wakeups and
latency. Automatically reopening the picker would introduce an unsolicited
operation. Trusting a queued notification as an availability snapshot would
miss a newer reader. A notification is only a signal to recheck the slot.

Only an accepted owner release emits a signal. A foreign or repeated release
does not. Callbacks execute outside the slot lock so a view may query or detach
without blocking cleanup on a lock it needs itself. Android isolates ordinary
observer exceptions so a broken view cannot prevent another view's notice or
turn a completed cleanup into an unhandled worker failure. Swift subscriptions
detach explicitly and on deinitialization; Android detaches on pause/destroy.

Both screens update only when they were waiting for work and the current slot
is free. Clear, a new selection and an accepted result stop that waiting state,
so an old signal cannot overwrite a newer result. Resume/active-scene handling
queries current availability after registering, covering missed releases.

The UI says “The previous photo has finished. Choose a photo.” No picker is
opened and no read is submitted by the notice. Actual admission still acquires
the existing unique lease. A framework operation that never returns continues
to own its capacity. The 30-second result window and physical-control gates
remain separate; a ready notice does not verify a TV connection.

Latency and battery: one event per real owner release, dispatched to the main
queue, plus one query on resume. No extra timer, wakeup loop or dependency.
Memory: one small callback per attached view, detached with its lifecycle. This
is an implementation policy, not a handset memory, battery or latency result.

## Verification

The native regression was published at
`d1fdb0aae90ce2742776d4e4c8cf7e78f44a33fd` before changing production behavior.
Android run `39701384417`, job `119571171008`, compiled successfully and then
failed with `Missing camera review text: The previous photo has finished.
Choose a photo.` The original read had returned; the old busy message remained.
The failure is an observed native UI result, not a missing API or compiler error.
Notification API scaffolds and new behavioral cases were then published at
`15bd560b847c79b1d425ea187891864386dee955` before implementing notification
delivery or wiring either screen to it.

At that API-only checkpoint, Android run `39702152602`, job `119573677154`,
ran **80 tests with the four new notification cases failing**. Swift run
`39702152632`, job `119573677242`, ran **81 tests with seven assertion failures
across the three new notification cases**. Existing ownership and photo-window
cases passed. These were executable assertions after successful compilation.

The initial native regression requires readiness after the original delayed
provider job actually terminates, while retaining all 0.12 overlap checks. It
then clears a second blocked import, covers it with the real setup-guide
Activity, releases that work while photo setup is paused, and requires ready
on return. Picker counts must stay unchanged at both transitions; a fresh ML
Kit read, unknown cleared hints and committed native frames remain required.

Observer tests separately cover accepted/foreign/duplicate owner returns,
detached views, callbacks outside the lock and Android observer failure
isolation. Existing ownership and elapsed-window cases remain intact.
Final run IDs, runtime failures, artifact hash and exact source identity are
recorded in draft PR #45. Android forced-provider behavior and iPhone's real
Photos/Vision walkthrough remain distinct evidence. Handset resource behavior,
physical audio, TV pairing and signed iPhone distribution are not qualified by
these automated tests.
