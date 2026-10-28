# iPhone and iPad manual output details

October 27, 2026. The owner requested continuing directly from each completed
phase into the next available phase while the Android test phone is away.
This is the next phone-independent implementation of the existing mobile
inventory review. Android's delivered 0.36 APK remains unchanged; iPhone/iPad
source becomes 0.37.0/build 1. Signing and real-device distribution remain
separate prerequisites.

## Scope

Sound → Output details → Refresh details reads one audio session current-route
description. It retains only a closed vocabulary for the first 16 output port
types and the reported count. A dated, immutable preview can be shared through
the existing native text-sharing presenter. The installed build envelope and
iOS/iPadOS version accompany it. Port names, UIDs, addresses and input ports
are never queried or retained by this reader.

This describes session metadata, not every available output, an active playback
connection or negotiated hardware format. The reader does not activate or
configure the session, request permission, create a player/engine, capture sound
or change a route. Sample rate, channels, latency and active-session state stay
unknown. The existing input lease must be available before the manual read.

The Foundation snapshot validates the build/version/clock/counts before producing
bounded text: 16 ports, 8,192 UTF-16 units and 16,384 UTF-8 bytes. Unrecognized
port types become Other output. A copied array and fixed labels prevent free-text
device identifiers or later edits from rewriting the report. Integer milliseconds
are formatted without far-future fractional-date rounding.

## Freshness and sharing

There is no read on entry, rotation, resume, notification or report handoff.
Refresh is explicit and main-actor synchronous. Backgrounding, Close, route or
interruption notices and media-service loss/reset clear the snapshot and return
Review to disabled. Notifications arrive on a secondary thread and are delivered
to this UI on the main queue. Notices invalidate; they do not refresh anything.
Back from review keeps the unchanged current snapshot. Native Cancel returns to
the same reviewed text. Copy must match that actual preview byte for byte.

The next software increment will attach this typed snapshot to the existing
optional setup worksheet, retaining its capture time separately from the notes'
review time. Clear notes and Remove output details will remain distinct choices.
That work starts after this increment's compiled and native UI checks.

## Primary-source check within the existing inventory review

- [currentRoute](https://developer.apple.com/documentation/avfaudio/avaudiosession/currentroute)
  describes the session's route ports; this is not Android-style available-device enumeration.
- [routeChangeNotification](https://developer.apple.com/documentation/avfaudio/avaudiosession/routechangenotification)
  documents route notices and secondary-thread delivery.
- [QA1631](https://developer.apple.com/library/archive/qa/qa1631/_index.html)
  explains why reading hardware timing/rate before activation can give incorrect
  values. This read-only increment leaves those values unknown and performs no activation.
- [Port](https://developer.apple.com/documentation/avfaudio/avaudiosession/port)
  supplies the fixed type constants. Unknown or newer types retain no raw strings.

The original mobile-backend Ready confirmation covers this existing inventory
follow-up; it does not qualify a playback backend. Tests-first and final source-
bound receipts belong to the draft PR. Simulator observations are not a report
from the owner's phone, physical output/retirement evidence or an iPhone installer.
N2b–N5, protection and signed iPhone distribution remain pending.
