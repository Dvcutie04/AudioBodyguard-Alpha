# Output inventory freshness — October 25, 2026

The owner is testing 0.32.1 and authorized independent work on 0.32.2. This
increment follows the existing phone-output preflight and its approved research
scope. A displayed inventory in 0.32.1 clears on pause, but can remain after an
output is added or removed while the screen stays open. It is labelled as a
snapshot; this repair additionally withdraws it when a relevant notice arrives.

## Primary-source refresh and decision

Official references checked October 25, 2026:

- [AudioManager registration](https://developer.android.com/reference/android/media/AudioManager#registerAudioDeviceCallback(android.media.AudioDeviceCallback,%20android.os.Handler))
  provides device-change notifications on a chosen Handler. Use the main thread
  to serialize invalidation with the existing synchronous manual refresh.
- [AudioDeviceCallback](https://developer.android.com/reference/android/media/AudioDeviceCallback)
  reports added and removed audio devices. Inspect only sink/output notices;
  neither callback reports an active playback route or physical output.
- [AudioManager unregistration](https://developer.android.com/reference/android/media/AudioManager#unregisterAudioDeviceCallback(android.media.AudioDeviceCallback))
  removes the previously registered callback. Retire its identity before cleanup
  so a queued older notice cannot affect a later foreground visit.

Decision: register only while this screen is resumed. On a relevant notice,
remove the displayed rows and show **Output list needs a fresh check. Tap
Refresh outputs.** Never query automatically or treat a callback as connection
verification. Empty/input-only notices leave a displayed output list alone.
The initial registration notification may conservatively invalidate a recently
read snapshot; the wording therefore does not claim a physical change occurred.
Notices larger than the existing 16-device bound invalidate conservatively
without traversal. No device descriptors are retained by the app.

No polling, stream, microphone session, focus request, route change, new
permission, export or persistence is needed. Callback delivery is asynchronous
and does not make snapshots continuously current or atomic. Registration failure
keeps manual reads available with an explicit unavailable-notices footer. A
weak owner reference prevents an unsuccessful framework cleanup from retaining
the Activity. Background/resume/Back clearing remains in force.

## Test-first record and limits

The separate test observer delivers synthetic add/remove callbacks using actual
emulator AudioDeviceInfo objects. It checks displayed-row invalidation, explicit
Refresh, no automatic reread, input-only/empty notices, pause/resume, and rejection
of retired callbacks after returning or closing. The app uses the actual native
inventory, lifecycle, registration API and rendered UI. This does not simulate
a physical peripheral disconnect, verify real OS notice delivery for a handset,
identify an active route or establish physical latency. Observer code is excluded
from the delivered APK. Actual red/green run identities belong to the draft PR.

0.32.2 is an Android inventory repair; the Samsung guidance remains in the
candidate and iPhone source stays at 0.32.1. Installed-phone compatibility,
actual peripheral notification behavior, Samsung pairing, signed iPhone delivery
and N2b–N5 remain pending.
