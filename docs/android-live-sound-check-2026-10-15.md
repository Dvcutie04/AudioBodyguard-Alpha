# Android live microphone sound check

## Scope and decision

David installed the existing Android preview on his VL68 Pro running Android 16
on October 15, 2026 and asked to continue toward an active build. This increment
adds a real foreground input test under **Sound → Live sound check**. It is an
increment toward sensing, not a qualified output adapter or active protection.
N2b–N5 remain pending. The existing iOS shell is unchanged; iPhone remains a
product target and needs its own native implementation and device tests.

The test reads mono PCM16 microphone input into one reusable 100 ms buffer,
computes RMS dBFS, peak fraction and clipped-sample count, and discards raw
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

Results will be recorded after the focused PCM/window tests, Android builds
and available lifecycle/UI checks complete.
