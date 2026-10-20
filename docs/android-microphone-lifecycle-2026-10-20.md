# Shared Android microphone ownership and voice lifetime

October 20, 2026 UTC. This follows the Android 0.3 live-input/artwork increment.
The recorder's process owner previously covered only sound-meter instances;
Voice check did not participate. Speech cleanup also skipped destroy if cancel
threw and ignored cleanup failures. This increment closes those app-owned gaps
and produces a separate 0.4 test build. It does not qualify a TV output path.

## Research and implementation decision

| Primary source refreshed | Implementation consequence |
| --- | --- |
| [Android SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer) | Keep API calls on the main thread; use only the on-device factory after its API/support check. Always attempt destroy even if cancel throws. Any cleanup exception retains the shared reservation and blocks both tools until process exit. A returning API is not physical retirement proof. |
| [RecognitionListener](https://developer.android.com/reference/android/speech/RecognitionListener) | Callbacks are delivered on the main thread. Check the current run, foreground/focus, permission and elapsed deadline before accepting them. Provider RMS is optional and relative; it is not microphone PCM, calibrated dB SPL or verified audible output. |
| [Sharing audio input](https://developer.android.com/media/platform/sharing-audio-input) | Android may silence/change capture priority or route. Existing AudioRecord silencing/route checks remain. One shared process gate now prevents Voice check and sound-meter overlap without treating the gate as authority over other apps or the OS. |
| [Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle) | Stop on pause/destroy and additionally on window-focus loss. Returning to the app never starts capture; permissions also require another explicit Start. |

The existing on-device SpeechRecognizer and AudioRecord implementations are
retained. No server recognizer, model download, persistent audio, new permission,
background service or TV controller is introduced.

## App-owned guarantees and limits

- Synchronized process-wide gate, opaque per-run identity, stale/missing-release
  rejection and sticky cleanup failure. It survives Activity recreation and
  includes the meter's worker-thread cleanup plus Voice check's main-thread
  cleanup. No hardware/service call runs while holding this gate's monitor.
- The recorder retains its reservation through worker completion/release. A
  second tool cannot acquire it while a blocking read or teardown is unresolved.
  Closing an idle voice/photo Activity cannot release another tool's reservation.
- Voice callbacks and a 100 ms watchdog share a monotonic 30-second run policy.
  Clock rollback, foreground/focus loss or permission removal latch the run off.
  Old run callbacks cannot revive it or stop a newer run. A permission callback
  changes text only. It cannot create a recognizer or acquire the gate.
- RMS display clears after 750 ms without a new provider level, independently
  of optional speech callbacks. Provider silence/omitted RMS is not classified
  as a quiet room. Words are bounded to 500 Unicode code points, at most 2,000
  UTF-8 bytes, without cutting a valid surrogate pair.
- Destroy is attempted after cancel even when cancel fails. Any exception in
  those two calls blocks capture until a complete app force stop. Successful
  return still does not establish when a remote system service or microphone
  actually stopped; installed-device observation is pending.
- Application/OS scheduling can delay timers and stop operations. Provider
  buffering, speech accuracy, raw-audio erasure and real-time latency are not
  measured or guaranteed. No physical protection/coverage claim is added.

## Verification record

The tests-only revision `f037f0f1179a711733449048d3be60d101c243ab`
[failed Android compilation](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39358642323)
at the missing shared gate, voice run and text-bound types (job `118419720698`).

Nine new Kotlin cases exercise single ownership, stale/idle release, sticky
cleanup failure, simultaneous starts, old callback generations, exact elapsed
deadline, permission/inactivity, clock rollback and Unicode bounds. Red and green
hosted results are tied to exact revisions in the draft PR.

The Android 16 emulator workflow retains the prior denial/PCM/Stop/Home/rotation/
deadline/Back checks and adds notification-shade focus loss, stopped app-ops,
Voice check navigation/service attempt, clearing on Home and meter reuse after
voice close. Its recorded service result must distinguish an unavailable
on-device model from actual speech capture. No synthetic speech input is used.

The 0.4 live-input APK has the same separate test application ID and opening
poster as 0.3. It is an early test build; no Play Store publication, installed
VL68 Pro 0.4 result or N2b–N5 qualification is implied. iOS work is separately
tracked in draft PR #35 rather than included in this Android branch.
