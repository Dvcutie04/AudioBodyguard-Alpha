# Android live microphone sound check

## Scope and decision

David installed the existing Android preview on his VL68 Pro running Android 16
on October 15, 2026 and asked to continue toward an active build. This increment
adds a real foreground input test under **Sound → Live sound check**. It is an
increment toward sensing, not a qualified output adapter or active protection.
N2b–N5 remain pending. The existing iOS shell is unchanged; iPhone remains a
product target and needs its own native implementation and device tests.

The test reads mono PCM16 microphone input into one reusable 100 ms buffer,
computes RMS dBFS, peak fraction and full-scale-sample count, and discards raw
samples. It runs only after an explicit Start with microphone permission, for
at most 30 seconds while the Activity is resumed. No audio is written, uploaded,
transcribed or played. No sound command, volume change, output observation,
physical receipt, coverage status or endpoint authorization is produced.

## Refreshed primary research

Reviewed October 15, 2026:

| Source | Design consequence |
| --- | --- |
| [AudioRecord](https://developer.android.com/reference/android/media/AudioRecord) | Read bounded blocks away from the UI thread; handle negative/zero returns and release the owned recorder after the reader exits. A PCM read is input data, not evidence of speaker output. |
| [Sharing audio input](https://developer.android.com/media/platform/sharing-audio-input) | Capture may be silenced or rerouted. Register the recording callback before starting on API 29+, check the current capture configuration, and stop when blocked or when a known route changes. Missing or zero input cannot establish acoustic silence. |
| [MediaRecorder overview](https://developer.android.com/media/platform/mediarecorder) | Request UNPROCESSED only when the platform advertises it; otherwise request VOICE_RECOGNITION. Neither request establishes actual calibrated gain. |

The selected design uses AudioRecord instead of the existing SpeechRecognizer
meter. It works independently of an installed on-device speech recognizer and
does not collect words. A MediaRecorder file workflow would create avoidable
audio retention. A continuous background microphone service is outside this
increment and is not requested.

## Bounds, interruptions and uncertainty

- One worker, one capture buffer, one latest-summary slot and 60 display values.
  The UI consumes at most ten summaries a second. No per-buffer UI work queue.
- Lifecycle pause, manual Stop, permission loss, platform silencing, route
  change, recorder failure and the time limit close that capture. Restart
  requires another explicit Start. A new capture waits for prior cleanup.
- A generation-bound display window rejects old runs, future or rolled-back
  receive times, summaries older than 750 ms, and input at the 30-second limit.
  These are local receive times, not calibrated microphone acquisition times.
- The graph and numeric value clear on stop and stale input. Zero samples show
  **quiet or blocked**; they do not label the room quiet or the sound safe.
- PCM digital full scale is 32768. RMS uses only the prefix actually read;
  `-32768` is widened before absolute-value arithmetic. dBFS is not dBA/dB SPL,
  hearing exposure, syllable detection or evidence of effective protection.
- No new permission, network operation, background service, telemetry or
  retained audio history is introduced. Android's microphone permission already
  exists for the optional voice tool.

## Packaging and manual phone trial

`gradle -p native/android :app:assembleLiveInput` creates a separate debug-signed
test app with ID `com.aqss.bodyguard.prototype.liveinput` and label **Audio
Bodyguard Live Test**. It can coexist with the earlier preview, whose ephemeral
CI signing key is not available for signing an update. The normal debug and
release variants retain the original application ID.

On the VL68 Pro: open Sound → Live sound check; deny permission and confirm no
capture; allow permission and tap Start; speak normally and observe the bars;
tap Stop; try Home, Back, screen lock, microphone privacy toggle and route
changes. Each interruption must clear live input and require another Start.
Confirm the automatic 30-second stop. Do not produce loud test sounds.

Software and emulator checks establish only their recorded behavior. Actual
phone capture, latency, battery, accessibility and acoustic calibration require
independent observations. No installed-device trial has yet been recorded for
this new feature.

## Verification

- The five new PCM/window tests first failed compilation because their
  implementations were absent. After implementation, all **23 Kotlin tests**
  passed, including the existing contracts and new arithmetic/freshness cases.
- The local Python suite passed **1,879 tests plus 19 subtests**. The **41**
  focused input/repository boundary checks passed again after compatibility
  edits. These counts overlap and must not be added.
- Java 17 / Gradle 8.13 / API 36 built `:app:assembleLiveInput` and passed
  `:app:lintLiveInput`: **0 errors, 139 nonfatal warnings**. Warnings include
  existing platform-view conventions and English UI strings. Existing guarded
  Insets access was made explicit for lint; platform Back handlers and the
  intentional platform-only ImageView are documented with narrow annotations.
- [Hosted CI for the code revision](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/38834770814)
  passed Python, Android, Swift/iOS simulator compilation and the scripted C lab.
- The first Android 16 UI run installed and launched the new Activity, then
  stopped at a test-runner case mismatch: the platform's **DON’T ALLOW** button
  was uppercase. A second run encountered a missing UI hierarchy at cold launch.
  The runner now matches labels without case sensitivity and uses four bounded
  hierarchy attempts, refusing to infer any result from missing or stale XML.
  The [Android 16 lifecycle workflow](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/workflows/android-live-input.yml)
  retains the current result and UI evidence; inspect the run for the runtime
  result rather than inferring it from compilation. A local software-rendered
  emulator did not finish Android service startup and provides no UI pass.
- The deliverable is `AudioBodyguard-Live-Input-Test-0.2.apk`, version code **2**,
  target API **36**, min API **26**, with ARM64, ARMv7, x86 and x86-64 libraries.
  Its APK v2 signature verifies. SHA-256:
  `8542c251bdbc99dd38fb3bb9ee6ae34da2d728220194616d80f59db86eb23ced`.

The VL68 Pro microphone trial, calibrated acoustic measurements, resource
measurements and physical protection qualification remain unreported.
