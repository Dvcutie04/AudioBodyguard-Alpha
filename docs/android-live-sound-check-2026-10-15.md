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

Reviewed October 15, 2026; verification updated October 16, 2026:

| Source | Design consequence |
| --- | --- |
| [AudioRecord](https://developer.android.com/reference/android/media/AudioRecord) | Read bounded blocks away from the UI thread; handle negative/zero returns and release the owned recorder after the reader exits. A PCM read is input data, not evidence of speaker output. |
| [Sharing audio input](https://developer.android.com/media/platform/sharing-audio-input) | Capture may be silenced or rerouted. Register the recording callback before starting on API 29+, check the current capture configuration, and stop when blocked or when a known route changes. Missing or zero input cannot establish acoustic silence. |
| [MediaRecorder overview](https://developer.android.com/media/platform/mediarecorder) | Request UNPROCESSED only when the platform advertises it; otherwise request VOICE_RECOGNITION. Neither request establishes actual calibrated gain. |
| [UiAutomation](https://developer.android.com/reference/android/app/UiAutomation) | A test-only observer can snapshot the active window directly. The older idle-waiting dump command cannot reliably observe a continuously changing live meter. |

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
  requires another explicit Start. A process-wide owner makes a new capture
  wait for prior cleanup even across Activity recreation. Failed native release
  keeps that owner closed until the app process is force-stopped.
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

## Reported VL68 Pro trial — October 17, 2026

David reported that Home navigation and locking/unlocking the Android 16
VL68 Pro stopped a user-started capture. Three user-provided camera videos
show the installed app's Live sound check screen:

| Video (SHA-256 prefix) | Visual observation |
| --- | --- |
| `CameraRecording-BBE9E380-7DB9-4FCF-816F-7A8A0431532E.mp4` (`2804ea6a0bcf`), 16.67 s | Start with no displayed input, followed by moving bars and readings near -44 dBFS. |
| `CameraRecording-D4C38587-91DC-4FF6-B4A0-BF264C2254B4.mp4` (`6d5c9d59efe7`), 11.10 s | Start near -90 dBFS and continue near -44 dBFS; no clear return to the initial level. |
| `CameraRecording-F4E1962D-A87E-4513-90E4-966F82DA8B2C.mp4` (`b1ecd7f95053`), 20.00 s | Bars remain active, with the visible reading falling from roughly -44 to -48 dBFS to about -52 to -53 dBFS near 13 s. |

The videos have no audio stream and do not show TV mute state or the TV
speakers. This is real handset evidence that the foreground display received
microphone input and responded to a change. Attribution to the TV source,
acoustic calibration, automatic protection, native output ownership and
verified physical control remain unestablished. The Home/lock behavior is a
user report rather than a filmed lifecycle trial. The original manual-trial
section above is a protocol; it is not a claim that every listed case passed.

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
- [Hosted CI for the code revision](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/38837915574)
  passed Python, Android, Swift/iOS simulator compilation and the scripted C lab.
- The [Android 16 live-input run](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/38837915714)
  passed at source commit `65776630cf3281b12e543f38c6b5fb5286b559ce`.
  It observed permission denial, PCM input, manual Stop, background stop,
  rotation stop, no automatic restart, the 30-second time limit, Back navigation
  and no fatal crash. The run retains the actual UI hierarchies, screenshots,
  AppOps observation and logs. Emulator PCM is not a physical-microphone trial.
- Earlier UI-run failures were test observer defects: permission-label case,
  missing cold-launch roots, UiAutomator's idle wait during a changing meter,
  and a permission-dialog coordinate tap. The final runner uses a separate
  test-only UiAutomation process, bounded root retrieval, case-insensitive
  labels and actual accessibility click actions with shell-safe arguments.
  Missing XML fails the test. The observer is not included in the user APK.
  A local software-rendered emulator did not finish Android service startup
  and provides no UI pass.
- The deliverable is `AudioBodyguard-Live-Input-Test-0.2.apk`, version code **2**,
  target API **36**, min API **26**, with ARM64, ARMv7, x86 and x86-64 libraries.
  Its APK v2 signature verifies. SHA-256:
  `d92f1b0f233eed05736df005024575cfc10c87d11c23569bb30f7aca3da83ee3`.

The bounded visual VL68 Pro microphone trial is recorded above. Calibrated
acoustic measurements, resource measurements and physical protection
qualification remain unreported.
