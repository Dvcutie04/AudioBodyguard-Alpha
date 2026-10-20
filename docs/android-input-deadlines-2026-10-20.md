# Android sound-check deadline closure

October 20, 2026. This follows the 0.5 input-recap candidate and repairs a
software-policy difference from the existing iPhone sound-check window. It is
an input display/lifecycle increment, not an output adapter or a qualification
of the installed phone. N2b still awaits actual host/route/capture inventory.

## Finding and source basis

Code review found that Android's window cleared its reading at expiry or some
backward clock observations without making the run inactive. A later callback
with a pre-expiry timestamp could then restore the reading. A backward display
tick after the last sample but before the previous tick could also leave the
old reading visible. No clock failure on David's handset has been observed.

[Android SystemClock](https://developer.android.com/reference/android/os/SystemClock)
documents `elapsedRealtime()` as monotonic time since boot, including deep
sleep; the app continues to use it rather than wall time. Rejecting an invalid
sequence is a defensive application policy. It is not evidence that this clock
normally moves backward. The existing [input lifecycle research](android-microphone-lifecycle-2026-10-20.md)
already covers explicit Start, foreground capture, process ownership and
asynchronous cleanup. No new OS API, permission or background behavior is added.

## Behavior

- Every current-run offer and display poll checks against the most recently
  accepted clock observation, including polls before the first sample and
  offers whose sample timestamps are rejected.
- The exact 30,000 ms boundary or a backward clock observation clears the
  reading and closes that run. Later samples cannot revive it. Another explicit
  Start creates a new generation. Invalid Start first discards the previous
  presentation run; generation exhaustion refuses to wrap.
- An old generation is rejected before its clock is considered, so it cannot
  close a newer run. A 750 ms stale reading clears the display but allows a
  genuinely fresh sample within the same still-valid run. Missing input remains
  unknown, not acoustic silence.
- The Activity consumes the window's latched end reason, requests recorder
  shutdown, and clears the graph/reading. Its existing worker cleanup and shared
  microphone reservation remain the authority for allowing another capture.
  Recaps retain the existing typed time-limit or invalid-input end reason.

The software watchdog and framework calls are scheduled work. They do not
establish an exact physical microphone cutoff, complete buffer erasure, sound
safety, continuous coverage, or TV control. Clearing presentation state cannot
release a microphone lease or unlock a cleanup failure. The iPhone source and
its existing latch are unchanged.

## Verification

Five additional Kotlin tests use public behavior: deadline revival after an
earlier timestamp, rollback between display ticks, rollback before any sample,
invalid restart, and stale-generation isolation with freshness recovery near
the largest representable clock value. The tests-only revision is
`dd5a51f580d42353829da69f42061375d373adcf`; its
[hosted CI run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39515780588)
is retained separately from the corrected build.

The corrected candidate uses version 0.6 with the prior live-input test package
and approved Silicon Workforce poster. The Android workflow retains its actual
permission, input, Stop, focus/Home, rotation, elapsed-limit, recap, process
restart and app-ops observations. Exact green test results, source revision,
APK signature and byte identity belong to the draft PR after verification.
Installed-phone timing, speech capture and physical output remain pending.
