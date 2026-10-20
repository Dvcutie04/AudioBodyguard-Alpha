# iPhone foreground microphone sound check

## Scope and research decision

October 19, 2026. This is the iPhone sensing-parity increment identified by the
[roadmap](development-roadmap.md) and the Android input record. It reuses the
existing foreground AVAudioEngine research and refreshes the primary API
constraints below. It adds a separate **Sound → Live sound check**; speech
recognition is not required. Android source and the delivered 0.3 APK are unchanged.

| Refreshed primary source | Consequence in this increment |
| --- | --- |
| [Apple audio tap callback](https://developer.apple.com/documentation/avfaudio/avaudionodetapblock) | The callback may run off the main thread. It borrows channel-zero Float32 samples, computes a summary and publishes into one slot; it never queues per-buffer UI tasks or retains the buffer. |
| [Float channel data](https://developer.apple.com/documentation/avfaudio/avaudiopcmbuffer/floatchanneldata) and [frame length](https://developer.apple.com/documentation/avfaudio/avaudiopcmbuffer/framelength) | Reject interleaved/non-Float32, empty, oversized, nonfinite or changed-format input. Bound work to 65,536 samples per callback and preserve actual frame length. |
| [Microphone permission](https://developer.apple.com/documentation/avfaudio/avaudiosession/requestrecordpermission(_:)) | Microphone consent is required. The iOS-15-compatible API is retained; a permission result never starts delayed recording. Another explicit Start is required. No speech authorization is requested by this tool. |
| [Audio interruptions](https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions) and [route changes](https://developer.apple.com/documentation/avfaudio/responding-to-audio-route-changes) | Stop on interruption or changed selected input identity; neither a positive interruption callback nor a returning route restarts capture. Engine failure and format changes also stop the check. |
| [Media-services reset](https://developer.apple.com/documentation/avfaudio/avaudiosession/mediaserviceswereresetnotification) | Discard this run's engine and require user action before constructing another. Reset/loss notifications do not imply recovery or qualification. |

AVAudioEngine matches the existing app and avoids an audio-file recorder or a
speech-recognition dependency. This is an input-only category with measurement
mode requested, not a claim of raw/unprocessed or calibrated microphone data.
The selected channel and actual sample rate are disclosed in optional details.

## Behavior and bounds

- Idle on opening. Permission grant, app activation and route recovery cannot
  automatically start a check. Stop/close/help/app inactivity invalidate pending
  permission callbacks and clear the graph immediately on the main thread.
- One engine per sound-check owner, one pending numeric summary, 60 display
  values, and at most 10 scheduled display updates per second. The display timer
  uses common run-loop modes so scrolling does not deliberately suspend it.
- The audio publisher uses a nonwaiting lock attempt; contention discards a
  summary rather than queuing or waiting. Consumer access/closure is serialized.
  Callback format failures latch when publication can acquire the slot; a
  contended error publication can also be discarded. No hard real-time bound or
  complete error-event history is claimed.
- Generation-bound input expires at 750 ms. Clock discontinuity and the
  30-second window latch the run off. Three seconds without fresh summaries
  stops the native check. Main-thread or OS scheduling can delay actual native
  stop; these are application deadlines, not measured physical cut guarantees.
- Raw framework buffers are never retained, modified, written, uploaded,
  transcribed or played by this tool. The OS owns those borrowed buffers; the
  app does not claim to erase OS microphone storage. No new permission category,
  background mode, telemetry, output command or persistent history is added.
- RMS is relative digital Float32 input, with zero represented as **quiet or
  blocked**, and values reaching/exceeding full scale identified. dBFS is not
  dBA/SPL, sound-source attribution, hearing exposure or a safety decision.
- Deactivation failure retains the process's sound-check owner and disables
  retry until the user completely closes the app. No cleanup callback, signature
  or test result is turned into output retirement evidence.

The existing optional Voice check remains separate. General multi-window audio
ownership, full speech-tool lifecycle parity and exact installed-device route
behavior require further review; this increment does not qualify them.

## Verification record

The test-only revision `99b93a138046d52d8ae6a48c19015a11e06bfc43`
[failed Swift compilation](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/39352811166)
because the new input level/window/mailbox types did not yet exist. This is the
recorded red phase. The implementation and its final checks are recorded in the
pull request and subsequent exact-revision workflow results; do not infer a
pass from the presence of this file.

Six Swift tests exercise digital arithmetic/zero/full scale, malformed and
bounded sample prefixes, stale input, clock rollback, stop/restart generations,
the 30-second deadline, and one-slot closure against late publication.
The focused iPhone Simulator workflow pre-establishes denied/granted microphone
permission, checks idle/help/return and denial, and attempts input/Stop/Home/
no-auto-restart/timeout. A host without input explicitly skips the latter
capture trial after asserting the unavailable input ends with an empty display.
Such a skip is not a capture pass. XCUITest screenshots/results are retained.

No signed iPhone install, physical microphone measurement, calibrated acoustic
capture, latency/battery measurement, TV control or automatic protection is
established. N2b–N5 remain pending. No user hardware, router change, account
credential, app-store submission or purchase is needed for this source/build work.
