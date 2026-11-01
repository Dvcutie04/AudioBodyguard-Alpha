# Two-phone output research — October 24, 2026

The owner confirmed readiness for the new research with **Ready**, after the
roadmap's 6 Astra Max switch/confirmation request. Available equipment is one
Android and one iPhone, with no computer in the reported setup. Android is the
first implementation candidate because test APK delivery already works.
iPhone remains an equal product target; signed iPhone installation is pending.

## Decision for 0.32

Build an Android **output inventory preflight** before a real playback adapter.
The screen reads current phone model, OS/API level, available output kinds and
their advertised sample rates, channel counts and encodings. Refresh is an
explicit action. Display collections and strings are bounded and capped;
unreadable, omitted or truncated data must retain their uncertainty rather
than becoming an invented complete capability list.

At most 16 devices and 16 values from each capability list are displayed, with
the observed total/count and truncation visible. Framework getters can return
full arrays; only traversal and rendered data are bounded by this presentation.
Unknown encoding numbers remain uninterpreted metadata and are never used to
select a format.

The snapshot contains no audio-device IDs, addresses or product names. It is
not exported or persisted. Opening or refreshing this screen creates no
player, microphone session, audio-focus request or route/volume change.
Availability does not identify an active or verified playback route. Negotiated
format, physical output and capture calibration remain unknown. Empty advertised
arrays are not evidence of unsupported audio: Android documents them as arbitrary
supported values. Present them as not individually advertised, while keeping
the actual negotiated format unknown.

This supplies actual phone observations for the
[N2b inventory](n2b-lab-qualification-record.md). It does not complete N2b or
authorize a physical trial. Source-bound tests and artifact identity belong to
the implementation PR; this research contains no handset measurements.

## Primary-source matrix

Sources retrieved October 24, 2026. Platform documentation supports API or app
semantics; it supplies no AQSS physical performance result.

| Source | Supported fact and implementation consequence | Limit |
| --- | --- | --- |
| [Android AudioManager](https://developer.android.com/reference/android/media/AudioManager#getDevices(int)) | `getDevices(GET_DEVICES_OUTPUTS)` lists currently connected sink devices matching the query. Use it for a bounded manual inventory. | Connected/available is not selected, routed or independently observed. |
| [Android AudioRouting](https://developer.android.com/reference/android/media/AudioRouting) | `getRoutedDevices()` is API 36 and returns an empty list when the stream is not playing; legacy `getRoutedDevice()` returns null then. `getPreferredDevice()` need not match actual routing. | A stopped stream cannot supply the actual output route. A preference or routing callback is not an acoustic observation or atomic fence. The preflight creates no stream to probe this. |
| [Android AudioDeviceInfo](https://developer.android.com/reference/android/media/AudioDeviceInfo) | Its sample-rate, channel-count and encoding arrays advertise capabilities. Empty arrays indicate arbitrary supported values. Ignore unrecognized encoding entries for forward compatibility. | Lists are not a negotiated configuration, proof that all listed properties combine, exact physical layout, calibration or measured performance. |
| [Android AudioTrack](https://developer.android.com/reference/android/media/AudioTrack) | Streaming `stop()` allows queued data to finish. The documented immediate-stop sequence uses `pause()` then `flush()` to discard queued stream data. `getMinBufferSize()` is an estimate that does not consider the eventual route/sink. | Queue discard is scoped to the API queue, not proof of physical silence. The estimate is not negotiated hardware configuration or a latency bound. |
| [Android audio focus](https://developer.android.com/media/optimize/audio-focus) | Playback requests and losses interact with other apps; version-dependent system behavior includes fading or muting existing playback. | An inventory query must not acquire focus. Later playback needs explicit focus/admission/loss handling and cannot assume exclusive physical output. |
| [Android audio latency guide](https://developer.android.com/ndk/guides/audio/audio-latency) | Input/output clocks and callbacks need not synchronize; actual sample rates can differ from nominal rates and the system monotonic clock. Mobile acoustic processing can add latency. | Do not subtract unrelated phone timestamps or derive sensor-to-response latency from nominal rate or buffer size. |
| [AOSP audio latency measurement](https://source.android.com/docs/core/audio/latency/measure) | The documented method synchronizes full-duplex loopback and correlates a recognizable signal. Built-in speaker/microphone loopback can work without additional hardware. | Its result is round-trip latency; it does not independently partition output and input delay, calibrate acoustic levels or qualify AQSS. |
| [Android recording overview](https://developer.android.com/media/platform/mediarecorder) | Most sources process input. Query declared `UNPROCESSED` support; requesting that source without support gives no unprocessed guarantee. The documented `VOICE_RECOGNITION` fallback avoids AGC/noise suppression. | Source choice alone does not calibrate a microphone or validate its actual path. 0.32 adds no capture. |
| [Apple Voice Memos, iOS 26 guide](https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/26/ios/26), [microphone modes](https://support.apple.com/en-us/101993) | Voice Memos offers background filtering and model-dependent mono/stereo/spatial modes. Multiple microphones can contribute. iCloud sync can copy recordings when enabled; recording names can use location. Same-iPhone playback in another app stops recording. | These sources do not establish raw, AGC-free or calibrated capture. Options depend on actual device, OS and app settings, which remain unrecorded. |
| [NIST TN1297, uncertainty reporting](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-7-reporting-uncertainty) | Record uncertainty components and how they were evaluated when reporting a measurement result. | Historical metrology guidance supplies no uncertainty value for these phones. |

## Observer and later playback obligations

The second phone may later be an optional qualitative witness for a recognizable
app-owned signal or an unexpected audible tail. Stock Voice Memos avoids an
AQSS installation requirement, but its processing, microphone mode, placement,
interruptions and account/retention settings must be recorded. No cloud-backed
recording or recording upload is required by this plan. Missing or unsuitable
capture stays missing; it is not replaced with simulated proof.

A relative interval inside one recording is scoped to its acquisition and
processing. A marker emitted by the tested output cannot independently establish
command-to-output delay. Qualitative capture cannot prove silence beyond its
sensitivity/window, acoustic dB/SPL, containment, TV control, continuous protection
or the complete under-200-ms aspiration.

Before implementing the later owned-output experiment, finish the actual
phone/route/observer inventory and the exact backend review. Preserve these
separate obligations:

- Explicit user Start, a bounded known signal, consent and test volume, without
  automatic replay or control of other apps or the TV.
- Focus and foreground/lifecycle admission, route changes and callbacks,
  disconnect/error invalidation, and cleanup ownership through actual return.
- Backend-specific partial-write accounting, zero/would-block behavior,
  accepted prefixes and immutable unsent suffixes; no retry after a hold.
- Distinct stop/pause/flush/release semantics and residual-buffer evidence.
  API completion is not proof of immediate physical silence.
- Bounded trace reservation before native submission, scoped timestamps,
  crash/restart uncertainty and retained unresolved work.
- Independent acquisition, clock mapping, calibration, detector/window and
  uncertainty review before any quantitative physical claim.

These are research and implementation debt for the selected playback backend,
not completed behavior in 0.32. Exact API selection and tests belong to that
later increment. N2b–N5, production execution and successor readiness remain
pending.
